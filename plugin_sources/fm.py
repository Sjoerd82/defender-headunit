
from hu_utils import *

# Logging
mytag='fm'
sourceName='fm'

# Station list
#  TODO: load/save. In configuration(?)
lFmStations = [ 96.40, 99.10, 101.20, 102.54 ]

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

# Source Check: Return True/False (available/not available)
def fm_check():
	#global Sources
	printer('CHECK availability...')
	#arSourceAvailable[0]=0 # not available
	#Sources.setAvailable('name','fm',False) # not available
	#echo "Source 0 Unavailable; FM"
	return True

def fm_play():
	printer('[FM] Start playing FM radio...')
	return True
	#TODO

def fm_stop():
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
