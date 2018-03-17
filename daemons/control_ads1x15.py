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

# Button presses are NOT asynchronous!! i.e. wait until a button press is handled before the next button can be handled.
# TODO: Consider making them asynchronous, or at least the update lib (long) / volume (short) buttons

import sys						# path
import os						# 
import time						# sleep
from logging import getLogger	# logger
import Adafruit_ADS1x15			# ADS1x15 module

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MessageController

# *******************************************************************************
# Global variables and constants
#
CONTROL_NAME='ad1x15'

# adc
adc = None

# Logging
DAEMONIZED = None
LOG_TAG = 'AD1X15'
LOGGER_NAME = 'ad1x15'
LOG_LEVEL = LL_INFO
logger = None

# Messaging
messaging = None

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

#********************************************************************************
# Parse command line arguments and environment variables
#
def parse_args():

	import argparse
	
	global LOG_LEVEL
	global DAEMONIZED

	parser = argparse.ArgumentParser(description='ADS1x15 Remote Control')
	parser.add_argument('--loglevel', action='store', default=LL_INFO, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('-b', action='store_true')	# background, ie. no output to console
	args = parser.parse_args()

	LOG_LEVEL = args.loglevel
	DAEMONIZED = args.b	

def setup():

	global messaging
	global adc

	# ZMQ
	messaging = MessageController()
	if not messaging.connect():
		printer("Failed to connect to messenger", level=LL_CRITICAL)

	# ADC
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
	 , "zmq_cmd"    : "SET" } )

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
	 , "zmq_cmd"    : "SET" } )

	# Volume DOWN
	buttonfunc.append( {
	   "channel0_lo": 380
	 , "channel0_hi": 410
	 , "wait"       : False
	 , "delay"      : None
	 , "zmq_path"   : "/volume/decrease"
	 , "zmq_cmd"    : "SET" } )

	# Next Track 
	buttonfunc.append( {
	   "channel0_lo": 460
	 , "channel0_hi": 490
	 , "channel1_lo": 0
	 , "channel1_hi": 300
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "/player/next"
	 , "zmq_cmd"    : "SET" } )

	# Next Track / Next Dir (if channel 1 engaged)
	buttonfunc.append( {
	   "channel0_lo": 460
	 , "channel0_hi": 490
	 , "channel1_lo": 301
	 , "channel1_hi": 1100
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "/player/nextdir"
	 , "zmq_cmd"    : "SET" } )

	# Prev Track
	buttonfunc.append( {
	   "channel0_lo": 560
	 , "channel0_hi": 580
	 , "channel1_lo": 0
	 , "channel1_hi": 300
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "/player/prev"
	 , "zmq_cmd"    : "SET" } )

	# Prev Track / Prev Dir (if channel 1 engaged)
	buttonfunc.append( {
	   "channel0_lo": 560
	 , "channel0_hi": 580
	 , "channel1_lo": 301
	 , "channel1_hi": 1100
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "/player/prevdir"
	 , "zmq_cmd"    : "SET" } )

	# Big trianlge (Shuffle)
	buttonfunc.append( {
	   "channel0_lo": 640
	 , "channel0_hi": 670
	 , "wait"       : True
	 , "delay"      : None
	 , "zmq_path"   : "/player/random"
	 , "zmq_cmd"    : "SET" } )

	# Round button with dot (ATT)
	buttonfunc.append( {
	   "channel0_lo": 740
	 , "channel0_hi": 770
	 , "wait"       : True
	 , "delay"      : None
	 , "zmq_path"   : "/volume/att"
	 , "zmq_cmd"    : "SET" } )

	# Source
	buttonfunc.append( {
	   "channel0_lo": 890
	 , "channel0_hi": 910
	 , "wait"       : True
	 , "delay"      : None
	 , "zmq_path"   : "/source/next"
	 , "zmq_cmd"    : "SET" } )

	# Round smooth button (OFF)
	buttonfunc.append( {
	   "channel0_lo": 1050
	 , "channel0_hi": 1110
	 , "wait"       : True
	 , "delay"      : None
	 , "long_press" : 0.10
	 , "zmq_path"   : "/system/halt"
	 , "zmq_cmd"    : "SET" } )
	 
	def button_press(button):
		printer("Button was pressed: {0}".format(button))
	
	def button_down_wait():

		global adc
		#adc = Adafruit_ADS1x15.ADS1015()
		
		printer("Waiting for button to be released...")
		value_0 = adc.read_adc(0)
		while value_0 > BUTTON_LO:
			value_0 = adc.read_adc(0)
			time.sleep(0.1)
		printer("...released")
		
	def button_down_delay():

		#adc = Adafruit_ADS1x15.ADS1015()
		global adc
		press_count = 0
		
		printer("Waiting for button to be released/or max. press count reached")
		value_0 = adc.read_adc(0)
		while value_0 > BUTTON_LO and press_count < 2:
			press_count+=1
			printer(press_count)
			value_0 = adc.read_adc(0)
			time.sleep(0.1)
		printer("...released/max. delay reached")
	
	def handle_button_press( button_spec ):
		if 'zmq_path' and 'zmq_cmd' in button_spec:

			send_command(button_spec['zmq_path'],button_spec['zmq_cmd'])
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
							long_press_start = time.clock()
						else:
							print "DEBUG LP diff ={0}".format(time.clock()-long_press_start)
							if time.clock()-long_press_start > button['long_press']:
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
		
		time.sleep(0.1)

if __name__ == "__main__":
	parse_args()
	setup()
	main()
	