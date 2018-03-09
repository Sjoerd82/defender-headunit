# MISC (self.__printer, colorize)
from hu_utils import *

import copy

class SourceController():

	def __init__(self):
		self.__printer('INIT', level=LL_DEBUG)
		
		# initialize instance variables:
		self.lSource = []
		#self.iCurrent = None
		#self.iCurrentSS = None
		self.iCurrentSource = [ None, None ]
		self.lSourceClasses = []
		self.iRecentSS = None

	def __printer( self, message, level=LL_INFO, continuation=False, tag='SOURCE' ):
		if continuation:
			myprint( message, level, '.'+tag )
		else:
			myprint( message, level, tag )
		
	# add source
	def add( self, source_config ):
		# check required fields:
		if not all (k in source_config for k in ('name','displayname','order','controls','template')):
			self.__printer('ADD: source NOT added, missing one or more required field(s)...',LL_ERROR)
			self.__printer('Required fields are: name,displayname,order,controls,template',LL_ERROR,True)
			return False

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
		if 'sourceModule' in source_config:
			obj = source_config['sourceModule']	#[0]
			sc = getattr(obj,'sourceClass')()
			self.lSourceClasses.append(sc)
			#self.lSourceClasses.append(getattr(obj,'sourceClass')())
			# add a class field containing the class
			source_config['sourceClass'] = sc
			
		return True

	# add sub-source
	def addSub( self, index, subsource_config ):

		# check required fields:
		if not all (k in subsource_config for k in ('displayname','order')):
			self.__printer('ADD SUB: sub-source NOT added, missing one or more required field(s)...',LL_ERROR)
			self.__printer('Required fields are: displayname and order',LL_ERROR,True)
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
	
	# remove source by index. Set force to True to allow removal of active source.
	def rem( self, index, force ):
		if not index == self.iCurrentSource[0] or force:
			sourceName = self.lSource[index]['displayname']
			#self.lSource.remove(index)
			del self.lSource[index]
			self.__printer('Source removed: {0}'.format(sourceName))
		else:
			self.__printer('ERROR: Cannot remove active source. Doing nothing.',LL_ERROR,self.mytag)

	# remove subsource by index
	def remSub( self, index, index_subsource ):
		del self.lSource[index]['subsources'][index_subsource]
		
		#Check if there are any available subsources left, if not mark source unavailable..
		if self.getAvailableSubCnt(index) == 0:
			self.setAvailableIx(index, False)
		
		return True

	# get index based on key-value pair
	# the "name" key is unique
	def getIndex( self, key, value ):
		i=0
		for source in self.lSource:
			if source[key] == value:
				return i
			i+=1

	# get list of index and subindex of current source
	def getIndexCurrent( self ):
		#copy.copy?
		return self.iCurrentSource

	# get index of most recently added sub-source
	def getIndexSub( self, index, key, value ):
		i=0
		for subsource in self.lSource[index]['subsources']:
			if subsource[key] == value:
				return i
			i+=1
		return
		
	# set current source, by index
	def setCurrent( self, index, subIndex=None ):
		if index == None:
			self.__printer('Setting active source to None')
			return True
		elif index >= len(self.lSource):
			self.__printer('ERROR: Index ({0}) out of bounds'.format(index),LL_ERROR)
			return False
		elif not self.lSource[index]['available']:
			self.__printer('ERROR: Requested source ({0}: {1:s}) is not available.'.format(index,self.lSource[index]['displayname']),LL_ERROR)
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


	# make the next available source the current, returns the new active source index
	# return None if not succesful
	
	# if reverse=True make the *PREVIOUS* available source the current
	""" Useful in case an active source becomes unavailable, it's more natural for the user to jump back
	    to a previously playing source, instead of the next in line """
	def next( self, reverse=False ):
	
		print ( "DEBUG!" )
		self.__printer( "DEBUG!!" )
		
		print lSource
	
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
					print('NEXT: Switching {0} {1}: {2:s}'.format(logtext,ix_start,source['displayname']))
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
							print('NEXT: Switching {0}: {1}/{2}: {3:s}'.format(logtext,ix_start,j_start,subsource['displayname']))
							self.iCurrentSource[0] = ix_start
							self.iCurrentSource[1] = j_start
							return self.iCurrentSource
							
						j_start += step

				ix_start += step

			return None
			
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
		# check if we have at least two sources
		#
		iSourceCnt = self.getAvailableCnt()

		if iSourceCnt == 0:
			self.__printer('NEXT: No available sources.',LL_WARNING)
			return self.iCurrentSource
		elif iSourceCnt == 1:
			self.__printer('NEXT: Only one source, cannot switch.',LL_WARNING)

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
	
	# return the complete lSource ## do we really need this?
	def getAll( self ):
		return copy.copy(self.lSource)

	# return source for given index, returns current source, if no index provided
	#def get( self, index=self.iCurrent ):	syntax not allowed?
	def get( self, index ):
		if index == None:
			if self.iCurrentSource[0] == None:
				return None
			else:
				return copy.copy(self.lSource[self.iCurrentSource[0]])
		else:
			return copy.copy(self.lSource[index])			

	# return the current source + subsource
	# subsource is a dictionary in ['subsource'], containing the curren sub-source
	# the returned source is stripped of python objects (for no real reason)
	def getComposite( self ):
	
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
			del composite_current_source['sourceModule']	# what did we use this for again??? #TODO
			del composite_current_source['sourceClass']		# what did we use this for again??? #TODO
			return composite_current_source
	
	def getSubSources( self, index ):
		return self.lSource[index]['subsources']

	def getSubSource( self, index, ssIndex ):
		if 'subsources' in self.lSource[index]:
			#print len(self.lSource[index]['subsources'])
			if len(self.lSource[index]['subsources']) > 0:
				#print self.lSource[index]['subsources']
				return self.lSource[index]['subsources'][ssIndex]
		
	# return controls for given index ## do we need this
	def getSourceControls( self, index ):
		return self.lSource[index]['controls']

	# overload using decorators?
	# subsources:
	#	available -> False: will all be set to False
	#   available -> True: will not change (will need to set to available "manually")
	def setAvailable( self, key, value, available ):
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

	def setAvailableIx( self, index, available, subIndex=None ):
	
		#TODO: cleanup this code
		if subIndex == None:
			# NOW ALLOWED:
			#if self.lSource[index]['template']:
			#	self.__printer('Availability: ERROR cannot make templates available.',LL_ERROR)
			#	return False
		
			try:
				self.lSource[index]['available'] = available
				if available:
					availableText = colorize('[available    ]','light_green')
				else:
					availableText = colorize('[not available]','light_red')
				self.__printer('Source {0} availability set to {1} - {2}'.format(index,availableText,self.lSource[index]['displayname']))
			except:
				self.__printer('Availability: ERROR could not set availability',LL_ERROR)
		else:
			try:
				# also make parent source available
				self.lSource[index]['available'] = available
				self.lSource[index]['subsources'][subIndex]['available'] = available
				if available:
					availableText = colorize('[available    ]','light_green')
				else:
					availableText = colorize('[not available]','light_red')
				self.__printer('Sub-Source {0} availability set to {1} - {2}'.format(subIndex,availableText,self.lSource[index]['subsources'][subIndex]['displayname']))
			except:
				self.__printer('Availability: ERROR could not set availability',LL_ERROR)
		
	# return availability true/false
	# return None if key-value pair didn't exist
	def getAvailable( self, index ):
		return self.lSource[index]['available']
	
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

	# execute a init() for given source
	def sourceInit( self, index ):
		self.__printer('INIT: {0}'.format(index)) #LL_DEBUG
		checkResult = self.lSource[index]['sourceClass'].init(self)

	# execute a check() for given source and sets availability accordingly
	def sourceCheck( self, index, subSourceIx=None ):
		self.__printer('CHECK: {0}/{1}'.format(index,subSourceIx)) #LL_DEBUG
		checkResult = self.lSource[index]['sourceClass'].check(self)
		return checkResult

	# execute a check() for all sources..
	#  if template set to False (default), exclude template sources..
	#  if template set to True, include template sources but exclude template based sources?
	def sourceCheckAll( self ):
		i=0
		for source in self.lSource:
			self.sourceCheck(i)				
			i+=1


	def sourceAddSub( self, index, parameters ):
		# TODO: check if index is valid
		checkResult = self.lSource[index]['sourceClass'].add_subsource(self,parameters)
		return checkResult

	"""
	def sourceExec( self, index, sourceFunction ):
		obj = self.lSource[index][sourceFunction][0]
		func = self.lSource[index][sourceFunction][1]
		if len(self.lSource[index][sourceFunction]) == 3:
			params = self.lSource[index][sourceFunction][2]
			checkResult = getattr(obj,func)(params)
		else:
			checkResult = getattr(obj,func)()
	"""

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

	# Proxy for `stopping playback
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

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].pause( self, mode )
		return ret

	# Proxy for next (track/station/...)
	def source_next( self ):
		if self.iCurrentSource[0] == None:
			self.__printer('NEXT: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].next( self )
		return ret

	# Proxy for previous (track/station/...)
	def source_prev( self ):
		if self.iCurrentSource[0] == None:
			self.__printer('PREV: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].prev( self )
		return ret

	# Proxy for random. Modes: on | off | toggle | 1 | 0 | "special modes.."
	def source_random( self, mode ):
		if self.iCurrentSource[0] == None:
			self.__printer('RANDOM: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].random( self, mode )
		return ret

	# Proxy for seeking forward. Optionally provide arguments on how to seek (ie. number of seconds)
	def source_seekfwd( self, **kwargs ):
		if self.iCurrentSource[0] == None:
			self.__printer('SEEKFWD: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].seekfwd( self, kwargs )
		return ret

	# Proxy for seeking backwards. Optionally provide arguments on how to seek (ie. number of seconds)
	def source_seekrev( self, **kwargs ):
		if self.iCurrentSource[0] == None:
			self.__printer('SEEKREV: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].seekrev( self, kwargs )
		return ret

	# Proxy for database update. Optionally provide arguments. Suggestions: location
	def source_update( self, **kwargs ):
		if self.iCurrentSource[0] == None:
			self.__printer('UPDATE: No current source',LL_WARNING)
			return False

		ret = self.lSource[self.iCurrentSource[0]]['sourceClass'].update( self, kwargs )
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
