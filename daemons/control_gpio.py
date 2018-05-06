#!/usr/bin/python

#
# GPIO Remote Control
# Venema, S.R.G.
# 2018-05-04
#
# GPIO remote control enables GPIO input for buttons and encoders.
# It comes with optional rudimentary debouncing.
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
from time import clock
from logging import getLogger	# logger
from RPi import GPIO			# GPIO

import gobject				# main loop
from dbus.mainloop.glib import DBusGMainLoop

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "GPIO Remote Control"
BANNER = "GPIO Controller Daemon"
LOG_TAG = 'GPIO'
LOGGER_NAME = 'gpio'

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560

#DELAY = 0.005
DELAY = 0.01
LONG_PRESS = 0.05

FUNCTIONS = [
	'VOLUME',
	'BASS',
	'TREBLE',
	'SOURCE',
	'POWEROFF',
	'NEXT_TRACK',
	'NEXT_FOLDER',
	'PREV_TRACK',
	'PREV_FOLDER',
	'RANDOM',
	'MENU_ENTER',
	'MENU_SCROLL',
	'MENU_SELECT' ]

function_map = {}
function_map['VOLUME'] = { "zmq_path":"volume", "zmq_command":"PUT" }
function_map['SOURCE'] = { "zmq_path":"source", "zmq_command":"PUT" }


logger = None
args = None
messaging = None

cfg_ctrlgpio = None

encoder1_cnt = 0
encoder1_last_clk_state = None
#temp
clk = None
dt = None

pins_state = {}			# pin (previous) state
pins_function = {}		# pin function(s)
pins_config = {}		# consolidated config, key=pin

active_modes = [ None ]

