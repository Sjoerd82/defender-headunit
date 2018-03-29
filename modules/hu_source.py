#
# Source Control
# Venema, S.R.G.
# 2018-03-23
#
# SOURCE CONTROL provides source control functionality to act on proxy classes
# Source Plugins are managed via YAPSY.
#
# Provide a logger object to __init__ to get output from this class.
#
# CONVENTIONS:
# 
# - Leave (sub)index parameter None (default) to indicate current source
# - Returns True or data, if succesful
# - Return None if nothing to do / no change
# - Return False if failure
#
#
#	add					Add a source
#	add_sub				Add a sub-source
#	check				Check if (sub)source is available
#	check_all			Check all sources (and sub-sources)
#	set_available		Set available indicator by (sub)source index
#	set_available_kw	Set available indicator by keyword
#	count_available_source		<= (internal) variable?
#	count_available_subsource	<= (internal) variable?
#	rem					Remove a source
#	rem_sub				Remove a sub-source
#	index				Returns index of source by keyword
#	index_current		Returns list of indexes of current source and current sub-source
#	source				Returns source by index (current if no index given)
#	source_all			Returns list of all sources (class refs omitted)
#	subsource			Returns subsource for given source index (current source if no index given)
#	subsource_all		Returns list of all sources (class refs omitted)
#	composite			Returns composite source (source+subsource)
#	select				Set source
#	select_next			Next source
#>>>select_next_pri		Next primary source (skipping over sub-sources)
#	select_prev			Prev source
#>>>select_prev_pri		Prev primary source (skipping over sub-sources)
#
#   SOURCE PROXY FUNCTIONS:
#	Executes functions in the source class
#
#	source_init			Code to be executed once, during initialization of the source
#	source_check		Check source availability, including subsources. If no index provided will check all sources
#	source_play
#	source_stop
#	source_pause
#	source_next
#	source_prev
#	source_random
#	source_seekfwd
#	source_seekrev
#	source_update
#	source_get_source_details
#	source_get_state
#	source_get_playlist
#	source_get_media_details
#

# renamed:
#	addSub		=>	add_sub
#	remSub		=>	rem_sub
#	getIndex	=>	index
#	getIndexCurrent		=>	index_current
#	get			=>	source
#	getAll		=>	source_all
#	setCurrent	=>	select
#	getComposite	=>	composite
#	getSubSource	=>	subsource
#	getSubSources	=>	subsource_all
#	setAvailable	=>	set_available_kw
#	setAvailableIx	=>	set_available
#
#	sourceInit		=>	source_init
#	sourceCheck		=>	source_check
#	sourceCheckAll	=>	source_check
#	
# TODO: can we omit class fields from getAll return? => if so, we won't need the get_all_simple

from yapsy.PluginManager import PluginManager
from hu_utils import *
import copy

LOG_TAG = 'SOURCE'

