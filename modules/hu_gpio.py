#
# GPIO
# Venema, S.R.G.
# 2018-05-13
#
# GPIO stuff
# 
#

# BUGS:
# printer() doesn't work! WTF?

import sys						# path
import os						# 
from time import sleep
#from time import clock			# cpu time, not easily relateable to ms.
from datetime import datetime
from datetime import timedelta

from logging import getLogger	# logger
from RPi import GPIO			# GPIO
from threading import Timer		# timer to reset mode change

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_datastruct import Modes

#********************************************************************************
# GPIO stuff
#
class GpioController(object):

	def __init__(self, cfg_gpio, cb_function=None):
		self.cfg_gpio = cfg_gpio

		# callbacks
		#staticmethod(int_switch)
		self.callback_function = cb_function
		staticmethod(self.callback_function)
		
		self.callback_mode_change = None
		
		# pins
		self.pins_state = {}			# pin (previous) state
		self.pins_function = {}		# pin function(s)
		self.pins_config = {}		# consolidated config, key=pin

		self.mode_sets = {}
		self.modes = Modes()
		
		self.active_modes = []
		self.long_press_ms = 800
		self.timer_mode = None		# timer object

		# experimental -- detect speed
		self.encoder_last_chg = datetime.now()
		self.encoder_last_speed = None
		self.encoder_fast_count = 0
		
		if cb_function is None:
			self.gpio_setup()
		else:
			self.gpio_setup(self.int_handle_switch,self.int_handle_encoder)
	
	def set_cb_mode_change(self,cb_function):
		self.callback_mode_change = cb_function
		staticmethod(self.callback_mode_change)
	
	def get_modes(self):
		master_modes_list = Modes()
		for mode_set in self.mode_sets:
			print mode_set #['mode_list']
			print type(mode_set)
			master_modes_list.extend(mode_set['mode_list'])
		return master_modes_list
	
	# ********************************************************************************
	# GPIO helpers
	# 
	def get_device_config(self,name):
		for device in self.cfg_gpio['devices']:
			if device['name'] == name:
				return device
		return None
		
	def get_device_config_by_pin(self,pin):
		for device in self.cfg_gpio['devices']:
			if device['clk'] == pin:
				return device
			elif device['dt'] == pin:
				return device
			elif device['sw'] == pin:
				return device
		return None

	def get_encoder_function_by_pin(self,pin):
		""" Returns function dictionary
		"""
		# loop through all possible functions for given pin
		# examine if func meets all requirements (only one check needed for encoders: mode)
		
		for func_cfg in self.pins_config[pin]['functions']:
			# check mode #TODO!! TODO!! add mode here!!
			if 'mode' in func_cfg and func_cfg['mode'] not in self.active_modes:
				pass # these are not the mode you're looking for
			else:
				#if 'encoder' in func_cfg:
				return func_cfg
				
		return None				

	def exec_function_by_code(self,code,param=None):
		print "EXECUTE: {0} {1}".format(code,param)
		self.callback_function(code)
		"""
		if code in function_map:
			zmq_path = function_map[code]['zmq_path']
			zmq_command = function_map[code]['zmq_command']
			arguments = None
			messaging.publish_command(zmq_path,zmq_command,arguments)
		else:
			print "function {0} not in function_map".format(code)
		"""
		

	def cb_mode_reset(self,mode_set_id):
		self.mode_sets[mode_set_id]['mode_list'].set_active_modes(['volume'])
		
		master_modes_list = Modes()
		for set in self.modes_sets:
			master_modes_list.extend(set['mode_list'])
		
		#self.callback_mode_change(self.mode_sets[mode_set_id]['mode_list'][:])	# return a copy
		self.callback_mode_change(master_modes_list)

	def handle_mode(self,pin,function_ix):
		""" If function has a mode_cycle attribute, then handle that.
			Called by interrupt handlers.
		"""
		function = self.pins_config[pin]['functions'][function_ix]

		if 'mode_cycle' in function: # and 'mode' in self.pins_config[pin]:		
			print "DEBUG: handle_mode()"
			
			# new
			mode_list = self.mode_sets[function['mode_cycle']]['mode_list']
			current_active_mode = mode_list.get_active_mode()
			mode_ix = mode_list.unique_list().index(current_active_mode)
			mode_old = mode_list[mode_ix]['name']
					
			if mode_ix >= len(mode_list)-1:
				mode_ix = 0
			else:
				mode_ix += 1
			mode_new = mode_list[mode_ix]['name']
			
			#printer("Mode changed from {0} to: {1}".format(mode_old,mode_new)) # LL_DEBUG
			print("Mode changed from {0} to: {1}".format(mode_old,mode_new)) # LL_DEBUG
			mode_list.set_active_modes(mode_new)
			self.callback_mode_change(mode_list)
			
			if 'reset' in self.mode_sets[function['mode_cycle']]:
				reset_time = self.mode_sets[function['mode_cycle']]['reset']
				print "Starting mode reset timer, seconds: {0}".format(reset_time)
				self.reset_mode_timer(reset_time,function['mode_cycle'])

	def reset_mode_timer(self,seconds,mode_set_id):
		""" reset the mode time-out if there is still activity in current mode """
		#mode_timer = 0
		#gobject.timeout_add_seconds(function['mode_reset'],self.cb_mode_reset,pin,function_ix)
		if self.timer_mode is not None:
			self.timer_mode.cancel()
		self.timer_mode = Timer(seconds, self.cb_mode_reset, [mode_set_id])
		self.timer_mode.start()
					
	# ********************************************************************************
	# GPIO interrupt handlers
	# 
	def int_handle_switch(self,pin):
		""" Callback function for switches """
		#press_start = clock()
		press_start = datetime.now()
		press_time = 0 #datetime.now() - datetime.now()	# wtf?
		
		# debounce
		#if 'debounce' in self.pins_config[pin]:
		#	debounce = self.pins_config[pin]['debounce'] / 1000
		#	print "DEBUG: sleeping: {0}".format(debounce)
		#	sleep(debounce)
		#	
		sleep(0.02)
		if not GPIO.input(pin) == self.pins_config[pin]['gpio_on']:
			return None
		
		print "DEBUG: self.int_handle_switch! for pin: {0}".format(pin)

		# try-except?
		""" why do we do this?
		print "DEBUG THIS!!"
		# if active_modes is empty then we don't need to check the mode
		if self.active_modes:
		
			#
			#self.reset_mode_timer(self.modes_old[0]['reset'])
			
			if 'reset' in self.mode_sets[function['mode_cycle']]:
				self.reset_mode_timer(self.mode_sets[function['mode_cycle']]['reset'])
		"""

		# check wheather we have short and/or long press functions and multi-press functions
		if self.pins_config[pin]['has_short'] and not self.pins_config[pin]['has_long'] and not self.pins_config[pin]['has_multi']:
			""" Only a SHORT function, no long press functions, no multi-button, go ahead and execute """
			print "EXECUTING THE SHORT FUNCTION (only option)..."
			
			# execute, checking mode
			for ix, fun in enumerate(self.pins_config[pin]['functions']):
				if 'mode' in fun:
					if fun['mode'] in self.active_modes:
						self.exec_function_by_code(fun['function'])
					else:
						print "DEBUG mode mismatch"
				else:
					if 'mode_toggle' in fun or 'mode_select' in fun:
						self.handle_mode(pin,ix)
					self.exec_function_by_code(fun['function'])
				
			return

		if (self.pins_config[pin]['has_long'] or self.pins_config[pin]['has_short']) and not self.pins_config[pin]['has_multi']:
			""" LONG + possible short press functions, no multi-buttons, go ahead and execute, if pressed long enough """
			print "EXECUTING THE LONG or SHORT FUNCTION, DEPENDING ON PRESS TIME."

			printer("Waiting for button to be released....")
			pressed = True
			while True: #pressed == True or press_time >= self.long_press_ms:
				state = GPIO.input(pin)
				if state != self.pins_config[pin]['gpio_on']:
					print "RELEASED!"
					pressed = False
					break
				if press_time >= self.long_press_ms:
					print "TIMEOUT"
					break
				#press_time = (clock()-press_start)*1000
				delta = datetime.now() - press_start
				press_time = int(delta.total_seconds() * 1000)
				sleep(0.005)
				
			print "switch was pressed for {0} miliseconds".format(press_time) #,press_start,clock())

			if press_time >= self.long_press_ms and self.pins_config[pin]['has_long']:
				print "EXECUTING THE LONG FUNCTION (long enough pressed)"
				
				# execute, checking mode
				for ix, fun in enumerate(self.pins_config[pin]['functions']):
					if fun['press_type'] == 'long':
						if 'mode' in fun:
							if fun['mode'] in self.active_modes:
								self.exec_function_by_code(fun['function'])
							else:
								print "DEBUG mode mismatch"
						else:
							if 'mode_toggle' in fun or 'mode_select' in fun:
								self.handle_mode(pin,ix)
							self.exec_function_by_code(fun['function'])			
				
			elif press_time < self.long_press_ms and self.pins_config[pin]['has_short']:
				print "EXECUTING THE SHORT FUNCTION (not long enough pressed)"
				
				# execute, checking mode
				for ix, fun in enumerate(self.pins_config[pin]['functions']):
					if fun['press_type'] == 'short':
						if 'mode' in fun:
							if fun['mode'] in self.active_modes:
								self.exec_function_by_code(fun['function'])
							else:
								print "DEBUG mode mismatch"
						else:
							if 'mode_toggle' in fun or 'mode_select' in fun:
								self.handle_mode(pin,ix)
							self.exec_function_by_code(fun['function'])

			else:
				print "No Match!"
				
			return
			
		# check wheather we have short and/or long press functions and multi-press functions
		if self.pins_config[pin]['has_multi']:
			""" There are multi-button combinations possible. The function pin list is sorted with highest button counts first.
				Looping from top to bottom we will check if any of these are valid.	"""
			print "checking multi-button..."
			matched_short_press_function_code = None
			matched_long_press_function_code = None
			for function in self.pins_config[pin]['functions']:
			
				if 'mode' in function and function['mode'] in self.active_modes:
			
					multi_match = True
					for multi_pin in function['multi']:
						if not GPIO.input(multi_pin) == self.pins_config[pin]['gpio_on']:
							multi_match = False
					if multi_match == True:
						if function['press_type'] == 'short_press':
							matched_short_press_function_code = function['function']
						elif function['press_type'] == 'long_press':
							matched_long_press_function_code = function['function']
					
			printer("Waiting for button to be released....")
			pressed = True
			while pressed == True or press_time >= self.long_press_ms:
				state = GPIO.input(pin)
				if state != self.pins_config[pin]['gpio_on']:
					print "RELEASED!"
					pressed = False
					break
				#press_time = clock()-press_start
				delta = datetime.now() - press_start
				press_time = int(delta.total_seconds() * 1000)
				sleep(0.01)
					
			print "....done"
			print "switch was pressed for {0} ms".format(press_time)
			
	#			if self.pins_config[pin]['has_long'] and not self.pins_config[pin]['has_short']:
	#				print "EXECUTING THE LONG FUNCTION (only long)"
			if press_timemiliseconds >= self.long_press_ms and self.pins_config[pin]['has_long'] and matched_long_press_function_code is not None:
				print "EXECUTING THE LONG FUNCTION (long enough pressed)"
			elif press_timemiliseconds < self.long_press_ms and self.pins_config[pin]['has_short'] and matched_short_press_function_code is not None:
				print "EXECUTING THE SHORT FUNCTION (not long enough pressed)"
			else:
				print "No Match!"

	def int_handle_encoder(self,pin):
		""" Called for either inputs from rotary switch (A and B) """
		
		#print "DEBUG: self.int_handle_encoder! for pin: {0}".format(pin)
			
		device = self.get_device_config_by_pin(pin)
		
		encoder_pinA = device['clk']
		encoder_pinB = device['dt']
		#print "DEBUG! Found encoder pins:"
		#print encoder_pinA
		#print encoder_pinB

		Switch_A = GPIO.input(encoder_pinA)
		Switch_B = GPIO.input(encoder_pinB)
														# now check if state of A or B has changed
														# if not that means that bouncing caused it	
		Current_A = self.pins_state[encoder_pinA]
		Current_B = self.pins_state[encoder_pinB]
		if Current_A == Switch_A and Current_B == Switch_B:		# Same interrupt as before (Bouncing)?
			return										# ignore interrupt!

		self.pins_state[encoder_pinA] = Switch_A								# remember new state
		self.pins_state[encoder_pinB] = Switch_B								# for next bouncing check
		
		# -------------------------------
		
		function = self.get_encoder_function_by_pin(pin)
		if function is not None:

			if (Switch_A and Switch_B):						# Both one active? Yes -> end of sequence
			
				this_chg = datetime.now()
				delta = this_chg - self.encoder_last_chg
				#print "diff: {0}".format(delta.total_seconds())
				#print type(delta.total_seconds())	#float
				if delta.total_seconds() < 0.1:
					self.encoder_fast_count += 1
					#if self.encoder_fast_count > 3:
					#	print "FAST {0}".format(self.encoder_fast_count)
					#else:
					#	print "Maybe....."
				else:
					self.encoder_fast_count = 0
			
				""" why do we do this?
				if self.active_modes:
					#self.reset_mode_timer(self.modes_old[0]['reset'])
					if 'reset' in self.mode_sets[function['mode_cycle']]:
						self.reset_mode_timer(self.mode_sets[function['mode_cycle']]['reset'])
				"""

				if pin == encoder_pinB:							# Turning direction depends on 
					#counter clockwise
					#print "[Encoder] {0}: DECREASE/CCW".format(function['function_ccw'])
					if self.encoder_fast_count > 3 and 'function_fast_ccw' in function:
						self.exec_function_by_code(function['function_fast_ccw'],'ccw')
					elif 'function_ccw' in function:
						self.exec_function_by_code(function['function_ccw'],'ccw')
				else:
					#clockwise
					#print "[Encoder] {0}: INCREASE/CW".format(function['function_cw'])
					if self.encoder_fast_count > 3 and 'function_fast_cw' in function:
						self.exec_function_by_code(function['function_fast_cw'],'cw')
					elif 'function_cw' in function:
						self.exec_function_by_code(function['function_cw'],'cw')
					
				self.encoder_last_chg = this_chg


	# ********************************************************************************
	# GPIO setup
	# 
	def gpio_setup(self,int_switch=None,int_encoder=None):
		
		# gpio mode: BCM or board
		if 'gpio_mode' in self.cfg_gpio:
			if self.cfg_gpio['gpio_mode'] == 'BCM':
				GPIO.setmode(GPIO.BCM)
			elif self.cfg_gpio['gpio_mode'] == 'BOARD':
				GPIO.setmode(GPIO.BOARD)
		else:
			GPIO.setmode(GPIO.BCM)	# default

		# check if mandatory sections present
		if not 'devices' in self.cfg_gpio:
			printer("Error: 'devices'-section missing in configuration.", level=LL_CRITICAL)
			return False
			
		if not 'functions' in self.cfg_gpio:
			printer("Error: 'functions'-section missing in configuration.", level=LL_CRITICAL)
			return False

		# get global settings (default already set)
		if 'self.long_press_ms' in self.cfg_gpio:
			self.long_press_ms = self.cfg_gpio['self.long_press_ms']
			
		# set mode, if configured
		#if 'start_mode' in self.cfg_gpio:
		#	self.active_modes.append(self.cfg_gpio['start_mode'])
		#else:
		#	self.active_modes.append(None)
				
		# modes
		if 'mode_sets' in self.cfg_gpio:
			if len(self.cfg_gpio['mode_sets']) > 1:
				printer("WARNING: Multiple modes specified, but currently one one set is supported (only loading the first).", level=LL_WARNING)
			
			# deprecated:
			#self.modes_old.append(self.cfg_gpio['mode_sets'][0])
			
			for mode_set in self.cfg_gpio['mode_sets']:
				new_mode_set = {}
				new_mode_set['id'] = mode_set['id']
				new_mode_set['mode_list'] = Modes()
				new_mode_set['reset'] = mode_set['reset']
				for mode in mode_set['mode_list']:
					new_mode = {}
					new_mode['name'] = mode
					if mode == mode_set['base_mode']:
						new_mode['state'] = True
					else:
						new_mode['state'] = False
					new_mode_set['mode_list'].append(new_mode)
					
				self.mode_sets[mode_set['id']] = new_mode_set
				
			print self.mode_sets
				
		else:
			# don't deal with modes at all
			if len(self.active_modes) > 0:
				printer("WARNING: No 'mode_sets'-section, modes will not be available.", level=LL_WARNING)
			self.active_modes = []
		
		# initialize all pins in configuration
		pins_monitor = []
		for device in self.cfg_gpio['devices']:
			if 'type' in device and device['type'] == 'led':
				# Normal led
				pin = device['pin']
				printer("Setting up pin: {0}".format(pin))
				GPIO.setup(pin, GPIO.OUT)
				
			if 'type' in device and device['type'] == 'rgb':
				# RGB led
				pin_r = device['r']
				pin_g = device['g']
				pin_b = device['b']
				printer("Setting up pins: {0}, {1} and {2}".format(pin_r, pin_g, pin_b))
				GPIO.setup(pin_r, GPIO.OUT)
				GPIO.setup(pin_g, GPIO.OUT)
				GPIO.setup(pin_b, GPIO.OUT)
				
				
			if 'sw' in device and int_switch is not None:
				#pin = self.cfg_gpio['devices'][ix]['sw']
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
						GPIO.add_event_detect(pin, GPIO.RISING, callback=int_switch) #
						printer("Pin {0}: Added Rising Edge interrupt; bouncetime=600".format(pin))
					elif device['gpio_edgedetect'] == 'falling':
						GPIO.add_event_detect(pin, GPIO.FALLING, callback=int_switch) #
						printer("Pin {0}: Added Falling Edge interrupt; bouncetime=600".format(pin))
					elif device['gpio_edgedetect'] == 'both':
						GPIO.add_event_detect(pin, GPIO.BOTH, callback=int_switch) #
						printer("Pin {0}: Added Both Rising and Falling Edge interrupt; bouncetime=600".format(pin))
						printer("Pin {0}: Warning: detection both high and low level will cause an event to trigger on both press and release.".format(pin),level=LL_WARNING)
					else:
						printer("Pin {0}: ERROR: invalid edge detection value.".format(pin),level=LL_ERROR)
				else:
					if gpio_on == GPIO.HIGH:
						GPIO.add_event_detect(pin, GPIO.RISING, callback=int_switch) #
						printer("Pin {0}: Added Rising Edge interrupt; bouncetime=600".format(pin))				
					else:
						GPIO.add_event_detect(pin, GPIO.FALLING, callback=int_switch) #, bouncetime=600
						printer("Pin {0}: Added Falling Edge interrupt; bouncetime=600".format(pin))

				
				self.pins_state[pin] = GPIO.input(pin)
					
				# consolidated config
				self.pins_config[pin] = { "dev_name":device['name'], "dev_type":"sw", "gpio_on": gpio_on, "has_multi":False, "has_short":False, "has_long":False, "functions":[] }
				
			if 'clk' in device and int_encoder is not None:
				pin_clk = device['clk']
				pin_dt = device['dt']
				
				printer("Setting up encoder on pins: {0} and {1}".format(pin_clk, pin_dt))
				GPIO.setup((pin_clk,pin_dt), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
				GPIO.add_event_detect(pin_clk, GPIO.RISING, callback=int_encoder) # NO bouncetime 
				GPIO.add_event_detect(pin_dt, GPIO.RISING, callback=int_encoder) # NO bouncetime 
				
				self.pins_state[pin_clk] = GPIO.input(pin_clk)
				self.pins_state[pin_dt] = GPIO.input(pin_dt)
				
				# consolidated config
				self.pins_config[pin_clk] = { "dev_name":device['name'], "dev_type":"clk", "functions":[] }
				self.pins_config[pin_dt] = { "dev_name":device['name'], "dev_type":"dt", "functions":[] }
						
		# map pins to functions
		for ix, function in enumerate(self.cfg_gpio['functions']):
			if 'encoder' in function:		
				device = self.get_device_config(function['encoder'])
				pin_dt = device['dt']
				pin_clk = device['clk']
				
				#fnc = { "fnc_name":function['name'], "fnc_code":function['function'], "multicount":0 }
				fnc = function
				fnc["fnc_name"]=function['name']
				#fnc["fnc_code"]=function['function']			
				fnc["multicount"]=0
				self.pins_config[pin_dt]["functions"].append(fnc)
				self.pins_config[pin_clk]["functions"].append(fnc)
				
			if 'short_press' in function:
						
				multicount = len(function['short_press'])
				if multicount == 1:
					device = self.get_device_config(function['short_press'][0])
					if device is None:
						printer("ID not found in devices: {0}".format(function['short_press'][0]),level=LL_CRITICAL)
						exit(1)
					pin_sw = device['sw']
					self.pins_config[pin_sw]["has_short"] = True
					self.pins_config[pin_sw]["has_multi"] = False
					fnc = function
					#fnc = { "fnc_name":function['name'], "fnc_code":function['function'], "press_type":"short", "multicount":0 }
					fnc["fnc_name"]=function['name']
					#fnc["fnc_code"]=function['function']
					fnc["press_type"]="short"
					fnc["multicount"]=0
					self.pins_config[pin_sw]["functions"].append(fnc)
				else:
					#device = self.get_device_config(function['short_press'][0])
					#pin_sw = device['sw']
					#self.pins_config[pin_sw]["has_multi"] = True
					multi = []	# list of buttons for multi-press

					# self.pins_function
					for short_press_button in function['short_press']:
						device = self.get_device_config(short_press_button)
						pin_sw = device['sw']
						multi.append( pin_sw )
						self.pins_config[pin_sw]["has_multi"] = True
						if pin_sw in self.pins_function:
							self.pins_function[ pin_sw ].append( ix )
						else:
							self.pins_function[ pin_sw ] = []
							self.pins_function[ pin_sw ].append( ix )

					#fnc = { "fnc_name":function['name'], "fnc_code":function['function'], "press_type":"short", "multicount":multicount, "multi":multi }
					fnc = function
					fnc["fnc_name"]=function['name']
					#fnc["fnc_code"]=function['function']
					fnc["press_type"]="short"
					fnc["multicount"]=multicount
					fnc["multi"]=multi
					self.pins_config[pin_sw]["functions"].append(fnc)
					
			if 'long_press' in function:

				multicount = len(function['long_press'])
				if multicount == 1:
					device = self.get_device_config(function['long_press'][0])
					if device is None:
						printer("ID not found in devices: {0}".format(function['long_press'][0]),level=LL_CRITICAL)
						exit(1)
					pin_sw = device['sw']
					self.pins_config[pin_sw]["has_long"] = True
					self.pins_config[pin_sw]["has_multi"] = False
					fnc = { "fnc_name":function['name'], "function":function['function'], "press_type":"long", "multicount":0 }
					self.pins_config[pin_sw]["functions"].append(fnc)
				else:
					#device = self.get_device_config(function['long_press'][0])
					#pin_sw = device['sw']
					#self.pins_config[pin_sw]["has_multi"] = True
					multi = []	# list of buttons for multi-press

					# self.pins_function
					for short_press_button in function['long_press']:
						device = self.get_device_config(short_press_button)
						pin_sw = device['sw']
						multi.append( pin_sw )
						self.pins_config[pin_sw]["has_multi"] = True
						if pin_sw in self.pins_function:
							self.pins_function[ pin_sw ].append( ix )
						else:
							self.pins_function[ pin_sw ] = []
							self.pins_function[ pin_sw ].append( ix )

					fnc = { "fnc_name":function['name'], "function":function['function'], "press_type":"long", "multicount":multicount, "multi":multi }
					self.pins_config[pin_sw]["functions"].append(fnc)

		# we sort the functions so that the multi-button functions are on top, the one with most buttons first
		# that way we can reliably check which multi-button combination is pressed, if any.
		# sort self.pins_config[n]['functions'] by self.pins_config[n]['functions']['multicount'], highest first
	#	for pin in self.pins_config:
			#newlist = sorted(list_to_be_sorted, key=lambda k: k['name'])
	#		newlist = sorted(self.pins_config[pin]['functions'], key=lambda k: k['multicount'], reverse=True)
	#		print "DEBUG: Sorted function list: -- todo:test --"
	#		print newlist
			#self.pins_config[pin]['functions'] = newlist
					
		# check for any duplicates, but don't exit on it. (#todo: consider making this configurable)
		if len(pins_monitor) != len(set(pins_monitor)):
			printer("WARNING: Same pin used multiple times, this may lead to unpredictable results.",level=LL_WARNING)
			pins_monitor = set(pins_monitor) # no use in keeping duplicates

