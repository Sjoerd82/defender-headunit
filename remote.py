# Loaded by: remote_dbus.py
# Button presses are NOT asynchronous!! i.e. wait until a button press is handled before the next button can be handled.
# TODO: Consider making them asynchronous, or at least the update lib (long) / volume (short) buttons

import dbus.service
import random
import time

import threading

# Import the ADS1x15 module.
import Adafruit_ADS1x15

class RemoteControl(dbus.service.Object):
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

	def __init__(self, bus_name):
		super(RemoteControl,self).__init__(bus_name, "/com/arctura/remote")
		adc = Adafruit_ADS1x15.ADS1015()
		#pavol = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')

		while True:
			value_0 = adc.read_adc(0, gain=self.GAIN)
			value_1 = adc.read_adc(1, gain=self.GAIN)
			if self.BUTTON01_LO <= value_0 <= self.BUTTON01_HI:
				#Bottom button
				self.button_press('UPDATE_LOCAL')
				#Wait until button is released (no need to continue updating...)
				self.button_down_wait()			

			elif self.BUTTON02_LO <= value_0 <= self.BUTTON02_HI:
				#Side button, met streepje
				print('BUTTON02')

			elif self.BUTTON03_LO <= value_0 <= self.BUTTON03_HI:
				self.button_press('VOL_UP')
				
			elif self.BUTTON04_LO <= value_0 <= self.BUTTON04_HI:
				self.button_press('VOL_DOWN')
				
			elif self.BUTTON05_LO <= value_0 <= self.BUTTON05_HI:
				if value_1 < 300:
					self.button_press('SEEK_NEXT')
				else:
					self.button_press('DIR_NEXT')
				#Wait a little...
				self.button_down_delay()
				
			elif self.BUTTON06_LO <= value_0 <= self.BUTTON06_HI:
				if value_1 < 300:
					self.button_press('SEEK_PREV')
				else:
					self.button_press('DIR_PREV')
				#Wait a little...
				self.button_down_delay()

			elif self.BUTTON07_LO <= value_0 <= self.BUTTON07_HI:
				self.button_press('SHUFFLE')
				#Wait until button is released
				self.button_down_wait()

			elif self.BUTTON08_LO <= value_0 <= self.BUTTON08_HI:
				self.button_press('ATT')
				#Wait until button is released
				self.button_down_wait()

			elif self.BUTTON09_LO <= value_0 <= self.BUTTON09_HI:
				self.button_press('SOURCE')
				#Wait until button is released
				self.button_down_wait()

			elif self.BUTTON10_LO <= value_0 <= self.BUTTON10_HI:
				print("Waiting for button to be pressed long enough")
				print value_0
				time.sleep(3)
				value_0 = adc.read_adc(0, gain=self.GAIN)
				print value_0
				if self.BUTTON10_LO <= value_0 <= self.BUTTON10_HI:
					print("Long press, really shutting down...")
					self.button_press('OFF')
				else:
					print("Not pressed long enough, not shutting down")
				
			time.sleep(0.1)		

	@dbus.service.signal("com.arctura.remote", signature='s')
	def button_press(self, button):
		print("Button was pressed")
		
	def button_down_wait(self):
	
		adc = Adafruit_ADS1x15.ADS1015()
		
		print("Waiting for button to be released...")
		value_0 = adc.read_adc(0)
		while value_0 > self.BUTTON_LO:
			value_0 = adc.read_adc(0)
			time.sleep(0.1)
		print("...released")
		
	def button_down_delay(self):
	
		adc = Adafruit_ADS1x15.ADS1015()
		press_count = 0
		
		print("Waiting for button to be released/or max. press count reached")
		value_0 = adc.read_adc(0)
		while value_0 > self.BUTTON_LO and press_count < 2:
			press_count+=1
			print(press_count)
			value_0 = adc.read_adc(0)
			time.sleep(0.1)
		print("...released/max. delay reached")
	