class SourceController(object):

	def __printer( self, message, level=LL_INFO, tag=LOG_TAG):
		self.logger.log(level, message, extra={'tag': tag})
	
	def __init__(self, logger):
		self.logger = logger
		
		# initialize INSTANCE! variables:
		self.lSource = []
		self.iCurrentSource = [ None, None ]	#Source, Sub-Source
		self.lSourceClasses = []
		self.iRecentSS = None

		self.source_manager = PluginManager()
		
		logyapsy = logging.getLogger('yapsy')
		logyapsy.setLevel(logging.DEBUG)

		ch = logging.StreamHandler()						# create console handler
		ch.setLevel(logging.DEBUG)								# set log level
		logyapsy.addHandler(ch)
		#logyapsy = log_create_console_loghandler(logyapsy, logging.DEBUG, 'YAPSY')
		
		#self.__load_plugins('sources')	# let's call it from the caller's side

	def __check_index(self, test_index):
		"""	Check if a given index is valid
			Returns False if not valid
			If provided None, will return None
			Returns the index as int, if valid
		"""
		if test_index is None:
			return None
		else:
			index = int(test_index)
			
		if index >= len(self.lSource):
			self.__printer('ERROR: subsource index ({0}) out of bounds'.format(index),LL_ERROR)
			return False
		else:
			return index
	
	def __check_subindex(self, test_index, test_index_subsource):
		"""	Check if a given subsource index is valid
			Returns False if not valid
			If provided None, will return None
			Returns the subsource index as int, if valid
		"""
	
		if test_index_subsource is None:
			return None
		else:
			index_subsource = int(test_index_subsource)
		
		# index MUST be given, if a subsource_index is given
		if test_index is None:
			return False
		else:
			index = int(test_index)

		print self.lSource[index]
		# test if the soures has subsources
		if not 'subsources' in self.lSource[index]:
			self.__printer('ERROR: index {0} has no subsources'.format(index),LL_ERROR)	
			return False

		# test if the subsource_index exists:
		if index_subsource >= len(self.lSource[index]['subsources']):
			self.__printer('ERROR: subsource index ({0}) out of bounds'.format(index_subsource),LL_ERROR)
			return False
		else:
			return index_subsource
		
	def load_source_plugins(self, plugindir):
		# check if plugin dir exists
		if not os.path.exists(plugindir):
			self.__printer('Source path not found: {0}'.format(plugindir), level=LL_CRITICAL)
			#exit()
			return False
		
		#
		# YAPSY Plugin Manager
		#
		# Load the plugins from the plugin directory.
		#self.source_manager.setPluginPlaces([plugindir])
		self.source_manager.setPluginPlaces(['/mnt/PIHU_APP/defender-headunit/sources'])
		self.source_manager.collectPlugins()

		# Activate and add all collected plugins
		for plugin in self.source_manager.getAllPlugins():
			plugin.plugin_object.set_logger(logger)
			self.source_manager.activatePluginByName(plugin.name)
			
			
			# Run init
			plugin.plugin_object.init(plugin.name)
			
			
			# Get config
			config = plugin.plugin_object.configuration(plugin.name)
			
			# Add
			isAdded = self.add(config)
			if isAdded:
				print "ADDED W/ SUCCESS"
				indexAdded = self.index('name',config['name'])
				#self.source_init(indexAdded)
				# Add "hard" subsources
				plugin.plugin_object.uhm_subs(self)
			else:
				print "NOT ADDED!"
				
				
	
	def add( self, source_config ):
		""" Add a Source
		"""
		# check required fields:
		if not all (k in source_config for k in ('name','displayname','order','controls','template')):
			self.__printer('ADD: source NOT added, missing one or more required field(s)...',LL_ERROR)
			self.__printer('Required fields are: name,displayname,order,controls,template',LL_ERROR)
			return False

		# test if name is unique
		# #TODO

		# availability = False for all new sources, until cleared by the check() function
		source_config['available'] = False
		
		# add an empty array for subsources, it it's a template:
		if 'template' in source_config:
			source_config['subsources'] = []
		
		# all good, add the source:
		self.__printer('ADD: {0}'.format(source_config['displayname']))
		self.lSource.append(source_config)
		self.lSource.sort( key=lambda k: k['order'] )
		
		# create a class object and store the reference to it
		# REPLACED BY YAPSY...
		'''
		if 'sourceModule' in source_config:
			obj = source_config['sourceModule']	#[0]
			sc = getattr(obj,'sourceClass')(self.logger)
			self.lSourceClasses.append(sc)
			#self.lSourceClasses.append(getattr(obj,'sourceClass')())
			# add a class field containing the class
			source_config['sourceClass'] = sc
		'''
		return True

	def add_sub( self, index, subsource_config ):
		""" Add a sub-source
		"""
		index = self.__check_index(index)
		
		if index is None:
			return False
		
		# check required fields:
		if not all (k in subsource_config for k in ('displayname','order')):
			self.__printer('ADD SUB: sub-source NOT added, missing one or more required field(s)...',LL_ERROR)
			self.__printer('Required fields are: displayname and order',LL_ERROR)
			return False
		
		# check key:
		keys = []
		keyvals = []
		for key in self.lSource[index]["subsource_key"]:
			if not key in subsource_config:
				self.__printer('Defined key ({0}) is missing value in subsource_config'.format(key),LL_ERROR)
				return False
			else:
				keys.append(key)
				keyvals.append(subsource_config[key])
				self.__printer("[OK] Found key value: {0}: {1}".format(key, subsource_config[key])) # LL_DEBUG

		# check for duplicate sub-source
		if len(self.lSource[index]["subsources"]) > 0:
	
			# for all defined keys, loop
			for key in keys:		
				# collect all key values from existing sub-sources
				existing_keyvals = []
				for i in self.lSource[index]["subsources"]:
					if key in i:
						print i[key]
						existing_keyvals.append(i[key])
				
				# check if mountpoint already exists	
				if subsource_config[key] in existing_keyvals:
					#TODO: remove+replace or abort?
					self.__printer('Sub-Source already exists, removing existing (?).'.format(key),LL_WARNING)
					#del self.lSource[index]["subsources"][]
					return False
			
		"""
		print "EXISTING KEYVALS: {0}".format(existing_keyvals)

		
		# check if the subsource already exist
		print "CONFIG RECEIVED:"
		print subsource_config
		print "MATCH FOR KEY:"
		print self.lSource[index]["subsource_key"]
		#print "MATCH FOR VALUE(s):"
		print "LOOKING FOR MATCH:"
		print set(keyvals)
		print set(existing_keyvals)
		#print set(keyvals) & set(dMatchAgainst.items())
		print "DEBUG! ----"
		
		#matches = set(dTest.items()) & set(dMatchAgainst.items())
		#if len(matches) == len(dTest):
		#return True
		"""
		
		# availability = False for all new subsources, until cleared by the check() function
		# TODO -- not fully implemented yet
		subsource_config['available'] = False

		# all good, add the source:
		self.__printer('ADD SUB: {0}'.format(subsource_config['displayname']))
		self.lSource[index]['subsources'].append(subsource_config)
		self.lSource[index]['subsources'].sort( key=lambda k: k['order'] )
		return True
	
	def rem( self, index=None, force=False ):
		"""Remove source by index. TODO: remove force variable
		"""
		if index:
			index = self.__check_index(index)
			if not index:
				self.__printer('ERROR rem: Not a valid index. Doing nothing.',LL_ERROR)
				return None

		elif index is None:
			index = self.iCurrentSource[0]
			if index is None:
				self.__printer('ERROR rem: No current source. Doing nothing.',LL_ERROR)
				return None
			
		#if index == self.iCurrentSource[0] and not force:
		#	self.__printer('ERROR rem: Cannot remove active source. Doing nothing.',LL_ERROR)
		#	return None
			
		#if not index == self.iCurrentSource[0]: or force:
		sourceName = self.lSource[index]['displayname']
		
		if len(self.lSource[index]) > index:
			del self.lSource[index]
			self.__printer('Source removed: {0}'.format(sourceName))
			return True
		else:
			self.__printer('ERROR rem: Invalid index: {0}'.format(index),LL_ERROR)
			return None
			
		# TODO: stop playing if removing current source
		#if index == self.iCurrentSource[0]
			
	def rem_sub( self, index=None, index_subsource=None ):
		"""	Remove subsource by index
			Remove current subsource, if no indexes given
		"""
		if index and index_subsource:
			index = self.__check_index(index)
			index_subsource = self.__check_subindex(index,index_subsource)
			if index is None or index_subsource is None:
				self.__printer('ERROR: No current source or sub-source. Doing nothing.',LL_ERROR)
				return None
							
		elif not index and not index_subsource:
			index = self.iCurrentSource[0]
			index_subsource = self.iCurrentSource[1]
			if index is None or index_subsource is None:
				return None
		
		elif index and not index_subsource:
			self.__printer('ERROR rem_sub: Sub-Source index missing',LL_ERROR)
			return None #?
			
		elif index_subsource and not index:
			self.__printer('ERROR rem_sub: Source index missing',LL_ERROR)
			return None #?
		
		if 'subsources' in self.lSource[index] and len(self.lSource[index]['subsources']) > index_subsource:
			del self.lSource[index]['subsources'][index_subsource]
		else:
			self.__printer('ERROR rem_sub: Invalid index or sub-source index',LL_ERROR)
			return None
			
		#Check if there are any available subsources left, if not mark source unavailable..
		if self.getAvailableSubCnt(index) == 0:
			self.__printer('No subsources left, marking source ({0}) as unavailable'.format(index))
			self.set_available(index, False)
		
		return True

	def index( self, key, value ):
		"""Return index based on key-value pair
		Tip: the "name" key is unique
		TODO: return None if not found?
		"""
		i=0
		for source in self.lSource:
			if source[key] == value:
				return i
			i+=1

	def index_current( self ):
		"""Return list of index and subindex of current source
		"""
		#copy.copy?
		return self.iCurrentSource

	def select( self, index, subIndex=None ):
		"""Set current source, by index
		"""
		index = int(index)		# not sure why, by since passing through MQ this is needed
			
		if index == None:
			self.__printer('Setting active source to None')
			return True
		elif index >= len(self.lSource):
			self.__printer('ERROR selecting source: Index ({0}) out of bounds'.format(index),LL_ERROR)
			print len(self.lSource)
			print self.lSource
			return False
		elif not self.lSource[index]['available']:
			self.__printer('ERROR selecting source: Requested source ({0}: {1:s}) is not available.'.format(index,self.lSource[index]['displayname']),LL_ERROR)
			return False
		#elif self.lSource[index]['template']:
		#	self.__printer('ERROR: Requested source ({0}: {1:s}) is a template.'.format(index,self.lSource[index]['displayname']),LL_ERROR)
		#	return False
		elif self.lSource[index]['available']:
			self.__printer('Setting active source to {0}: {1:s}'.format(index,self.lSource[index]['displayname']))
			self.iCurrentSource[0] = index

			# NEW: SUBSOURCES:
			if not subIndex == None:
				#TODO: add checks... (available, boundry, etc..)
				self.iCurrentSource[1] = subIndex
				return True
			else:
				return True

		else:
			self.__printer('ERROR: Requested source ({0}: {1:s}) cannot be set.'.format(index,self.lSource[index]['displayname']),LL_ERROR)
			return False

	def select_prev( self ):
		return self.select_next(True)
		
	def select_next( self, reverse=False ):
		""" Make the next available source the current, returns the new active source index
			return None if not succesful
			
			if reverse=True make the *PREVIOUS* available source the current
			Useful in case an active source becomes unavailable, it's more natural for the user to jump back
			to a previously playing source, instead of the next in line
		"""
		def source_iterator(ix_start, ix_stop, j_start, reverse):
			#
			# if no current source, we'll loop through the sources until we find one
			#
			# TODO CHECK IF i_start isn't at the end of the list!
			
			# python list slicing
			# step -1 reverses direction
			# the start and end needs to be reversed too
			# 
			original_start = ix_start
			
			if reverse:
				step = -1
				logtext = "to prev."
			else:
				step = 1
				logtext = "to next"
			
			# loop sources
			for source in self.lSource[ix_start:ix_stop:step]:
			
				# source available and has *no* sub-sources:
				if not source['template'] and source['available']:
					self.__printer('NEXT: Switching {0} {1}: {2:s}'.format(logtext,ix_start,source['displayname']))
					self.iCurrentSource[0] = ix_start
					self.iCurrentSource[1] = None
					return iCurrentSource
				
				# sub-source and available:
				elif source['template'] and source['available']:
				
					# reverse initialize sub-sources loop
					if reverse and j_start is None:
						j_start = len(source['subsources'])-1
									
					# reset sub-loop counter to 0
					if ix_start > original_start and j_start > 0:
						j_start = 0
				
					# loop sub-sources:
					for subsource in source['subsources'][j_start::step]:

						if subsource['available']:
							self.__printer('NEXT: Switching {0}: {1}/{2}: {3:s}'.format(logtext,ix_start,j_start,subsource['displayname']))
							self.iCurrentSource[0] = ix_start
							self.iCurrentSource[1] = j_start
							return self.iCurrentSource
							
						j_start += step

				ix_start += step

			return None
			
		#
		# check if iCurrentSource is set
		# (in that case, set the next available)
		#
		if self.iCurrentSource[0] is None:
			i = 0
			for source in self.lSource:
				if source['available'] and not source['template']:
					self.iCurrentSource[0] = i
					self.iCurrentSource[1] = None
					return self.iCurrentSource
				elif source['available'] and source['template']:
					self.iCurrentSource[0] = i
					j = 0
					for subsource in source['subsources']:
						if subsource['available']:
							self.iCurrentSource[1] = j
							return self.iCurrentSource
						j += 1
				i += 1
			
			if not self.iCurrentSource:
				self.__printer('NEXT: No available sources.',LL_WARNING)
				return None
			
			#return self.iCurrentSource
			return True
			
		#
		# check if we have at least two sources
		#
		iSourceCnt = self.getAvailableCnt()

		if iSourceCnt == 0:
			self.__printer('NEXT: No available sources.',LL_WARNING)
			return None
			
		elif iSourceCnt == 1:
			self.__printer('NEXT: Only one source, cannot switch.',LL_WARNING)
			return True

		#
		# determine starting positions
		#
		#
		# Current source is a Sub-Source
		#
		if not self.iCurrentSource[1] is None: # and
			
			if not reverse:
				
				# set source start point
				start = self.iCurrentSource[0]
				
				# set sub-source start point
				if self.iCurrentSource[1] is None:
					ssi_start = 0
				else:
					ssi_start = self.iCurrentSource[1]+1	#next sub-source (+1) isn't neccesarily available, but this will be checked later
					#print "Starting Sub-Source loop at {0}".format(ssi_start)

			elif reverse:
				
				#if the current sub-source is the first, the don't loop sub-sources, but start looping at the previous source
				ss_cnt = self.getAvailableSubCnt(self.iCurrentSource[0])
				if self.iCurrentSource[1] == 0 or ss_cnt-1 == 0:
				#if self.iCurrentSource[1] == 0 or ssi_start == 0:
					start = self.iCurrentSource[0]-1	# previous source
					ssi_start = None			# identifies to start at the highest sub-source
				else:
					start = self.iCurrentSource[0]	# current source
					ssi_start = ss_cnt-2		# previous sub-source
				
		#
		# Current source is *not* a Sub-Source:
		#
		elif self.iCurrentSource[1] is None:

			if not reverse:
			
				start = self.iCurrentSource[0]+1
				ssi_start=0
				
			elif reverse:
			
				# if the current source is the first, then start at the last source
				if self.iCurrentSource[0] == 0:
					start = len(self.lSource)-1		# start at the last item in the list
				else:
					start = self.iCurrentSource[0]-1		# previous source
				
				ssi_start=None
		
		# loop through sources
		# source_iterator returns next source index, or None, in case no next available was found
		res = source_iterator(start, None, ssi_start, reverse)
		
		# if nothing was found, "wrap-around" to beginning/ending of list
		if res == None:
				
			if not reverse:
				stop = start-1	# stop before current source
				start = 0		# start at the beginning
				ssi_start = 0
				return source_iterator(start, stop, ssi_start, reverse)
				
			elif reverse:
				stop = start					# stop at the current source
				start = len(self.lSource)-1 	# start at the last item in the list
				ssi_start = None
				return source_iterator(start, stop, ssi_start, reverse)
			
		else:
			return res
			
	def source_all( self, index=None ):
		""" Return a COPY of the complete lSource
		"""
		#return copy.copy(self.lSource)
		# Integrated get_all_simple:
		if index == None:
			mycopy = copy.copy(self.lSource)
