
# MISC (self.__printer, colorize)
from hu_utils import *

import copy

class SourceController():

	def __init__(self):
		self.__printer('INIT', level=LL_DEBUG)
		
		# initialize instance variables:
		self.lSource = []
		self.iCurrent = None
		self.iCurrentSS = None
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
		
		if len(self.lSource[index]["subsources"]) > 0:
			print "WE HAVE SS'S.. CHECK REQUIRED..."

		print "DEBUG! ----"
		
		# for all defined keys, loop
		print "WE HAVE TO CHECK THESE KEYS:"
		for key in keys:
			print key	# mountpoint, uuid, etc.
			
			# collect all key values from existing sub-sources
			# existing key values:
			#existing_keyvals = []
			#i = 0
			for i in range(0, len(self.lSource[index]["subsource_key"]) ):
				print self.lSource[index]["subsource_key"][i]
				
				#if keyA == key:
					#existing_keyvals.append( self.lSource[index]["subsource_key"][i][keyA]
			
			#if subsource_config[key] 
			# check if mountpoint already exists
			
		
		# existing key values:
		existing_keyvals = []
		i = 0
		for key in self.lSource[index]["subsource_key"]:
			print "EXISTING KEY: {0}".format(key)
			#print "EXISTING KEY VALUE: {0}".format( self.lSource[index]["subsources"][i][key] )
			#existing_keyvals.append( self.lSource[index]["subsources"][i][key] )
			i += 1
		
		
		# check if the subsource already exist
		print "SS COUNT:"
		print len(self.lSource[index]["subsources"])
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
		if not index == self.iCurrent or force:
			sourceName = self.lSource[index]['displayname']
			#self.lSource.remove(index)
			del self.lSource[index]
			self.__printer('Source removed: {0}'.format(sourceName))
		else:
			self.__printer('ERROR: Cannot remove active source. Doing nothing.',LL_ERROR,self.mytag)

	# remove subsource by index
	def remSub( self, index, index_subsource ):
		del self.lSource[index]['subsources'][index_subsource]
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
		arCurrIx = []
		arCurrIx.append(self.iCurrent)
		arCurrIx.append(self.iCurrentSS)
		#return self.iCurrent
		return arCurrIx

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
			self.iCurrent = index #TODO: OLD REMOVE
			self.iCurrentSource[0] = index

			# NEW: SUBSOURCES:
			if not subIndex == None:
				#TODO: add checks... (available, boundry, etc..)
				self.iCurrentSS = subIndex
				return True
			else:
				return True

		else:
			self.__printer('ERROR: Requested source ({0}: {1:s}) cannot be set.'.format(index,self.lSource[index]['displayname']),LL_ERROR)
			return False


	# make the next available source the current, returns the new active source index
	# return None if not succesful
	def next( self ):

		def dingding(i_start, i_end, j_start):
			#
			# if no current source, we'll loop through the sources until we find one
			#
			# TODO CHECK IF i_start isn't at the end of the list!
			for source in self.lSource[i_start:i_end]:
				#print "DEBUG A -- {0}".format(source)
				# no sub-source and available:
				if not source['template'] and source['available']:
					self.__printer('NEXT: Switching to {0}: {1:s}'.format(i_start,source['displayname']))
					self.iCurrent = i_start
					self.iCurrentSS = j_start
					self.iCurrentSource[0] = i_start
					self.iCurrentSource[1] = 0
					return self.iCurrentSource
				
				# sub-source and available:
				elif source['template'] and source['available']:
					for subsource in source['subsources'][j_start:]:
						if subsource['available']:
							#print "DEBUG 4"
							self.__printer('NEXT: Switching to {0}/{1}: {2:s}'.format(i_start,j_start,subsource['displayname']))
							self.iCurrent = i_start
							self.iCurrentSS = j_start
							self.iCurrentSource[0] = i_start
							self.iCurrentSource[1] = j_start
							return self.iCurrentSource
							
						j_start += 1

				i_start += 1
				
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

			# it's possible the iCurrentSource isn't set yet
			if (self.iCurrentSource[0] is None or
			    self.iCurrent is None):
				i = 0
				print "debug 1"
				for source in self.lSource:
					print "debug 2 {0}".format(i)
					if source['available'] and not source['template']:
						self.iCurrent = i
						self.iCurrentSource[0] = i
						self.iCurrentSource[1] = None
						print "debug 3"
						return self.iCurrentSource
					elif source['available'] and source['template']:
						self.iCurrentSource[0] = i
						self.iCurrent = i
						j = 0
						print "debug 4"
						for subsource in source['subsources']:
							print "debug 5 {0}".format(j)
							if subsource['available']:
								self.iCurrentSS = j
								self.iCurrentSource[1] = j
								print "debug 6 {0}".format(j)
								return self.iCurrentSource
							j += 1
					i += 1
			print "debug 7"
			return self.iCurrentSource

		#
		# determine starting positions
		#
		
		if self.iCurrent == None:
			self.__printer('NEXT: No active source. Searching for first available ...',LL_DEBUG)
			i_start=0
			j_start=0
			i_end = None
			i_end2 = None
		else:
			# if the current source is a sub-source, then first check if there are more sub-sources after the current
			if ( not self.iCurrentSource[1] == None and
			     self.getAvailableSubCnt(self.iCurrent) > self.iCurrentSource[1]+1 ):
				#print "DEBUG 1"
				# there are more available sub-sources..
				i_start = self.iCurrentSource[0]
				i_end = None
				i_end2 = i_start-1
				j_start = self.iCurrentSource[1]+1	#next sub-source (+1) isn't neccesarily available, but this will be checked later
			else:
				#print "DEBUG 2"
				# no more available sub-sources
				i_start = self.iCurrentSource[0]+1
				i_end = None
				i_end2 = i_start-1
				j_start=0

		#print "DEBUG: STARTING POSITIONS ARE: {0}, {1}".format(i_start, j_start)

		res = dingding(i_start, i_end, j_start)
		if res == None:
			# Still here?
			# Let's start from the top...
			i_start = 0
			j_start = 0
			#print "DEBUG still here..."
			return dingding(i_start, i_end2, j_start)
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
			if self.iCurrent == None:
				return None
			else:
				return copy.copy(self.lSource[self.iCurrent])
		else:
			return copy.copy(self.lSource[index])			

	# return the current source + subsource
	# subsource is a dictionary in ['subsource'], containing the curren sub-source
	# the returned source is stripped of python objects (for no real reason)
	def getComposite( self ):
		# make a copy
		composite_current_source = dict( self.lSource[self.iCurrent] )
		# remove sub-sources:
		del composite_current_source['subsources']
		# add current sub-source: Note that this entry is called subsource, not subsources!
		composite_current_source['subsource'] = self.lSource[self.iCurrent]['subsources'][self.iCurrentSS]
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
		c = 0
		for subsource in self.lSource[index]['subsources']:
			if subsource['available']:
				c += 1
		return c
		

		
	def sourceExec( self, index, sourceFunction ):
		obj = self.lSource[index][sourceFunction][0]
		func = self.lSource[index][sourceFunction][1]
		if len(self.lSource[index][sourceFunction]) == 3:
			params = self.lSource[index][sourceFunction][2]
			checkResult = getattr(obj,func)(params)
		else:
			checkResult = getattr(obj,func)()
	
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
	
	# execute a play() for the current source
	# optionally, a dictionary may be given containing resume data
	def sourcePlay( self, resume={} ):
	
		if self.iCurrent == None:
			self.__printer('PLAY: No current source',LL_WARNING)
			return False
		
		if not self.lSource[self.iCurrent]['available']:
			self.__printer('PLAY: Source not available: {0}'.format(self.iCurrent),LL_WARNING)
			return False
		
