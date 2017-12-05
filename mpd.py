# Loaded by: dbus_mpd.py

import dbus.service
import random
import time

import threading

class mpdControl(dbus.service.Object):

	def __init__(self, bus_name):
		super(mpdControl,self).__init__(bus_name, "/com/arctura/mpd")

		while True:
			value_0 = 0
			value_1 = 0
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
				self.button_press('OFF')
				
			time.sleep(0.1)		

	@dbus.service.signal("com.arctura.mpd", signature='s')
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
			