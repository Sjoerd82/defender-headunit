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
# - Naming: Index, Subindex
#
# - Leave (sub)index parameter None (default) to indicate current source
# - Returns True or data, if succesful
# - Return None if nothing to do / no change
# - Return False if failure
#
# Sources can be enabled/disabled
# Subsources can be available/unavailable
#
#
#	add					Add a source
#	add_sub				Add a sub-source
#	check				Check if (sub)source is available
#	check_all			Check all sources (and sub-sources)
#   set_enabled			Set enabled indicator by source index
#	set_available		Set available indicator by (sub)source index
#	cnt_subsources		Returns number of available subsources (all, or for given index)
#	rem					Remove a source
#	rem_sub				Remove a sub-source
#	index				Returns index of source by keyword
#	index_current		Returns list of indexes of current source and current sub-source
#   subindex			
#	source				Returns source by index (current if no index given)
#	source_all			Returns list of all sources (class refs omitted)
#	subsource			Returns COPY of subsource for given source index (current subsource if no indexes given)
#	subsource_all		Returns list of all sources (class refs omitted)
#	composite			Returns composite source (source+subsource)
#	select				Set source
#	select_next			Next source
#>>>select_next_pri		Next primary source (skipping over sub-sources)
#	select_prev			Prev source
#>>>select_prev_pri		Prev primary source (skipping over sub-sources)
#
#	CATEGORY
#
#	do_category			Do something for a category
#
#   SOURCE PROXY FUNCTIONS:
#	Executes functions in the source class
#
#	source_init			Code to be executed once, during initialization of the source
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

import copy

from yapsy.PluginManager import PluginManager
from hu_utils import *
from slugify import slugify

LOG_TAG = 'SOURCE'

