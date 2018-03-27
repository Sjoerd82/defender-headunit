#********************************************************************************
#
# Source: Example
#

from modules.hu_utils import *
from modules.source_plugin import BaseSourceClass

sourceName='fm'
LOG_TAG = 'FM'
LOGGER_NAME = 'fm'

# Station list
#  TODO: load/save. In configuration(?)
lFmStations = [ 96.40, 99.10, 101.20, 102.54 ]

class sourceClass(BaseSourceClass):

	# output wrapper
	def __printer( self, message, level=LL_INFO, tag=LOG_TAG):
		self.logger.log(level, message, extra={'tag': tag})

	def __init__(self, logger):
		self.logger = logger
		
	#def __del__( self ):
		#self.__printer('FM CLASS DELETE!')		# 	ERROR! } Exception TypeError: TypeError("'NoneType' object is not iterable",)
		#printer('FM CLASS DELETE!')			# 	ERROR! }
		#print('FM CLASS DELETE!')
		
	def init( self, sourceCtrl ):
		self.__printer('Initializing...', level=15)
		return True

	def check( self, sourceCtrl, subSourceIx=None  ):
		"""	Check source
		
			Checks to see if FM is available (SUBSOURCE INDEX will be ignored)
			Returns a list with dict containing changes in availability
			
			TODO: Will now simply return TRUE.
		"""
		self.__printer('CHECK availability...')

		subsource_availability_changes = []
		new_availability = True
		
		ix = sourceCtrl.index('name','fm')	# source index
		fm_source = sourceCtrl.source(ix)		
		original_availability = fm_source['available']
		
		if new_availability is not None and new_availability != original_availability:
			sourceCtrl.set_available( ix, new_availability )
			subsource_availability_changes.append({"index":ix,"available":new_availability})
		
		return subsource_availability_changes
		
	def play( self, sourceCtrl, subSourceIx=None ):
		self.__printer('Start playing FM radio...')
		return True	

	def stop( self ):
		self.__printer('Stop CLASS!')
		return True
		
	def pause( self, mode ):
		self.__printer('Pause. Mode: {0}'.format(mode))
		#TODO IMPLEMENT
		return True

	def random( self, mode ):
		self.__printer('Random. Mode: {0}'.format(mode))
		#TODO IMPLEMENT
		return True

	def seekfwd( self ):
		self.__printer('Seek FFWD')
		#TODO IMPLEMENT
		return True

	def seekrev( self ):
		self.__printer('Seek FBWD')
		#TODO IMPLEMENT
		return True

	def update( self ):
		self.__printer('Update not supported')
		return True

	def get_details():
		return False

	def get_state():
		return False

	def get_playlist():
		return False

	#def get_folders():

	def source_get_media_details():
		return False


	
def fm_popMenu():
	newMenu = []
	if lFmStations == []:
		newMenu.append( { "entry":"No saved stations" } )
		newMenu.append( { "entry":"Scan for stations", "run":"fm_scan" } )
	else:
		for station in lFmStations:
			newStation = { "entry":str(station)+'FM', "sub":None, "run":"fm_play", "params":str(station) }
			newMenu.append(newStation)
	return newMenu
