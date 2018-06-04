#!/usr/bin/python

#
# GPIO Remote Control
# Venema, S.R.G.
# 2018-05-04
#
# GPIO remote control enables GPIO input for buttons and encoders.
# It comes with optional rudimentary debouncing.
#
# Only one mode group is supported at the moment!
#

# Button presses are NOT asynchronous!! i.e. wait until a button press is handled before the next button can be handled.
# TODO: Consider making them asynchronous, or at least the update lib (long) / volume (short) buttons

# printer -> syslog adds considerable latency!  ?
# (and?) Or.. is it the MQ send() ?

# TODO:
# 
# 

import sys						# path
import os						# 
from time import sleep
from operator import itemgetter

#from time import clock			# cpu time, not easily relateable to ms.
from datetime import datetime
from logging import getLogger	# logger

import gobject					# main loop
from dbus.mainloop.glib import DBusGMainLoop

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController
from hu_msg import parse_message
from hu_gpio import GpioController
from hu_datastruct import Modes

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "GPIO Remote Control"
BANNER = "GPIO Controller Daemon"
LOG_TAG = 'GPIO'
LOGGER_NAME = 'gpio'

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_LOG_LEVEL = LL_INFO
SUBSCRIPTIONS = ['/mode/']
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560

#DELAY = 0.005
DELAY = 0.01
#LONG_PRESS = 0.05

# global variables
logger = None
args = None
messaging = None
gpio = None

# configuration
cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ
cfg_gpio = None		# GPIO setup

# MQ paths
mq_path_list = []
mq_path_func = {}

modes = Modes()

function_map = {}
function_map['SOURCE_NEXT'] = { 'zmq_path':'/source/next', 'zmq_command':'PUT' }
function_map['SOURCE_PREV'] = { 'zmq_path':'/source/prev', 'zmq_command':'PUT' }
function_map['SOURCE_PRI_NEXT'] = { 'zmq_path':'/source/next_primary', 'zmq_command':'PUT' }
function_map['SOURCE_PRI_PREV'] = { 'zmq_path':'/source/prev_primary', 'zmq_command':'PUT' }
function_map['SOURCE_CHECK'] = { 'zmq_path':'/source/check', 'zmq_command':'PUT' }
function_map['PLAYER_PAUSE'] = { 'zmq_path':'/player/pause', 'zmq_command':'PUT' }
function_map['PLAYER_RANDOM'] = { 'zmq_path':'/player/random', 'zmq_command':'PUT' }
function_map['PLAYER_NEXT'] = { 'zmq_path':'/player/next', 'zmq_command':'PUT' }
function_map['PLAYER_PREV'] = { 'zmq_path':'/player/prev', 'zmq_command':'PUT' }
function_map['PLAYER_FOLDER_NEXT'] = { 'zmq_path':'/player/next_folder', 'zmq_command':'PUT' }
function_map['PLAYER_FOLDER_PREV'] = { 'zmq_path':'/player/prev_folder', 'zmq_command':'PUT' }
function_map['VOLUME_INC'] = { 'zmq_path':'/volume/master/increase', 'zmq_command':'PUT' }
function_map['VOLUME_DEC'] = { 'zmq_path':'/volume/master/decrease', 'zmq_command':'PUT' }
function_map['VOLUME_ATT'] = { 'zmq_path':'/volume/att', 'zmq_command':'PUT' }
function_map['VOLUME_MUTE'] = { 'zmq_path':'/volume/mute', 'zmq_command':'PUT' }
function_map['SYSTEM_SHUTDOWN'] = { 'zmq_path':'/system/shutdown', 'zmq_command':'PUT' }

'''
pins_config = 
	{ "23": {
		dev_name
		dev_type
		functions: [ {
			fnc_name
			function
			mode							= valid for this mode only
			fnc_short_press/fnc_long_press 	= list of
			}
		]
		has_short
		has_long
		has_multi
		},
	  "26": { .. }
	 }



'''


# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# ********************************************************************************
# Load configuration
#
def load_cfg_main():
	""" load main configuration """
	config = configuration_load(LOGGER_NAME,args.config)
	return config

def load_cfg_zmq():
	""" load zeromq configuration """	
	if not 'zeromq' in cfg_main:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		#cfg_main["zeromq"] = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB } }
		config = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB }
		return config
	else:
		config = {}
		# Get portnumbers from either the config, or default value
		if 'port_publisher' in cfg_main['zeromq']:
			config['port_publisher'] = cfg_main['zeromq']['port_publisher']
		else:
			config['port_publisher'] = DEFAULT_PORT_PUB
		
		if 'port_subscriber' in cfg_main['zeromq']:
			config['port_subscriber'] = cfg_main['zeromq']['port_subscriber']		
		else:
			config['port_subscriber'] = DEFAULT_PORT_SUB
			
		return config