#		if 'sourcePlay' not in self.lSource[self.iCurrent] or self.lSource[self.iCurrent]['sourcePlay'] == None:
#			self.__printer('PLAY: function not defined',LL_WARNING)
#			return False
		
		if resume:
			checkResult = self.lSource[self.iCurrent]['sourceClass'].play(self,resume)
		else:
			checkResult = self.lSource[self.iCurrent]['sourceClass'].play(self)
			
		if not checkResult:
			self.__printer('PLAY: failed, marking source unavailable, playing next source...',LL_ERROR)
			self.setAvailableIx(self.iCurrent,False,self.iCurrentSS)
			self.next()
			self.sourcePlay()
	
	# execute a stop() for current source
	def sourceStop( self ):
		if self.iCurrent == None:
			self.__printer('STOP: No current source',LL_WARNING)
			return False
			
		checkResult = self.lSource[self.iCurrent]['sourceClass'].stop(self)
		
	# seek/next:
	def sourceSeekNext( self ):
		if self.iCurrent == None:
			self.__printer('STOP: No current source',LL_WARNING)
			return False

		checkResult = self.lSource[self.iCurrent]['sourceClass'].next()

	# seek/prev:
	def sourceSeekPrev( self ):
		if self.iCurrent == None:
			self.__printer('STOP: No current source',LL_WARNING)
			return False


		checkResult = self.lSource[self.iCurrent]['sourceClass'].prev()

