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

# zmq
subscriber = None
publisher = None


# ********************************************************************************
# Zero MQ functions
#
def zmq_connect():

	global subscriber
	global publisher
	
	printer("Connecting to ZeroMQ forwarder")

	zmq_ctx = zmq.Context()
	port_client = "5559"
	publisher = zmq_ctx.socket(zmq.PUB)
	publisher.connect("tcp://localhost:{0}".format(port_client))
	
def zmq_send(path_send,message):

	global publisher

	#TODO
	data = json.dumps(message)
	printer("Sending message: {0} {1}".format(path_send, data))
	publisher.send("{0} {1}".format(path_send, data))
	time.sleep(1)


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

	# ADC remote variables
	GAIN = 2/3
	BUTTON_LO   = 100
	BUTTON01_LO = 180	# Bottom button
	BUTTON01_HI = 190	#   starts at around 185, but then spikes to around 278
	BUTTON02_LO = 220	# Side button, with raised center line
	BUTTON02_HI = 260	
	BUTTON03_LO = 310	# 
	BUTTON03_HI = 330	
	BUTTON04_LO = 380	# 
	BUTTON04_HI = 410	
	BUTTON05_LO = 460	# 
	BUTTON05_HI = 490	
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

	buttonfunc.append( {
	   "channel0_lo": 180
	 , "channel0_hi": 190
	 , "delay"      : None
	 , "zmq_msg"    : "\player\update SET" } )
	
	adc = Adafruit_ADS1x15.ADS1015()
	#pavol = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')
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
	
	while True:
		value_0 = adc.read_adc(0, gain=GAIN)
		value_1 = adc.read_adc(1, gain=GAIN)
		
		if buttonfunc[0]['channel0_lo'] <= value_0 <= buttonfunc[0]['channel0_hi']
			#Bottom button
			zmq_send(buttonfunc[0]['zmq_msg'])
			#button_press('UPDATE_LOCAL')
			#Wait until button is released (no need to continue updating...)
			button_down_wait()			

		elif BUTTON02_LO <= value_0 <= BUTTON02_HI:
			#Side button, met streepje
			print('BUTTON02')

		elif BUTTON03_LO <= value_0 <= BUTTON03_HI:
			button_press('VOL_UP')
			
		elif BUTTON04_LO <= value_0 <= BUTTON04_HI:
			button_press('VOL_DOWN')
			
		elif BUTTON05_LO <= value_0 <= BUTTON05_HI:
			if value_1 < 300:
				button_press('SEEK_NEXT')
			else:
				button_press('DIR_NEXT')
			#Wait a little...
			button_down_delay()
			
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