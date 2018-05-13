#
# GPIO
# Venema, S.R.G.
# 2018-05-13
#
# GPIO stuff
# 
#

import sys						# path
import os						# 
from time import sleep
#from time import clock			# cpu time, not easily relateable to ms.
from datetime import datetime
from logging import getLogger	# logger
from RPi import GPIO			# GPIO
from threading import Timer		# timer to reset mode change

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *

function_map = {}
function_map['SOURCE_NEXT'] = { 'zmq_path':'/source/next', 'zmq_command':'PUT' }
function_map['SOURCE_PREV'] = { 'zmq_path':'/source/prev', 'zmq_command':'PUT' }
function_map['SOURCE_PRI_NEXT'] = { 'zmq_path':'/source/next_primary', 'zmq_command':'PUT' }
function_map['SOURCE_PRI_PREV'] = { 'zmq_path':'/source/prev_primary', 'zmq_command':'PUT' }
function_map['SOURCE_CHECK'] = { 'zmq_path':'/source/check', 'zmq_command':'PUT' }
function_map['PLAYER_PAUSE'] = { 'zmq_path':'/player/pause', 'zmq_command':'PUT' }
function_map['PLAYER_RANDOM'] = { 'zmq_path':'/player/random', 'zmq_command':'PUT' }
function_map['PLAYER_NEXT'] = { 'zmq_path':'/player/next', 'zmq_command':'PUT' }
function_map['PLAYER_PREV'] = { 'zmq_path':'/player/prev', 'zmq_command':'PUT' }
function_map['PLAYER_FOLDER_NEXT'] = { 'zmq_path':'/player/next_folder', 'zmq_command':'PUT' }
function_map['PLAYER_FOLDER_PREV'] = { 'zmq_path':'/player/prev_folder', 'zmq_command':'PUT' }
function_map['VOLUME_INC'] = { 'zmq_path':'/volume/master/increase', 'zmq_command':'PUT' }
function_map['VOLUME_DEC'] = { 'zmq_path':'/volume/master/decrease', 'zmq_command':'PUT' }
function_map['VOLUME_ATT'] = { 'zmq_path':'/volume/att', 'zmq_command':'PUT' }
function_map['VOLUME_MUTE'] = { 'zmq_path':'/volume/mute', 'zmq_command':'PUT' }
function_map['SYSTEM_SHUTDOWN'] = { 'zmq_path':'/system/shutdown', 'zmq_command':'PUT' }

#********************************************************************************
# GPIO stuff
#
class GpioController(object):

	def __init__(self, cfg_gpio, int_switch=None, int_encoder=None):
		self.cfg_gpio = cfg_gpio

		# callbacks
		self.cb_int_sw = int_switch
		self.cb_int_en = int_encoder
		
		# pins
		self.pins_state = {}			# pin (previous) state
		self.pins_function = {}		# pin function(s)
		self.pins_config = {}		# consolidated config, key=pin

		self.modes = []
		self.active_modes = []
		self.long_press_ms = 800
		self.timer_mode = None		# timer object

		self.gpio_setup(self.int_handle_switch,self.int_handle_encoder)
	
	
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
		"""
		if code in function_map:
			zmq_path = function_map[code]['zmq_path']
			zmq_command = function_map[code]['zmq_command']
			arguments = None
			messaging.publish_command(zmq_path,zmq_command,arguments)
		else:
			print "function {0} not in function_map".format(code)
		"""
		

	def cb_mode_reset(self): #(pin,function_ix):
		self.active_modes = [ 'track' ]	# FIX THIS!!!!

	def check_mode(self,pin,function_ix):

		function = self.pins_config[pin]['functions'][function_ix]
		print function
		
		"""
		if 'mode_cycle' in function: # and 'mode' in self.pins_config[pin]:
			print "DEBUG: Toggeling Mode"
			if function['mode_toggle'] in self.active_modes:
				self.active_modes.remove(function['mode_toggle'])
				print "DEBUG: Active Mode(s): {0}".format(self.active_modes)
			else:
				self.active_modes.append(function['mode_toggle'])
				print "DEBUG: Active Mode(s): {0}".format(self.active_modes)
				
		el
		"""
		if 'mode_cycle' in function: # and 'mode' in self.pins_config[pin]:		
			for mode in self.active_modes:
					
				#mode_ix = function['mode_select'].index(mode)
				mode_list = self.modes[0]['mode_list']
				mode_ix = mode_list.index(mode)			# get index of mode in mode_list
				if mode_ix is not None:
					mode_old = mode_list[mode_ix]
					self.active_modes.remove(mode_old)
					if mode_ix >= len(mode_list)-1:
						mode_ix = 0
					else:
						mode_ix += 1
					mode_new = mode_list[mode_ix]
					print "Mode change {0} -> {1}".format(mode_old,mode_new)
					self.active_modes.append(mode_new)
					
					if 'reset' in self.modes[0]:
						print "Starting mode reset timer, seconds: {0}".format(self.modes[0]['reset'])
						#if self.timer_mode is not None:
						#	self.timer_mode.cancel()
						#self.timer_mode = Timer(float(self.modes[0]['reset']), self.cb_mode_reset)
						#self.timer_mode.start()
						self.reset_mode_timer(self.modes[0]['reset'])
					break

	def reset_mode_timer(self,seconds):
		""" reset the mode time-out if there is still activity in current mode """
		#mode_timer = 0
		#gobject.timeout_add_seconds(function['mode_reset'],self.cb_mode_reset,pin,function_ix)
		if self.timer_mode is not None:
			self.timer_mode.cancel()
		self.timer_mode = Timer(seconds, self.cb_mode_reset)
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
		staticmethod(self.cb_int_sw)

		# try-except?
		print "DEBUG THIS!!"
		# if active_modes is empty then we don't need to check the mode
		if self.active_modes:
			self.reset_mode_timer(self.modes[0]['reset'])

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
						self.check_mode(pin,ix)
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
								self.check_mode(pin,ix)
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
								self.check_mode(pin,ix)
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
			
				if self.active_modes:
					self.reset_mode_timer(self.modes[0]['reset'])

				if pin == encoder_pinB:							# Turning direction depends on 
					#counter clockwise
					print "[Encoder] {0}: DECREASE/CCW".format(function['function_ccw'])			
					staticmethod(self.cb_int_en)
					self.exec_function_by_code(function['function_ccw'],'ccw')
				else:
					#clockwise
					print "[Encoder] {0}: INCREASE/CW".format(function['function_cw'])
					staticmethod(self.cb_int_en)
					self.exec_function_by_code(function['function_cw'],'cw')


	# ********************************************************************************
	# GPIO setup
	# 
	def gpio_setup(self,int_switch,int_encoder):
		
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
		if 'start_mode' in self.cfg_gpio:
			self.active_modes.append(self.cfg_gpio['start_mode'])
		else:
			self.active_modes.append(None)
		
		# modes
		if 'modes' in self.cfg_gpio:
			if len(self.cfg_gpio['modes']) > 1:
				printer("WARNING: Multiple modes specified, but currently one one set is supported (only loading the first).", level=LL_WARNING)
			self.modes.append(self.cfg_gpio['modes'][0])
		else:
			# don't deal with modes at all
			if len(self.active_modes) > 0:
				printer("WARNING: No 'modes'-section, modes will not be available.", level=LL_WARNING)
			self.active_modes = []
		
		# initialize all pins in configuration
		pins_monitor = []
		for device in self.cfg_gpio['devices']:
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
