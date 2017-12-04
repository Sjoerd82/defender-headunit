import dbus.service
import random
import time

import threading

# Import the ADS1x15 module.
import Adafruit_ADS1x15

# Import pulseaudio volume handler
import pa_volume

class RemoteControl(dbus.service.Object):
	# ADC remote variables
	GAIN = 2/3
	BUTTON01_LO = 180
	BUTTON01_HI = 190
	BUTTON02_LO = 220
	BUTTON02_HI = 260
	BUTTON03_LO = 310
	BUTTON03_HI = 330
	BUTTON04_LO = 380
	BUTTON04_HI = 410
	BUTTON05_LO = 460
	BUTTON05_HI = 490
	BUTTON06_LO = 560
	BUTTON06_HI = 580
	BUTTON07_LO = 640
	BUTTON07_HI = 670
	BUTTON08_LO = 740
	BUTTON08_HI = 770
	BUTTON09_LO = 890
	BUTTON09_HI = 910
	BUTTON10_LO = 1050
	BUTTON10_HI = 1100

	def __init__(self, bus_name):
		super(RemoteControl,self).__init__(bus_name, "/com/arctura/remote")
		adc = Adafruit_ADS1x15.ADS1015()
		#pavol = pa_volume()

		while True:
			value_0 = adc.read_adc(0, gain=self.GAIN)
			value_1 = adc.read_adc(1, gain=self.GAIN)
			if self.BUTTON01_LO <= value_0 <= self.BUTTON01_HI:
				#Bottom button
				self.button_press('UPDATE_LOCAL')

			elif self.BUTTON02_LO <= value_0 <= self.BUTTON02_HI:
				#Side button, met streepje
				print('BUTTON02')

			elif self.BUTTON03_LO <= value_0 <= self.BUTTON03_HI:
				#pavol.vol_up()
				self.button_press('VOL_UP')
				
			elif self.BUTTON04_LO <= value_0 <= self.BUTTON04_HI:
				self.button_press('VOL_DOWN')
				
			elif self.BUTTON05_LO <= value_0 <= self.BUTTON05_HI:
				if value_1 < 300:
					self.button_press('SEEK_NEXT')
				else:
					self.button_press('DIR_NEXT')

			elif self.BUTTON06_LO <= value_0 <= self.BUTTON06_HI:
				if value_1 < 300:
					self.button_press('SEEK_PREV')
				else:
					self.button_press('DIR_PREV')

			elif self.BUTTON07_LO <= value_0 <= self.BUTTON07_HI:
				self.button_press('SHUFFLE')

			elif self.BUTTON08_LO <= value_0 <= self.BUTTON08_HI:
				self.button_press('ATT')

			elif self.BUTTON09_LO <= value_0 <= self.BUTTON09_HI:
				self.button_press('SOURCE')

			elif self.BUTTON10_LO <= value_0 <= self.BUTTON10_HI:
				self.button_press('OFF')
				
			time.sleep(0.1)

	@dbus.service.signal("com.arctura.remote", signature='s')
	def button_press(self, button):
		print("Button was pressed")