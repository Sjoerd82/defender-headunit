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
from hu_datastruct import Modeset

#********************************************************************************
# GPIO stuff
#
class GpioController(object):

	def __init__(self, cfg_gpio, cb_function=None, logger=None):
		""" Provide a logger if you want feedback.
		"""
	
		# configuration
		self.cfg_gpio = cfg_gpio
		
		# (optional) logger
		self.LOG_TAG = 'GPIO'
		self.logger = logger

		# (optional) callbacks
		#staticmethod(int_switch)
		self.callback_function = cb_function
		staticmethod(self.callback_function)
		
		self.callback_mode_change = None
		
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

	
	def __active_modes(self):
		ret_active = []
		for key,val in self.ms_all.iteritems():
			ret_active.extend( val.active() )
		print "Active (all): {0}".format(ret_active)
		return ret_active
	
	def set_cb_mode_change(self,cb_function):
		self.callback_mode_change = cb_function
		staticmethod(self.callback_mode_change)
	
	'''
	def set_active_mode(self,mode):
		for mode_set_id,mode_set in self.mode_sets.iteritems():
			if mode_set_id != 'active_modes':
				mode_set['mode_list'].set_active_modes([mode])
		self.__update_active_modes()
		
	def unset_active_mode(self,mode):
		self.__update_active_modes()
		#print "Active modes now: {0}".format(self.mode_sets['active_modes'])
		if mode in self.mode_sets['active_modes']:
			
			for mode_set_id,mode_set in self.mode_sets.iteritems():
				if mode_set_id != 'active_modes':
					mode_set['mode_list'].unset_active_modes([mode])

			self.__update_active_modes()
					
		#else:
		#	print "Mode {0} is not currently active, ignoring request..".format(mode)
	'''
	
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
		self.__update_active_modes()
		for func_cfg in self.pins_config[pin]['functions']:
			# check mode #TODO!! TODO!! add mode here!!
			if 'mode' in func_cfg and func_cfg['mode'] not in self.ms.active(): #self.mode_sets['active_modes']:
				pass # these are not the mode you're looking for
			else:
				#if 'encoder' in func_cfg:
				return func_cfg
				
		return None				

	def exec_function_by_code(self,code,param=None):
		if code is not None:
			#print "exec_function_by_code() EXECUTE: {0} {1}".format(code,param)
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
		
		self.__update_active_modes()
		
		# call that other callback
		master_modes_list = self.get_modes()
		self.callback_mode_change(copy.deepcopy(master_modes_list))
	'''

	''''
	def __update_active_modes(self):
		self.mode_sets['active_modes'] = []	# required?
		
		for mode_set_id,mode_set in self.mode_sets.iteritems():
			if mode_set_id != 'active_modes':
				self.mode_sets['active_modes'].extend(mode_set['mode_list'].active_modes())
		
		"""
		for ix, mode_set in enumerate(self.mode_sets):
			print "{0}: {1}".format(ix,mode_set)
			if 'mode_list' in mode_set:
				print "Yup"
			else:
				print "Nope"

		for ix, mode_set in enumerate(self.mode_sets):
			print "{0}: {1}".format(ix,mode_set)
			if 'mode_list' in mode_set:
				self.mode_sets['active_modes'].extend( [] ) #mode_set[ix]['mode_list'].active_modes() )
				#print mode_set[ix]['mode_list'].active_modes()
				
		"""
	'''
	
	def handle_mode(self,pin,function_ix):
		""" If function has a mode_cycle attribute, then handle that.
			Called by interrupt handlers.
		"""
		function = self.pins_config[pin]['functions'][function_ix]

		if 'mode_cycle' in function: # and 'mode' in self.pins_config[pin]:		
		
			ms.active_next(function['mode_cycle'])
			return
			
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
					self.ms.reset_start(function['mode_cycle'])
			
			else:
				self.__printer("[MODE] Changed from: '{0}' to: '{1}' without reset.".format(mode_old,mode_new)) # LL_DEBUG TODO

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

		# > self.__update_active_modes()
		
		# check wheather we have short and/or long press functions and multi-press functions
		if self.pins_config[pin]['has_short'] and not self.pins_config[pin]['has_long'] and not self.pins_config[pin]['has_multi']:
			""" Only a SHORT function, no long press functions, no multi-button, go ahead and execute """
			self.__printer("Executing short function, as it is the only option") # LL_DEBUG #TODO
			
			# execute, checking mode
			for ix, fun in enumerate(self.pins_config[pin]['functions']):
				if 'mode' in fun:
					if fun['mode'] in self.ms.active(): #self.mode_sets['active_modes']:
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
							if fun['mode'] in self.ms.active(): #self.mode_sets['active_modes']:
								self.exec_function_by_code(fun['function'])
							else:
								print "DEBUG mode mismatch"
						else:
							if 'mode_toggle' in fun or 'mode_select' in fun:
								self.handle_mode(pin,ix)
							self.exec_function_by_code(fun['function'])			
				
			elif press_time > 0 and press_time < self.long_press_ms and self.pins_config[pin]['has_short']:
				self.__printer("Button was pressed for {0}ms (threshold={1}). Executing short function.".format(press_time,self.long_press_ms))	# TODO: LL_DEBUG
				
				# execute, checking mode
				for ix, fun in enumerate(self.pins_config[pin]['functions']):
					if fun['press_type'] == 'short':
						if 'mode' in fun:
							if fun['mode'] in self.ms.active(): #self.mode_sets['active_modes']:
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
			
				if 'mode' in function and function['mode'] in self.ms.active(): #self.mode_sets['active_modes']:
			
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
			
		# set mode, if configured
		#if 'start_mode' in self.cfg_gpio:
		#	self.active_modes.append(self.cfg_gpio['start_mode'])
		#else:
		#	self.active_modes.append(None)
				
		# modes
		
		"""
		mode_sets = {
			"active_modes": []
			"<mode_set_name>":{
				"id":
				"mode_list": modes()
				"reset"
			},
			{}
		}
		"""
		self.mode_sets['active_modes'] = []
		if 'mode_sets' in self.cfg_gpio:
			
			self.__printer("Mode sets:")
			for mode_set in self.cfg_gpio['mode_sets']:
			
				self.ms_all[mode_set['id']] = Modeset()
				
				# basemode
				if 'base_mode' in mode_set:
					self.ms_all[mode_set['id']].basemode = mode_set['base_mode']
					base_mode = mode_set['base_mode'] #	DEBUG print
					
				#	self.__printer("> {0}; resets after {1} seconds".format(new_mode_set['id'],new_mode_set['reset'])) # LL_DEBUG TODO
				#else:
				#	self.__printer("> {0} (no reset)".format(new_mode_set['id'])) # LL_DEBUG TODO
					
				for i, mode in enumerate(mode_set['mode_list']):
					self.ms_all[mode_set['id']].append(mode)
					
					#if mode == new_mode_set['base_mode']:
					#	new_mode['state'] = True
					#else:
					#	new_mode['state'] = False
					#new_mode_set['mode_list'].append(new_mode)
					
					# debug feedback
					dbg_base = ""
					dbg_state = "?"
					if mode == base_mode: dbg_base = "(base)"
					#if new_mode['state'] : dbg_state = "(active) "
					self.__printer("  {0} {1} {2}{3}".format(i,mode,dbg_base,dbg_state)) # LL_DEBUG TODO
					
				#self.mode_sets[mode_set['id']] = new_mode_set
				#self.ms.append(mode_set['id'], new_mode_set['mode_list'])
				
				if 'reset' in mode_set:
					self.ms_all[mode_set['id']].reset_enable(mode_set['reset'] )	# TODO add call-back function
					self.__printer("> {0}; resets to {1} after {2} seconds".format(mode_set['id'],base_mode,mode_set['reset'])) # LL_DEBUG TODO
				else:
					self.__printer("> {0} (no reset)".format(mode_set['id'])) # LL_DEBUG TODO
			
			self.__active_modes()
			exit(0)

			# gather active modes
			# > self.__update_active_modes()
			
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

