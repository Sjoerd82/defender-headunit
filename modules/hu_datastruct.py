
from threading import Timer		# Modesets: timer to reset mode change
import copy

class Stateful(dict):
	"""
	Simple class that adds state supports operations.
	Callback may be added to act upon state changes.
	"""

	def __init__(self, mode, cb_state_change=None):
		self['mode'] = mode
		self['state'] = False
		self.cb_state_change=cb_state_change
		
	def __repr__(self):
		return self['mode']
	
	@property
	def state(self):
		"""
		Return active state. True or False.
		"""
		return self['state']

	@state.setter
	def state(self,state):
		"""
		Set active state. True or False.
		Calls Callback function, if defined
		"""
		self['state']  = state
		if callable(self.cb_state_change):
			self.cb_state_change(self['mode'])

	def activate(self):
		"""
		Set state to active state (True).
		"""
		self.state(True)
		
	def deactivate(self):
		"""
		Set state to inactive state (False).
		"""
		self.state(False)

class Modeset(list):
	"""
	List of stateful modes. + Reset Timer
	Reset timer engages on state change (cb_check_state), no need to call explicitly
	"""
	def __init__(self):
		super(Modeset, self).__init__()
		self._singular = None
		self._basemode = None
		self.ix_active = None
		self.timer = None
		self.callback_mode_change = None
		self.timer_enabled = False

	def __contains__(self, item):
		# When using a dict
		for listitem in self:
			for key, value in listitem.iteritems():
				if key == 'mode':
					if value == str(item):
						return True
		return False
		# When using attributes
		#for mode in self:
		#	if mode.mode == str(item):
		#		return True
		#return False

	def __cb_mode_reset(self):
		""" Reset Timer call back """
		print "__cb_mode_reset"
		if callable(self.callback_mode_change):
			self.callback_mode_change()

	def reset_enable(self,seconds,cb_function=None):
		print "enabling timer"
		self.callback_mode_change = cb_function
		staticmethod(self.callback_mode_change)
		self.timer = Timer(seconds, self.__cb_mode_reset)
		#self.timer_mode = Timer(seconds, self.__cb_mode_reset, [mode_set_id,base_mode])
		#self.timers[mode_set_id].start()
		self.timer.start()
		self.timer_enabled = True
		
	def reset_start(self):
		
	def index(self,item):
		for ix, listitem in enumerate(self):
			if listitem['mode'] == str(item):
				return ix
			
		# When using attributes:
		#for ix, mode in enumerate(self):
		#	if mode.mode == str(item):
		#		return ix
	
	def append(self,item):
		stateful_item = Stateful(item, self.cb_check_state)	# add State operations + callback
		if item not in self:								# only add if unique
			super(Modeset, self).append(stateful_item)
		
		if item == self._basemode and item in self:		# if item = basemode, activate it
			self.ix_active = self.index(str(item))
			self[self.ix_active].activate()
	
	@property
	def singular(self):
		"""
		Return singular state. True or False.
		"""
		return self._singular

	@singular.setter
	def singular(self, state):
		"""
		When enabled enforces only one mode to be active at all times.
		"""
		self._singular = state
		if self.ix_active is not None:
			self[self.ix_active].activate()
	
	@property
	def basemode(self):
		"""
		Return base mode.
		"""
		return self._basemode
		
	@basemode.setter
	def basemode(self,basemode):
		"""
		Set base mode, base mode is the mode to reset to and to initally set.
		"""
		self._basemode = basemode
	
	def active(self):
		"""
		Return list of only active modes
		"""
		ret_list = []
		for mode in self:
			if mode.state:
				ret_list.append(mode)
		return ret_list
		
	#def category():
		""" Return the type of modeset """
		#return self._singular

	def next(self):
		"""
		Activate next. Only available for category "single".
		"""
		if self._singular and self.ix_active is None:
			self.ix_active = 0
			self[self.ix_active].activate()			
		elif self._singular:
			self[self.ix_active].deactivate()
			self.ix_active = (self.ix_active + 1) % len(self)
			self[self.ix_active].activate()

	def prev(self):
		"""
		Activate previous. Only available for category "single".
		"""
		if self._singular and self.ix_active is None:
			self.ix_active = len(self)-1
			self[self.ix_active].activate()			
		elif self._singular:
			self[self.ix_active].deactivate()
			self.ix_active = (self.ix_active - 1) % len(self)
			self[self.ix_active].activate()
	
		
	def set_cb_mode_change(self):
		pass
		
	def cb_check_state(self, activated):
		"""
		Called via Mode callback when it changes state
		- Enforces only one active mode rule
		- Starts Reset
		"""
		if self._singular or self.timer_enabled:
			# Dict:
			for ix,mode in enumerate(self):
				if mode['state'] and mode['mode'] == activated:
					self.ix_active = ix
					print "active index is now: {0}".format(ix)
					if self.timer_enabled and activated != self._basemode:
						print "activating timer"
						self.timer.start()
					else:
						print "not activating timer"
				elif mode['state'] and mode['mode'] != activated:
					mode.deactivate()
					print "deactivating a mode"
				
		#return
		# Attributes
		#for ix,mode in enumerate(self):
		#	if mode.state and mode.mode == activated:
		#		self.ix_active = ix
		#		print "active index = {0}".format(ix)
		#	elif mode.state and mode.mode != activated:
		#		mode.deactivate()
		
