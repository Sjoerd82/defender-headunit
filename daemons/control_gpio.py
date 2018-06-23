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
from hu_gpio import GpioController
from hu_commands import Commands
from hu_datastruct import CircularModeset, Modeset

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "GPIO Remote Control"
BANNER = "GPIO Controller Daemon"
LOG_TAG = 'CTGPIO'
LOGGER_NAME = 'ctgpio'

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_LOG_LEVEL = LL_INFO
SUBSCRIPTIONS = []
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560

#DELAY = 0.005
DELAY = 0.01
#LONG_PRESS = 0.05

# global variables
logger = None
args = None
messaging = MqPubSubFwdController(origin=LOGGER_NAME)
gpio = None
commands = Commands()

# configuration
cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ
cfg_gpio = None		# GPIO setup

# data structures
modes = Modeset()

# other stuff
mode_controller = True

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
'''
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
'''

# ********************************************************************************
# MQ functions
#
# args = list of arguments
# return False to return a 500 error thingy
# return None to not return anything

@messaging.handle_mq('/mode/list', cmd='GET')
def testje_get_list(path=None, cmd=None, args=None, data=None):
	""" Return all modes. No parameters """	
	printer("MQ: {0} {1}, returning registered modes: {2} ".format(cmd,path,modes))
	return modes

@messaging.handle_mq('/mode/active')
def testje_get_active(path=None, cmd=None, args=None, data=None):
	""" Return active modes. No parameters """
	printer("MQ: {0} {1}, returning active mode(s): {2} ".format(cmd,path,modes.active_modes()))
	return modes.active_modes()

@messaging.handle_mq('/mode/set','PUT')
def mq_mode_set(path=None, cmd=None, args=None, data=None):
	""" Set mode """
	vargs = commands.validate_args('MODE-SET',args)
	
	printer("MQ: {0} {1}, setting active mode(s): {2} ".format(cmd,path,args))
	try:
		modes.set_active_modes(args)
		return True
	except:
		return False

@messaging.handle_mq('/mode/change', cmd='PUT')
def mq_mode_change_put(path=None, cmd=None, args=None, data=None):
	
	ret = commands.validate_args('MODE-CHANGE',args)
	
	if ret is not None and ret is not False:	
		# arguments are mode-state pairs
		'''
		for i in range(0,len(ret),2):
			printer('[MQ] Received Mode: "{0}", State: {1}'.format(ret[i],ret[i+1]), level=LL_DEBUG)
			
			#modes.active_modes()
			if ret[i+1] == True and ret[i] not in active_modes:
				active_modes.append(ret[i])
			elif ret[i+1] == False and ret[i] in active_modes:
				active_modes.remove(ret[i])
				
		printer("Active Modes: {0}".format(active_modes))
		'''
		pass
	else:
		printer("put_change: Arguments: [FAIL]",level=LL_ERROR)
		
	if mode_controller:
		return True
	else:
		return None
		
@messaging.handle_mq('/mode/unset','PUT')
def mq_mode_set(path=None, cmd=None, args=None, data=None):
	""" Unset mode """
	print "A MODE WAS UNSET"
	if mode_controller:
		return True
	else:
		return None

@messaging.handle_mq('/mode/*','GET')
def mq_mode_test(path=None, cmd=None, args=None, data=None):
	""" Unset mode """
	print "TEST MODE! GET"
	return None

@messaging.handle_mq('/mode/*','PUT')
def mq_mode_test(path=None, cmd=None, args=None, data=None):
	""" Unset mode """
	print "TEST MODE! Anything but Get"
	return False

"""
def idle_message_receiver():
	parsed_msg = messaging.poll(timeout=500, parse=True)	#Timeout: None=Blocking
	if parsed_msg:
		ret = messaging.execute_mq(parsed_msg['path'], parsed_msg['cmd'], args=parsed_msg['args'], data=parsed_msg['data'] )
		if parsed_msg['resp_path'] and ret is not None:
			messaging.publish_command(parsed_msg['resp_path'],'DATA',ret)	
	return True # Important! Returning true re-enables idle routine.
"""
	
# ********************************************************************************
# GPIO Callback
#
def cb_gpio_function(code, arguments):
	print "cb_gpio_function: code={0}, arguments={1}".format(code,arguments)
	#print "CALL: {0}".format(function)
	if code in commands.command_list:
		cmd = commands.get_command(code)
		printer("Executing: {0}".format(code))
		zmq_path = cmd['path']
		zmq_command = cmd['command']
		#arguments = None
		messaging.publish_command(zmq_path,zmq_command,arguments)
	else:
		printer("Function {0} not in function_mq_map".format(code),level=LL_ERROR)
	return
	
	""" The Old Function Mapper:
	if code in function_map:
		printer("Executing: {0}".format(code))
		zmq_path = function_map[code]['zmq_path']
		zmq_command = function_map[code]['zmq_command']
		arguments = None
		messaging.publish_command(zmq_path,zmq_command,arguments)
	else:
		printer("Function {0} not in function_map".format(code),level=LL_ERROR)
	"""
			
def cb_mode_change(mode_changes):
	# active_modes is a Modes() struct
	
		# find modes that are no longer active.
		# active modes
		#mq_instruction = 
		#exec_function_by_code('MODE-CHANGE', ...)
	
	print "Hello from cb_mode_change(): {0}".format(mode_changes)
	
	'''
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
	'''
				
	
	
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
	cfg_main, cfg_zmq, cfg_daemon, cfg_gpio = load_cfg(
		args.config,
		['main','zmq','daemon','gpio'],
		args.port_subscriber, args.port_subscriber,
		daemon_script=os.path.basename(__file__),
		logger_name=LOGGER_NAME	)
	
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
			
	if cfg_daemon is None:
		printer("Daemon configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	if cfg_gpio is None:
		printer("GPIO configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging.set_address('localhost',cfg_zmq['port_publisher'],cfg_zmq['port_subscriber'])
	
	printer("ZeroMQ: Creating Publisher: {0}".format(cfg_zmq['port_publisher']))
	messaging.create_publisher()
	
	printer("ZeroMQ: Creating Subscriber: {0}".format(cfg_zmq['port_subscriber']))
	messaging.create_subscriber(SUBSCRIPTIONS)

	printer('ZeroMQ subscriptions:')
	for topic in messaging.subscriptions():
		printer("> {0}".format(topic))
	
	#
	# GPIO
	#
	global gpio
	global modes
	printer("GPIO: Initializing")
	gpio = GpioController(cfg_gpio,cb_gpio_function,cb_mode_change,logger=logger)
	
	my_ms_all = gpio.modesets(deepcopy=False) #return a reference
	print "activating genre random"
	my_ms_all['random'].activate(3)
	my_ms_all['random'].activate(4)
	print "activating bass"
	my_ms_all['modecycle1'].activate(2)
	print gpio.activemodes()
	gpio.ms_all['modecycle1'].activate(2)
	print gpio.activemodes()

	#my_ms_all2 = gpio.modesets(deepcopy=True) #return a reference
	#print "Copy={0}".format(my_ms_all2)
	

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
			messaging.poll_and_execute(500) # do this less often TODO! not critical, but takes up precious response time
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
	