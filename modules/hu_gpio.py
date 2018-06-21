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
import copy						# deepcopy
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
from hu_datastruct import CircularModeset
from hu_commands import Commands

import json

#********************************************************************************
# GPIO stuff
#
class GpioController(object):

	def __init__(self, cfg_gpio, cb_function, logger=None):
		"""
		cfg_gpio is a configuration dictionary.
		cb_function is the callback_function which is called whenever a function needs executing.
		Optionally, provide a logger if you want feedback.
		"""
	
		# configuration (dictionary)
		self.cfg_gpio = cfg_gpio

		# callbacks
		self.callback_function = cb_function
		staticmethod(self.callback_function)
			
		# (optional) logger
		self.LOG_TAG = 'GPIO'
		self.logger = logger

		
		# pins
		self.pins_state = {}		# pin (previous) state
		self.pins_function = {}		# pin function(s)
		self.pins_config = {}		# consolidated config, key=pin
		
		# mode sets
		self.mode_sets = {}			# contains set of modes()
		self.ms_all = {}			# contains the different modesets, key=modeset name
		#self.ms.set_cb_mode_change(cb_mode_change)
		
		self.long_press_ms = 800

		# experimental -- detect speed
		self.encoder_last_chg = datetime.now()
		self.encoder_last_speed = None
		self.encoder_fast_count = 0
		
		if cb_function is None:
			self.gpio_setup()
		else:
			self.gpio_setup(self.int_handle_switch,self.int_handle_encoder)
	
	def __printer( self, message, level=LL_INFO, tag=None):
		if self.logger is not None:
			if tag is None: tag = self.LOG_TAG
			self.logger.log(level, message, extra={'tag': tag})

	def __cb_mode_change(self, list_of_modes):
		"""
		Called by modeset whenever a new mode becomes active. List_of_modes is a list of mode-dictionaries.
		Source: Modeset.state_change
		"""
		exec_function_by_code('MODE-CHANGE',list_of_modes)	
	
	def __active_modes(self):
		"""
		Returns a list of all active modes across all modesets.
		"""
		ret_active = []
		for key,val in self.ms_all.iteritems():
			ret_active.extend( val.active() )
		print "Active (all): {0}".format(ret_active)	# ToDo clean-up
		return ret_active
		
	def get_modes(self):
		""" Returns Mode-structure containing all modes and states of all sets. """
		
		return self.ms.get_modes()
		
		master_modes_list = Modes()
		for mode_set_id,mode_set in self.mode_sets.iteritems():
			if mode_set_id != 'active_modes':
				master_modes_list.extend(mode_set['mode_list'])
			
		return copy.deepcopy(master_modes_list)		# list of dicts, requires deepcopy() instead of copy()
		
	
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
			if 'mode' in func_cfg and func_cfg['mode'] not in self.__active_modes():
				pass # these are not the mode you're looking for
			else:
				#if 'encoder' in func_cfg:
				return func_cfg
				
		return None				

	def exec_function_by_code(self,code,param=None):
		"""
		Kind of like a pass-through function to execute a code.
		Code are executed by passing them back to our owner for execution.
		
		The user can configure any command available in the commands class.
		Consider making this a json file...
		
		We will already validate the command before passing it back.
		"""		
		
		if code is None:
			return
			
		cmd_exec = Commands()
		if code not in cmd_exec.command_list:
			return
		
		if param is not None:
			if isinstance(param, (str, unicode)):
				param = [param]
		
		valid = cmd_exec.validate_args(code,param)
		print "DEBUG: EXEC ding, ret = {0}, param = {1}".format(valid, param)
		self.callback_function(code)	# calls call-back function
			
			
			
			
		"""
		if code in function_map:
			zmq_path = function_map[code]['zmq_path']
			zmq_command = function_map[code]['zmq_command']
			arguments = None
			messaging.publish_command(zmq_path,zmq_command,arguments)
		else:
			print "function {0} not in function_map".format(code)
		"""
	'''
	def cb_mode_reset(self,mode_set_id):
		""" Reset Timer call back """
		# set active mode
		base_mode = self.mode_sets[mode_set_id]['base_mode']
		if base_mode is None:
			self.mode_sets[mode_set_id]['mode_list'].unset_active_modes([base_mode])
		else:
			self.mode_sets[mode_set_id]['mode_list'].set_active_modes([base_mode])
		
		# just printin'
		self.__printer('[MODE] Reset to: "{0}"'.format(self.mode_sets[mode_set_id]['base_mode']))
		
		
		# call that other callback
		master_modes_list = self.get_modes()
		self.callback_mode_change(copy.deepcopy(master_modes_list))
	'''

	def handle_mode(self,pin,function_ix):
		""" If function has a mode_cycle attribute, then handle that.
			Called by interrupt handlers.
		"""
		function = self.pins_config[pin]['functions'][function_ix]

		if 'mode_cycle' in function: # and 'mode' in self.pins_config[pin]:	
			self.ms.next()
			'''
			# new
			mode_list = self.mode_sets[function['mode_cycle']]['mode_list']
			current_active_mode = mode_list.get_active_mode()
			mode_ix = mode_list.unique_list().index(current_active_mode)
			mode_old = mode_list[mode_ix]['name']
			mode_base = self.mode_sets[function['mode_cycle']]['base_mode']
					
			if mode_ix >= len(mode_list)-1:
				mode_ix = 0
			else:
				mode_ix += 1
			mode_new = mode_list[mode_ix]['name']
			
			mode_list.set_active_modes(mode_new)
			self.callback_mode_change(copy.deepcopy(mode_list))
			
			# reset
			if 'reset' in self.mode_sets[function['mode_cycle']]:
			
				if mode_new == mode_base:
					self.__printer("[MODE] Changed from: '{0}' to: '{1}' (base mode; no reset timer)".format(mode_old,mode_new)) # LL_DEBUG TODO
					# > self.timer_mode.cancel()
					self.ms.reset_cancel(function['mode_cycle'])
				else:
					# > reset_time = self.mode_sets[function['mode_cycle']]['reset']
					# > self.__printer("[MODE] Changed from: '{0}' to: '{1}'. Reset timer set to seconds: {2}".format(mode_old,mode_new,reset_time)) # LL_DEBUG TODO
					# > self.reset_mode_timer(reset_time,function['mode_cycle'])
					self.__printer("[MODE] Changed from: '{0}' to: '{1}'. Reset timer started.".format(mode_old,mode_new)) # LL_DEBUG TODO
					#self.ms.reset_start(function['mode_cycle'])
					self.ms.reset_start()
			
			else:
				self.__printer("[MODE] Changed from: '{0}' to: '{1}' without reset.".format(mode_old,mode_new)) # LL_DEBUG TODO
			'''

	'''
	def reset_mode_timer(self,seconds,mode_set_id):
		""" reset the mode time-out if there is still activity in current mode """
		#mode_timer = 0
		#gobject.timeout_add_seconds(function['mode_reset'],self.cb_mode_reset,pin,function_ix)
		if self.timer_mode is not None:
			self.timer_mode.cancel()
		self.timer_mode = Timer(seconds, self.cb_mode_reset, [mode_set_id])
		self.timer_mode.start()
	'''
					
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
		
		#print "DEBUG: self.int_handle_switch! for pin: {0}".format(pin)
		
		# check wheather we have short and/or long press functions and multi-press functions
		if self.pins_config[pin]['has_short'] and not self.pins_config[pin]['has_long'] and not self.pins_config[pin]['has_multi']:
			""" Only a SHORT function, no long press functions, no multi-button, go ahead and execute """
			self.__printer("Executing short function, as it is the only option") # LL_DEBUG #TODO
			
			# execute, checking mode
			for ix, fun in enumerate(self.pins_config[pin]['functions']):
				if 'mode' in fun:
					if fun['mode'] in self.__active_modes():
						self.exec_function_by_code(fun['function'])
					else:
						print "DEBUG mode mismatch"
				else:
					if 'mode_select' in fun and 'mode_cycle' in fun:
						#self.handle_mode(pin,ix)
						self.ms_all[fun['mode_cycle']].next()
					self.exec_function_by_code(fun['function'])
				
			return

		if (self.pins_config[pin]['has_long'] or self.pins_config[pin]['has_short']) and not self.pins_config[pin]['has_multi']:
			""" LONG + possible short press functions, no multi-buttons, go ahead and execute, if pressed long enough """
			self.__printer("Button pressed (pin {0}), waiting for button to be released....".format(pin))
			pressed = True
			while True: #pressed == True or press_time >= self.long_press_ms:
				state = GPIO.input(pin)
				if state != self.pins_config[pin]['gpio_on']:
					pressed = False
					break
				if press_time >= self.long_press_ms:
					print "TIMEOUT"
					break
				#press_time = (clock()-press_start)*1000
				delta = datetime.now() - press_start
				press_time = int(delta.total_seconds() * 1000)
				sleep(0.005)
				
			if press_time >= self.long_press_ms and self.pins_config[pin]['has_long']:
				self.__printer("Button was pressed for {0}ms (threshold={1}). Executing long function.".format(press_time,self.long_press_ms))	# TODO: LL_DEBUG
				
				# execute, checking mode
				for ix, fun in enumerate(self.pins_config[pin]['functions']):
					if fun['press_type'] == 'long':
						if 'mode' in fun:
							if fun['mode'] in self.__active_modes():
								self.exec_function_by_code(fun['function'])
							else:
								print "DEBUG mode mismatch"
						else:
							if 'mode_select' in fun and 'mode_cycle' in fun:
								#self.handle_mode(pin,ix)
								self.ms_all[fun['mode_cycle']].next()
							self.exec_function_by_code(fun['function'])			
				
			elif press_time > 0 and press_time < self.long_press_ms and self.pins_config[pin]['has_short']:
				self.__printer("Button was pressed for {0}ms (threshold={1}). Executing short function.".format(press_time,self.long_press_ms))	# TODO: LL_DEBUG
				
				# execute, checking mode
				for ix, fun in enumerate(self.pins_config[pin]['functions']):
					if fun['press_type'] == 'short':
						if 'mode' in fun:
							if fun['mode'] in self.__active_modes():
								self.exec_function_by_code(fun['function'])
							else:
								print "DEBUG mode mismatch"
						else:
							if 'mode_select' in fun and 'mode_cycle' in fun:
								#self.handle_mode(pin,ix)
								self.ms_all[fun['mode_cycle']].next()
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
			
				if 'mode' in function and function['mode'] in self.__active_modes():
			
					multi_match = True
					for multi_pin in function['multi']:
						if not GPIO.input(multi_pin) == self.pins_config[pin]['gpio_on']:
							multi_match = False
					if multi_match == True:
						if function['press_type'] == 'short_press':
							matched_short_press_function_code = function['function']
						elif function['press_type'] == 'long_press':
							matched_long_press_function_code = function['function']
					
			self.__printer("Waiting for button to be released....")
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
		#print function
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
				if self.modes.active_modes():
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
			self.__printer("Error: 'devices'-section missing in configuration.", level=LL_CRITICAL)
			return False
			
		if not 'functions' in self.cfg_gpio:
			self.__printer("Error: 'functions'-section missing in configuration.", level=LL_CRITICAL)
			return False

		# get global settings (default already set)
		if 'self.long_press_ms' in self.cfg_gpio:
			self.long_press_ms = self.cfg_gpio['self.long_press_ms']
			
		# modes
		if 'mode_sets' in self.cfg_gpio:
			
			self.__printer("Mode sets:")
			for mode_set in self.cfg_gpio['mode_sets']:
				self.ms_all[mode_set['id']] = CircularModeset()	# GPIO only uses circular modesets, meaning only one active mode per set.
				self.ms_all[mode_set['id']].set_cb_mode_change(__cb_mode_change)	# calls __cb_mode_change when a mode changes (actually: when a new mode becomes active)

				# basemode
				if 'base_mode' in mode_set:
					self.ms_all[mode_set['id']].basemode = mode_set['base_mode']
					base_mode = mode_set['base_mode'] #	DEBUG print
								
				if 'reset' in mode_set:
					self.ms_all[mode_set['id']].reset_enable(mode_set['reset'])
					self.__printer("> {0}; resets to {1} after {2} seconds".format(mode_set['id'],base_mode,mode_set['reset'])) # LL_DEBUG TODO
				else:
					self.__printer("> {0} (no reset)".format(mode_set['id'])) # LL_DEBUG TODO
				
				for i, mode in enumerate(mode_set['mode_list']):
					self.ms_all[mode_set['id']].append(mode)
					
					# debug feedback
					dbg_base = ""
					if mode == base_mode: dbg_base = "(base)"
					self.__printer("  {0} {1} {2}".format(i,mode,dbg_base)) # LL_DEBUG TODO
			
		else:
			self.__printer("WARNING: No 'mode_sets'-section.", level=LL_WARNING)
		
		# initialize all pins in configuration
		pins_monitor = []
		for device in self.cfg_gpio['devices']:
			if 'type' in device and device['type'] == 'led':
				# Normal led
				pin = device['pin']
				self.__printer("Setting up pin: {0}".format(pin))
				GPIO.setup(pin, GPIO.OUT)
				
			if 'type' in device and device['type'] == 'rgb':
				# RGB led
				pin_r = device['r']
				pin_g = device['g']
				pin_b = device['b']
				self.__printer("Setting up pins: {0}, {1} and {2}".format(pin_r, pin_g, pin_b))
				GPIO.setup(pin_r, GPIO.OUT)
				GPIO.setup(pin_g, GPIO.OUT)
				GPIO.setup(pin_b, GPIO.OUT)
				
				
			if 'sw' in device and int_switch is not None:
				#pin = self.cfg_gpio['devices'][ix]['sw']
				pin = device['sw']
				pins_monitor.append(pin)
				
				self.__printer("Setting up pin: {0}".format(pin))
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
							self.__printer("Pin {0}: Pull-down resistor enabled".format(pin))
						else:
							#GPIO.set_pullupdn(pin, pull_up_down=GPIO.PUD_UP)	#v0.10
							GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
							self.__printer("Pin {0}: Pull-up resistor enabled".format(pin))
					elif device['gpio_pullupdown'] == False:
						pass
					elif device['gpio_pullupdown'] == 'up':
						#GPIO.set_pullupdn(pin, pull_up_down=GPIO.PUD_UP)	#v0.10
						GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
						self.__printer("Pin {0}: Pull-up resistor enabled".format(pin))
					elif device['gpio_pullupdown'] == 'down':
						#GPIO.set_pullupdn(pin, pull_up_down=GPIO.PUD_DOWN)	#v0.10
						GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
						self.__printer("Pin {0}: Pull-down resistor enabled".format(pin))
					else:
						self.__printer("ERROR: invalid pull_up_down value. This attribute is optional. Valid values are: True, 'up' and 'down'.",level=LL_ERROR)

				# edge detection trigger type
				# valid settings are: "rising", "falling" or both
				# if left out, the trigger will be based on the on-level
				if 'gpio_edgedetect' in device:				
					if device['gpio_edgedetect'] == 'rising':
						GPIO.add_event_detect(pin, GPIO.RISING, callback=int_switch) #
						self.__printer("Pin {0}: Added Rising Edge interrupt; bouncetime=600".format(pin))
					elif device['gpio_edgedetect'] == 'falling':
						GPIO.add_event_detect(pin, GPIO.FALLING, callback=int_switch) #
						self.__printer("Pin {0}: Added Falling Edge interrupt; bouncetime=600".format(pin))
					elif device['gpio_edgedetect'] == 'both':
						GPIO.add_event_detect(pin, GPIO.BOTH, callback=int_switch) #
						self.__printer("Pin {0}: Added Both Rising and Falling Edge interrupt; bouncetime=600".format(pin))
						self.__printer("Pin {0}: Warning: detection both high and low level will cause an event to trigger on both press and release.".format(pin),level=LL_WARNING)
					else:
						self.__printer("Pin {0}: ERROR: invalid edge detection value.".format(pin),level=LL_ERROR)
				else:
					if gpio_on == GPIO.HIGH:
						GPIO.add_event_detect(pin, GPIO.RISING, callback=int_switch) #
						self.__printer("Pin {0}: Added Rising Edge interrupt; bouncetime=600".format(pin))				
					else:
						GPIO.add_event_detect(pin, GPIO.FALLING, callback=int_switch) #, bouncetime=600
						self.__printer("Pin {0}: Added Falling Edge interrupt; bouncetime=600".format(pin))

				
				self.pins_state[pin] = GPIO.input(pin)
					
				# consolidated config
				self.pins_config[pin] = { "dev_name":device['name'], "dev_type":"sw", "gpio_on": gpio_on, "has_multi":False, "has_short":False, "has_long":False, "functions":[] }
				
			if 'clk' in device and int_encoder is not None:
				pin_clk = device['clk']
				pin_dt = device['dt']
				
				self.__printer("Setting up encoder on pins: {0} and {1}".format(pin_clk, pin_dt))
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
						self.__printer("ID not found in devices: {0}".format(function['short_press'][0]),level=LL_CRITICAL)
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
						self.__printer("ID not found in devices: {0}".format(function['long_press'][0]),level=LL_CRITICAL)
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
			self.__printer("WARNING: Same pin used multiple times, this may lead to unpredictable results.",level=LL_WARNING)
			pins_monitor = set(pins_monitor) # no use in keeping duplicates

	'''
	def set_cb_mode_change(self,cb_function):
		self.callback_mode_change = cb_function
		staticmethod(self.callback_mode_change)
	'''