def load_cfg_daemon():
	""" load daemon configuration """
	if 'daemons' not in cfg_main:
		return
	else:
		for daemon in cfg_main['daemons']:
			if 'script' in daemon and daemon['script'] == os.path.basename(__file__):
				return daemon

def load_cfg_gpio():
	""" load specified GPIO configuration """	
	if 'directories' not in cfg_main or 'daemon-config' not in cfg_main['directories'] or 'config' not in cfg_daemon:
		return
	else:		
		config_dir = cfg_main['directories']['daemon-config']
		# TODO
		config_dir = "/mnt/PIHU_CONFIG/"	# fix!
		config_file = cfg_daemon['config']
		
		gpio_config_file = os.path.join(config_dir,config_file)
	
	# load gpio configuration
	if os.path.exists(gpio_config_file):
		config = configuration_load(LOGGER_NAME,gpio_config_file)
		return config
	else:
		print "ERROR: not found: {0}".format(gpio_config_file)
		return


# ********************************************************************************
# MQ functions
#

def handle_mq(path):
	""" tbd.
		can we move this to hu_msg ?
	"""
	def decorator(fn):
		global mq_path_list
		global mq_path_func
		mq_path_list.append(path)
		mq_path_func[path] = fn
		def decorated(*args,**kwargs):
			print "Hello from handl_mq decorator, your path is: {0}".format(path)
			return fn(*args,**kwargs)
		return decorated
	return decorator


@handle_mq('/mode/list')
def testje_get_list(command, args=None, data=None):
	
	global modes
	
	# NO PARAMS
	#printer("All Modes: {0}".format(modes.active_modes()))
	print "Doing /mode/list..."
	#return struct_data(modes.active_modes())
	return struct_data("Useful data")

def idle_message_receiver():		
	
	print "DEBUG: idle_msg_receiver() -- New Style"

	rawmsg = messaging.poll(timeout=500)				#None=Blocking
	if rawmsg:
		printer("Received message: {0}".format(rawmsg))	#TODO: debug
		parsed_msg = parse_message(rawmsg)
				
		mq_path = "/" + "/".join(path)
		if mq_path in mq_path_list:
			ret = mq_path_func[mq_path]( command=parsed_msg['cmd'], args=parsed_msg['args'], data=parsed_msg['data'] )

		if parsed_msg['resp_path']:
			#print "DEBUG: Resp Path present.. returing message.. data={0}".format(retval)
			messaging.publish_command(parsed_msg['resp_path'],'DATA',ret)
		
	return True # Important! Returning true re-enables idle routine.
	
		
def idle_message_receiver0():
	#print "DEBUG: idle_msg_receiver()"
	
	def dispatcher(path, command, arguments, data):
		handler_function = 'handle_path_' + path[0]
		if handler_function in globals():
			ret = globals()[handler_function](path, command, arguments, data)
			return ret
		else:
			print("No handler for: {0}".format(handler_function))
			return None
			
		
	rawmsg = messaging.poll(timeout=500)				#None=Blocking
	if rawmsg:
		printer("Received message: {0}".format(rawmsg))	#TODO: debug
		parsed_msg = parse_message(rawmsg)
		
		# send message to dispatcher for handling	
		retval = dispatcher(parsed_msg['path'],parsed_msg['cmd'],parsed_msg['args'],parsed_msg['data'])

		if parsed_msg['resp_path']:
			#print "DEBUG: Resp Path present.. returing message.. data={0}".format(retval)
			messaging.publish_command(parsed_msg['resp_path'],'DATA',retval)
		
	return True # Important! Returning true re-enables idle routine.

def handle_path_mode(path,cmd,params,data):

	base_path = 'mode'
	# remove base path
	del path[0]

	def get_active(params):
		
		global modes
		
		# NO PARAMS
		
		#arg_defs = app_commands[0]['params']
		#ret = validate_args(arg_defs,params,app_commands[0]['params_repeat'])		
		#if ret is not None and ret is not False:	

		printer("Active Modes: {0}".format(modes.active_modes()))
		
		return struct_data(modes.active_modes())
		
	def put_set(params):
		print "A MODE WAS SET"

	def put_unset(params):
		print "A MODE WAS UNSET"

	if path:
		function_to_call = cmd + '_' + '_'.join(path)
	else:
		# called without sub-paths
		function_to_call = cmd + '_' + base_path

	ret = None
	if function_to_call in locals():
		ret = locals()[function_to_call](params)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret),level=LL_DEBUG)
	else:
		printer('Function {0} does not exist'.format(function_to_call))

	return ret
	
