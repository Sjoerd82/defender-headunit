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
LOG_TAG = 'GPIO'
LOGGER_NAME = 'gpio'

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560

DELAY = 0.005

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


logger = None
args = None
messaging = None

encoder1_cnt = 0
encoder1_last_clk_state = None
#temp
clk = None
dt = None

pins_monitor = []		# list of pins to monitor
pins_state = {}			# pin (previous) state
pins_function = {}		# pin function(s)

active_modes = []

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
	cfg_ctrlgpio = configuration['daemons'][4]

	GPIO.setmode(GPIO.BCM)

	# init all pins in configuration
	for ix, device in enumerate(cfg_ctrlgpio['devices']):
		if 'sw' in device:
			pin = cfg_ctrlgpio['devices'][ix]['sw']
			pins_monitor.append(pin)
			GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)	
			pins_state[pin] = GPIO.input(pin)
		if 'clk' in device:
			pin = cfg_ctrlgpio['devices'][ix]['clk']
			pins_monitor.append(pin)
			GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)	
			pins_state[pin] = GPIO.input(pin)
		#We don't need to monitor the DT-pin!
		#if 'dt' in device:
			pin = cfg_ctrlgpio['devices'][ix]['dt']
			#pins_monitor.append(pin)
			GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)	
			pins_state[pin] = GPIO.input(pin)
		
		if 'type' == 'rotenc':
			#encoder1_last_clk_state = GPIO.input(clk)
			#encoder1_cnt = 0
			pass

	# map pins to functions
	for ix, function in enumerate(cfg_ctrlgpio['functions']):
		if 'encoder' in function:		
			device = cfg_ctrlgpio['devices'][functions['encoder']]
			pin_clk = device['clk']
			if pin_clk in pins_function:
				pins_function[ pin_clk ].append( ix )	#functions['name']
			else:
				pins_function[ pin_clk ] = []
				pins_function[ pin_clk ].append( ix )
			
		if 'short_press' in function:
			pass
		
		if 'long_press' in function:
			pass
			
	# check for any duplicates, but don't exit on it. (#todo: consider making this configurable)
	if len(pins_monitor) != len(set(pins_monitor)):
		printer("WARNING: Same pin used multiple times, this may lead to unpredictable results.",level=LL_WARNING)
		pins_monitor = set(pins_monitor) # no use in keeping duplicates
	
	# initialize pins
	#for pin in pins_monitor:
	#	GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)	
	
	#temp:
	global clk
	global dt

	clk = cfg_ctrlgpio['encoder_1']['clk']
	dt = cfg_ctrlgpio['encoder_1']['dt']
	#btn = cfg_ctrlgpio['encoder_1']['btn']
	#GPIO.setup(clk, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	#GPIO.setup(dt, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	encoder1_cnt = 0
	encoder1_last_clk_state = GPIO.input(clk)

	printer('Initialized [OK]')
		
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
		
	def get_device_config(name):
		for device in cfg_ctrlgpio['devices']:
			if device['name'] == name:
				return device
		return None
	
	def handle_pin_change(pin):
		print "DEBUG: handle pin change for pin: {0}".format(pin)
		
		print "function(s) on this pin are:"
		print pins_function[pin]
		
		for function_ix in pins_function:
			#examine if func meets all requirements
			func_cfg = cfg_ctrlgpio['functions'][function_ix]
			ok = True
			
			# check mode
			if 'mode' in func_cfg and func_cfg['mode'] not in active_modes:
				print "DEBUG: not in the required mode"
			else:
				# encoder: check dt pin
				if 'encoder' in func_cfg:
					device_cfg = get_device_config( cfg_ctrlgpio['encoder'] )
					pin_clk = pin
					pin_dt = device_cfg['dt']
					#if dtState != clkState:
					if pins_state[dt] != pins_state[clk]:
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
							
			
	while True:

		# get all states
		for pin in pins_monitor:
			if pins_state[pin] != GPIO.input(pin):
				pins_state[pin] = GPIO.input(pin)
				# handle this pin, pref. asynchronous..
				handle_pin_change(pin)
				
	
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
	