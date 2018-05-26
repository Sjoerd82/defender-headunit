#!/usr/bin/python

#
# GPIO output
# Venema, S.R.G.
# 2018-05-23
#
# Description of the daemon goes here.. 
# 

import sys						# path
import os						# 
from time import sleep

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
DESCRIPTION = "Description, shown when using the help (-h) switch"
BANNER = "GPIO Output"
LOG_TAG = 'GPIOOUTP'
LOGGER_NAME = 'output_gpio'
SUBSCRIPTIONS = ['/events/','/mode/']
SLEEP_INTERVAL = 0.1

# global variables
logger = None
args = None
messaging = None
gpio = None

# global datastructures
modes = Modes()
list_modes = []

# configuration
cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ
cfg_gpio = None		# GPIO setup

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# ********************************************************************************
# Load configuration
#
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

def handle_path_mode(path,cmd,args,data):

	base_path = 'mode'
	# remove base path
	del path[0]
	
	def put_set(args):
		
		# args[0] = mode
		# args[1] = True|False (optional, default=True)
		
		mode_set = args[0]
		if len(args) > 1:
			if args[1].lower() in ['true','1','yes']:
				mode_state = True
			elif args[1].lower() in ['false','0','no']:
				mode_state = False
			else:
				mode_state = True
		else:
			mode_state = True
		
		print "Setting mode {0} to {1}".format(mode_set,mode_state)
		new_mode = { "name": mode_set, "state": mode_state }
	
		# new mode?
		if mode_set not in modes.unique_list():
			modes.append(new_mode)
		else:
			print "Existing Mode. Check if changed"
			#check if changed
			#current_state = modes.
			#if data['payload']['state'] != 
		print "--- MODES ---"
		print modes
			
	if path:
		function_to_call = cmd + '_' + '_'.join(path)
	else:
		# called without sub-paths
		function_to_call = cmd + '_' + base_path

	ret = None
	if function_to_call in locals():
		ret = locals()[function_to_call](args)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret))
	else:
		printer('Function {0} does not exist'.format(function_to_call))

	return ret

	
def handle_path_events(path,cmd,args,data):

	base_path = 'events'
	# remove base path
	del path[0]
	
	def data_mode_changed(data):
		print "MODE CHANGE!"
		print data
		if not 'payload' in data:
			return
		
		# new mode?
		if data['payload']['name'] not in modes:
			try:
				modes.append(data)
			except:
				print "Could not add mode"
		else:
			print "Check if changed"
			#check if changed
			#current_state = modes.
			#if data['payload']['state'] != 
		
	
	def data_source_active(data):
		print "ACTIVE"
		pass
	def data_source_available(data):
		print "AVAILABLE"
		pass
	def data_player_state(data):
		print "STATE"
		pass
	def data_player_track(data):
		print "TRACK"
		pass
	def data_player_elapsed(data):
		print "ELAPSED"
		pass
	def data_player_updating(data):
		print "UPDATING"
		pass
	def data_player_updated(data):
		print "UPDATED"
		pass
	def data_volume_changed(data):
		print "VOL_CHG"
		pass
	def data_volume_att(data):
		print "ATT"
		pass
	def data_volume_mute(data):
		print "MUTE"
		pass
	def data_network_up(data):
		print "NET UP"
		pass
	def data_network_down(data):
		payload = json.loads(data)
		sc_sources.do_event('network',path,payload)
		printSummary()
		return None
	def data_system_shutdown(data):
		print "SHUTDOWN"
		pass
	def data_system_reboot(data):
		print "REBOOT"
		pass
	def data_udisks_added(data):
		""" New media added
			
			Data object:
			{
				device
				uuid
				mountpoint
				label
			}
			Return data:
				?
			Return codes:
				?
		"""
		#valid = validate_args(args,1,3)
		#if not valid:
		#	return None

		payload = json.loads(data)
		sc_sources.do_event('udisks',path,payload)	# do_event() executes the 'udisks' event
		printSummary()
		return None
		
	def data_udisks_removed(data):
		print "REMOVED"
		pass

	if path:
		function_to_call = cmd + '_' + '_'.join(path)
	else:
		# called without sub-paths
		function_to_call = cmd + '_' + base_path

	ret = None
	if function_to_call in locals():
		ret = locals()[function_to_call](data)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret))
	else:
		printer('Function {0} does not exist'.format(function_to_call))

	return ret

	
def idle_message_receiver():
	#print "DEBUG: idle_msg_receiver()"
	
	def dispatcher(path, command, arguments, data):
		handler_function = 'handle_path_' + path[0]
			
		if handler_function in globals():
			ret = globals()[handler_function](path, command, arguments, data)
			return ret
		else:
			print("No handler for: {0}".format(handler_function))
			return None
					
	rawmsg = messaging.poll(timeout=1000)				#None=Blocking, 1000 = 1sec
	if rawmsg:
		printer("Received message: {0}".format(rawmsg))	#TODO: debug
		parsed_msg = parse_message(rawmsg)
		
		# send message to dispatcher for handling	
		retval = dispatcher(parsed_msg['path'],parsed_msg['cmd'],parsed_msg['args'],parsed_msg['data'])

		if parsed_msg['resp_path']:
			#print "DEBUG: Resp Path present.. returing message.. data={0}".format(retval)
			messaging.publish_command(parsed_msg['resp_path'],'DATA',retval)
		
	return True # Important! Returning true re-enables idle routine.
	
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
	#  Output will be logged to the syslog, if -b specified, otherwise output will be printed to console
	#
	global logger
	log_address = None
	if args.b: log_address='/dev/log' 	# output to syslog
	logger = log_getlogger(LOGGER_NAME,args.loglevel,LOG_TAG,log_address)
		
	#
	# Configuration
	#
	global cfg_main
	global cfg_zmq
	global cfg_daemon

	# main
	cfg_main = load_cfg_main(LOGGER_NAME)
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	# zeromq
	cfg_zmq = load_cfg_zmq(cfg_main,args.port_publisher,args.port_subscriber)
	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
			
	# daemon
	cfg_daemon = load_cfg_daemon(cfg_main,os.path.basename(__file__))
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
	messaging = MqPubSubFwdController('localhost',cfg_zmq['port_publisher'],cfg_zmq['port_subscriber'])
	
	#printer("ZeroMQ: Creating Publisher: {0}".format(cfg_zmq['port_publisher']))
	#messaging.create_publisher()

	printer("ZeroMQ: Creating Subscriber: {0}".format(cfg_zmq['port_subscriber']))
	messaging.create_subscriber(SUBSCRIPTIONS)

	
	#
	# GPIO
	#
	gpio = GpioController(cfg_gpio)
	

	printer('Initialized [OK]')
		
def main():		

	while True:
		idle_message_receiver()
		sleep(SLEEP_INTERVAL)


if __name__ == "__main__":
	parse_args()
	setup()
	try:
		main()
	finally:
		#GPIO.cleanup()
		pass
	