#			for source in mycopy:
#				if 'sourceClass' in source:
#					del source['sourceClass']
#				if 'sourceModule' in source:
#					del source['sourceModule']
				#TODO: delete based on type(), figure out why this doesn't work:
#				for key,value in source.iteritems():
#					if type(value) == 'instance':
#						del source[key]
			return mycopy
		else:
			mycopy = copy.copy(self.lSource[index])
			for source in mycopy:
				for key,val in source:
					if type(val) == 'instance':
						del source[key]
				return mycopy

	#def get( self, index=self.iCurrent ):	syntax not allowed?
	def source( self, index=None ):
		""" Return source for given index, returns current source, if no index provided
		"""	
		index = self.__check_index(index)
		if index is False:
			return False

		if index is None:
			if self.iCurrentSource[0] is None:
				return None
			else:
				return copy.copy(self.lSource[self.iCurrentSource[0]])
		else:
			return copy.copy(self.lSource[index])			
				

	#def get_all_simple( self, index=None ):
	
	def composite( self ):
		""" Return the current source + subsource
			subsource is a dictionary in ['subsource'], containing the curren sub-source
			the returned source is stripped of python objects (for no real reason)
		"""
		# check index
		if self.iCurrentSource[0] is None:
			return None

		# make a copy
		composite_current_source = dict( self.lSource[self.iCurrentSource[0]] )
		# remove sub-sources:
		del composite_current_source['subsources']
			
		# check if current source is a sub-source
		if self.iCurrentSource[1] is None:
			# return without a subsource
			return composite_current_source
		else:		
			# add current sub-source: Note that this entry is called subsource, not subsources!
			composite_current_source['subsource'] = self.lSource[self.iCurrentSource[0]]['subsources'][self.iCurrentSource[1]]
			# remove not-usefull stuff:
			#del composite_current_source['sourceModule']	# what did we use this for again??? #TODO
			#del composite_current_source['sourceClass']		# what did we use this for again??? #TODO
			return composite_current_source
	
	def subsource_all( self, index=None ):
		""" Return all subsources for given index
			TODO: check if index is valid
		"""
		if index:
			index = self.__check_index(index)
		else:
			index = self.iCurrentSource[0]
		
		if not index:
			self.__printer('Could not determine index')
			return None

		if 'subsources' in self.lSource[index]:
			return self.lSource[index]['subsources']
			

	def subsource( self, index, index_subsource ):
		""" Return subsource by given index
			TODO: check if indexes are valid
		"""
		index = int(index)
		index_subsource = int(index_subsource)
		# TODO
		
		if 'subsources' in self.lSource[index]:
			#print len(self.lSource[index]['subsources'])
			if len(self.lSource[index]['subsources']) > 0:
				#print self.lSource[index]['subsources']
				return self.lSource[index]['subsources'][index_subsource]

	def set_available_kw( self, key, value, available ):
		"""
			# subsources:
			#	available -> False: will all be set to False
			#   available -> True: will not change (will need to set to available "manually")
		"""
		for source in self.lSource:
			if key in source and source[key] == value:
				source['available'] = available
				if available:
					availableText = colorize('[available    ]','light_green')
				else:
					availableText = colorize('[not available]','light_red')
					# loop through subsources, marking them unavailable:
					if 'subsources' in source and len(source['subsources']) > 0:
						for subsource in source['subsources']:
							subsource['available'] = False #TODO: do we need self. ??
							self.__printer('Subsource availability set to: {0} - {1}'.format(availableText,subsource['displayname']))
						
				self.__printer('Source availability set to: {0} - {1}'.format(availableText,source['displayname']))

	def set_available( self, index, available, index_subsource=None ):
		""" Set (sub)source availability
		"""
		
		index = self.__check_index(index)
		if index_subsource:
			index_subsource = int(index_subsource)	#TODO: pass through a ix check function
			
		if not index is None and index_subsource is None:
		
			self.lSource[index]['available'] = available		
			if available:
				availableText = colorize('[available    ]','light_green')
			else:
				availableText = colorize('[not available]','light_red')
			self.__printer('Source {0} availability set to {1} - {2}'.format(index,availableText,self.lSource[index]['displayname']))
			return True
						
		elif not index is None and not index_subsource is None:
		
			# also make parent source available
			self.lSource[index]['available'] = available
			self.lSource[index]['subsources'][index_subsource]['available'] = available
			if available:
				availableText = colorize('[available    ]','light_green')
			else:
				availableText = colorize('[not available]','light_red')
			self.__printer('Sub-Source {0} availability set to {1} - {2}'.format(index_subsource,availableText,self.lSource[index]['subsources'][index_subsource]['displayname']))
			return True

		else:
			return None
				
	# return number of available sources, including sub-sources
	def getAvailableCnt( self ):
		c = 0
		for source in self.lSource:
			if not source['template']:
				if source['available']:
					c += 1
			else:
				for subsource in source['subsources']:
					if subsource['available']:
						c += 1
		return c

	# return number of available subsource for given index
	def getAvailableSubCnt( self, index ):

		# check if index is a subsource
		if not 'subsources' in self.lSource[index]:
			return None
		
		c = 0
		for subsource in self.lSource[index]['subsources']:
			if subsource['available']:
				c += 1
		return c

	"""
	PROXY functions:
	================
	 move into subclass or something?
	"""

	def source_init_OLD( self, index ):
		""" Execute a init() for given source
		"""
		#self.__printer('INIT: {0}'.format(index)) #LL_DEBUG
		checkResult = self.lSource[index]['sourceClass'].init(self)

	"""
	def source_init(self,index):
		source_name = self.lSource[index]['name']
		the_source = self.source_manager.getPluginByName(source_name)	
		the_source.plugin_object.init(self)
		# OR:
		#self.source_manager.getPluginByName(source_name).plugin_object.init(self)
	"""
	
	def source_check( self, index=None, index_subsource=None ):
		""" Execute a check() for given source or subsource and sets availability accordingly
			
			if NO INDEXES are given, all sources and sub-sources will be checked.
			if ONLY a SOURCE INDEX is given, it will check the source and if it's a template will also check all subsources
			if BOTH INDEXES are given will check the specified sub-source
			
		X	Returns a list of dicts
			
			(Some soureces may themselves also set the available flag, but we do it here too....)
		"""
		index = self.__check_index(index)
		if index is False:
			return False
		
		index_subsource = self.__check_subindex(index,index_subsource)
		if index_subsource is False:
			return False
		
		changed_sources = []
		
		# Check all indexes
		if index is None and index_subsource is None:
			self.__printer('Checking all sources') #LL_DEBUG
			i=0
			for source in self.lSource:
				self.__printer('Checking: {0}'.format(i)) #LL_DEBUG
				if 'sourceClass' not in self.lSource[i]:
					self.__printer('has no sourceClass: {0}'.format(self.lSource[i]['name']))
				else:
					#checked_source_is_available = self.lSource[i]['available']
					check_result = self.lSource[i]['sourceClass'].check(self)	#returns a list of dicts with changes
					if check_result:
						for result in check_result:
							changed_sources.append(result)
										
					#if checked_source_is_available != check_result:
					#	self.lSource[i]['available'] = check_result
					#	changed_sources.append(i)
						
				i+=1
				
			if changed_sources:
				return changed_sources
			else:
				return None
				
		else:
			# Check specified subindex
			if index_subsource is not None:	
				self.__printer('Checking index/subindex: {0}/{1}'.format(index,index_subsource)) #LL_DEBUG
				
				#checked_source_is_available = self.lSource[index]['subsources'][index_subsource]['available']
				check_result = self.lSource[index]['sourceClass'].check(self,index_subsource)	#returns a list of dicts with changes
				
				return check_result
				
				#if len(check_result) > 0:
				
					#if checked_source_is_available != check_result:
					#	self.lSource[index]['available'] = check_result
					#	changed_sources.append( [index,index_subsource] )
					#	return changed_sources
				#else:
				#	return None
						
			# Check specified index
			elif index is not None:
				self.__printer('Checking index: {0}'.format(index)) #LL_DEBUG
				
				## todo  !! !!  ##
				#check_result = self.lSource[index]['sourceClass'].check(self,index_subsource)	#returns a list of dicts with changes

				#the_source = self.source_manager.getPluginByName(self.lSource[index]['name'])
				#check_result = the_source.plugin_object.check(self,index_subsource)	#returns a list of dicts with changes
				# OR:
				check_result = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.check(self,index_subsource)	#returns a list of dicts with changes

				for chg in check_result:
					if 'subindex' in chg and chg['subindex'] is not None:
						self.set_available( chg['index'], chg['available'], chg['subindex'] )
					else:
						self.set_available( chg['index'], chg['available'] )
						
				return check_result
				
			#if checked_source_is_available != check_result:
			#	self.lSource[index]['available'] = check_result
			#	changed_sources.append( [index] )
			#	return changed_sources
			#else:
			#	return None

				

	#TODO - INVESTIGATE
	def sourceAddSub( self, index, parameters ):
		# TODO: check if index is valid
		checkResult = self.lSource[index]['sourceClass'].add_subsource(self,parameters)
		return checkResult

	#def source_set_state( self, state ):
	
	# execute play() for the current source
	# suggested keywords: position in playlist; a dictionary may be given containing resume data
	def source_play( self, **kwargs ):
		if self.iCurrentSource[0] == None:
			self.__printer('PLAY: No current source',LL_WARNING)
			return False
		
		if not self.lSource[self.iCurrentSource[0]]['available']:
			self.__printer('PLAY: Source not available: {0}'.format(self.iCurrent),LL_WARNING)
			return False
		
		# pass arguments as-is to play function
		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].play( self, kwargs )
		
		if not ret:
			self.__printer('PLAY: failed, marking source unavailable, playing next source...',LL_ERROR)
			self.setAvailableIx(self.iCurrentSource[0],False,self.iCurrentSource[1])
			self.next()
			ret = self.sourcePlay()
			
		return ret

	# Proxy for stopping playback
	def source_stop( self ):
		if self.iCurrentSource[0] == None:
			self.__printer('STOP: No current source',LL_WARNING)
			return False
			
		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].stop()
		return ret

	# Proxy for pausing. Modes: on | off | toggle | 1 | 0
	def source_pause( self, mode ):
		if self.iCurrentSource[0] == None:
			self.__printer('PAUSE: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].pause( mode )
		return ret

	# Proxy for next (track/station/...)
	def source_next( self ):
		if self.iCurrentSource[0] == None:
			self.__printer('NEXT: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].next()
		return ret

	# Proxy for previous (track/station/...)
	def source_prev( self ):
		if self.iCurrentSource[0] == None:
			self.__printer('PREV: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].prev()
		return ret

	# Proxy for random. Modes: on | off | toggle | 1 | 0 | "special modes.."
	def source_random( self, mode ):
		if self.iCurrentSource[0] == None:
			self.__printer('RANDOM: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].random(mode )
		return ret

	# Proxy for seeking forward. Optionally provide arguments on how to seek (ie. number of seconds)
	def source_seekfwd( self, **kwargs ):
		if self.iCurrentSource[0] == None:
			self.__printer('SEEKFWD: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].seekfwd(kwargs )
		return ret

	# Proxy for seeking backwards. Optionally provide arguments on how to seek (ie. number of seconds)
	def source_seekrev( self, **kwargs ):
		if self.iCurrentSource[0] == None:
			self.__printer('SEEKREV: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].seekrev(kwargs )
		return ret

	# Proxy for database update. Optionally provide arguments. Suggestions: location
	def source_update( self, **kwargs ):
		if self.iCurrentSource[0] == None:
			self.__printer('UPDATE: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].update( kwargs )
		return ret


	# Return a dictionary containing source capabilities, etc.
	def source_get_source_details(self):
		# - available controls/functions
		# - available random modes
		if self.iCurrentSource[0] == None:
			self.__printer('GET DETAILS: No current source',LL_WARNING)
			return False

		data = self.lSource[self.iCurrentSource[0]]['sourceClass'].get_details( self )
		return data

	def source_get_state(self):
		# - playing/paused/stopped
		# - random, shuffle, repeat, 
		if self.iCurrentSource[0] == None:
			self.__printer('GET STATE: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].get_state( self )
		return ret

	# Return current playlist. NO: Optionally: getfolders=True
	def source_get_playlist(self, **kwargs):
		if self.iCurrentSource[0] == None:
			self.__printer('GET PLAYLIST: No current source',LL_WARNING)
			return False

		data = self.lSource[self.iCurrentSource[0]]['sourceClass'].get_playlist( self, kwargs )
		return data

	"""
	def source_get_folders(self, **kwargs):
		if self.iCurrentSource[0] == None:
			self.__printer('GET FOLDERS: No current source',LL_WARNING)
			return False

		data = self.lSource[self.iCurrentSource[0]]['sourceClass'].get_folders( self, kwargs )
		return data
	"""

	# Return details on the currently playing media
	def source_get_media_details(self):
		if self.iCurrentSource[0] == None:
			self.__printer('GET MEDIA DETAILS: No current source',LL_WARNING)
			return False

		data = self.lSource[self.iCurrentSource[0]]['sourceClass'].get_media_details( self, kwargs )
		return data


''' NOT USED:

	# get index of most recently added sub-source
	def getIndexSub( self, index, key, value ):
		"""
		"""
		i=0
		for subsource in self.lSource[index]['subsources']:
			if subsource[key] == value:
				return i
			i+=1
		return

	# return controls for given index ## do we need this
	def getSourceControls( self, index ):
		return self.lSource[index]['controls']

	# return availability true/false
	# return None if key-value pair didn't exist
	def getAvailable( self, index ):
		return self.lSource[index]['available']


	def sourceExec( self, index, sourceFunction ):
		obj = self.lSource[index][sourceFunction][0]
		func = self.lSource[index][sourceFunction][1]
		if len(self.lSource[index][sourceFunction]) == 3:
			params = self.lSource[index][sourceFunction][2]
			checkResult = getattr(obj,func)(params)
		else:
			checkResult = getattr(obj,func)()

			
	def nextOld( self, reverse=False ):

		def source_iterator(i_start, i_end, j_start, reverse):
			#
			# if no current source, we'll loop through the sources until we find one
			#
			# TODO CHECK IF i_start isn't at the end of the list!
			
			if reverse:
				step = -1
				logtext = "to prev."
			else:
				step = 1
				logtext = "to next"
			
			for source in self.lSource[i_start:i_end:step]:
				print "DEBUG B -- {0}".format(source)
				# no sub-source and available:
				if not source['template'] and source['available']:
					self.__printer('NEXT: Switching {0} {1}: {2:s}'.format(logtext,i_start,source['displayname']))
					self.iCurrentSource[0] = i_start
					self.iCurrentSource[1] = j_start
					return self.iCurrentSource
				
				# sub-source and available:
				elif source['template'] and source['available']:
					for subsource in source['subsources'][j_start::step]:
						print "DEBUG C {0}".format(subsource)
						if subsource['available']:
							self.__printer('NEXT: Switching {0}: {1}/{2}: {3:s}'.format(logtext,i_start,j_start,subsource['displayname']))
							self.iCurrentSource[0] = i_start
							self.iCurrentSource[1] = j_start
							return self.iCurrentSource
							
						j_start += 1

				i_start += step
				
			return None

		#
		# check if we have at least two sources
		#
		iSourceCnt = self.getAvailableCnt()

		if iSourceCnt == 0:
			self.__printer('NEXT: No available sources.',LL_WARNING)
			return self.iCurrentSource
		elif iSourceCnt == 1:
			self.__printer('NEXT: Only one source, cannot switch.',LL_WARNING)

		#
		# check if iCurrentSource is set
		# (in that case, set the next available, and return index)
		#
		if self.iCurrentSource[0] is None:
			i = 0
			for source in self.lSource:
				if source['available'] and not source['template']:
					self.iCurrentSource[0] = i
					self.iCurrentSource[1] = None
					return self.iCurrentSource
				elif source['available'] and source['template']:
					self.iCurrentSource[0] = i
					j = 0
					for subsource in source['subsources']:
						if subsource['available']:
							self.iCurrentSource[1] = j
							return self.iCurrentSource
						j += 1
				i += 1
			return self.iCurrentSource

		#
		# determine starting positions
		#
		# si  = source index
		# ssi = sub-source index
		#
		# _cur = current (starting) index
		# _end = ending index
		#
		
#		if self.iCurrent == None:
#			self.__printer('NEXT: No active source. Searching for first available ...',LL_DEBUG)
#			si_start=0
#			ssi_start=0
#			si_end = None
#		else:

		# Current source is a sub-source:
		if ( not self.iCurrentSource[1] == None and
			 self.getAvailableSubCnt(self.iCurrentSource[0]) > self.iCurrentSource[1]+1 ):
			# then first check if there are more sub-sources after the current..
			# there are more available sub-sources..
			si_cur = self.iCurrentSource[0]
			si_end = None
			ssi_start = self.iCurrentSource[1]+1	#next sub-source (+1) isn't neccesarily available, but this will be checked later
			
		# Current source is not a sub-source:
		else:
			#print "DEBUG 2"
			# no more available sub-sources
			si_cur = self.iCurrentSource[0]+1
			si_end = None
			ssi_start=0

		# source_iterator returns next source index, or None, in case no next available was found
		res = source_iterator(si_cur, si_end, ssi_start, reverse)
		if res == None:
			# Let's start from the beginning till current
			ssi_start = 0
			print "DEBUG still here..."
			return source_iterator(0, si_cur-1, ssi_start, reverse)
		else:
			return res
		
		"""
		
			
			i=self.iCurrent+1
			
			for source in self.lSource:
				if source['available']:
					if not source['template']:
						self.__printer('NEXT: Selecting {0}: {1:s}'.format(i,source['displayname']))
						self.iCurrent = i # source.index
						self.iCurrentSource[0] = i
						return self.iCurrentSource
					else:
						ss = 0
						for subsource in source['subsources']:
							if subsource['available']:
								self.__printer('NEXT: Selecting {0}: {1:s}'.format(i,source['displayname']))
								self.iCurrent = i # source.index
								self.iCurrentSS = ss
								self.iCurrentSource[0] = i
								self.iCurrentSource[1] = ss
								return self.iCurrentSource
							ss+=1
					#TODO? DO WE NEED TO SAVE HERE?
					# 	-> I think the caller shld take care of that...
					#print source.index
					#settings_save()
					#break
				i += 1
				
			if self.iCurrent == None:
				self.__printer('NEXT: No available sources!',LL_WARNING)

		else:
			# Starting for loop at next source
			
			self.__printer('TODO!!!! CONSIDER SUB-SOURCE!')
			
			i=self.iCurrent+1
			for source in self.lSource[self.iCurrent+1:]:
				if source['available']:
					self.__printer('NEXT: Switching to {0}: {1:s}'.format(i,source['displayname']))
					self.iCurrent = i
					return self.iCurrent
					break
				i += 1

			# Starting at beginning of the list until current source
			i=0
			for source in self.lSource[:self.iCurrent]:
				if source['available']:
					self.__printer('NEXT: Switching to {0}: {1:s}'.format(i,source['displayname']))
					self.iCurrent = i
					return self.iCurrent
					break
				i += 1
	
		"""
'''