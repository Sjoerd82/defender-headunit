#********************************************************************************
#
# Source: Example
#

from modules.hu_utils import *

sourceName='fm'

# Station list
#  TODO: load/save. In configuration(?)
lFmStations = [ 96.40, 99.10, 101.20, 102.54 ]

class sourceClass():

	# Wrapper for "myprint"
	def __printer( self, message, level=LL_INFO, continuation=False, tag=sourceName ):
		if continuation:
			myprint( message, level, '.'+tag )
		else:
			myprint( message, level, tag )

	#def __init__( self ):
		#self.__printer('Initialized')
		
	#def __del__( self ):
		#self.__printer('FM CLASS DELETE!')		# 	ERROR! } Exception TypeError: TypeError("'NoneType' object is not iterable",)
		#printer('FM CLASS DELETE!')			# 	ERROR! }
		#print('FM CLASS DELETE!')
		
	def init( self, sourceCtrl ):
		self.__printer('Initializing...', level=15)
		return True

	def check( self, sourceCtrl, subSourceIx=None  ):
		self.__printer('CHECK availability...')
		return True
		
	def play( self, sourceCtrl, subSourceIx=None ):
		self.__printer('Start playing FM radio...')
		return True	

	def stop( self ):
		self.__printer('Stop CLASS!')
		return True
		
	def next( self ):
		self.__printer('NOT IMPLEMENTED')
		return False
		
	def prev( self ):
		self.__printer('NOT IMPLEMENTED')
		return False

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
