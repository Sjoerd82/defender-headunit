#
# GPIO
# Venema, S.R.G.
# 2018-06-21
#
# Data structures
# 
#

from threading import Timer		# Modesets: timer to reset mode change
import copy

class Modeset(list):
	"""
	List of dictionaries.
	{"mode":<string>, "state":bool}
	"""
	def __init__(self):
		super(Modeset, self).__init__()
		self.callback_mode_change = None
			
	def __contains__(self, item):
		"""
		Used when an "in"-check is made. However, regular list would need an
		exact match on the complete Mode/dictionary. This function checks if
		the key (mode name) exists and returns True if it does, else False.
		"""
		for listitem in self:
			for key, value in listitem.iteritems():
				if key == 'mode':
					if value == str(item):
						return True
		return False
		
	def index(self,item):
		"""
		Returns an index based on the given key of the Mode/dictionary.
		"""
		for ix, listitem in enumerate(self):
			if listitem['mode'] == str(item):
				return ix
	
	def append(self,item):
		"""
		Updates given string to a Mode/dictionary object and appends it.
		Only appends if the mode name doesn't already exist.
		"""
		mode_item = {"mode":item,"state":False}
		if item not in self:
			super(Modeset, self).append(mode_item)
	
	def activate(self,ix):
		"""
		Set state to True for given index.
		"""
		if ix < len(self):
			self[ix]['state'] = True
			self.state_change()
			
	def deactivate(self,ix):
		"""
		Set state to False for given index.
		"""
		if ix < len(self):
			self[ix]['state'] = False
			self.state_change()
	
	def active(self):
		"""
		Return list of active modes
		"""
		ret_list = []
		for mode in self:
			if mode['state']:
				ret_list.append(mode['mode'])
		return ret_list
	
	def set_cb_mode_change(self, cb_function):
		"""
		Set callback function. This function is called when a mode changes state.
		"""
		self.callback_mode_change = cb_function
		staticmethod(self.callback_mode_change)
		
	def state_change(self):
		"""
		Called by the Mode callback when it changes state.
		Calls callback, if provided and callable.
		"""
		if callable(self.callback_mode_change):
			# Can't return self, as this may contain a Timer (in case of CircularModeset)
			# and we want to return a copy anyway.
			ret_list_of_dicts = []
			for mode in self:
				ret_list_of_dicts.append(mode)
			self.callback_mode_change(ret_list_of_dicts)	#no need to (deep)copy?
		
class CircularModeset(Modeset):
	"""
	Type of Modeset where exactly one mode is active at a time.
	It adds an option to reset back to a given mode after a reset timer expires.
	Reset timer engages on state change (__check_state), no need to call explicitly.
	"""
	def __init__(self):
		super(CircularModeset, self).__init__()
		self._basemode = None
		self.ix_basemode = None
		self.ix_active = None
		self.timer = None
		self.timer_seconds = None
		self.timer_enabled = False

	def __cb_mode_reset(self):
		"""
		Called by Timer on timeout.
		Enforces one active mode rule.
		"""
		if self.ix_basemode is not None:
			self[self.ix_active]['state'] = False
			self.ix_active = self.ix_basemode
			self[self.ix_active]['state'] = True
			self.__check_state(self.ix_active)

	def __check_state(self, ix_activated):
		"""
		Calls state_change() to activate change callback.
		Start reset timer.
		"""
		self.state_change()
	
		if self.timer_enabled and self[ix_activated]['mode'] != self._basemode:
			self.reset_start()

	def append(self,item):
		"""
		If appended mode is the basemode, then activate it.
		"""
		super(CircularModeset, self).append(item)
		
		if item == self._basemode and item in self:
			self.ix_basemode = self.index(str(item))
			if self.ix_active is None:
				self.ix_active = self.ix_basemode
			elif self.ix_basemode <> self.ix_active:
				self[self.ix_active]['state'] = False
				self.ix_active = self.ix_basemode

			self[self.ix_active]['state'] = True
			#self.__check_state()	# No callback
			
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
	
	def activate(self,ix):
		"""
		Activate given index, deactivates previously activate index
		"""
		if ix < len(self) and ix <> self.ix_active:
			self[self.ix_active]['state'] = False
			self.ix_active = ix
			self[self.ix_active]['state'] = True
			self.__check_state(self.ix_active)

	def deactivate(self,ix):
		"""
		Deactivate given index, activates index 0
		"""
		if ix < len(self) and ix > 0 and ix <> self.ix_active:
			self.ix_active = 0
			self[ix]['state'] = False
			self.__check_state(self.ix_active)
	
	def next(self):
		"""
		Activate next.
		"""
		if self.ix_active is None:
			self.ix_active = 0
			self[self.ix_active]['state'] = True
		else:
			self[self.ix_active]['state'] = False
			self.ix_active = (self.ix_active + 1) % len(self)
			self[self.ix_active]['state'] = True
		self.__check_state(self.ix_active)

	def prev(self):
		"""
		Activate previous.
		"""
		if self.ix_active is None:
			self.ix_active = len(self)-1
			self[self.ix_active]['state'] = True
		else:
			self[self.ix_active]['state'] = False
			self.ix_active = (self.ix_active - 1) % len(self)
			self[self.ix_active]['state'] = True
		self.__check_state(self.ix_active)
			
	def reset_enable(self,seconds):
		"""
		Enable reset functionality.
		"""
		self.timer_seconds = seconds
		
		# should have at least two modes
		if len(self) <= 1:
			return
		
		# check if we have a basemode to reset to (if not default to first item)
		if self._basemode is None:
			self.self._basemode = self[0]['mode']
			self.ix_basemode = 0
		
		# check if we have a basemode index yet
		if self.ix_basemode is None:
			self.ix_basemode = self.index(self._basemode)
		
		# all checks passed
		self.timer_enabled = True
		
	def reset_start(self):
		"""
		Start reset timer.
		"""
		if not self.timer_enabled:
			return
		
		# check if already in the basemode
		if self.ix_active == self.ix_basemode:
			return

		# cancel an already running timer
		if self.timer is not None and self.timer.is_alive():
			self.timer.cancel()
		
		self.timer = Timer(self.timer_seconds, self.__cb_mode_reset)
		self.timer.start()

	def reset_restart(self):
		"""
		Start reset timer, only if running.
		"""		
		if ( self.timer_enabled and
		     self.timer is not None and
			 self.timer.is_alive() ):
			self.timer.cancel()
			self.timer = Timer(self.timer_seconds, self.__cb_mode_reset)
			self.timer.start()		
		
	def __reset_cancel(self):
		"""
		Cancel the reset timer (not used at the moment)
		"""
		if self.timer is not None and self.timer.is_alive():
			self.timer.cancel()

		
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