# TODO: add feature to check for a unique key

class ListDataStruct(list):
	
	def __init__(self, unique_key, mandatory_keys):
		self.mandatory_keys = mandatory_keys
		self.unique_key = unique_key

	
	def __check_dict(self, dictionary):
		# returns True if all required fields are present, else returns False
		if self.mandatory_keys <= set(dictionary):
			# TODO: check if mandatory_keys are not None?
			return True
		else:
			return False
	
	# def index(self)
	def unique_list(self):
		""" returns a list of the unique key values """
		if self.unique_key is None:
			return None
		
		ret = []
		for dict_item in self:
			ret.append(dict_item[self.unique_key])
		return ret
		
	def key_exists(self, key):
		for dict_item in self:
			if dict_item[self.unique_key] == key:
				return True
		return False
				
	#terrible naming!
	def get_by_unique(self,key):
		for dict_item in self:
			if dict_item[self.unique_key] == key:
				return dict_item
		
	def set_by_unique(self,key,updated_dict):
		for ix, dict_item in enumerate(self):
			if dict_item[self.unique_key] == key:
				self[ix] = updated_dict
				return True
				
		return False
		
	
	def append(self, item):
		if not isinstance(item, dict):
			raise TypeError, 'item is not of type dict'
		if not self.__check_dict(item):
			raise NameError, 'mandatory key(s) missing'
		super(ListDataStruct, self).append(item)
		
	def extend(self,item):
		# todo
		super(ListDataStruct, self).extend(item)
		
	def __getslice__(self, i, j):
		return self.__getitem__(slice(i, j))
	def __setslice__(self, i, j, seq):
		return self.__setitem__(slice(i, j), seq)
	def __delslice__(self, i, j):
		return self.__delitem__(slice(i, j))

class OldModes(ListDataStruct):
	""" Modes is a LIST of dictionaries containing modes and state pairs.
		{ "name": <name>, "state": [bool] }
		
		modes.append( <dict> )
		modes.extend( <list of dicts>|<list of Modes> )
		modes.
		
	"""
	
	def __init__(self, *args, **kwargs):
		""" Possible arguments:
			- list of modes to add (will have default state).
			- key/value pair to add (must include mandatory key(s)), can only add one mode.
			mijnmodes0= ModeList()
			mijnmodes1 = ModeList('track','player')
			mijnmodes2 = ModeList(name='track',state=True)
			mijnmodes3 = ModeList(name='track')				# OK (default state)
			mijnmodes4 = ModeList(name='track',test=True)	# OK (default state, test is added, but ignored (?)
			mijnmodesX = ModeList(X='track')				# FAIL, missing name
		"""
		super(Modes, self).__init__('name',{'name'})
				
		empty = {}
		empty['state'] = False
	
		if args:
			for arg in args:
				# adding dict using empty defaults
				new = empty.copy()
				new['name'] = arg
				super(Modes, self).append(new)
			
		if kwargs:
			new = empty.copy()
			new.update(kwargs)
			self.append(new)
			
	#def sort(self):
	#	""" Careful, some modes need to be in a certain sequence! """
	#	self = [sorted(l, key=itemgetter('name')) for l in (self)]
	
	def unset_active_modes(self, modes):
		for mode in self:
			if mode['name'] in modes:
				mode['state'] = False
			else:
				mode['state'] = True	
	
	def set_active_modes(self, modes, only=True):
		for mode in self:
			if mode['name'] in modes:
				mode['state'] = True
			else:
				mode['state'] = False
			
		'''
		modes_list = self.unique_list()
		for mode in modes:
			# todo: check if mode exists
			self[modes_list.index(mode)]['state'] = True
		'''
	def get_active_mode(self):
		# THIS IS BROKEN, THERE CAN BE MORE THAN ONE ACTIVE MODE (just not in a mode-set)
		for mode in self:
			if mode['state']:
				return mode['name']
				
	def active_modes(self):
		active_modes = []
		for mode in self:
			if mode['state']:
				active_modes.append(mode['name'])
		return active_modes

