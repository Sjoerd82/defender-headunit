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

# MQ: Pub & Sub

# Button presses are NOT asynchronous!! i.e. wait until a button press is handled before the next button can be handled.
# TODO: Consider making them asynchronous, or at least the update lib (long) / volume (short) buttons

# printer -> syslog adds considerable latency!  ?
# (and?) Or.. is it the MQ send() ?


import sys						# path
import os						# 
from time import sleep
from operator import itemgetter

from datetime import datetime
from logging import getLogger	# logger

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController
from hu_gpio import GpioController
from hu_commands import Commands
from hu_datastruct import Modeset

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "GPIO Remote Control"
BANNER = "GPIO Controller Daemon"
LOG_TAG = 'CTGPIO'
LOGGER_NAME = 'ctgpio'
SUBSCRIPTIONS = []

# global variables
logger = None
args = None
messaging = MqPubSubFwdController(origin=LOGGER_NAME)
gpio = None
command = Commands()

# configuration
cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ
cfg_gpio = None		# GPIO setup

# data structures
modes = Modeset()

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
# MQ functions
#
# args = list of arguments
# return False to return a 500 error thingy
# return None to not return anything

@messaging.handle_mq('/mode/list','GET')
def testje_get_list(path=None, cmd=None, args=None, data=None):
	"""
	Return all modes. No parameters
	TODO: return only modes over which we are authorative
	TODO: support multiple message returns in other parts of the system
	"""	
	ret = []
	modesets = gpio.modesets()
	for modesetid in modesets:
		for mode in modesets[modesetid]:
			ret.append(mode['mode'])
	
	printer("MQ: {0} {1}, returning all known modes: {2} ".format(cmd,path,ret))
	return ret

@messaging.handle_mq('/mode/active','GET')
def testje_get_active(path=None, cmd=None, args=None, data=None):
	"""
	Return active modes. No parameters
	"""
	ret = gpio.activemodes()
	printer("MQ: {0} {1}, returning active mode(s): {2} ".format(cmd,path,ret))
	return ret

@messaging.handle_mq('/mode/set','PUT')
@command.validate('MODE-SET')
def mq_mode_set(path=None, cmd=None, args=None, data=None):
	"""
	Set mode. Param: Mode
	Returns True if succeful, False if not
	"""
	#valid_arg = commands.validate_args('MODE-SET',args)
	if args is not None and args is not False:
		printer("MQ: {0} {1}, setting active mode(s): {2} ".format(cmd,path,args))
		gpio.set_mode(args)
		return True
	else:
		return False

@messaging.handle_mq('/mode/change','PUT')
@command.validate('MODE-CHANGE')
def mq_mode_change_put(path=None, cmd=None, args=None, data=None):
	"""
	Change modes; MODE-CHANGE
	Args:    Pairs of Mode-State
	Returns: None
	"""
	#valid_args = commands.validate_args('MODE-CHANGE',args)
	if args is not None and args is not False:
		print "DEBUG, before: {0}".format(gpio.activemodes())
		gpio.change_modes(args)
		printer("Active Modes: {0}".format(gpio.activemodes()))
	else:
		printer("put_change: Arguments: [FAIL]",level=LL_ERROR)
	return None
		
@messaging.handle_mq('/mode/unset','PUT')
@command.validate('MODE-UNSET')
def mq_mode_unset(path=None, cmd=None, args=None, data=None):
	"""
	Unset mode
	Arg: Mode
	Returns: None
	"""
	#args = commands.validate_args('MODE-UNSET',args)
	gpio.set_mode(args,False)
	printer("MQ: {0} {1}, unsetting mode: {2} ".format(cmd,path,args))
	return None


# TODO --  REMOVE -- REMOVING THIS STOPS OTHER MQ TO WORK
@messaging.handle_mq('/mode/*','GET')
def mq_mode_test(path=None, cmd=None, args=None, data=None):
	""" Unset mode """
	print "TEST MODE! GET"
	return None

# TODO --  REMOVE -- REMOVING THIS STOPS OTHER MQ TO WORK
@messaging.handle_mq('/mode/*','PUT')
def mq_mode_test(path=None, cmd=None, args=None, data=None):
	""" Unset mode """
	print "TEST MODE! Anything but Get"
	return False

	
# ********************************************************************************
# GPIO Callback
#
def cb_gpio_function(code, arguments):
	"""
	Execute the function indicated by code.
	"""
	print "cb_gpio_function: code={0}, arguments={1}".format(code,arguments)
	#print "CALL: {0}".format(function)
	if code in command.command_list:
		cmd = command.get_command(code)
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
			
def cb_mode_change(mode_changes,init=False):
	"""
	Mode change.
	"""
	# active_modes is a Modes() struct
	
		# find modes that are no longer active.
		# active modes
		#mq_instruction = 
		#exec_function_by_code('MODE-CHANGE', ...)
	
	
	
	print "Hello from cb_mode_change(): {0} Init={1}".format(mode_changes,init)
	print "Doing Nothing, but thanks for the update"
	
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

	cfg_main, cfg_zmq, cfg_daemon, cfg_gpio = load_cfg(
		args.config,
		['main','zmq','daemon','gpio'],
		args.port_publisher, args.port_subscriber,
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
	