
from hu_utils import *

# Logging
sourceName='media'

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

def media_add( dir, sourceCtrl ):
	ix = sourceCtrl.getIndex('name','media',True)
	template = sourceCtrl.get(ix)
	template['template'] = False
	template['mountpoint'] = dir
	sourceCtrl.add(template)

def media_check():
	return False

def media_play():
	return True
 
def media_stop():
	return True