#!/usr/bin/python

#
# ADS1x15 Remote Control
# Venema, S.R.G.
# 2018-03-11
#
# ADS1x15 remote control is a resistor network remote control using the
# four channel ADS1015 or ADS1115 analog to digital converter.
#
# http://www.ti.com/lit/ds/symlink/ads1115.pdf
#

# MQ: Pub only


# Button presses are NOT asynchronous!! i.e. wait until a button press is handled before the next button can be handled.
# TODO: Consider making them asynchronous, or at least the update lib (long) / volume (short) buttons

# printer -> syslog adds considerable latency!  ?
# (and?) Or.. is it the MQ send() ?

try:
	# ADS1x15 module
	import Adafruit_ADS1x15
except ImportError as err:
	print "Error importing required module: {0}".format(err)
	exit(1)
	
import sys						# path
import os						# 
from time import sleep
from time import clock
from logging import getLogger	# logger

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController



# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "ADS1x15 Remote Control"
BANNER = "ADS1015/ADS1115 Remote Control"
LOG_TAG = 'AD1X15'
LOGGER_NAME = 'ad1x15'

# global variables
logger = None
args = None
messaging = MqPubSubFwdController(origin=LOGGER_NAME)
adc = None

# configuration
cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ


# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

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

	global adc

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
	cfg_dummy = None	#TODO, make load_cfg listen to the configs parameter

	# main
	cfg_main, cfg_zmq, cfg_daemon, cfg_dummy = load_cfg(
		args.config,
		['main','zmq','daemon'],
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
			
	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")	
	messaging.set_address('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()

	#
	# ADC
	#
	adc = Adafruit_ADS1x15.ADS1015()

	printer('Initialized [OK]')
		
def main():

	global adc

	# ADC remote variables
	GAIN = 2/3
	BUTTON_LO   = 100
	
	#button-2-function mapper
	buttonfunc = []

	# Bottom button
	buttonfunc.append( {
	   "channel0_lo": 180
	 , "channel0_hi": 190	# Starts at around 185, but then spikes to around 278
	 , "wait"       : True	# Wait until button is released (no need to continue updating...)
	 , "delay"      : None
	 , "zmq_path"   : "/player/update"
	 , "zmq_cmd"    : "PUT" } )

	# Side button, with raised center line (not assigned any task)
	buttonfunc.append( {
	   "channel0_lo": 220
	 , "channel0_hi": 260
	 , "wait"       : False
	 , "delay"      : None } )

	# Volume UP
	buttonfunc.append( {
	   "channel0_lo": 310
	 , "channel0_hi": 330
	 , "wait"       : False
	 , "delay"      : None
	 , "zmq_path"   : "/volume/increase"
	 , "zmq_cmd"    : "PUT" } )

	# Volume DOWN
	buttonfunc.append( {
	   "channel0_lo": 380
	 , "channel0_hi": 410
	 , "wait"       : False
	 , "delay"      : None
	 , "zmq_path"   : "/volume/decrease"
	 , "zmq_cmd"    : "PUT" } )

	# Next Track 
	buttonfunc.append( {
	   "channel0_lo": 460
	 , "channel0_hi": 490
	 , "channel1_lo": 0
	 , "channel1_hi": 300
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "/player/next"
	 , "zmq_cmd"    : "PUT" } )

	# Next Track / Next Dir (if channel 1 engaged)
	buttonfunc.append( {
	   "channel0_lo": 460
	 , "channel0_hi": 490
	 , "channel1_lo": 301
	 , "channel1_hi": 1100
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "/player/nextdir"
	 , "zmq_cmd"    : "PUT" } )

	# Prev Track
	buttonfunc.append( {
	   "channel0_lo": 560
	 , "channel0_hi": 580
	 , "channel1_lo": 0
	 , "channel1_hi": 300
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "/player/prev"
	 , "zmq_cmd"    : "PUT" } )

	# Prev Track / Prev Dir (if channel 1 engaged)
	buttonfunc.append( {
	   "channel0_lo": 560
	 , "channel0_hi": 580
	 , "channel1_lo": 301
	 , "channel1_hi": 1100
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "/player/prevdir"
	 , "zmq_cmd"    : "PUT" } )

	# Big trianlge (Shuffle)
	buttonfunc.append( {
	   "channel0_lo": 640
	 , "channel0_hi": 670
	 , "wait"       : True
	 , "delay"      : None
	 , "zmq_path"   : "/player/random"
	 , "zmq_cmd"    : "PUT" } )

	# Round button with dot (ATT)
	buttonfunc.append( {
	   "channel0_lo": 740
	 , "channel0_hi": 770
	 , "wait"       : True
	 , "delay"      : None
	 , "zmq_path"   : "/volume/att"
	 , "zmq_cmd"    : "PUT" } )

	# Source
	buttonfunc.append( {
	   "channel0_lo": 890
	 , "channel0_hi": 910
	 , "wait"       : True
	 , "delay"      : None
	 , "zmq_path"   : "/source/next"
	 , "zmq_cmd"    : "PUT" } )

	# Round smooth button (OFF)
	buttonfunc.append( {
	   "channel0_lo": 1050
	 , "channel0_hi": 1110
	 , "wait"       : True
	 , "delay"      : None
	 , "long_press" : 0.10
	 , "zmq_path"   : "/system/halt"
	 , "zmq_cmd"    : "PUT" } )
	 
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
	
	def handle_button_press( button_spec ):
		if 'zmq_path' and 'zmq_cmd' in button_spec:
			#printer("Sending message: {0} {1}".format(button_spec['zmq_path'],button_spec['zmq_cmd']))
			messaging.publish(button_spec['zmq_path'],button_spec['zmq_cmd'])
			if button_spec['delay']:
				button_down_delay()
			elif button_spec['wait']:
				button_down_wait()
		else:
			printer('No function configured for this button')
	
	long_press_ix = None
	long_press_start = None
	while True:
		value_0 = adc.read_adc(0, gain=GAIN)
		value_1 = adc.read_adc(1, gain=GAIN)

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
		if buttonfunc[0]['channel0_lo'] <= value_0 <= buttonfunc[0]['channel0_hi']:
			handle_button_press(buttonfunc[0])

		elif buttonfunc[1]['channel0_lo'] <= value_0 <= buttonfunc[1]['channel0_hi']:
			handle_button_press(buttonfunc[1])

		elif buttonfunc[2]['channel0_lo'] <= value_0 <= buttonfunc[2]['channel0_hi']:
			handle_button_press(buttonfunc[2])
			
		elif buttonfunc[3]['channel0_lo'] <= value_0 <= buttonfunc[3]['channel0_hi']:
			handle_button_press(buttonfunc[3])

		elif (buttonfunc[4]['channel0_lo'] <= value_0 <= buttonfunc[4]['channel0_hi'] and
				('channel1_lo' and 'channel1_hi' in buttonfunc[4]
					and buttonfunc[4]['channel1_lo'] <= value_1 <= buttonfunc[4]['channel1_hi']) ):
			handle_button_press(buttonfunc[4])


		elif ( buttonfunc[5]['channel0_lo'] <= value_0 <= buttonfunc[5]['channel0_hi'] and
				('channel1_lo' and 'channel1_hi' in buttonfunc[5]
					and buttonfunc[5]['channel1_lo'] <= value_1 <= buttonfunc[5]['channel1_hi']) ):
			handle_button_press(buttonfunc[5])
			
		elif (buttonfunc[6]['channel0_lo'] <= value_0 <= buttonfunc[6]['channel0_hi'] and
				('channel1_lo' and 'channel1_hi' in buttonfunc[6]
					and buttonfunc[6]['channel1_lo'] <= value_1 <= buttonfunc[6]['channel1_hi']) ):
			handle_button_press(buttonfunc[6])


		elif ( buttonfunc[7]['channel0_lo'] <= value_0 <= buttonfunc[7]['channel0_hi'] and
				('channel1_lo' and 'channel1_hi' in buttonfunc[7]
					and buttonfunc[7]['channel1_lo'] <= value_1 <= buttonfunc[7]['channel1_hi']) ):
			handle_button_press(buttonfunc[7])
		
		elif buttonfunc[8]['channel0_lo'] <= value_0 <= buttonfunc[8]['channel0_hi']:
			handle_button_press(buttonfunc[8])

		elif buttonfunc[9]['channel0_lo'] <= value_0 <= buttonfunc[9]['channel0_hi']:
			handle_button_press(buttonfunc[9])

		elif buttonfunc[10]['channel0_lo'] <= value_0 <= buttonfunc[10]['channel0_hi']:
			handle_button_press(buttonfunc[10])

		elif buttonfunc[11]['channel0_lo'] <= value_0 <= buttonfunc[11]['channel0_hi']:
			if 'long_press' in buttonfunc[11]:
				printer("Waiting for button to be pressed long enough")
				time.sleep(buttonfunc[11]['long_press'])
				value_0 = adc.read_adc(0, gain=GAIN)
				
				if buttonfunc[11]['channel0_lo'] <= value_0 <= buttonfunc[11]['channel0_hi']:
					handle_button_press(buttonfunc[11])
				else:
					printer("Not pressed long enough, not shutting down")
			
		"""
		
		sleep(0.1)

if __name__ == "__main__":
	parse_args()
	setup()
	main()
	