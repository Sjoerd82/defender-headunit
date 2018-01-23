
# MISC (self.__printer, colorize)
from hu_utils import *

import copy

class SourceController():

	lSource = []
	iCurrent = None

	#def __init__(self):
		#print('[INIT] Setting up sources')

	def __printer( self, message, level=LL_INFO, continuation=False, tag='SOURCE' ):
		if continuation:
			myprint( message, level, '.'+tag )
		else:
			myprint( message, level, tag )
		
	# add source
	def add( self, source ):
		#Check required fields:
		if not all (k in source for k in ('name','displayname','order','available','controls','template')):
			self.__printer('ADD: Source NOT added, missing one or more required field(s)...',LL_ERROR)
			self.__printer('Required fields are: name,displayname,order,available,controls,template',LL_ERROR,True)
			return False

		#Availability = False for all new sources, until cleared by the check() function
		source['available'] = False
			
		#All good, add the source:
		self.__printer('ADD: {0}'.format(source['displayname']))
		#self.logger.info('ADD: {0}'.format(source['displayname']))
		self.lSource.append(source)
		self.lSource.sort( key=lambda k: k['order'] )
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

	# get index based on key-value pair. Set template to True to match only templates, False does not match Templates, None matches regardless of Template status
	def getIndex( self, key, value, template=False ):
		i=0
		for source in self.lSource:
			if source[key] == value and template == None:
				return i
			elif source[key] == value and source['template'] == template:
				return i
			i+=1
				
	# get index of current source
	def getIndexCurrent( self ):
		#copy.copy?
		return self.iCurrent

	# set current source, by index
	def setCurrent( self, index ):
		if index == None:
			self.__printer('Setting active source to None')
			return True
		elif index >= len(self.lSource):
			self.__printer('ERROR: Index ({0}) out of bounds'.format(index),LL_ERROR)
			return False
		elif self.lSource[index]['available']:
			self.__printer('Setting active source to {0}: {1:s}'.format(index,self.lSource[index]['displayname']))
			self.iCurrent = index
			return True
		elif not self.lSource[index]['available']:
			self.__printer('ERROR: Requested source ({0}: {1:s}) is not available.'.format(index,self.lSource[index]['displayname']),LL_ERROR)
			return False
		elif self.lSource[index]['template']:
			self.__printer('ERROR: Requested source ({0}: {1:s}) is a template.'.format(index,self.lSource[index]['displayname']),LL_ERROR)
			return False
		else:
			self.__printer('ERROR: Requested source ({0}: {1:s}) cannot be set.'.format(index,self.lSource[index]['displayname']),LL_ERROR)
			return False

	# make the next available source the current, returns the new active source index
	def next( self ):
		iSourceCnt = len(self.lSource)

		if iSourceCnt == 0:
			self.__printer('NEXT: No available sources.',LL_WARNING)
		elif iSourceCnt == 1:
			self.__printer('NEXT: Only one source, cannot switch.',LL_WARNING)
		else:

			# If no current source, we'll loop through the sources until we find one
			if self.iCurrent == None:
				self.__printer('NEXT: No active source. Searching for first available ...',LL_DEBUG)
				i=0
				for source in self.lSource:
					if source['available']:
						self.__printer('NEXT: Selecting {0}: {1:s}'.format(i,source['displayname']))
						self.iCurrent = i # source.index
						#print source.index
						#settings_save()
						break
					i += 1
					
				if self.iCurrent == None:
					self.__printer('NEXT: No available sources!',LL_WARNING)

			else:
				# Starting for loop at next source
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

	# return controls for given index ## do we need this
	def getSourceControls( self, index ):
		return self.lSource[index]['controls']

	# overload using decorators?
	def setAvailable( self, key, value, available ):
		for source in self.lSource:
			if key in source and source[key] == value and not source['template']:
				source['available'] = available
				if available:
					availableText = colorize('[available    ]','light_green')
				else:
					availableText = colorize('[not available]','light_red')
				self.__printer('Source availability set to: {0} - {1}'.format(availableText,source['displayname']))

	def setAvailableIx( self, index, available ):
		if self.lSource[index]['template']:
			self.__printer('Availability: ERROR cannot make templates available.',LL_ERROR)
			return False
		
		try:
			self.lSource[index]['available'] = available
			if available:
				availableText = colorize('[available    ]','light_green')
			else:
				availableText = colorize('[not available]','light_red')
			self.__printer('Source {0} availability set to {1} - {2}'.format(index,availableText,self.lSource[index]['displayname']))
		except:
			self.__printer('Availability: ERROR could not set availability',LL_ERROR)
		
	# return availability true/false
	# return None if key-value pair didn't exist
	def getAvailable( self, index ):
		return self.lSource[index]['available']
	
	# return number of available sources
	def getAvailableCnt( self ):
		#return len(self.lSource) # all sources
		i=0
		for source in self.lSource:
			if source['available']:
				i += 1
		return i

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
		if 'sourceInit' in self.lSource[index]:
			obj = self.lSource[index]['sourceInit'][0]
			func = self.lSource[index]['sourceInit'][1]
			if len(self.lSource[index]['sourceInit']) == 3:
				params = self.lSource[index]['sourceInit'][2]
				checkResult = getattr(obj,func)(params)
			else:
				checkResult = getattr(obj,func)(self)
	
	# execute a check() for given source and sets availability accordingly
	def sourceCheck( self, index ):
		#if self.iCurrent == None:
		#	print('[SOURCE] CHECK: No current source')
		#	return False

		obj = self.lSource[index]['sourceCheck'][0]
		func = self.lSource[index]['sourceCheck'][1]
		if len(self.lSource[index]['sourceCheck']) == 3:
			params = self.lSource[index]['sourceCheck'][2]
			checkResult = getattr(obj,func)(params)
		else:
			checkResult = getattr(obj,func)()
		self.setAvailableIx(index,checkResult)
	
	# execute a check() for all sources
	def sourceCheckAll( self ):
		i=0
		for source in self.lSource:
			if not source['template']:
				self.sourceCheck(i)
			i+=1
	
	# execute a play() for the current source
	def sourcePlay( self ):
		if self.iCurrent == None:
			self.__printer('PLAY: No current source',LL_WARNING)
			return False
			
		if not self.lSource[self.iCurrent]['available']:
			self.__printer('PLAY: Source not available: {0}'.format(self.iCurrent),LL_WARNING)
			return False
		
		try:
			if self.lSource[self.iCurrent]['sourcePlay'] == None:
				self.__printer('PLAY: function not defined',LL_WARNING)
		except Exception as ex:
			self.__printer('PLAY: ERROR: {0}'.format(ex),LL_CRITICAL)
		
		#try:
		obj = self.lSource[self.iCurrent]['sourcePlay'][0]
		func = self.lSource[self.iCurrent]['sourcePlay'][1]
		if self.lSource[self.iCurrent]['sourcePlay'].count == 3:
			params = self.lSource[self.iCurrent]['sourcePlay'][2]
			checkResult = getattr(obj,func)(params)
		else:
			checkResult = getattr(obj,func)()
		#except:
		#	print('[SOURCE] ERROR: calling player function')
		if not checkResult:
			self.__printer('PLAY: failed, marking source unavailable, playing next source...',LL_ERROR)
			self.setAvailableIx(self.iCurrent,False)
			self.next()
			self.sourcePlay()
	
	# execute a stop() for current source
	def sourceStop( self ):
		if self.iCurrent == None:
			self.__printer('STOP: No current source',LL_WARNING)
			return False
			
		try:
			if self.lSource[self.iCurrent]['sourceStop'] == None:
				self.__printer('STOP: function not defined',LL_WARNING)
		except Exception as ex:
			self.__printer('STOP: ERROR: {0}'.format(ex),LL_CRITICAL)
		
		try:
			obj = self.lSource[self.iCurrent]['sourceStop'][0]
			func = self.lSource[self.iCurrent]['sourceStop'][1]
			if self.lSource[self.iCurrent]['sourceStop'].count == 3:
				params = self.lSource[self.iCurrent]['sourceStop'][2]
				checkResult = getattr(obj,func)(params)
			else:
				checkResult = getattr(obj,func)()
		except:
			self.__printer('ERROR: calling player function',LL_CRITICAL)
		
