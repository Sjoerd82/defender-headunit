
from threading import Timer		# Modesets: timer to reset mode change
import copy

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


class Modes(ListDataStruct):
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

class Modeset(list):
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
	
	def append(self, mode_set_id, item):
	
		if not isinstance(item, Modes):
			raise TypeError, 'item is not of type: "Modes"'
		else:
			# if mode_set_id already exists??
			super(Modeset, self).append(item)
			#mode_set_properties = { "id":mode_set_id, "timer":None }
			#self.mode_set_id_list.append(mode_set_properties)
			self.mode_set_id_list.append(mode_set_id)
			
	def remove(self):
		#todo
		pass
			
	def activate(self, mode_activate, mode_set_id=None):
		print "activate"
		if mode_set_id is None:
			for modes in self:
				if modes.key_exists(mode_activate):
					modes.set_active_modes([mode_activate])
					
		else:
			ix = self.mode_set_id_list.index(mode_set_id)
			if ix is not None:
				if self[ix].key_exists(mode_activate):
					self[ix].set_active_modes([mode_activate])
					
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
		
		master_modes_list = Modes()
		for modes in self:
			master_modes_list.extend(modes)
		self.callback_mode_change(copy.deepcopy(master_modes_list))
		
	def reset_enable(self,mode_set_id,base_mode,seconds):
		self.timers[mode_set_id] = Timer(seconds, self.__cb_mode_reset, [mode_set_id,base_mode])
		#self.timer_mode = Timer(seconds, self.__cb_mode_reset, [mode_set_id,base_mode])
		#self.timers[mode_set_id].start()
		
	def reset_start(self, mode_set_id):
		print "reset_start"
		# TODO: ignore this if mode == base-mode
		if mode_set_id not in self.timers:
			return
			
		if self.timers[mode_set_id] is not None:
			self.timers[mode_set_id].cancel()
		else:
			self.timers[mode_set_id].start()

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