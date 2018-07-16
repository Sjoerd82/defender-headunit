#
# GPIO
# Venema, S.R.G.
# 2018-05-13
#
# The GPIO CONTROLLER Class provides an interface to execute functions on actions.
# Supports Modesets.
#

import sys						# path
import os						# 
import copy						# deepcopy
from time import sleep
#from time import clock			# cpu time, not easily relateable to ms.
from datetime import datetime
from datetime import timedelta

from logging import getLogger	# logger
from threading import Timer		# timer to reset mode change

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_RPi_GPIO import GpioWrapper
from hu_utils import *
from hu_datastruct import CircularModeset
from hu_commands import Commands

import json

#********************************************************************************
# GPIO stuff
#
class GpioController(object):
	"""	
	Public functions:
	  modeset(mode_set_id)		Return mode set as list of dicts
	  modesets()				Return all mode sets as dict[id] of list of modes
	  set_mode(mode)			Set mode to active
	  change_modes( ** )		Change list of modes
	  activemodes()				Return list of all active modes
	 
	 Callbacks:
	   callback_function(		Whenever a function needs executing
	       command, params )
	   callback_mode_change(?)	Whenever a mode changes
	"""

	def __init__(self, cfg_gpio, cb_function=None, cb_mode_change=None, logger=None):
		"""
		cfg_gpio 		is a configuration dictionary.
		cb_function		is the callback_function called when a function needs executing.
		cb_mode_change 	is the callback function called on mode change
		logger			Optionally, provide a logger if you want feedback.
		"""
	
		self.gpio = GpioWrapper()
	
		# CONSTANTS
		self.RGB_PWM_FREQ = 100
	
		#TEMP - DEBUG - EXPERIMENTAL
		self.int_encoder = None
		self.int_enabled = True
	
		# configuration (dictionary)
		self.cfg_gpio = cfg_gpio

		# callbacks
		if cb_function is not None:
			self.callback_function = cb_function
			staticmethod(self.callback_function)
		
		if cb_mode_change is not None:
			self.callback_mode_change = cb_mode_change
			staticmethod(self.callback_mode_change)
			
		# (optional) logger
		if logger is not None:
			self.LOG_TAG = 'GPIO'
			self.logger = logger
			self.__printer("GpioController initializing.",level=LL_DEBUG)
	
		# pins
		self.pins_state = {}		# pin (previous) state
		self.pins_function = {}		# pin function(s)
		self.pins_config = {}		# consolidated config, key=pin
		
		# mode sets
		self.ms_all = {}			# contains the different modesets, key=modeset name
		self.ms_authorative = []	# list of modeset of which we have an authority
		
		# events
		self.event_mode_change = [] # list of event dicts, connected to mode changes
		
		# default long press time
		self.long_press_ms = 800

		# experimental -- detect speed
		self.encoder_last_chg = datetime.now()
		self.encoder_last_speed = None
		self.encoder_fast_count = 0
		
		if callable(self.callback_function):
			self.__gpio_setup(self.int_handle_switch,self.int_handle_encoder)
		else:
			self.__gpio_setup()
			
		# inform our parent that we have an authorative modeset, so it can inform the world of its state
		if callable(self.callback_function):
			mode_change_params = []
		
			for modesetid in self.ms_authorative:
				for modeset in self.ms_all[modesetid]:
					mode_change_params.append(modeset['mode'])
					mode_change_params.append(modeset['state'])
					
			if len(mode_change_params) > 0:
				self.callback_function('MODE-CHANGE',mode_change_params)	# TODO. CHANGE to *mode_change_params
				#self.callback_mode_change(mode_change_params,init=True)
	
	def __printer( self, message, level=LL_INFO, tag=None):
		if self.logger is not None:
			if tag is None: tag = self.LOG_TAG
			self.logger.log(level, message, extra={'tag': tag})
	
	# ********************************************************************************
	# Callback
	def __cb_mode_change(self, list_of_modes):
		"""
		Called by modeset whenever a new mode becomes active. List_of_modes is a list of mode-dictionaries.
		First, executes the 'MODE-CHANGE' function.
		Secondly, executes the user defined callback.
		Source: Modeset.state_change
		"""	
		
		new_active_modes = []		# only the new active mode(s)
		mode_change_params = []
		for mode in list_of_modes:
			mode_change_params.append(mode['mode'])
			mode_change_params.append(mode['state'])
			if mode['state']:
				new_active_modes.append(mode['mode'])

		self.__printer("Mode change. {0}".format(mode_change_params),level=LL_DEBUG)
		self.__exec_function_by_code('MODE-CHANGE',*mode_change_params)
		
		if callable(self.callback_mode_change):
			self.callback_mode_change(mode_change_params)
		
		# Check if we have an event for this..
		if self.event_mode_change:
		
			for emc in self.event_mode_change:
				if any(x in new_active_modes for x in emc['modes']):
				
					for active_mode in new_active_modes:
						if active_mode in emc['modes']:
							
							# HIT!
							print "DEBUG EVENT-MODE HIT!"
							print emc
							"""
							  "name": "mode_track"
							, "type": "mode_change"
							, "modes": [ "track" ]
							, "device": "rgb_1"
							, "pattern": "on"
							, "rgb": "#ff0000"
							"""
							rgb_dev = self.get_device_config("rgb_1")	# todo change to emc['device']
							pin_r = rgb_dev['r']
							pin_g = rgb_dev['g']
							pin_b = rgb_dev['b']
							
							# ignore pattern for now..
							#turn on rgb_1, using ff0000
							self.gpio.pwm_rgb(pin_r,pin_g,pin_b,"#ff0000") # todo change to emc['rgb']
	
	def __exec_function_by_code(self,command,*args):
		"""
		Kind of like a pass-through function to execute a command.
		command are executed by passing them back to our owner for execution.
		
		The user can configure any command available in the commands class.
		Consider making this a json file...
		
		We will already validate the command before passing it back.
		"""
		self.__printer("Preparing to execute function: {0}".format(command),level=LL_DEBUG)
		
		if command is None:
			return
			
		cmd_exec = Commands()
		if command not in cmd_exec.command_list:
			return
		
		if args:
			valid_params = cmd_exec.validate_args(command,*args)
		else:
			valid_params = None
		
		if callable(self.callback_function):
			print "-> Calling callback"
			self.callback_function(command,valid_params)
		
	# ********************************************************************************
	# Mode helpers
	def __mode_reset(self):
		"""
		Restart all running timers
		"""
		for key,val in self.ms_all.iteritems():
			val.reset_restart()
			
	def __mode_modesetid(self, mode):
		"""
		Return tuple of modesetid and index the first modesetid mode exists in
		"""
		for key,val in self.ms_all.iteritems():
			ix = val.index(mode)
			if ix is not None:
				return key, ix


	# ********************************************************************************
	# Public functions
	def activemodes(self):
		"""
		Returns a list of all active modes across all modesets.
		"""
		ret_active = []
		for key,val in self.ms_all.iteritems():
			ret_active.extend( val.active() )
		return ret_active
	
	def set_mode(self,mode,state=True):
		"""
		Set given mode to active, or deactivate if state is False.
		
		WHAT IF A MODE DOESNT EXIST, BUT T
		
		"""
		print "SET_MODE START"
		for key,val in self.ms_all.iteritems():
			if val.index(mode) is not None:
				if state:
					val.activate( val.index(mode) )
				else:
					val.deactivate( val.index(mode) )
		"""
		print "SET_MODE DONE -- ALSO DOING EXPERIMENTAL -- "
		# DEBUG / EXPERIMENTAL
		if self.int_encoder is not None:
			if mode == 'volume' and state == True and 'mode_timeout' in self.cfg_gpio and self.int_enabled:
				print "DEBUG2.. GPIO/VOLUME ({0}:{1}).. disabling our interrupts..".format(mode,state)
				self.gpio.remove_event_detect(13)
				self.gpio.remove_event_detect(6)
				self.int_enabled = False
			elif mode != 'volume' and state == True and 'mode_timeout' in self.cfg_gpio and not self.int_enabled:
				print "DEBUG2.. GPIO/NOT VOLUME ({0}:{1}).. enabling our interrupts..".format(mode,state)
				self.gpio.setup((13,6), self.gpio.IN, pull_up_down=self.gpio.PUD_DOWN)
				self.gpio.add_event_detect(13, self.gpio.RISING, callback=self.int_encoder) # NO bouncetime 
				self.gpio.add_event_detect(6, self.gpio.RISING, callback=self.int_encoder) # NO bouncetime
				self.int_enabled = True
			elif mode == 'volume' and state == True and 'mode_timeout' not in self.cfg_gpio and not self.int_enabled:
				print "DEBUG2.. ECA/VOLUME ({0}:{1}).. enabling our interrupts..".format(mode,state)
				self.gpio.setup((13,6), self.gpio.IN, pull_up_down=self.gpio.PUD_DOWN)
				self.gpio.add_event_detect(13, self.gpio.RISING, callback=self.int_encoder) # NO bouncetime 
				self.gpio.add_event_detect(6, self.gpio.RISING, callback=self.int_encoder) # NO bouncetime
				self.int_enabled = True
			elif mode != 'volume' and state == True and 'mode_timeout' not in self.cfg_gpio and self.int_enabled:
				print "DEBUG2.. ECA/NOT VOLUME ({0}:{1}).. disabling our interrupts..".format(mode,state)
				self.gpio.remove_event_detect(13)
				self.gpio.remove_event_detect(6)
				self.int_enabled = False
			print "DEBUG2.. done"
		"""
	
	def change_modes(self, change_list):
		"""
		Change a list of modes
		"""
		print "CHG_MODE START"
		for mode_ix in range(0,len(change_list),2):
			setid_and_index = self.__mode_modesetid(change_list[mode_ix])
			if setid_and_index is not None:
				if change_list[mode_ix+1] == True:
					print "Setting Active Set:{0} Index:{1}".format(setid_and_index[0], setid_and_index[1])
					self.ms_all[setid_and_index[0]].activate(setid_and_index[1])
				elif change_list[mode_ix+1] == False:
					print "Setting DEactive Set:{0} Index:{1}".format(setid_and_index[0], setid_and_index[1])
					self.ms_all[setid_and_index[0]].deactivate(setid_and_index[1])
				else:
					print "Invalid State"
		if 'volume' in self.ms_all:
			print self.ms_all['volume'].active()
		if 'modecycle1' in self.ms_all:
			print self.ms_all['modecycle1'].active()
		print "CHG_MODE STOP"
	
	def modeset(self,modesetid):
		"""
		Returns ModeSet-structure, converted to a simple list of dicts.
		"""
		if modesetid in self.ms_all:
			return copy.deepcopy(self.ms_all[modesetid].simple())
		else:
			return
		
	def modesets(self):
		"""
		Returns list of ModeSet-structures, converted to a simple list of dicts.
		"""
		copy_ms_all = {}
		for mode_set_id,mode_set in self.ms_all.iteritems():
			copy_ms_all[mode_set_id] = copy.deepcopy(mode_set.simple())
		return copy_ms_all
		
	def cleanup(self):
		self.__printer("Cleaning up GPIO")
		self.gpio.cleanup()
		
	# ********************************************************************************
	# GPIO helpers
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
		"""
		Returns function dictionary (?) whick looks like this, for a given pin index:
		
		{	  'dev_type': 'clk'
			, 'dev_name': u'multi_encoder'
			, 'functions': [
				  {u'name': u'track_select', 'fnc_name': u'track_select', u'encoder': u'multi_encoder', u'mode': u'track', 'multicount': 0, u'function_ccw': u'PLAYER-PREV', u'function_cw': u'PLAYER-NEXT'}
				, {u'name': u'bass', 'fnc_name': u'bass', u'encoder': u'multi_encoder', u'mode': u'bass', 'multicount': 0, u'function_ccw': u'ECA-BASS-DEC', u'function_cw': u'ECA-BASS-INC'}
				, {u'name': u'treble', 'fnc_name': u'treble', u'encoder': u'multi_encoder', u'mode': u'treble', 'multicount': 0, u'function_ccw': u'ECA-TREBLE-DEC', u'function_cw': u'ECA-TREBLE-INC'}
				, {u'name': u'random', 'fnc_name': u'random', u'encoder': u'multi_encoder', u'mode': u'random', 'multicount': 0, u'function_ccw': u'PLAYER-RANDOM-PREV', u'function_cw': u'PLAYER-RANDOM-NEXT'}
				, {u'name': u'browse_menu', 'fnc_name': u'browse_menu', u'encoder': u'multi_encoder', u'mode': u'menu', 'multicount': 0, u'function_ccw': u'MENU_SCROLL_UP', u'function_cw': u'MENU_SCROLL_DOWN'}
				]
		}
		
		"""	
		active_modes = self.activemodes()
		# loop through all possible functions for given pin
		# examine if func meets all requirements (only one check needed for encoders: mode)
		for func_cfg in self.pins_config[pin]['functions']:
			if 'mode' in func_cfg and func_cfg['mode'] not in active_modes:
				pass # these are not the mode you're looking for
			else:
				return func_cfg
				
		return None
					
	# ********************************************************************************
	# GPIO interrupt handlers
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
		if not self.gpio.input(pin) == self.pins_config[pin]['gpio_on']:
			return None
		
		#print "DEBUG: self.int_handle_switch! for pin: {0}".format(pin)
		self.__mode_reset()									# Keep resetting as long as the mode is being used
		# TODO, check if possible to only reset affected timer: self.ms_all[fun['mode_cycle']].
		
		# check wheather we have short and/or long press functions and multi-press functions
		if self.pins_config[pin]['has_short'] and not self.pins_config[pin]['has_long'] and not self.pins_config[pin]['has_multi']:
			""" Only a SHORT function, no long press functions, no multi-button, go ahead and execute """
			self.__printer("Executing short function, as it is the only option") # LL_DEBUG #TODO
			
			# execute, checking mode
			for ix, fun in enumerate(self.pins_config[pin]['functions']):
				if 'mode' in fun:
					if fun['mode'] in self.activemodes():
						self.__exec_function_by_code(fun['function'])
					else:
						print "DEBUG mode mismatch"
				else:
					if 'mode_select' in fun and 'mode_cycle' in fun:
						self.ms_all[fun['mode_cycle']].next()
					self.__exec_function_by_code(fun['function'])
				
			return

		if (self.pins_config[pin]['has_long'] or self.pins_config[pin]['has_short']) and not self.pins_config[pin]['has_multi']:
			""" LONG + possible short press functions, no multi-buttons, go ahead and execute, if pressed long enough """
			self.__printer("Button pressed (pin {0}), waiting for button to be released....".format(pin))
			pressed = True
			while True: #pressed == True or press_time >= self.long_press_ms:
				state = self.gpio.input(pin)
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
							if fun['mode'] in self.activemodes():
								self.__exec_function_by_code(fun['function'])
							else:
								print "DEBUG mode mismatch"
						else:
							if 'mode_select' in fun and 'mode_cycle' in fun:
								self.ms_all[fun['mode_cycle']].next()
							self.__exec_function_by_code(fun['function'])			
				
			elif press_time > 0 and press_time < self.long_press_ms and self.pins_config[pin]['has_short']:
				self.__printer("Button was pressed for {0}ms (threshold={1}). Executing short function.".format(press_time,self.long_press_ms))	# TODO: LL_DEBUG
				
				# execute, checking mode
				for ix, fun in enumerate(self.pins_config[pin]['functions']):
					if fun['press_type'] == 'short':
						if 'mode' in fun:
							if fun['mode'] in self.activemodes():
								self.__exec_function_by_code(fun['function'])
							else:
								print "DEBUG mode mismatch"
						else:
							if 'mode_select' in fun and 'mode_cycle' in fun:
								self.ms_all[fun['mode_cycle']].next()
							self.__exec_function_by_code(fun['function'])

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
			
				if 'mode' in function and function['mode'] in self.activemodes():
			
					multi_match = True
					for multi_pin in function['multi']:
						if not self.gpio.input(multi_pin) == self.pins_config[pin]['gpio_on']:
							multi_match = False
					if multi_match == True:
						if function['press_type'] == 'short_press':
							matched_short_press_function_code = function['function']
						elif function['press_type'] == 'long_press':
							matched_long_press_function_code = function['function']
					
			self.__printer("Waiting for button to be released....")
			pressed = True
			while pressed == True or press_time >= self.long_press_ms:
				state = self.gpio.input(pin)
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
				
		# feedback in case of no attached function
		self.__printer("Switch. Pin: {0}".format(pin),level=LL_DEBUG)


	def int_handle_encoder(self,pin):
		"""
		Called for either inputs from rotary switch (A and B)
		"""
		
		#print "DEBUG: self.int_handle_encoder! for pin: {0}".format(pin)
			
		device = self.get_device_config_by_pin(pin)
		
		encoder_pinA = device['clk']
		encoder_pinB = device['dt']

		Switch_A = self.gpio.input(encoder_pinA)
		Switch_B = self.gpio.input(encoder_pinB)
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
		self.__mode_reset()									# Keep resetting as long as the mode is being used

		# TODO, check if possible to only reset affected timer: self.ms_all[fun['mode_cycle']].
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

				f_args = None
				if pin == encoder_pinB:							# Turning direction depends on 
					#COUNTER CLOCKWISE (CCW) or DECREASE
					if self.encoder_fast_count > 3 and 'function_fast_ccw' in function:				
						key = 'function_fast_ccw'
						key_args = 'function_fast_ccw_args'

					elif 'function_ccw' in function:
						key = 'function_ccw'
						key_args = 'function_ccw_args'
					
				else:
					#CLOCKWISE (CW) or INCREASE
					if self.encoder_fast_count > 3 and 'function_fast_cw' in function:
						key = 'function_fast_cw'
						key_args = 'function_cw_args'
					
					elif 'function_cw' in function:
						key = 'function_cw'
						key_args = 'function_cw_args'

				# prepare arguments
				if key_args in function:
					if isinstance(function[key_args],str):
						#f_args = [function[key_args]]
						self.__exec_function_by_code(function[key], *[function[key_args]])
					else:
						#f_args = *function[key_args]
						self.__exec_function_by_code(function[key], *function[key_args])
				else:
					self.__exec_function_by_code(function[key])
					
				# execute
				#self.__exec_function_by_code(function[key], *[function[key_args]])
						
				self.encoder_last_chg = this_chg
		else:
			self.__printer("Encoder, no function",level=LL_DEBUG)


			pigpio.pi()
	# ********************************************************************************
	# GPIO setup
	def __gpio_setup(self,int_switch=None,int_encoder=None):
		"""
		Setup
		"""
		self.int_encoder = int_encoder
		self.gpio.setwarnings(True)
		
		# gpio mode: BCM or board
		"""
		if 'gpio_mode' in self.cfg_gpio:
			if self.cfg_gpio['gpio_mode'] == 'BCM':
				self.gpio.setmode(self.gpio.BCM)
			elif self.cfg_gpio['gpio_mode'] == 'BOARD':
				self.gpio.setmode(self.gpio.BOARD)
		else:
			self.gpio.setmode(self.gpio.BCM)	# default
		"""

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
		
		# *********************************************************************
		# Modes
		if 'mode_sets' in self.cfg_gpio:
			
			self.__printer("Mode sets:")
			for mode_set in self.cfg_gpio['mode_sets']:
				self.ms_all[mode_set['id']] = CircularModeset()	# GPIO only uses circular modesets, meaning only one active mode per set.
				self.ms_all[mode_set['id']].set_cb_mode_change(self.__cb_mode_change)	# calls __cb_mode_change when a mode changes (actually: when a new mode becomes active)

				# basemode
				if 'base_mode' in mode_set:
					self.ms_all[mode_set['id']].basemode = mode_set['base_mode']
					base_mode = mode_set['base_mode'] #	DEBUG print
								
				if 'reset' in mode_set:
					self.ms_all[mode_set['id']].reset_enable(mode_set['reset'])
					self.__printer("> {0}; resets to {1} after {2} seconds".format(mode_set['id'],base_mode,mode_set['reset']),level=LL_DEBUG)
				else:
					self.__printer("> {0} (no reset)".format(mode_set['id']),level=LL_DEBUG)
				
				for i, mode in enumerate(mode_set['mode_list']):
					self.ms_all[mode_set['id']].append(mode)
					
					# debug feedback
					dbg_base = ""
					if mode == base_mode: dbg_base = "(base)"
					self.__printer("  {0} {1} {2}".format(i,mode,dbg_base),level=LL_DEBUG)
					
				# authorative
				if 'authorative' in mode_set and mode_set['authorative']:
					self.ms_authorative.append(mode_set['id'])
			
		else:
			self.__printer("WARNING: No 'mode_sets'-section.", level=LL_WARNING)
		
		# *********************************************************************
		# Initialize all pins in configuration
		pins_monitor = []
		for device in self.cfg_gpio['devices']:
			# *****************************************************************
			if 'type' in device and device['type'] == 'led':
				# Normal led
				pin = device['pin']
				self.__printer("Setting up pin: {0}".format(pin))
				self.gpio.setup(pin, self.gpio.OUT)
				
			# *****************************************************************
			# Single RGB led, controlled using PWM
			if 'type' in device and device['type'] == 'rgb_pwm':
				# RGB led
				pin_r = device['r']
				pin_g = device['g']
				pin_b = device['b']
				self.__printer("Setting up pins: {0}, {1} and {2}".format(pin_r, pin_g, pin_b))
				self.gpio.setup(pin_r, self.gpio.OUT, softpwm=True)
				self.gpio.setup(pin_g, self.gpio.OUT, softpwm=True)
				self.gpio.setup(pin_b, self.gpio.OUT, softpwm=True)
				
			# *****************************************************************
			# Switch
			if 'sw' in device and int_switch is not None:
				#pin = self.cfg_gpio['devices'][ix]['sw']
				pin = device['sw']
				pins_monitor.append(pin)
				
				self.__printer("Setting up pin: {0}".format(pin))
				self.gpio.setup(pin, self.gpio.IN)
				
				# convert high/1, low/0 to bool
				if device['gpio_on'] == "high" or device['gpio_on'] == 1:
					gpio_on = self.gpio.HIGH
				else:
					gpio_on = self.gpio.LOW
				
				# pull up/down setting
				# valid settings are: True, "up", "down"
				# if left out, no pull up or pull down is enabled
				# Set to True to automatically choose pull-up or down based on the on-level.
				if 'gpio_pullupdown' in device:
					if device['gpio_pullupdown'] == True:
						if gpio_on == self.gpio.HIGH:
							#self.gpio.set_pullupdn(pin, pull_up_down=self.gpio.PUD_DOWN)	#v0.10
							self.gpio.setup(pin, self.gpio.IN, pull_up_down=self.gpio.PUD_DOWN)
							self.__printer("Pin {0}: Pull-down resistor enabled".format(pin))
						else:
							#self.gpio.set_pullupdn(pin, pull_up_down=self.gpio.PUD_UP)	#v0.10
							self.gpio.setup(pin, self.gpio.IN, pull_up_down=self.gpio.PUD_UP)
							self.__printer("Pin {0}: Pull-up resistor enabled".format(pin))
					elif device['gpio_pullupdown'] == False:
						pass
					elif device['gpio_pullupdown'] == 'up':
						#self.gpio.set_pullupdn(pin, pull_up_down=self.gpio.PUD_UP)	#v0.10
						self.gpio.setup(pin, self.gpio.IN, pull_up_down=self.gpio.PUD_UP)
						self.__printer("Pin {0}: Pull-up resistor enabled".format(pin))
					elif device['gpio_pullupdown'] == 'down':
						#self.gpio.set_pullupdn(pin, pull_up_down=self.gpio.PUD_DOWN)	#v0.10
						self.gpio.setup(pin, self.gpio.IN, pull_up_down=self.gpio.PUD_DOWN)
						self.__printer("Pin {0}: Pull-down resistor enabled".format(pin))
					else:
						self.__printer("ERROR: invalid pull_up_down value. This attribute is optional. Valid values are: True, 'up' and 'down'.",level=LL_ERROR)

				# edge detection trigger type
				# valid settings are: "rising", "falling" or both
				# if left out, the trigger will be based on the on-level
				if 'gpio_edgedetect' in device:				
					if device['gpio_edgedetect'] == 'rising':
						self.gpio.add_event_detect(pin, self.gpio.RISING, callback=int_switch) #
						self.__printer("Pin {0}: Added Rising Edge interrupt; bouncetime=600".format(pin))
					elif device['gpio_edgedetect'] == 'falling':
						self.gpio.add_event_detect(pin, self.gpio.FALLING, callback=int_switch) #
						self.__printer("Pin {0}: Added Falling Edge interrupt; bouncetime=600".format(pin))
					elif device['gpio_edgedetect'] == 'both':
						self.gpio.add_event_detect(pin, self.gpio.BOTH, callback=int_switch) #
						self.__printer("Pin {0}: Added Both Rising and Falling Edge interrupt; bouncetime=600".format(pin))
						self.__printer("Pin {0}: Warning: detection both high and low level will cause an event to trigger on both press and release.".format(pin),level=LL_WARNING)
					else:
						self.__printer("Pin {0}: ERROR: invalid edge detection value.".format(pin),level=LL_ERROR)
				else:
					if gpio_on == self.gpio.HIGH:
						self.gpio.add_event_detect(pin, self.gpio.RISING, callback=int_switch) #
						self.__printer("Pin {0}: Added Rising Edge interrupt; bouncetime=600".format(pin))				
					else:
						self.gpio.add_event_detect(pin, self.gpio.FALLING, callback=int_switch) #, bouncetime=600
						self.__printer("Pin {0}: Added Falling Edge interrupt; bouncetime=600".format(pin))

				
				self.pins_state[pin] = self.gpio.input(pin)
					
				# consolidated config
				self.pins_config[pin] = { "dev_name":device['name'], "dev_type":"sw", "gpio_on": gpio_on, "has_multi":False, "has_short":False, "has_long":False, "functions":[] }
			
			# *****************************************************************
			# Encoder
			if 'clk' in device and int_encoder is not None:
				pin_clk = device['clk']
				pin_dt = device['dt']
				
				self.__printer("Setting up encoder on pins: {0} and {1}".format(pin_clk, pin_dt))
				self.gpio.setup((pin_clk,pin_dt), self.gpio.IN, pull_up_down=self.gpio.PUD_DOWN)
				self.gpio.add_event_detect(pin_clk, self.gpio.RISING, callback=int_encoder) # NO bouncetime 
				self.gpio.add_event_detect(pin_dt, self.gpio.RISING, callback=int_encoder) # NO bouncetime 
				
				self.pins_state[pin_clk] = self.gpio.input(pin_clk)
				self.pins_state[pin_dt] = self.gpio.input(pin_dt)
				
				# consolidated config
				self.pins_config[pin_clk] = { "dev_name":device['name'], "dev_type":"clk", "functions":[] }
				self.pins_config[pin_dt] = { "dev_name":device['name'], "dev_type":"dt", "functions":[] }
						
		# *********************************************************************
		# Map pins to functions
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

		# *********************************************************************
		# Register (?) configured events
		if 'events' in self.cfg_gpio:
			for ix, event in enumerate(self.cfg_gpio['events']):
			
				if event['type'] == 'mode_change':
					self.event_mode_change.append(event)
		