class SourceController(object):

	def do_event(self,category,path,payload=None):	
		#for pluginInfo in self.source_manager.getPluginsOfCategory(category):
		#	print "DEBUG: executing plugins on_category()"
		#	pluginInfo.plugin_object.on_category(category,payload)
		i = 0
		for source in self.lSource:
			if category in source['trigger_events']:
				self.source_manager.getPluginByName(self.lSource[i]['name']).plugin_object.on_event(category,path,payload)
			i += 1
		

	def __printer( self, message, level=LL_INFO, tag=LOG_TAG):
		self.logger.log(level, message, extra={'tag': tag})
	
	def __init__(self, logger):
		self.logger = logger
		
		# initialize INSTANCE! variables:
		self.lSource = []
		self.iCurrentSource = [ None, None ]	#Source, Sub-Source
		self.lSourceClasses = []
		self.iRecentSS = None
		
		# TODO
		self.cnt_sources_total = 0
		self.cnt_sources_avail = 0

		self.source_manager = PluginManager()


		# YAPSY LOG OUTPUT TO CONSOLE
		logyapsy = logging.getLogger('yapsy')
		logyapsy.setLevel(logging.DEBUG)
		ch = logging.StreamHandler()
		ch.setLevel(logging.DEBUG)
		logyapsy.addHandler(ch)

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
		self.source_manager.setPluginPlaces(['/mnt/PIHU_APP/defender-headunit/sources'])	#TODO: plugindir
		self.source_manager.collectPlugins()

		# Activate and add all collected plugins
		for plugin in self.source_manager.getAllPlugins():
			try:
				ret_init = plugin.plugin_object.on_init(plugin.name, self, self.logger)
			except:
				pass
				
			if not ret_init:
				self.__printer('Plugin {0} failed (on_init); cannot load plugin'.format(plugin.name))
			else:			
				self.source_manager.activatePluginByName(plugin.name)
				config = plugin.plugin_object.configuration()							# Get config
				#self.source_manager.appendPluginToCategory(plugin,config['category'])	# Set plugin category	-- NOT SUPPORTED IN PY2.7!
				isAdded = self.add(config)												# Add
				if isAdded:
					indexAdded = self.index('name',config['name'])
					try:
						plugin.plugin_object.on_add(config)
					except Exception, e:
						self.__printer('Plugin {0} failed; disabling plugin. Error in on_add(): {1}'.format(plugin.name,str(e)))
						self.lSource[indexAdded]['enabled'] = False
			
	def add( self, source_config ):
		""" Add a Source
		"""
		# check required fields:
		if not all (k in source_config for k in ('name','controls')):
			self.__printer('ADD: source NOT added, missing one or more required field(s)...',LL_ERROR)
			self.__printer('Required fields are: name,controls',LL_ERROR)
			return False

		# test if name is unique
		# #TODO
		
		if 'displayname' not in source_config:
			source_config['displayname'] = source_config['name']

		if 'order' not in source_config:
			source_config['order'] = 0

		if 'enabled' not in source_config:
			source_config['enabled'] = True

		# check subsource(s)
		if 'subsources' not in source_config:
			source_config['subsources'] = []
		else:
			i=0
			for subsource in source_config['subsources']:
				if 'displayname' not in subsource:
					source_config['subsources'][i]['displayname'] = source_config['name']
				
				if 'order' not in subsource:
					source_config['subsources'][i]['order'] = 0

				if 'available' not in subsource:
					source_config['subsources'][i]['available'] = False

						
		# availability = False for all new sources, until cleared by the check() function
		source_config['available'] = False
			
		# all good, add the source:
		self.__printer('ADD: {0}'.format(source_config['displayname']))
		self.lSource.append(source_config)
		self.lSource.sort( key=lambda k: k['order'] )	
		return True

	def add_sub( self, index, subsource_config ):
		""" Add a sub-source
		"""
		index = self.__check_index(index)
		
		if index is None:
			return False
		
		# check required fields:
		#if not all (k in subsource_config for k in ('displayname','order')):
		#	self.__printer('ADD SUB: sub-source NOT added, missing one or more required field(s)...',LL_ERROR)
		#	self.__printer('Required fields are: displayname and order',LL_ERROR)
		#	return False

		if 'displayname' not in subsource_config:
			subsource_config['displayname'] = subsource_config['name']

		if 'order' not in subsource_config:
			subsource_config['order'] = 0

		if 'available' not in subsource_config:
			subsource_config['available'] = False

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
		
		# handy unique identifier for this subsource
		subsource_config['keyvalue'] = slugify('.'.join(keyvals))

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
		if self.cnt_subsources(index) == 0:
			self.__printer('No subsources left, marking source ({0}) as unavailable'.format(index))
			self.set_available(index, False)
		
		return True
	
	def check( self, index=None, subindex=None ):
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
		
		subindex = self.__check_subindex(index,subindex)
		if subindex is False:
			return False
		
		changed_sources = []
		
		# Check all indexes
		if index is None and subindex is None:
			self.__printer('Checking all sources') #LL_DEBUG
			i=0
			for source in self.lSource:
				self.__printer('Checking: {0}'.format(i)) #LL_DEBUG
				if 'sourceClass' not in self.lSource[i]:
					self.__printer('has no sourceClass: {0}'.format(self.lSource[i]['name']))
				else:
					#checked_source_is_available = self.lSource[i]['available']
					#check_result = self.lSource[i]['sourceClass'].check(self)	#returns a list of dicts with changes
					check_result = self.source_manager.getPluginByName(self.lSource[i]['name']).plugin_object.check_availability()	#returns a list of dicts with changes
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
			if subindex is not None:	
				self.__printer('Checking index/subindex: {0}/{1}'.format(index,subindex)) #LL_DEBUG
				
				#checked_source_is_available = self.lSource[index]['subsources'][subindex]['available']
				#check_result = self.lSource[index]['sourceClass'].check(self,subindex)	#returns a list of dicts with changes
				check_result = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.check_availability(subindex=subindex)	#returns a list of dicts with changes
				
				return check_result
				
				#if len(check_result) > 0:
				
					#if checked_source_is_available != check_result:
					#	self.lSource[index]['available'] = check_result
					#	changed_sources.append( [index,subindex] )
					#	return changed_sources
				#else:
				#	return None
						
			# Check specified index
			elif index is not None:
				self.__printer('Checking index: {0}'.format(index)) #LL_DEBUG
				
				## todo  !! !!  ##
				#check_result = self.lSource[index]['sourceClass'].check(self,subindex)	#returns a list of dicts with changes

				#the_source = self.source_manager.getPluginByName(self.lSource[index]['name'])
				#check_result = the_source.plugin_object.check(self,subindex)	#returns a list of dicts with changes
				# OR:
				check_result = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.check_availability(subindex=subindex)	#returns a list of dicts with changes
				
				if check_result is None:
					self.__printer('Checking source {0} ({1}) did not return any results (no available sources?)'.format(self.lSource[index]['name'],index),level=LL_WARNING)
				else:
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

	def subindex(self,index,key,value):
		index = self.__check_index(index)
		if index is False:
			return False

		j=0
		for subsource in self.lSource[index]['subsources']:
			if subsource[key] == value:
				return j
			j+=1
		
		return False
		
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
			""" Returns next available source.
				Return None, if none found
				
				ix_start: start at this source index
				ix_stop: stop at this source index (inclusive)
						None: until end
				
			"""
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
			
			# set loop end point:
			if ix_stop is not None:
				ix_stop += 1
			
			# loop sources
			for source in self.lSource[ix_start:ix_stop:step]:
			
				if source['enabled'] is True:
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
							self.source_manager.getPluginByName(self.lSource[ix_start]['name']).plugin_object.on_activate(j_start)
							return self.iCurrentSource
							
						j_start += step

				ix_start += step
			return None
			
		#
		# check if iCurrentSource is set
		# (if not, set the next available)
		#
		if self.iCurrentSource[0] is None:
			i = 0
			
			for source in self.lSource:
			
				if source['enabled'] is True:
					j = 0
					for subsource in source['subsources']:
						if subsource['available']:
							self.iCurrentSource[0] = i
							self.iCurrentSource[1] = j
							self.source_manager.getPluginByName(self.lSource[i]['name']).plugin_object.on_activate(j)
							return self.iCurrentSource
						j += 1
				i += 1
			
			if not self.iCurrentSource:
				self.__printer('NEXT: No available sources.',LL_WARNING)
				return None
			
			return None
			
		#
		# check if we have at least two sources
		#
		iSourceCnt = self.cnt_subsources()

		if iSourceCnt == 0:
			self.__printer('NEXT: No available sources.',LL_WARNING)
			return None
			
		elif iSourceCnt == 1:
			self.__printer('NEXT: Only one source, cannot switch.',LL_WARNING)
			return None

		#
		# determine starting positions
		#
		#
		# Current source is a Sub-Source
		# Why?
		if self.iCurrentSource[1] is not None: # and

			if not reverse:

				# set source start point
				start = self.iCurrentSource[0]
				
				# set sub-source start point
				if self.iCurrentSource[1] is None:
					print "Y4 DEPRECATED"
					ssi_start = 0
				else:
					ssi_start = self.iCurrentSource[1]+1	#next sub-source (+1) isn't neccesarily available, but this will be checked later
					#print "Starting Sub-Source loop at {0}".format(ssi_start)

			elif reverse:
				#if the current sub-source is the first, the don't loop sub-sources, but start looping at the previous source
				ss_cnt = self.cnt_subsources(self.iCurrentSource[0])
				if self.iCurrentSource[1] == 0 or ss_cnt-1 == 0:
				#if self.iCurrentSource[1] == 0 or ssi_start == 0:
					start = self.iCurrentSource[0]-1	# previous source
					ssi_start = None			# identifies to start at the highest sub-source
				else:
					start = self.iCurrentSource[0]	# current source
					ssi_start = ss_cnt-2		# previous sub-source
				
		#
		# Current source is *not* a Sub-Source: (DEPRECATED!!)
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
		if res is None:
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
#			mycopy = copy.copy(self.lSource)
#			for source in mycopy:
#				if 'sourceClass' in source:
#					del source['sourceClass']
#				if 'sourceModule' in source:
#					del source['sourceModule']
				#TODO: delete based on type(), figure out why this doesn't work:
#				for key,value in source.iteritems():
#					if type(value) == 'instance':
#						del source[key]
#			return mycopy
			return self.lSource
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
	
	def composite(self, index=None, subindex=None):
		""" Return COPY of the current source + subsource
			subsource is a dictionary in ['subsource'], containing the curren sub-source
		"""
		index = self.__check_index(index)
		subindex = self.__check_subindex(index,subindex)
		
		if index is None and subindex is None:
			# use current subsource
			index = self.iCurrentSource[0]
			subindex = self.iCurrentSource[1]
			
		if index is None or subindex is None:
			# we need both
			return False
			
		# make a copy of the source
		source_copy = copy.deepcopy(self.lSource[index])
		del source_copy['subsources']
		
		#subsource_copy = copy.deepcopy(self.lSource[index]['subsources'][subindex])
		#subsource_copy.update(source_copy)
		
		composite = {}
		composite.update(source_copy)
		composite.update(self.lSource[index]['subsources'][subindex])
		# some useful bonus fields (careful, these indexes are volatile!
		composite['index'] = index
		composite['subindex'] = subindex
		return composite
	
	def subsource_all( self, index=None ):
		""" Return all subsources for given index
			If no index is given, will return for active source (if any)
		"""
		if index is not None:
			index = self.__check_index(index)
		else:
			index = self.iCurrentSource[0]
		
		if index is None:
			self.__printer('Could not determine index')
			return None

		if 'subsources' in self.lSource[index]:
			return self.lSource[index]['subsources']
			

	def subsource(self, index=None, subindex=None):
		""" Return COPY of subsource by given index """
		index = self.__check_index(index)
		subindex = self.__check_subindex(index,subindex)
		
		if index is None and subindex is None:
			# use current subsource
			index = iCurrentSource[0]
			subindex = iCurrentSource[1]
			
		if index is None or subindex is None:
			# we need both
			return False
		
		if 'subsources' in self.lSource[index]:
			if len(self.lSource[index]['subsources']) > 0:
				subsource_copy = copy.deepcopy(self.lSource[index]['subsources'][subindex])
				#subsource_copy['index'] = index	# Use composite() if you need source details..
				return subsource_copy

	def set_enabled(self, index, enabled):
		"""Set source en/disabled"""
		index = self.__check_index(index)
		
		if index is not None:
			if enabled:
				enabledText = colorize('[enabled ]','light_green')
			else:
				enabledText = colorize('[disabled]','light_red')
				
			self.lSource[index]['enabled'] = enabled
			self.__printer('Source {0} set to {1} - {2}'.format(index,enabledText,self.lSource[index]['displayname']))
			return True
			
		else:
			return None
			
	def set_available( self, index, available, subindex=None ):
		"""Set subsource availability"""
		index = self.__check_index(index)
		subindex = self.__check_subindex(index,subindex)
		
		if index is not None and subindex is None:
			# Mark all subsources of this index
			if available:
				availableText = colorize('[available    ]','light_green')
			else:
				availableText = colorize('[not available]','light_red')
				
			for subindex in range(len(self.lSource[index]['subsources'])):
				self.lSource[index]['subsources'][subindex]['available'] = available
				self.__printer('Source {0} availability set to {1} - {2}'.format(index,availableText,self.lSource[index]['displayname']))
			return True
						
		elif index is not None and subindex is not None:
			# Mark specified subsource
			self.lSource[index]['subsources'][subindex]['available'] = available
			if available:
				availableText = colorize('[available    ]','light_green')
			else:
				availableText = colorize('[not available]','light_red')
			self.__printer('Sub-Source {0} availability set to {1} - {2}'.format(subindex,availableText,self.lSource[index]['subsources'][subindex]['displayname']))
			return True

		else:
			return None
			
	def cnt_subsources(self, index=None):
		"""Return number of available subsources"""		
		if index is None:
			i = self.lSource
		else:
			index = self.__check_index(index)
			if index is None:
				return False
			else:
				i = self.lSource[index]
		
		c = 0
		for source in i:
			if source['enabled'] is True:
				for subsource in source['subsources']:
					if subsource['available']:
						c += 1			
		return c

	# -------------------------------------------------------------------------
	# PROXY FUNCTIONS
	#
	# Call with arguments:
	# index, subindex, SrcCtrl + index passed from caller
	#
	# (always?) called with parameters:
	# index, subindex, SourceControl
	#
	# move into subclass or something?
	#

	def __get_current(self,function):
	
		index = self.iCurrentSource[0]
		subindex = self.iCurrentSource[1]

		if index is None or subindex is None:
			self.__printer('{0}: No current source'.format(function),LL_WARNING)
			return None, None
			
		else:
			return index, subindex		

	#def source_set_state( self, state ):
	
	# execute play() for the current source
	# suggested keywords: position in playlist; a dictionary may be given containing resume data
	def source_play(self, **kwargs ):
		""" Current source: Play
		"""
		
		index, subindex = self.__get_current('PLAY')
		if index is not None and subindex is not None:

			if not self.lSource[index]['subsources'][subindex]['available']:
				self.__printer('PLAY: Source not available: {0}.{1}'.format(index,subindex),LL_WARNING)
				return False

			if index is not None and subindex is not None:
				ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.play(index=index,subindex=subindex,**kwargs)
				return ret
			
			if not ret:
				self.__printer('PLAY: failed, marking source unavailable, playing next source...',LL_ERROR)
				self.set_available(index,False,subindex)
				ret_next = self.select_next()
				if ret_next:
					ret = self.source_play()
					return ret
				else:
					return False

	# Proxy for stopping playback
	def source_stop(self, **kwargs ):
		index, subindex = self.__get_current('STOP')
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.stop(index=index,subindex=subindex,**kwargs)
			return ret

	# Proxy for pausing. Modes: on | off | toggle | 1 | 0
	def source_pause(self, mode, **kwargs ):
		index, subindex = self.__get_current('PAUSE')
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.pause(index=index,subindex=subindex,mode=mode,**kwargs)
			return ret

	# Proxy for next (track/station/...)
	def source_next(self, **kwargs ):
		index, subindex = self.__get_current('NEXT')
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.next(index=index,subindex=subindex,**kwargs)
			return ret

	# Proxy for previous (track/station/...)
	def source_prev(self, **kwargs ):
		index, subindex = self.__get_current('PREV')
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.prev(index=index,subindex=subindex,**kwargs)
			return ret

	# Proxy for random. Modes: on | off | toggle | 1 | 0 | "special modes.."
	def source_random(self, mode, **kwargs ):
		index, subindex = self.__get_current('MODE')
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.random(index=index,subindex=subindex,mode=mode,**kwargs)
			return ret

	# Proxy for seeking forward. Optionally provide arguments on how to seek (ie. number of seconds)
	def source_seekfwd(self, **kwargs ):
		index, subindex = self.__get_current('SEEKFWD')
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.seekfwd(index=index,subindex=subindex,**kwargs)
			return ret

	# Proxy for seeking backwards. Optionally provide arguments on how to seek (ie. number of seconds)
	def source_seekrev(self, **kwargs ):
		index, subindex = self.__get_current('SEEKREV')
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.seekrev(index=index,subindex=subindex,**kwargs)
			return ret

	# Proxy for database update. Optionally provide arguments. Suggestions: location
	def source_update(self, **kwargs ):
		index, subindex = self.__get_current('SEEKFWD')
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.update(index=index,subindex=subindex,**kwargs)
			return ret

	def source_get_state(self, **kwargs ):
		index, subindex = self.__get_current('GET_STATE')
		# - playing/paused/stopped
		# - random, shuffle, repeat, 
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.get_state(**kwargs)
			return ret

	# Return a dictionary containing source capabilities, etc.
	def source_get_details(self, **kwargs ):
		index, subindex = self.__get_current('GET_DETAILS')
		# - available controls/functions
		# - available random modes
		if index is not None and subindex is not None:
			ret = self.source_manager.getPluginByName(self.lSource[index]['name']).plugin_object.get_details(**kwargs)
			return ret
		

	# -------------------------------------------------------------------------			


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

	#TODO - INVESTIGATE
	def sourceAddSub( self, index, parameters ):
		# TODO: check if index is valid
		checkResult = self.lSource[index]['sourceClass'].add_subsource(self,parameters)
		return checkResult



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
		iSourceCnt = self.cnt_subsources()

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
			 self.cnt_subsources(self.iCurrentSource[0]) > self.iCurrentSource[1]+1 ):
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
#	sourceCheck		=>	source_check	=> check
#	sourceCheckAll	=>	source_check