'''
pins_config = 
	{ "23": {
		dev_name
		dev_type
		functions: [ {
			fnc_name
			fnc_code
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
def load_zeromq_configuration():
	
	configuration = configuration_load(LOGGER_NAME,args.config)
	
	if not configuration or not 'zeromq' in configuration:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		configuration = { "zeromq": { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB } }
		return configuration
		
	else:
		# Get portnumbers from either the config, or default value
		if not 'port_publisher' in configuration['zeromq']:
			configuration['zeromq']['port_publisher'] = DEFAULT_PORT_PUB
			
		if not 'port_subscriber' in configuration['zeromq']:
			configuration['zeromq']['port_subscriber'] = DEFAULT_PORT_SUB
			
	return configuration

def load_gpio_configuration():
	global cfg_ctrlgpio
	gpio_ix = 4	#todo!
	config_dir = configuration['daemons'][gpio_ix]['config-dir']
	config_file = configuration['daemons'][gpio_ix]['config']
	configfile = os.path.join(config_dir,config_file)
	cfg_ctrlgpio = configuration_load(LOGGER_NAME,configfile)
	
def get_device_config(name):
	for device in cfg_ctrlgpio['devices']:
		if device['name'] == name:
			return device
	return None
	
def get_device_config_by_pin(pin):
	for device in cfg_ctrlgpio['devices']:
		if device['clk'] == pin:
			return device
		elif device['dt'] == pin:
			return device
		elif device['sw'] == pin:
			return device
	return None

def get_encoder_function_by_pin(pin):
	""" Returns function dictionary
	"""
	# loop through all possible functions for given pin
	# examine if func meets all requirements (only one check needed for encoders: mode)
	
	for func_cfg in pins_config[pin]['functions']:
		# check mode #TODO!! TODO!! add mode here!!
		if 'mode' in func_cfg and func_cfg['mode'] not in active_modes:
			pass # these are not the mode you're looking for
		else:
			#if 'encoder' in func_cfg:
			return func_cfg
			
	return None

def get_function_by_pin(pin,type):
	""" Returns function dictionary
	pin = pin
	type = encoder | short_press | long_press
	"""
	# loop through all possible functions for given pin
	# examine if func meets all requirements (only one check needed for encoders: mode)
	for function_ix in pins_function[pin]:
		
		func_cfg = cfg_ctrlgpio['functions'][function_ix]
		ok = True
		
		# check mode
		if 'mode' in func_cfg and func_cfg['mode'] not in active_modes:
			print "DEBUG: not in the required mode"
			return None
		else:
			if type in func_cfg:
				return func_cfg

			# check multi-press

def get_functions_by_pin(pin):
	""" Returns list of valiid functions for given pin
		It will take the mode into account
	"""
	retlist = []
	# loop through all possible functions for given pin
	for function_ix in pins_function[pin]:
		
		func_cfg = cfg_ctrlgpio['functions'][function_ix]
		ok = True
		
		# check mode
		if 'mode' in func_cfg and func_cfg['mode'] not in active_modes:
			print "DEBUG: not in the required mode"
		else:
			retlist.append(func_cfg)
		
	return retlist
			

def exec_function_by_code(code,param=None):
	print "EXECUTE: {0} {1}".format(code,param)
	#function_map[func_cfg['function']] = { "zmq_path":"volume", "zmq_command":"PUT" }
	if code in function_map:
		zmq_path = function_map[code]['zmq_path']
		zmq_command = 'PUT'
		arguments = None
		if code == 'VOLUME':
			if param='cw':
				arguments = 'up'
			if param='ccw':
				arguments = 'down'
		messaging.publish_command(zmq_path,zmq_command,arguments)
	else:
		print "function {0} not in function_map".format(code)
	
			
def handle_pin_change(pin,value_old,value_new):
	""" When a pin changes value
	"""
	print "DEBUG: handle pin change for pin: {0}".format(pin)
	
	if pin not in pins_function:
		print "WHat??"
		return None
	
	print "DEBUG: This pins config:"
	print pins_config[pin]
	
		
	for function_ix in pins_function[pin]:
		
		#examine if func meets all requirements
		func_cfg = cfg_ctrlgpio['functions'][function_ix]
		ok = True
		
		# check mode
		if 'mode' in func_cfg and func_cfg['mode'] not in active_modes:
			print "DEBUG: not in the required mode"
		else:
			# encoder: check dt pin
			if 'encoder' in func_cfg:
				device_cfg = get_device_config( func_cfg['encoder'] )
				pin_clk = pin
				pin_dt = device_cfg['dt']
				#if clkState != encoder1_last_clk_state:
				#  if dtState != clkState:
				if value_new != value_old:
					if GPIO.input(pin_dt) != value_new:
						print function_map[func_cfg['function']]
						#function_map[func_cfg['function']] = { "zmq_path":"volume", "zmq_command":"PUT" }
						print "ENCODER: INCREASE"
					else:
						print function_map[func_cfg['function']]
						print "ENCODER: DECREASE"

			# switch (long or short): check if other switches need to be engaged
			elif 'short_press' in func_cfg:
				if len( func_cfg['short_press'] ) == 1:
					print function_map[func_cfg['function']]
					# assume(?) it's the same gpio number?
				else:
					#check if other buttons are pressed
					for switch in func_cfg['short_press']:
						switch_cfg = get_device_config( switch )
						i = 0
						if GPIO.input(switch_cfg['sw']) == switch_cfg['on']:
							i += 1
							
					if i == len(func_cfg['short_press']):								
						print function_map[func_cfg['function']]
					
			#elif 'long_press' in .. #todo
			else:
				printer("Unsupported device or incomplete configuration",level=LL_WARNING)
				

def cb_mode_reset(pin,function_ix):
	print "TODO! RESET MODE!"

def check_mode(pin,function_ix):

	function = pins_config[pin]['functions'][function_ix]
	print function
	
	if 'mode_toggle' in function: # and 'mode' in pins_config[pin]:
		print "DEBUG: Toggeling Mode"
		if function['mode_toggle'] in active_modes:
			active_modes.remove(function['mode_toggle'])
			print "DEBUG: Active Mode(s): {0}".format(active_modes)
		else:
			active_modes.append(function['mode_toggle'])
			print "DEBUG: Active Mode(s): {0}".format(active_modes)
			
	elif 'mode_select' in function: # and 'mode' in pins_config[pin]:		
		for mode in active_modes:
			mode_ix = function['mode_select'].index(mode)
			if mode_ix is not None:
				mode_old = function['mode_select'][mode_ix]
				active_modes.remove(mode_old)
				if mode_ix >= len(function['mode_select'])-1:
					mode_ix = 0
				else:
					mode_ix += 1
				mode_new = function['mode_select'][mode_ix]
				print "Mode change {0} -> {1}".format(mode_old,mode_new)
				active_modes.append(mode_new)
				
				if 'mode_reset' in function:
					print "TODO! START RESET TIMER!! Seconds: {0}".format(function['mode_reset'])
					#gobject.timeout_add_seconds(function['mode_reset'],cb_mode_reset,pin,function_ix)
				break

				
def handle_switch_interrupt(pin):
	""" Callback function for switches
	"""
	press_start = clock()
	press_time = 0

	# debounce
	#if 'debounce' in pins_config[pin]:
	#	debounce = pins_config[pin]['debounce'] / 1000
	#	print "DEBUG: sleeping: {0}".format(debounce)
	#	sleep(debounce)
	#	
	sleep(0.02)
	if not GPIO.input(pin) == pins_config[pin]['gpio_on']:
		return None
	
	print "DEBUG: HANDLE_SWITCH_INTERRUPT! for pin: {0}".format(pin)

	# check wheather we have short and/or long press functions and multi-press functions
	if pins_config[pin]['has_short'] and not pins_config[pin]['has_long'] and not pins_config[pin]['has_multi']:
		""" Only a SHORT function, no long press functions, no multi-button, go ahead and execute """
		print "EXECUTING THE SHORT FUNCTION (only option)..."
		
		# execute, checking mode
		for ix, fun in enumerate(pins_config[pin]['functions']):
			if 'mode' in fun:
				if fun['mode'] in active_modes:
					exec_function_by_code(fun['fnc_code'])
				else:
					print "DEBUG mode mismatch"
			else:
				if 'mode_toggle' in fun or 'mode_select' in fun:
					check_mode(pin,ix)
				exec_function_by_code(fun['fnc_code'])
			
		return

	if (pins_config[pin]['has_long'] or pins_config[pin]['has_short']) and not pins_config[pin]['has_multi']:
		""" LONG + possible short press functions, no multi-buttons, go ahead and execute, if pressed long enough """
		print "EXECUTING THE LONG or SHORT FUNCTION, DEPENDING ON PRESS TIME."

		printer("Waiting for button to be released....")
		pressed = True
		while True: #pressed == True or press_time >= LONG_PRESS:
			state = GPIO.input(pin)
			if state != pins_config[pin]['gpio_on']:
				print "RELEASED!"
				pressed = False
				break
			if press_time >= LONG_PRESS:
				print "TIMEOUT"
				break
			press_time = clock()-press_start
			sleep(0.005)
			
		print "....done"
		print "switch was pressed for {0} seconds".format(press_time*100)		

		if press_time >= LONG_PRESS and pins_config[pin]['has_long']:
			print "EXECUTING THE LONG FUNCTION (long enough pressed)"
			
			# execute, checking mode
			for ix, fun in enumerate(pins_config[pin]['functions']):
				if fun['press_type'] == 'long':
					if 'mode' in fun:
						if fun['mode'] in active_modes:
							exec_function_by_code(fun['fnc_code'])
						else:
							print "DEBUG mode mismatch"
					else:
						if 'mode_toggle' in fun or 'mode_select' in fun:
							check_mode(pin,ix)
						exec_function_by_code(fun['fnc_code'])			
			
		elif press_time < LONG_PRESS and pins_config[pin]['has_short']:
			print "EXECUTING THE SHORT FUNCTION (not long enough pressed)"
			
			# execute, checking mode
			for ix, fun in enumerate(pins_config[pin]['functions']):
				if fun['press_type'] == 'short':
					if 'mode' in fun:
						if fun['mode'] in active_modes:
							exec_function_by_code(fun['fnc_code'])
						else:
							print "DEBUG mode mismatch"
					else:
						if 'mode_toggle' in fun or 'mode_select' in fun:
							check_mode(pin,ix)
						exec_function_by_code(fun['fnc_code'])

		else:
			print "No Match!"
			
		return
		
	# check wheather we have short and/or long press functions and multi-press functions
	if pins_config[pin]['has_multi']:
		""" There are multi-button combinations possible. The function pin list is sorted with highest button counts first.
			Looping from top to bottom we will check if any of these are valid.	"""
		print "checking multi-button..."
		matched_short_press_function_code = None
		matched_long_press_function_code = None
		for function in pins_config[pin]['functions']:
		
			if 'mode' in function and function['mode'] in active_modes:
		
				multi_match = True
				for multi_pin in function['multi']:
					if not GPIO.input(multi_pin) == pins_config[pin]['gpio_on']:
						multi_match = False
				if multi_match == True:
					if function['press_type'] == 'short_press':
						matched_short_press_function_code = function['fnc_code']
					elif function['press_type'] == 'long_press':
						matched_long_press_function_code = function['fnc_code']
				
		printer("Waiting for button to be released....")
		pressed = True
		while pressed == True or press_time >= LONG_PRESS:
			state = GPIO.input(pin)
			if state != pins_config[pin]['gpio_on']:
				print "RELEASED!"
				pressed = False
				break
			press_time = clock()-press_start
			sleep(0.01)
				
		print "....done"
		print "switch was pressed for {0} seconds".format(press_time)
		
#			if pins_config[pin]['has_long'] and not pins_config[pin]['has_short']:
#				print "EXECUTING THE LONG FUNCTION (only long)"
		if press_time >= LONG_PRESS and pins_config[pin]['has_long'] and matched_long_press_function_code is not None:
			print "EXECUTING THE LONG FUNCTION (long enough pressed)"
		elif press_time < LONG_PRESS and pins_config[pin]['has_short'] and matched_short_press_function_code is not None:
			print "EXECUTING THE SHORT FUNCTION (not long enough pressed)"
		else:
			print "No Match!"

# Rotarty encoder interrupt:
# this one is called for both inputs from rotary switch (A and B)
def handle_rotary_interrupt(pin):
	global pins_state
	
	#print "DEBUG: HANDLE_ROTARY_INTERRUPT! for pin: {0}".format(pin)
	
	device = get_device_config_by_pin(pin)
	
	encoder_pinA = device['clk']
	encoder_pinB = device['dt']
	#print "DEBUG! Found encoder pins:"
	#print encoder_pinA
	#print encoder_pinB

	Switch_A = GPIO.input(encoder_pinA)
	Switch_B = GPIO.input(encoder_pinB)
													# now check if state of A or B has changed
													# if not that means that bouncing caused it	
	Current_A = pins_state[encoder_pinA]
	Current_B = pins_state[encoder_pinB]
	if Current_A == Switch_A and Current_B == Switch_B:		# Same interrupt as before (Bouncing)?
		return										# ignore interrupt!

	pins_state[encoder_pinA] = Switch_A								# remember new state
	pins_state[encoder_pinB] = Switch_B								# for next bouncing check
	
	# -------------------------------
	
	function = get_encoder_function_by_pin(pin)
	if function is not None:

		if (Switch_A and Switch_B):						# Both one active? Yes -> end of sequence
			if pin == encoder_pinB:							# Turning direction depends on 
				#clockwise
				print "[Encoder] {0}: INCREASE/CW".format(function['function'])			
				exec_function_by_code(function['function'],'cw')
			else:
				#counter clockwise
				print "[Encoder] {0}: DECREASE/CCW".format(function['function'])
				exec_function_by_code(function['function'],'ccw')

	
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
	# Load configuration
	#
	global configuration
	if not args.port_publisher and not args.port_subscriber:
		configuration = load_zeromq_configuration()
	else:
		if args.port_publisher and args.port_subscriber:
			pass
		else:
			configuration = load_zeromq_configuration()
	
		# Pub/Sub port override
		if args.port_publisher:
			configuration['zeromq']['port_publisher'] = args.port_publisher
		if args.port_subscriber:
			configuration['zeromq']['port_subscriber'] = args.port_subscriber
			
	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()

	#
	# GPIO
	#
	global pins_function # old?
	load_gpio_configuration()
	GPIO.setmode(GPIO.BCM)	# todo: get this from the config file

	# init all pins in configuration
	pins_monitor = []
	#for ix, device in enumerate(cfg_ctrlgpio['devices']):
	for device in cfg_ctrlgpio['devices']:
		if 'sw' in device:
			#pin = cfg_ctrlgpio['devices'][ix]['sw']
			pin = device['sw']
			pins_monitor.append(pin)
			
			printer("Setting up pin: {0}".format(pin))
			GPIO.setup(pin, GPIO.IN)
			
			# convert high/1, low/0 to bool
			if device['gpio_on'] == "high" or device['gpio_on'] == 1:
				gpio_on = GPIO.HIGH
			else:
				gpio_on = GPIO.LOW
			
			# pull up/down setting
			# valid settings are: True, "up", "down"
			# if left out, no pull up or pull down is enabled
			# Set to True to automatically choose pull-up or down based on the on-level.
			if 'gpio_pullupdown' in device:
				if device['gpio_pullupdown'] == True:
					if gpio_on == GPIO.HIGH:
						#GPIO.set_pullupdn(pin, pull_up_down=GPIO.PUD_DOWN)	#v0.10
						GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
						printer("Pin {0}: Pull-down resistor enabled".format(pin))
					else:
						#GPIO.set_pullupdn(pin, pull_up_down=GPIO.PUD_UP)	#v0.10
						GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
						printer("Pin {0}: Pull-up resistor enabled".format(pin))
				elif device['gpio_pullupdown'] == False:
					pass
				elif device['gpio_pullupdown'] == 'up':
					#GPIO.set_pullupdn(pin, pull_up_down=GPIO.PUD_UP)	#v0.10
					GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
					printer("Pin {0}: Pull-up resistor enabled".format(pin))
				elif device['gpio_pullupdown'] == 'down':
					#GPIO.set_pullupdn(pin, pull_up_down=GPIO.PUD_DOWN)	#v0.10
					GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
					printer("Pin {0}: Pull-down resistor enabled".format(pin))
				else:
					printer("ERROR: invalid pull_up_down value. This attribute is optional. Valid values are: True, 'up' and 'down'.",level=LL_ERROR)

			# edge detection trigger type
			# valid settings are: "rising", "falling" or both
			# if left out, the trigger will be based on the on-level
			if 'gpio_edgedetect' in device:				
				if device['gpio_edgedetect'] == 'rising':
					GPIO.add_event_detect(pin, GPIO.RISING, callback=handle_switch_interrupt) #
					printer("Pin {0}: Added Rising Edge interrupt; bouncetime=600".format(pin))
				elif device['gpio_edgedetect'] == 'falling':
					GPIO.add_event_detect(pin, GPIO.FALLING, callback=handle_switch_interrupt) #
					printer("Pin {0}: Added Falling Edge interrupt; bouncetime=600".format(pin))
				elif device['gpio_edgedetect'] == 'both':
					GPIO.add_event_detect(pin, GPIO.BOTH, callback=handle_switch_interrupt) #
					printer("Pin {0}: Added Both Rising and Falling Edge interrupt; bouncetime=600".format(pin))
					printer("Pin {0}: Warning: detection both high and low level will cause an event to trigger on both press and release.".format(pin),level=LL_WARNING)
				else:
					printer("Pin {0}: ERROR: invalid edge detection value.".format(pin),level=LL_ERROR)
			else:
				if gpio_on == GPIO.HIGH:
					GPIO.add_event_detect(pin, GPIO.RISING, callback=handle_switch_interrupt) #
					printer("Pin {0}: Added Rising Edge interrupt; bouncetime=600".format(pin))				
				else:
					GPIO.add_event_detect(pin, GPIO.FALLING, callback=handle_switch_interrupt) #, bouncetime=600
					printer("Pin {0}: Added Falling Edge interrupt; bouncetime=600".format(pin))

			
			pins_state[pin] = GPIO.input(pin)
				
			# consolidated config
			pins_config[pin] = { "dev_name":device['name'], "dev_type":"sw", "gpio_on": gpio_on, "has_multi":False, "has_short":False, "has_long":False, "functions":[] }
			
		if 'clk' in device:
			pin_clk = device['clk']
			pin_dt = device['dt']
			
			printer("Setting up encoder on pins: {0} and {1}".format(pin_clk, pin_dt))
			GPIO.setup((pin_clk,pin_dt), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
			GPIO.add_event_detect(pin_clk, GPIO.RISING, callback=handle_rotary_interrupt) # NO bouncetime 
			GPIO.add_event_detect(pin_dt, GPIO.RISING, callback=handle_rotary_interrupt) # NO bouncetime 
			
			pins_state[pin_clk] = GPIO.input(pin_clk)
			pins_state[pin_dt] = GPIO.input(pin_dt)
			
			# consolidated config
			pins_config[pin_clk] = { "dev_name":device['name'], "dev_type":"clk", "functions":[] }
			pins_config[pin_dt] = { "dev_name":device['name'], "dev_type":"dt", "functions":[] }
					
	# map pins to functions
	for ix, function in enumerate(cfg_ctrlgpio['functions']):
		if 'encoder' in function:		
			device = get_device_config(function['encoder'])
			pin_dt = device['dt']
			pin_clk = device['clk']
			
			#fnc = { "fnc_name":function['name'], "fnc_code":function['function'], "multicount":0 }
			fnc = function
			fnc["fnc_name"]=function['name']
			fnc["fnc_code"]=function['function']			
			fnc["multicount"]=0
			pins_config[pin_dt]["functions"].append(fnc)
			pins_config[pin_clk]["functions"].append(fnc)
			
		if 'short_press' in function:
					
			multicount = len(function['short_press'])
			if multicount == 1:
				device = get_device_config(function['short_press'][0])
				if device is None:
					printer("ID not found in devices: {0}".format(function['short_press'][0]),level=LL_CRITICAL)
					exit(1)
				pin_sw = device['sw']
				pins_config[pin_sw]["has_short"] = True
				pins_config[pin_sw]["has_multi"] = False
				fnc = function
				#fnc = { "fnc_name":function['name'], "fnc_code":function['function'], "press_type":"short", "multicount":0 }
				fnc["fnc_name"]=function['name']
				fnc["fnc_code"]=function['function']
				fnc["press_type"]="short"
				fnc["multicount"]=0
				pins_config[pin_sw]["functions"].append(fnc)
			else:
				#device = get_device_config(function['short_press'][0])
				#pin_sw = device['sw']
				#pins_config[pin_sw]["has_multi"] = True
				multi = []	# list of buttons for multi-press

				# pins_function
				for short_press_button in function['short_press']:
					device = get_device_config(short_press_button)
					pin_sw = device['sw']
					multi.append( pin_sw )
					pins_config[pin_sw]["has_multi"] = True
					if pin_sw in pins_function:
						pins_function[ pin_sw ].append( ix )
					else:
						pins_function[ pin_sw ] = []
						pins_function[ pin_sw ].append( ix )

				#fnc = { "fnc_name":function['name'], "fnc_code":function['function'], "press_type":"short", "multicount":multicount, "multi":multi }
				fnc = function
				fnc["fnc_name"]=function['name']
				fnc["fnc_code"]=function['function']
				fnc["press_type"]="short"
				fnc["multicount"]=multicount
				fnc["multi"]=multi
				pins_config[pin_sw]["functions"].append(fnc)
				
		if 'long_press' in function:

			multicount = len(function['long_press'])
			if multicount == 1:
				device = get_device_config(function['long_press'][0])
				if device is None:
					printer("ID not found in devices: {0}".format(function['long_press'][0]),level=LL_CRITICAL)
					exit(1)
				pin_sw = device['sw']
				pins_config[pin_sw]["has_long"] = True
				pins_config[pin_sw]["has_multi"] = False
				fnc = { "fnc_name":function['name'], "fnc_code":function['function'], "press_type":"long", "multicount":0 }
				pins_config[pin_sw]["functions"].append(fnc)
			else:
				#device = get_device_config(function['long_press'][0])
				#pin_sw = device['sw']
				#pins_config[pin_sw]["has_multi"] = True
				multi = []	# list of buttons for multi-press

				# pins_function
				for short_press_button in function['long_press']:
					device = get_device_config(short_press_button)
					pin_sw = device['sw']
					multi.append( pin_sw )
					pins_config[pin_sw]["has_multi"] = True
					if pin_sw in pins_function:
						pins_function[ pin_sw ].append( ix )
					else:
						pins_function[ pin_sw ] = []
						pins_function[ pin_sw ].append( ix )

				fnc = { "fnc_name":function['name'], "fnc_code":function['function'], "press_type":"long", "multicount":multicount, "multi":multi }
				pins_config[pin_sw]["functions"].append(fnc)

	# we sort the functions so that the multi-button functions are on top, the one with most buttons first
	# that way we can reliably check which multi-button combination is pressed, if any.
	# sort pins_config[n]['functions'] by pins_config[n]['functions']['multicount'], highest first
#	for pin in pins_config:
		#newlist = sorted(list_to_be_sorted, key=lambda k: k['name'])
#		newlist = sorted(pins_config[pin]['functions'], key=lambda k: k['multicount'], reverse=True)
#		print "DEBUG: Sorted function list: -- todo:test --"
#		print newlist
		#pins_config[pin]['functions'] = newlist
				
	# check for any duplicates, but don't exit on it. (#todo: consider making this configurable)
	if len(pins_monitor) != len(set(pins_monitor)):
		printer("WARNING: Same pin used multiple times, this may lead to unpredictable results.",level=LL_WARNING)
		pins_monitor = set(pins_monitor) # no use in keeping duplicates
	

	printer('Initialized [OK]')
	print "\nDEBUG; pins_function:"
	print pins_function
	
	print "DEBUG; pins_config:"
	print pins_config
		
def main():		

	# Initialize the mainloop
	#DBusGMainLoop(set_as_default=True)
	#mainloop = gobject.MainLoop()

	#try:
	#	mainloop.run()
	#finally:
	#	mainloop.quit()
	
	while True:
		sleep(0.1)


if __name__ == "__main__":
	parse_args()
	setup()
	try:
		main()
	finally:
		GPIO.cleanup()
	