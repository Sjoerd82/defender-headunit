
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

def stream_play( sourceCtrl, subSourceIx=None ):
	printer('Play (MPD)',mytag)

	#
	# variables
	#
	
	mpc = mpdController()

	
	#
	# load playlist
	#
	
	# NOT ANYMORE - OR TODO: MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..

	# populate playlist
	mpc.playlistClear()
	mpc.playlistPop('stream',None)
	
	# check if succesful...
	playlistCount = mpc.playlistIsPop()
	if playlistCount == "0":
		printer(' > Nothing in the playlist, aborting...')
		pa_sfx(LL_ERROR)
		return False	
	else:
		printer(' .... . Found {0:s} items'.format(playlistCount))
		
	#
	# continue where left
	#
	
	playslist_pos = mpc.lastKnownPos( sLabel )
	
	printer(' > Starting playback')
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