class OldModeset(list):
	""" Modeset is a LIST of Modes.
		Within a Modeset only one mode can be active per Modes-list.
	
		modeset.append( <Modes> )
		modeset[ix].activate( <mode-name> [mode-set] )
		modeset.active()
		modeset.enable_reset( <mode-set>, <base-mode>, <seconds> )
	"""
	def __init__(self):
		super(Modeset, self).__init__()
		self.mode_set_id_list = []
		#self.mode_set_properties = {}
		self.timers = {}
		self.callback_mode_change = None
	
	#EXPERIMENTAL
	def get_modes(self):
		#return copy.deepcopy(self)	#not tried..
		new_mode_set = []
		for modes in self:
			new_mode_set.append(modes)
		return new_mode_set
	
	def append(self, mode_set_id, item, base_mode=None):
	
		if not isinstance(item, Modes):
			raise TypeError, 'item is not of type: "Modes"'
		else:
			item.base_mode = base_mode
			# if mode_set_id already exists??
			super(Modeset, self).append(item)
			#mode_set_properties = { "id":mode_set_id, "timer":None }
			#self.mode_set_id_list.append(mode_set_properties)
			self.mode_set_id_list.append(mode_set_id)
			#self.mode_set_id_list[-1].base_mode = base_mode
			print self[-1].base_mode
			
	def remove(self):
		#todo
		pass
			
	def activate(self, mode_activate, mode_set_id=None):
		print "activate"
		if mode_set_id is None:
			for modes in self:
				if modes.key_exists(mode_activate):
					modes.set_active_modes([mode_activate])
			# resets
			# TODO, for every modeset, if it has a timer...
		
		else:
			ix = self.mode_set_id_list.index(mode_set_id)
			if ix is not None:
				if self[ix].key_exists(mode_activate):
					self[ix].set_active_modes([mode_activate])
			# reset
			# only reset if not already in base mode
			print self[ix].base_mode
			if self[ix].base_mode != mode_activate:
				self.reset_start(mode_set_id)

					
	def activate_next(self, mode_set_id):

		ix = self.mode_set_id_list.index(mode_set_id)
		current_active_mode = self.active(mode_set_id)[0]	# Hmm, do we want lists??
		print current_active_mode
		print ix
		print self[ix].unique_list()
		mode_ix = self[ix].unique_list().index(current_active_mode)
		#mode_base = self.mode_sets[function['mode_cycle']]['base_mode']
		
		if mode_ix >= len(self[ix])-1:
			mode_ix = 0
		else:
			mode_ix += 1
			
		mode_new = self[ix][mode_ix]['name']
		#print "Old: {0} New: {1}".format(current_active_mode,mode_new)
		self[ix].set_active_modes(mode_new, True)
		self.reset_start(mode_set_id)
		# TODO self.callback_mode_change(copy.deepcopy(mode_list))
	

	def active(self,mode_set_id=None):
		""" Return list with all active mode names of given/all modesets """
		active_modes = []
		
		if mode_set_id is None:
			for modes in self:
				active_modes.extend(modes.active_modes())
		else:
			ix = self.mode_set_id_list.index(mode_set_id)
			if ix is not None:
				active_modes.extend(self[ix].active_modes())		
		
		return active_modes
	
	def set_cb_mode_change(self,cb_function):
		self.callback_mode_change = cb_function
		staticmethod(self.callback_mode_change)

	def __cb_mode_reset(self, mode_set_id, base_mode):
		""" Reset Timer call back """
		print "__cb_mode_reset"
		# set active mode
		# ## base_mode = self.mode_sets[mode_set_id]['base_mode']
		# ## if base_mode is None:
		# ## 	self.mode_sets[mode_set_id]['mode_list'].unset_active_modes([base_mode])
		# ## else:
		# ## 	self.mode_sets[mode_set_id]['mode_list'].set_active_modes([base_mode])
		self.activate(base_mode,mode_set_id)
		
		# just printin'
		# ## self.__printer('[MODE] Reset to: "{0}"'.format(self.mode_sets[mode_set_id]['base_mode']))
		
		# ## self.__update_active_modes()
		
		# mode change callback
		# ## master_modes_list = self.get_modes()
		# ## self.callback_mode_change(copy.deepcopy(master_modes_list))
		
		""" TODO!! !!
		master_modes_list = Modes()
		for modes in self:
			master_modes_list.extend(modes)
		self.callback_mode_change(copy.deepcopy(master_modes_list))
		"""
		
	def reset_enable(self,mode_set_id,base_mode,seconds):
		self.timers[mode_set_id] = Timer(seconds, self.__cb_mode_reset, [mode_set_id,base_mode])
			
		#self.timer_mode = Timer(seconds, self.__cb_mode_reset, [mode_set_id,base_mode])
		#self.timers[mode_set_id].start()
		
	def reset_start(self, mode_set_id):
		print "reset_start"
		# TODO: ignore this if mode == base-mode
		if mode_set_id not in self.timers:
			return
		
		if self.timers[mode_set_id].is_alive():
			self.timers[mode_set_id].cancel()
			self.timers[mode_set_id] = Timer(5, self.__cb_mode_reset, [mode_set_id,'volume'])
			self.timers[mode_set_id].start()
		else:
			self.timers[mode_set_id] = Timer(5, self.__cb_mode_reset, [mode_set_id,'volume'])
			self.timers[mode_set_id].start()
			
		
		"""
		if self.timers[mode_set_id] is not None:
			self.timers[mode_set_id].cancel()
			self.timers[mode_set_id].start()
		else:
			self.timers[mode_set_id].start()
		"""

	def reset_cancel(self, mode_set_id):
		if mode_set_id not in self.timers:
			return
		else:
			self.timers[mode_set_id].cancel()


