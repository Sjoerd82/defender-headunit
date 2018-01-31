
from hu_utils import *

# Logging
mytag='fm'
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

	def __init__( self ):
		printer('FM CLASS INIT!')
		
	def __del__( self ):
		#self.__printer('FM CLASS DELETE!')		# 	ERROR! } Exception TypeError: TypeError("'NoneType' object is not iterable",)
		#printer('FM CLASS DELETE!')			# 	ERROR! }
		print('FM CLASS DELETE!')
		
	def check( self, sourceCtrl, subSourceIx=None  ):
		printer('CHECK availability...')
		return True
		
	def play( self, sourceCtrl, subSourceIx=None ):
		printer('Start playing FM radio...')
		return True	

	def stop( self, sourceCtrl ):
		printer('Stop CLASS!')
		return True
		
	def next( self ):
		printer('NOT IMPLEMENTED')
		return False
		
	def prev( self ):
		printer('NOT IMPLEMENTED')
		return False
		

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

# Source Check: Return True/False (available/not available)
def fm_check( sourceCtrl, subSourceIx=None  ):
	#global Sources
	printer('CHECK availability...')
	#arSourceAvailable[0]=0 # not available
	#Sources.setAvailable('name','fm',False) # not available
	#echo "Source 0 Unavailable; FM"
	return True

def fm_play( sourceCtrl, subSourceIx=None ):
	printer('[FM] Start playing FM radio...')
	return True
	#TODO

def fm_stop( sourceCtrl ):
	printer('[FM] Stop')
	return True
	
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
