#!/usr/bin/python

#
# GPIO Remote Control
# Venema, S.R.G.
# 2018-04-29
#
# GPIO remote control enables GPIO input for buttons and encoders.
#
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

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "GPIO Remote Control"
WELCOME = "GPIO Controller Daemon"
LOG_TAG = 'GPIO'
LOGGER_NAME = 'gpio'

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560

#DELAY = 0.005
DELAY = 0.01
LONG_PRESS = 5

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

pins_monitor = []		# list of pins to monitor
pins_state = {}			# pin (previous) state
pins_function = {}		# pin function(s)
pins_config = {}		# consolidated config, key=pin

active_modes = []

'''
pins_config = 
	{ "23": {
		dev_name
		dev_type
		functions: [ {
			fnc_name
			fnc_code
			fnc_short_press/fnc_long_press
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
	
	#for function_ix in pins_function[pin]:
	for func_cfg in pins_config[pin]['functions']:
		
		#func_cfg = cfg_ctrlgpio['functions'][function_ix]
		#ok = True
		
		# check mode #TODO!! TODO!! add mode here!!
		if 'mode' in func_cfg and func_cfg['mode'] not in active_modes:
			print "DEBUG: not in the required mode"
			return None
		else:
			#if 'encoder' in func_cfg:
			return func_cfg

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
	

def handle_switch_interrupt(pin):
	""" Callback function for switches
	"""
	
	print "DEBUG: HANDLE_SWITCH_INTERRUPT! for pin: {0}".format(pin)
	
	press_start = clock()

	# nothing to do, if no attached function
	if pin not in pins_function:
		print "WHat??"
		return None	
	
	# check wheather we have short and/or long press functions and multi-press functions
	if pins_config[pin]['has_short'] and not pins_config[pin]['has_long']:
		# short only, handle it..		
		if not pins_config[pin]['has_multi']:
			print "EXECUTING THE SHORT FUNCTION (only option)"
		else:
			# todo try combinations with highest button count first (even though overlap is not recommended)
			print "checking multi-button..."
			for function_ix in pins_function[pin]:
				func_cfg = cfg_ctrlgpio['functions'][function_ix]
				button_count = len( func_cfg['short_press'] )
				if button_count > 1:
					i = 0
					for switch in func_cfg['short_press']:
						if GPIO.input(switch) == pins_config[pin]['gpio_on']:
							i += 1
					print "i={0}. if i<count then not all buttons are pressed".format(i)
					if i == button_count:
						print "WE HAVE A MULTI-BUTTON MATCH! Stop"
				else:
					single_button_value = GPIO.input(func_cfg['short_press'][0])
					
			print "no multi-button match, trying single-button (value={0})".format(single_button_value)
			if single_button_value == pins_config[pin]['gpio_on']:
				print "SINGLE BUTTON MATCH! Stop"
			else:
				print "No single-button match. Stop."
		
		#sp_func = get_function_by_ptm(pin,'short_press',mode)
		#print function_map[sp_func['function']]
	else:
		# wait for release of button
		# handle according to press length

		printer("Waiting for button to be released")
		pressed = True
		while pressed == True or press_time >= LONG_PRESS:
			state = GPIO.input(pin)
			if state != pins_config[pin]['gpio_on']:
				pressed = False
			press_time = clock()-press_start
			delay(0.01)
				
		print "DEBUG"
		print "switch was pressed for {0} seconds".format(press_time)
		
		if pins_config[pin]['has_long'] and not pins_config[pin]['has_short']:
			print "EXECUTING THE LONG FUNCTION (only long)"
		elif press_time >= LONG_PRESS and pins_config[pin]['has_long']:
			print "EXECUTING THE LONG FUNCTION (long enough pressed)"
		elif press_time < LONG_PRESS and pins_config[pin]['has_short']:
			print "EXECUTING THE SHORT FUNCTION (not long enough pressed)"
		else:
			print "No Match!"	
		

# Rotarty encoder interrupt:
# this one is called for both inputs from rotary switch (A and B)
def handle_rotary_interrupt(pin):
	global pins_state
	
	print "DEBUG: HANDLE_ROTARY_INTERRUPT! for pin: {0}".format(pin)
	
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
	print function
	if function is not None:

		if (Switch_A and Switch_B):						# Both one active? Yes -> end of sequence
			if pin == encoder_pinB:							# Turning direction depends on 
				#clockwise
				#print function_map[func_cfg['function']]
				print "ENCODER: INCREASE"
				#function_map[func_cfg['function']] = { "zmq_path":"volume", "zmq_command":"PUT" }
			else:
				#counter clockwise
				#print function_map[func_cfg['function']]
				print "ENCODER: DECREASE"

	
#********************************************************************************
# Parse command line arguments
#
def parse_args():

	import argparse
	global args

	parser = argparse.ArgumentParser(description=DESCRIPTION)
	parser.add_argument('--loglevel', action='store', default=DEFAULT_LOG_LEVEL, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('--config','-c', action='store', help='Configuration file', default=DEFAULT_CONFIG_FILE)
	parser.add_argument('-b', action='store_true', default=False)
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
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
	global encoder1_cnt
	global encoder1_last_clk_state
	global pins_monitor
	global pins_function
	global cfg_ctrlgpio
	cfg_ctrlgpio = configuration['daemons'][4]

	GPIO.setmode(GPIO.BCM)

	# init all pins in configuration
	#for ix, device in enumerate(cfg_ctrlgpio['devices']):
	for device in cfg_ctrlgpio['devices']:
		if 'sw' in device:
			#pin = cfg_ctrlgpio['devices'][ix]['sw']
			pin = device['sw']
			pins_monitor.append(pin)
			
			printer("Setting up pin: {0}".format(pin))
			GPIO.setup(pin, GPIO.IN)
			
			# get pull up/down setting
			if device['gpio_pullupdown'] == 'up':
				#GPIO.set_pullupdn(pin, pull_up_down=GPIO.PUD_UP)	#v0.10
				GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
				printer("Pin {0}: Pull-up resistor enabled".format(pin))
			elif device['gpio_pullupdown'] == 'down':
				#GPIO.set_pullupdn(pin, pull_up_down=GPIO.PUD_DOWN)	#v0.10
				GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
				printer("Pin {0}: Pull-down resistor enabled".format(pin))
			else:
				printer('ERROR: invalid pull_up_down value.',level=LL_ERROR)

			# setup edge detection trigger type
			if device['gpio_edgedetect'] == 'rising':
				GPIO.add_event_detect(pin, GPIO.RISING, callback=handle_switch_interrupt, bouncetime=400)
				printer("Pin {0}: Added Rising Edge interrupt; bouncetime=200".format(pin))
			elif device['gpio_edgedetect'] == 'falling':
				GPIO.add_event_detect(pin, GPIO.FALLING, callback=handle_switch_interrupt, bouncetime=400)
				printer("Pin {0}: Added Falling Edge interrupt; bouncetime=200".format(pin))
			elif device['gpio_edgedetect'] == 'both':
				GPIO.add_event_detect(pin, GPIO.BOTH, callback=handle_switch_interrupt, bouncetime=400)
				printer("Pin {0}: Added Both Rising and Falling Edge interrupt; bouncetime=200".format(pin))
				printer("Pin {0}: Warning: detection both high and low level will cause an event to trigger on both press and release.".format(pin),level=LL_WARNING)
			else:
				printer("Pin {0}: ERROR: invalid edge detection value.".format(pin),level=LL_ERROR)
			
			# convert high/1, low/0 to bool
			if device['gpio_on'] == "high" or device['gpio_on'] == 1:
				gpio_on = GPIO.HIGH
			else:
				gpio_on = GPIO.LOW

			pins_state[pin] = GPIO.input(pin)
				
			# consolidated config
			pins_config[pin] = { "dev_name":device['name'], "dev_type":"sw", "gpio_on": gpio_on, "has_multi":False, "has_short":False, "has_long":False }
			
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
			pins_config[pin_clk] = { "dev_name":device['name'], "dev_type":"clk" }		
			pins_config[pin_dt] = { "dev_name":device['name'], "dev_type":"dt" }
			

	# map pins to functions
	for ix, function in enumerate(cfg_ctrlgpio['functions']):
		if 'encoder' in function:		
			device = get_device_config(function['encoder'])
			pin_clk = device['clk']
			
			# pins_function is a dictionary of pins
			if pin_clk in pins_function:
				pins_function[ pin_clk ].append( ix )	#functions['name']
			else:
				pins_function[ pin_clk ] = []
				pins_function[ pin_clk ].append( ix )

			# consolidated config
			fnc = { "fnc_name":function['name'], "fnc_code":function['function'] }
			if 'functions' in pins_config[pin_clk]:
				pins_config[pin_clk]["functions"].append(fnc)
			else:
				pins_config[pin_clk]["functions"] = []
				pins_config[pin_clk]["functions"].append(fnc)
				
		if 'short_press' in function:
		
			if len(function['short_press']) > 1:
				pins_config[pin_sw]["has_multi"] = True
				
			for short_press_button in function['short_press']:
				device = get_device_config(short_press_button)
				pin_sw = device['sw']
				if pin_sw in pins_function:
					pins_function[ pin_sw ].append( ix )
				else:
					pins_function[ pin_sw ] = []
					pins_function[ pin_sw ].append( ix )
					
			# consolidated config
			fnc = { "fnc_name":function['name'], "fnc_code":function['function'] }
			pins_config[pin_sw]["has_short"] = True
			if 'functions' in pins_config[pin_sw]:
				pins_config[pin_sw]["functions"].append(fnc)
			else:
				pins_config[pin_sw]["functions"] = []
				pins_config[pin_sw]["functions"].append(fnc)
				
		if 'long_press' in function:
			# consolidated config
			pin_sw=0#todo
			pins_config[pin_sw]["has_long"] = True
				
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

	global encoder1_cnt
	global encoder1_last_clk_state
	
	#temp:
	global clk
	global dt
	
	def button_down_wait():		
		#printer("Waiting for button to be released...")
		value_0 = adc.read_adc(0)
		while value_0 > BUTTON_LO:
			value_0 = adc.read_adc(0)
			sleep(0.1)
		#printer("...released")
		
	def button_down_delay():

		press_count = 0
		
		printer("Waiting for button to be released/or max. press count reached")
		value_0 = adc.read_adc(0)
		while value_0 > BUTTON_LO and press_count < 2:
			press_count+=1
			printer(press_count)
			value_0 = adc.read_adc(0)
			sleep(0.1)
		#printer("...released/max. delay reached")
	
	def handle_button_press( path, cmd ):
		messaging.publish_command(path,cmd)
		"""
			if button_spec['delay']:
				button_down_delay()
			elif button_spec['wait']:
				button_down_wait()
		else:
			printer('No function configured for this button')
		"""
							
			
	while True:

		# loop through monitored pins, looking for changes
		# ?? CAN WE USE INTERRUPTS? ??

		''' using INT's now...
		long_press_start = None

		for pin in pins_monitor:
			if pins_state[pin] != GPIO.input(pin):
				# pin has changed; handle it, pref. asynchronous..
				
				# if this button also has a long press function, then execute on button release
				# if this button only has a short press function, then execute on press
				# if this button has a delay, then repeat until delay time finished [todo]
				
				# wait for release:
					handle_pin_change(pin,pins_state[pin],GPIO.input(pin))
				pins_state[pin] = GPIO.input(pin)
		'''
	
		"""
		clkState = GPIO.input(clk)
		dtState = GPIO.input(dt)
		if clkState != encoder1_last_clk_state:
			if dtState != clkState:
				encoder1_cnt += 1
				zmq_path = "/volume/increase"
				zmq_cmd = "PUT"
				handle_button_press(zmq_path,zmq_cmd)
			else:
				encoder1_cnt -= 1
				zmq_path = "/volume/decrease"
				zmq_cmd = "PUT"
				handle_button_press(zmq_path,zmq_cmd)
				
			print encoder1_cnt
		encoder1_last_clk_state = clkState
		"""
		
		"""
		
		# did user let go of a long-press button?
		if long_press_ix and value_0 < BUTTON_LO:
			long_press_ix = None
	
		ix = 0
		for button in buttonfunc:
			if ( button['channel0_lo'] <= value_0 <= button['channel0_hi']):
				if ('channel1_lo' and 'channel1_hi' in button):
					if (button['channel1_lo'] <= value_1 <= button['channel1_hi']):
						handle_button_press(button)
				else:
					if 'long_press' in button:
						if not long_press_ix:
							printer("Waiting for button to be pressed at least {0} seconds".format(button['long_press']))
							long_press_ix = ix
							long_press_start = clock()
						else:
							printer("DEBUG LP diff ={0}".format(clock()-long_press_start))
							if clock()-long_press_start > button['long_press']:
								handle_button_press(button)
					else:
						# check if another button is pressed before completing the long-press
						if long_press_ix and not ix == long_press_ix:
							long_press_ix = None
						handle_button_press(button)
			ix += 1
		
		"""
		sleep(DELAY)

if __name__ == "__main__":
	parse_args()
	setup()
	try:
		main()
	finally:
		GPIO.cleanup()
	