class Tracks(ListDataStruct):
	"""	Field | Value
	--- | ---
	`display` | Formatted string
	`source` | Source name
	`rds` | RDS information (FM)
	`artist` | Artist name
	`composer` | The artist who composed the song
	`performer` | The artist who performed the song
	`album` | Album name
	`albumartist` | On multi-artist albums, this is the artist name which shall be used for the whole album
	`title` | Song title
	`length` | Track length (ms)
	`elapsed` | Elapsed time (ms) --?
	`track` | Decimal track number within the album
	`disc` | The decimal disc number in a multi-disc album.
	`genre` | Music genre, multiple genre's might be delimited by semicolon, though this is not really standardized
	`date` | The song's release date, may be only the year part (most often), but could be a full data (format?)
	"""
	
	def __init__(self, *args, **kwargs):
		super(Tracks, self).__init__(None,{})	# No mandatory fields
		empty = {}
		empty['display'] = None
		empty['source'] = None
		empty['rds'] = None
		empty['artist'] = None
		empty['composer'] = None
		empty['performer'] = None
		empty['album'] = None
		empty['albumartist'] = None
		empty['title'] = None
		empty['length'] = None
		empty['elapsed'] = None
		empty['track'] = None
		empty['disc'] = None
		empty['folder'] = None
		empty['genre'] = None
		empty['date'] = None
		
		if args:
			for arg in args:
				if isinstance(arg, dict):
					# adding dict using empty defaults
					new = empty.copy()
					new.update(arg)
					self.append(new)
				else:
					raise TypeError, 'item is not of type dict'
			
		if kwargs:
			new = empty.copy()
			new.update(kwargs)
			self.append(new)