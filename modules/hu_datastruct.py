
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
			
	def sort(self):
		""" Careful, some modes need to be in a certain sequence! """
		self = [sorted(l, key=itemgetter('name')) for l in (self)]
	
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
		for mode in self:
			if mode['state']:
				return mode['name']

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