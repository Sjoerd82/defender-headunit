
from hu_utils import *

from mpd import MPDClient

mytag = 'STREAM'
sourceName = 'stream'

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


def internet():
	try:
		# connect to the host -- tells us if the host is actually reachable
		socket.create_connection((sInternet, 80))
		return True
	except OSError:
		pass
	except:
		pass
	return False

# no initializations required
def stream_init( sourceCtrl ):
	pass
	
def stream_check( sourceCtrl, subSourceIx=None  ):

	#TODO!!
	sDirSave = "/mnt/PIHU_CONFIG"

	printer('CHECKING availability...')

	# Default to not available
	#arSourceAvailable[5]=0
	#Sources.setAvailable('name','strea',False)
	
	# Test internet connection
	connected = internet()
	if not connected:
		printer(' > Internet: [FAIL]')
		printer(' > Marking source not available')
		return False
	else:
		printer(' > Internet: [OK]')

	# See if we have streaming URL's
	streams_file = sDirSave + "/streams.txt"
	if os.path.isfile(streams_file):
		printer(' > Stream URL\'s: File found [OK]')
	else:
		printer(' > Stream URL\'s: File not found [FAIL]')
		printer(' > Marking source not available')
		return False

	# Check if at least one stream is good
	printer('Checking to see we have at least one valid stream')
	with open(streams_file,'r') as streams:
		for l in streams:
			uri = l.rstrip()
			if not uri[:1] == '#' and not uri == '':
				uri_OK = url_check(uri)					
				if uri_OK:
					printer(' > Stream [OK]: {0}'.format(uri))
					#arSourceAvailable[5]=1
					#Sources.setAvailable('name','stream',True)
					#break
					return True
				else:
					printer(' > Stream [FAIL]: {0}'.format(uri))
					return False

def stream_play():
	#global Sources
	printer('Play (MPD)',mytag)

	### To be handled by Sources ###
	#if bInit == 0:
	#	print(' ....  Checking if source is still good')
	#	stream_check()

	### To be handled by Sources ###
	"""
	if not Sources.getAvailable('name','stream')
		print(' ....  No, aborting playback, trying next source.') #TODO red color
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
		myprint('MPD: Failed to connect to MPD server',mytag)
		return False

	printer('MPD: Emptying playlist',mytag)
	#todo: how about cropping, populating, and removing the first? item .. for faster continuity???
	
	mpc.stop()
	mpc.clear()
	mpc.close()	
	
	#call(["mpc", "-q", "stop"])
	#call(["mpc", "-q", "clear"])

	printer(' .... Populating playlist')
	mpc_populate_playlist('stream')
	
	printer(' .... Checking if playlist is populated')
	playlistCount = mpc_playlist_is_populated()
	if playlistCount == "0":
		printer(' .... . Nothing in the playlist, aborting...')
		pa_sfx(LL_ERROR)
		#arSourceAvailable[5] = 0
		#Sources.setAvailable('name','stream',False)
		#source_next()
		#Sources.sourceNext()
		#source_play()
		return False
		
	else:
		printer(' .... . Found {0:s} tracks'.format(playlistCount))
		
	# continue where left
	playslist_pos = mpc_lkp('stream')
	
	printer(' .... Starting playback')
	call(["mpc", "-q" , "play", str(playslist_pos['pos'])])

	# double check if source is up-to-date
	# todo
	
	return True
		
def stream_stop():
	print('Stopping source: stream. Saving playlist position and clearing playlist.')
	
	# save position and current file name for this drive
	mpc_save_pos_for_label( 'stream' )
	
	# stop playback
	mpc_stop()
	#mpc $params_mpc -q stop
	#mpc $params_mpc -q clear	
	return True
