
from hu_utils import *

from mpd import MPDClient

# Logging
mytag='smb'
sourceName='smb'


# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


def smb_check():
	#global arSourceAvailable
	#global Sources
	
	printer('Checking availability...')

	#Default to not available
	#arSourceAvailable[6]=0
	
	#Check if network up
	#TODO
	
	#See if we have smb location(s)
	#TODO

	#Check if at least one stream is good
	#TODO

	#OVERRIDE
	printer(' > Not implemented yet, presenting source as available ',tag='.'+mytag,level=LL_CRITICAL)
	#arSourceAvailable[6]=1
	#Sources.setAvailable('name','smb', True)
	return True

def smb_play():
	#global arSourceAvailable
	#global Sources
	
	printer('Play (MPD)')
	### TO be handled by Sources ###
	#if bInit == 0:
	#	print(' ...  Checking if source is still good')
	#	smb_check()

	### TO be handled by Sources ###
	"""
	if not Sources.getAvailable('name','smb')
		print(' ...  Aborting playback, trying next source.') #TODO red color
		pa_sfx(LL_ERROR)
		#source_next()
		Sources.sourceNext()
		source_play()
	else:
	"""

	# Connect to MPD
	try:
		mpc.connect("localhost", 6600)
	except:
		printer('MPD: Failed to connect to MPD server')
		return False

	printer(' ...... Emptying playlist')
	#todo: how about cropping, populating, and removing the first? item .. for faster continuity???
	
	mpc.stop()
	mpc.clear()
	mpc.close()	
	
	#call(["mpc", "-q", "stop"])
	#call(["mpc", "-q", "clear"])

	printer(' .... Populating playlist')
	mpc_populate_playlist('smb')
	
	printer(' .... Checking if playlist is populated')
	playlistCount = mpc_playlist_is_populated()
	if playlistCount == "0":
		printer(' .... . Nothing in the playlist, aborting...')
		pa_sfx(LL_ERROR)
		#arSourceAvailable[6] = 0
		Sources.setAvailable('name','smb',False)
		#source_next()
		Sources.sourceNext()
		source_play()
	else:
		printer(' .... . Found {0:s} tracks'.format(playlistCount))
		
	# continue where left
	playslist_pos = mpc_lkp('smb')
	
	printer(' .... Starting playback')
	call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
	# double check if source is up-to-date
	
	# Load playlist directories, to enable folder up/down browsing.
	#mpc_get_PlaylistDirs()
	# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
	mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc_get_PlaylistDirs)
	mpc_get_PlaylistDirs_thread.start()

def smb_stop():
	printer('stop')
	return True
