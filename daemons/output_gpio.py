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
LOG_TAG = 'GPIOUT'
LOGGER_NAME = 'output_gpio'
SUBSCRIPTIONS = ['/events/','/mode/']
SLEEP_INTERVAL = 0.1

# global variables
logger = None
args = None
messaging = MqPubSubFwdController()
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

@messaging.handle_mq('/mode/set', cmd='PUT')
def mq_mode_set_put(path=None, cmd=None, args=None, data=None):
	# args[0] = mode
	# args[1] = True|False (optional, default=True)
	
	arg_defs = []
	arg0 = {
				'name': 'mode',
				'datatype': 'str',
				'required': True		
	}
	arg1 = {
				'name': 'state',
				'datatype': 'bool',		# will auto-convert str and int, if it makes sense
				'required': False,
				'default': False
				'choices': ['true','false','on','off','1','0',1,0,True,False],
				'convert_to' : 'bool'
	}
	arg_defs.append(arg0)
	arg_defs.append(arg1)
	ret = validate_args(arg_defs,args)
	if ret is not None and ret is not False:
		print "Arguments: [OK]"
	else:
		print "Arguments: [FAIL]"

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
		
	new_mode = { "name": mode_set, "state": mode_state }
	# new mode?
	if mode_set not in modes.unique_list():
		print "Setting new mode {0} to {1}".format(mode_set,mode_state)
		modes.append(new_mode)
	else:
		print "Existing Mode. Check if changed"
		mode_curr = modes.get_by_unique(mode_set)
		#print "Current   : {0}".format(mode_curr['state'])
		#print "Requested : {0}".format(mode_state)
		if mode_curr['state'] != mode_state:
			print "Updating mode to {0}".format(mode_state)
			modes.set_by_unique(mode_set,new_mode)
			
	#print "--- MODES ---"
	#print modes
	return True
			
@messaging.handle_mq('/events/mode/changed', cmd='DATA')
def data_mode_changed(path=None, cmd=None, args=None, data=None):
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
	
@messaging.handle_mq('/events/source/active', cmd='DATA')
def data_source_active(path=None, cmd=None, args=None, data=None):
	print "ACTIVE"
	pass
	
@messaging.handle_mq('/events/source/available', cmd='DATA')
def data_source_available(path=None, cmd=None, args=None, data=None):
	print "AVAILABLE"
	pass
	
@messaging.handle_mq('/events/source/state', cmd='DATA')
def data_player_state(path=None, cmd=None, args=None, data=None):
	print "STATE"
	pass
	
@messaging.handle_mq('/events/player/track', cmd='DATA')
def data_player_track(path=None, cmd=None, args=None, data=None):
	print "TRACK"
	pass
	
@messaging.handle_mq('/events/player/elapsed', cmd='DATA')
def data_player_elapsed(path=None, cmd=None, args=None, data=None):
	print "ELAPSED"
	pass
	
@messaging.handle_mq('/events/player/updating', cmd='DATA')
def data_player_updating(path=None, cmd=None, args=None, data=None):
	print "UPDATING"
	pass
	
@messaging.handle_mq('/events/player/updated', cmd='DATA')
def data_player_updated(path=None, cmd=None, args=None, data=None):
	print "UPDATED"
	pass
	
@messaging.handle_mq('/events/volume/changed', cmd='DATA')
def data_volume_changed(path=None, cmd=None, args=None, data=None):
	print "VOL_CHG"
	pass
	
@messaging.handle_mq('/events/volume/att', cmd='DATA')
def data_volume_att(path=None, cmd=None, args=None, data=None):
	print "ATT"
	pass
	
@messaging.handle_mq('/events/volume/mute', cmd='DATA')
def data_volume_mute(path=None, cmd=None, args=None, data=None):
	print "MUTE"
	pass
	
@messaging.handle_mq('/events/network/up', cmd='DATA')
def data_network_up(path=None, cmd=None, args=None, data=None):
	print "NET UP"
	pass
	
@messaging.handle_mq('/events/network/down', cmd='DATA')
def data_network_down(path=None, cmd=None, args=None, data=None):
	payload = json.loads(data)
	sc_sources.do_event('network',path,payload)
	printSummary()
	return None
	
@messaging.handle_mq('/events/system/shutdown', cmd='DATA')
def data_system_shutdown(path=None, cmd=None, args=None, data=None):
	print "SHUTDOWN"
	pass
	
@messaging.handle_mq('/events/system/reboot', cmd='DATA')
def data_system_reboot(path=None, cmd=None, args=None, data=None):
	print "REBOOT"
	pass
	
@messaging.handle_mq('/events/udisks/added', cmd='DATA')
def data_udisks_added(path=None, cmd=None, args=None, data=None):
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
	
@messaging.handle_mq('/events/udisks/removed', cmd='DATA')
def data_udisks_removed(path=None, cmd=None, args=None, data=None):
	print "REMOVED"
	pass
	
def idle_message_receiver():
	parsed_msg = messaging.poll(timeout=1000, parse=True)	#Timeout: None=Blocking
	if parsed_msg:
		ret = messaging.execute_mq(mq_path, parsed_msg['cmd'], args=parsed_msg['args'], data=parsed_msg['data'] )
			
		if parsed_msg['resp_path'] and ret is not False:
			messaging.publish_command(parsed_msg['resp_path'],'DATA',ret)
		
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
	messaging.set_address('localhost',cfg_zmq['port_publisher'],cfg_zmq['port_subscriber'])
	
	printer("ZeroMQ: Creating Publisher: {0}".format(cfg_zmq['port_publisher']))
	messaging.create_publisher()

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
	