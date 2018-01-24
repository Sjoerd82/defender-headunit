
from hu_utils import *

# Logging
mytag='line'
sourceName='line'

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

# updates arSourceAvailable[4] (alsa) -- TODO
def linein_check( sourceCtrl ):
	#global Sources
	printer('Checking if Line-In is available... not available')
	#arSourceAvailable[4]=0 # not available
	#Sources.setAvailable('name','alsa',False) # not available
	#echo "Source 4 Unavailable; Line-In / ALSA"
	return False

def linein_play():
	printer('[LINE] Start playing from line-in...')
	#TODO
	return True

def linein_stop():
	printer('[LINE] Stop')
	return True

