# MISC (myprint, colorize)
from hu_utils import *
from hu_settings import getSourceConfig

# LOGGING
sourceName = 'locmus'


# MPD
from hu_mpd import *

# SETTINGS
#LOCAL MUSIC (now also in locmus.py)
#sLocalMusic="/media/PIHU_DATA"		# local music directory
#sLocalMusicMPD="PIHU_DATA"			# directory from a MPD pov. #TODO: derive from sLocalMusic
sSambaMusic="/media/PIHU_SMB/music"
sSambaMusicMPD="PIHU_SMB"			# directory from a MPD pov.

"""
class Source():

	def init():
		return True

	def check():
		return True
	
	def play():
		return True
		
	def stop():
		return True
"""

# Wrapper for "myprint"
#  instead of this function you may use the 'headunit' logger, and use logger.info() 
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

def locmus_add( label, dir, mpd_dir, sourceCtrl ):

	#TODO:
	mpd_musicdir = '/media'

	# get index (name is unique)
	ix = sourceCtrl.getIndex('name','locmus')

	# construct the subsource
	subsource = {}
	subsource['displayname'] = 'local: ' + dir
	subsource['order'] = 0			# no ordering
	subsource['mountpoint'] = dir
	subsource['mpd_dir'] = mpd_dir
	subsource['label'] = label
	#subsource['uuid'] = None		# not relevant for local sources

	sourceCtrl.addSub( ix, subsource )
	
# Stuff that needs to run once
#def locmus_init( sourceCtrl ):
def locmus_init( sourceCtrl ):
	printer('Initializing....')
	
	# get source configuration from main configuration
	locmusConfig = getSourceConfig('locmus')
	
	# add all locations as configured
	for location in locmusConfig:
		locmus_add( location['label']
		           ,location['musicdir']
				   ,location['musicdir_mpd']
				   ,sourceCtrl )

	return True

# Source Check: Return True/False (available/not available)
# Optionally, provide list of mountpoint(s) to check
#def locmus_check( sourceCtrl, mountpoint=None ):
def locmus_check( sourceCtrl, subSourceIx=None ):
	printer('CHECKING availability...')
	
	ix = sourceCtrl.getIndex('name','locmus')
	mountpoints = []
	mpc = mpdController()
	foundStuff = 0
					
	if subSourceIx == None:
		subsources = sourceCtrl.getSubSources( ix )
		for subsource in subsources:
			mountpoints.append(subsource['mountpoint'])
		ssIx = 0
	else:
		subsource = sourceCtrl.getSubSource( ix, subSourceIx )
		mountpoints.append(subsource['mountpoint'])
		ssIx = subSourceIx

	# local dir, relative to MPD
	sLocalMusicMPD = subsource['mpd_dir']

	# check mountpoint(s)
	for location in mountpoints:
		printer('Local folder: {0}'.format(location))
		if not os.listdir(location):
			printer(" > Local music directory is empty.",LL_WARNING,True)
		else:
			printer(" > Local music directory present and has files.",LL_INFO,True)
			
			if not mpc.dbCheckDirectory( sLocalMusicMPD ):
				printer(" > Running MPD update for this directory.. ALERT! LONG BLOCKING OPERATION AHEAD...")
				mpc.update( sLocalMusicMPD )
				if not mpc.dbCheckDirectory( sLocalMusicMPD ):
					printer(" > Nothing to play marking unavailable...")
				else:
					printer(" > Music found after updating")
					sourceCtrl.setAvailableIx( ix, True, ssIx )
					foundStuff += 1
			else:
				sourceCtrl.setAvailableIx( ix, True, ssIx )
				foundStuff += 1
		ssIx+=1
	
	if foundStuff > 0:
		return True
	else:
		return False

		
# Source Play: Return True/False
def locmus_play( sourceCtrl, subSourceIx=None ):
	printer('Play (MPD)')

	#
	# variables
	#
	
	mpc = mpdController()

	# get directory to play, directory is relative to MPD music dir.
	ix = sourceCtrl.getIndex('name','locmus')
	subsource = sourceCtrl.getSubSource( ix, subSourceIx )
	sLocalMusicMPD = subsource['mpd_dir']
	sLabel = subsource['label']
	
	
	#
	# load playlist
	#
	
	# NOT ANYMORE - OR TODO: MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..

	# populate playlist
	mpc.playlistClear()
	mpc.playlistPop('locmus',sLocalMusicMPD)

	# check if succesful...
	playlistCount = mpc.playlistIsPop()
	if playlistCount == "0":
		printer(' > Nothing in the playlist, trying to update database...')
		
		# update and try again...
		mpc.update( sLocalMusicMPD, True )
		mpc.playlistPop('locmus',sLocalMusicMPD)
		
		# check if succesful...
		playlistCount = mpc.mpc_playlist_is_populated()
		if playlistCount == "0":
			# Failed. Returning false will cause caller to try next source
			printer(' > Nothing in the playlist, giving up. Marking source unavailable.')
			sourceCtrl.setAvailableIx( ix, False, subSourceIx )
			pa_sfx(LL_ERROR)
			return False
		else:
			printer(' > Found {0:s} tracks'.format(playlistCount))
	else:
		printer(' > Found {0:s} tracks'.format(playlistCount))

	#
	# continue where left
	#
	
	playslist_pos = mpc.lastKnownPos( sLabel )
	
	printer(' > Starting playback')
	#mpc.playStart( str(playslist_pos['pos']), playslist_pos['time'] )
	call(["mpc", "-q" , "stop"])
	call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
	if playslist_pos['time'] > 0:
		printer(' ...  Seeking to {0} sec.'.format(playslist_pos['time']))
		call(["mpc", "-q" , "seek", str(playslist_pos['time'])])

	# double check if source is up-to-date
	
	# Load playlist directories, to enable folder up/down browsing.
	#mpc_get_PlaylistDirs()
	# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
#	mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc.mpc_get_PlaylistDirs)
#	mpc_get_PlaylistDirs_thread.start()
	return True

def locmus_stop():
	printer('[LOCMUS] Stopping source: locmus. Saving playlist position and clearing playlist.')
	mpc = mpdwrapper()

	# save playlist position (file name + position)
	mpc_save_pos_for_label( 'locmus' )
	
	# stop playback
	mpc.mpc_stop()
	return True
