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

import sys
import os
import time

# ZeroMQ
import zmq

# ADS1x15 module
import Adafruit_ADS1x15

# Utils
sys.path.append('../modules')
from hu_utils import *


#********************************************************************************
# GLOBAL vars & CONSTANTS
#
CONTROL_NAME='ad1x15'

# adc
adc = None

# zmq
subscriber = None
publisher = None

# ********************************************************************************
# Zero MQ functions
#
def zmq_connect():

	global publisher
	
	printer("Connecting to ZeroMQ forwarder")

	zmq_ctx = zmq.Context()
	port_client = "5559"
	publisher = zmq_ctx.socket(zmq.PUB)
	publisher.connect("tcp://localhost:{0}".format(port_client))
	
def zmq_send(path_send,message):

	global publisher

	#TODO
	#data = json.dumps(message)
	data = message
	printer("Sending message: {0} {1}".format(path_send, data))
	publisher.send("{0} {1}".format(path_send, data))


# TODO!!! the "headunit"-logger is no longer accessible once this script is started "on its own"..
def myprint( message, level, tag ):
	print("[{0}] {1}".format(tag,message))

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=CONTROL_NAME ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

# Button presses are NOT asynchronous!! i.e. wait until a button press is handled before the next button can be handled.
# TODO: Consider making them asynchronous, or at least the update lib (long) / volume (short) buttons

def main():

	global adc

	# ADC remote variables
	GAIN = 2/3
	BUTTON_LO   = 100
	
	BUTTON06_LO = 560	# 
	BUTTON06_HI = 580	
	
	BUTTON07_LO = 640	# 
	BUTTON07_HI = 670	
	
	BUTTON08_LO = 740	# "ATT"
	BUTTON08_HI = 770	
	
	BUTTON09_LO = 890	# "SOURCE"
	BUTTON09_HI = 910	
	
	BUTTON10_LO = 1050	# "OFF"
	BUTTON10_HI = 1100	

	#button-2-function mapper
	buttonfunc = []

	# Bottom button
	buttonfunc.append( {
	   "channel0_lo": 180
	 , "channel0_hi": 190	# Starts at around 185, but then spikes to around 278
	 , "wait"       : True	# Wait until button is released (no need to continue updating...)
	 , "delay"      : None
	 , "zmq_path"   : "\player\update"
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
	 , "zmq_path"   : "\volume\increase"
	 , "zmq_cmd"    : "SET" } )

	# Volume DOWN
	buttonfunc.append( {
	   "channel0_lo": 380
	 , "channel0_hi": 410
	 , "wait"       : False
	 , "delay"      : None
	 , "zmq_path"   : "\volume\decrease"
	 , "zmq_cmd"    : "SET" } )

	# Next Track / Next Dir (if channel 1 engaged)
	buttonfunc.append( {
	   "channel0_lo": 460
	 , "channel0_hi": 490
	 , "channel1_lo": 0
	 , "channel1_hi": 300
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "\player\next"
	 , "zmq_cmd"    : "SET" } )

	# Next Track / Next Dir (if channel 1 engaged)
	buttonfunc.append( {
	   "channel0_lo": 460
	 , "channel0_hi": 490
	 , "channel1_lo": 301
	 , "channel1_hi": 1100
	 , "wait"       : False
	 , "delay"      : True
	 , "zmq_path"   : "\player\nextdir"
	 , "zmq_cmd"    : "SET" } )

	 
	# ADC
	adc = Adafruit_ADS1x15.ADS1015()
	# ZMQ
	zmq_connect()
	printer('Initialized [OK]')

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
			zmq_send(button_spec['zmq_path'],button_spec['zmq_cmd'])
			if button_spec['delay']:
				button_down_delay()
			elif button_spec['wait']:
				button_down_wait()
		else:
			printer('No function configured for this button')
	
	
	while True:
		value_0 = adc.read_adc(0, gain=GAIN)
		value_1 = adc.read_adc(1, gain=GAIN)
		
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
			
#		elif BUTTON05_LO <= value_0 <= BUTTON05_HI:
#			if value_1 < 300:
#				button_press('SEEK_NEXT')
#			else:
#				button_press('DIR_NEXT')
#			#Wait a little...
#			button_down_delay()
			
		elif BUTTON06_LO <= value_0 <= BUTTON06_HI:
			if value_1 < 300:
				button_press('SEEK_PREV')
			else:
				button_press('DIR_PREV')
			#Wait a little...
			button_down_delay()

		elif BUTTON07_LO <= value_0 <= BUTTON07_HI:
			button_press('SHUFFLE')
			#Wait until button is released
			button_down_wait()

		elif BUTTON08_LO <= value_0 <= BUTTON08_HI:
			button_press('ATT')
			#Wait until button is released
			button_down_wait()

		elif BUTTON09_LO <= value_0 <= BUTTON09_HI:
			button_press('SOURCE')
			#Wait until button is released
			button_down_wait()

		elif BUTTON10_LO <= value_0 <= BUTTON10_HI:
			printer("Waiting for button to be pressed long enough")
			time.sleep(3)
			value_0 = adc.read_adc(0, gain=GAIN)
			if BUTTON10_LO <= value_0 <= BUTTON10_HI:
				printer("Long press, really shutting down...")
				button_press('OFF')
			else:
				printer("Not pressed long enough, not shutting down")
			
		time.sleep(0.1)

	
if __name__ == "__main__":
	main()