# ********************************************************************************
# GPIO Callback
#
def cb_gpio_function(code):
	#print "CALL: {0}".format(function)
	print "EXECUTE: {0}".format(code)
	if code in function_map:
		zmq_path = function_map[code]['zmq_path']
		zmq_command = function_map[code]['zmq_command']
		arguments = None
		messaging.publish_command(zmq_path,zmq_command,arguments)
	else:
		print "function {0} not in function_map".format(code)	
			
def cb_mode_change(active_modes):
	# active_modes is a Modes() struct

	global modes
	
	active_modes.sort(key=itemgetter('name'))
	modes.sort(key=itemgetter('name'))
	
	pairs = zip(modes,active_modes)
	changes = [(y) for x, y in pairs if x != y]

	if not changes:
		return
	
	zmq_path = '/mode/change'
	zmq_command = 'PUT'
	zmq_arguments = []
	modes_update_active = []
	
	for mode in changes:
		if mode['state'] == True:
			modes_update_active.append(mode['name'])
			
		zmq_arguments.append(mode['name'])
		zmq_arguments.append(str(mode['state']))
				
	#print "sending MQ"
	messaging.publish_command(zmq_path,zmq_command,zmq_arguments)
	
	#print "Updating local modes"
	modes.set_active_modes(modes_update_active)
				
	
	
#********************************************************************************
# Parse command line arguments
#
def parse_args():

	global args
	import argparse
	parser = default_parser(DESCRIPTION,BANNER)
	# additional command line arguments mat be added here
	args = parser.parse_args()

def setup():

	#
	# Logging
	# -> Output will be logged to the syslog, if -b specified, otherwise output will be printed to console
	#
	global logger
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)

	if args.b:
		logger = log_create_syslog_loghandler(logger, args.loglevel, LOG_TAG, address='/dev/log') 	# output to syslog
	else:
		logger = log_create_console_loghandler(logger, args.loglevel, LOG_TAG) 						# output to console
	
	#
	# Configuration
	#
	global cfg_main
	global cfg_zmq
	global cfg_daemon
	global cfg_gpio

	# main
	cfg_main = load_cfg_main()
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	# zeromq
	if not args.port_publisher and not args.port_subscriber:
		cfg_zmq = load_cfg_zmq()
	else:
		if args.port_publisher and args.port_subscriber:
			pass
		else:
			load_cfg_zmq()
	
		# Pub/Sub port override
		if args.port_publisher:
			configuration['zeromq']['port_publisher'] = args.port_publisher
		if args.port_subscriber:
			configuration['zeromq']['port_subscriber'] = args.port_subscriber

	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
			
	# daemon
	cfg_daemon = load_cfg_daemon()
	if cfg_daemon is None:
		printer("Daemon configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	# gpio
	cfg_gpio = load_cfg_gpio()
	if cfg_gpio is None:
		printer("GPIO configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Subscriber: {0}".format(DEFAULT_PORT_SUB))
	messaging.create_subscriber(SUBSCRIPTIONS)

	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()

	#
	# GPIO
	#
	global gpio
	global modes
	printer("GPIO: Initializing")
	gpio = GpioController(cfg_gpio,cb_gpio_function)
	modes = gpio.get_modes()
	gpio.set_cb_mode_change(cb_mode_change)
	
	# if we're responisble for modes, then send out a MQ message ? *(or have clients pull?)
	
	printer('Initialized [OK]')
		
def main():		

	# Initialize the mainloop
	#DBusGMainLoop(set_as_default=True)
	#mainloop = gobject.MainLoop()

	#try:
	#	mainloop.run()
	#finally:
	#	mainloop.quit()
	
	counter = 0
	while True:
		
		if counter > 9:
			# only every 10th iteration
			idle_message_receiver() # do this less often TODO! not critical, but takes up precious response time
			#handle_mq_message()	# do this less often TODO! not critical, but takes up precious response time
			counter = 0
		
		counter += 1
		
		sleep(0.1)


if __name__ == "__main__":
	parse_args()
	setup()
	#try:
	main()
	#finally:
	#	pass
		#GPIO.cleanup()
	