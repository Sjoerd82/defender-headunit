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

def locmus_add( dir, label, sourceCtrl ):

	# get index (name is unique)
	ix = sourceCtrl.getIndex('name','locmus')

	# construct the subsource
	subsource = {}
	subsource['displayname'] = 'local: ' + dir
	subsource['order'] = 0		# no ordering
	subsource['mountpoint'] = dir
	subsource['label'] = label
	subsource['uuid'] = None	#TODO (but not relevant for local sources?)

	sourceCtrl.addSub( ix, subsource )
	
# Stuff that needs to run once
#def locmus_init( sourceCtrl ):
def locmus_init( sourceCtrl ):
	printer('Initializing....')
	
	# get source configuration from main configuration
	locmusConfig = getSourceConfig('locmus')
	
	# add all locations as configured
	for location in locmusConfig:
		locmus_add(location['musicdir'],location['musicdir_mpd'], sourceCtrl)

	return True

# Source Check: Return True/False (available/not available)
# Optionally, provide list of mountpoint(s) to check
def locmus_check( sourceCtrl, mountpoints=None ):
	
	# TODO
	if mountpoints == None:
		return False
	
	if len(mountpoints) > 1:
		printer('CHECKING availability...')	
	else:
		printer('CHECKING availability of {0}...'.format(mountpoints[0]))

#	sourceConfig = getSourceConfig(sourceName)
#	for location in sourceConfig:
	for location in mountpoints:
		printer('Local folder: {0}'.format(location))
		try:
			if not os.listdir(location):
				printer(" > Local music directory is empty.",LL_WARNING,True)
				return False
			else:
				printer(" > Local music directory present and has files.",LL_INFO,True)
				return True
		except:
			printer(" > [FAIL] Error checking for local music directory {0}".format(location),LL_ERROR,True)
			return False

		
# Source Play: Return True/False
def locmus_play():
	global sLocalMusicMPD
	#global arSourceAvailable
	global Sources
	print('[LOCMUS] Play (MPD)')

	### Is there a good reason for this? ###
	#if bInit == 0:
	#	print(' ... Checking if source is still good')
	#	locmus_check()
	
	### This check will be done by Sources ###
	#if arSourceAvailable[2] == 0:
	"""
	if not Sources.getAvailable('name','locmus')
		print(' ......  Aborting playback, trying next source.') #TODO red color
		#source_next()
		Sources.sourceNext()
		source_play()
		#TODO: error sound
		
	else:
	"""
	#mpc = MPDClient()
	mpc = mpdController()
	mpc.playlistClear()
	
	# MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..
	printer(' ...... Populating playlist')
	mpc.mpc_populate_playlist(sLocalMusicMPD)

	printer(' ...... Checking if playlist is populated')
	playlistCount = mpc.mpc_playlist_is_populated()
	if playlistCount == "0":
		printer(' ...... . Nothing in the playlist, trying to update database...')
		mpc.mpc_update( sLocalMusicMPD, True )
		mpc.mpc_populate_playlist(sLocalMusicMPD)
		playlistCount = mpc.mpc_playlist_is_populated()
		if playlistCount == "0":
			printer(' ...... . Nothing in the playlist, giving up. Marking source unavailable.')
			#Sources.setAvailable('name','locmus',False)
			#Sources.sourceNext()
			#source_play()
			pa_sfx(LL_ERROR)
			return False
		else:
			printer(' ...... . Found {0:s} tracks'.format(playlistCount))
	else:
		printer(' ...... . Found {0:s} tracks'.format(playlistCount))

	# continue where left
	playslist_pos = mpc.mpc_lkp('locmus')
	
	printer(' ...  Starting playback')
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
	mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc.mpc_get_PlaylistDirs)
	mpc_get_PlaylistDirs_thread.start()
	return True

def locmus_stop():
	printer('[LOCMUS] Stopping source: locmus. Saving playlist position and clearing playlist.')
	mpc = mpdwrapper()

	# save playlist position (file name + position)
	mpc_save_pos_for_label( 'locmus' )
	
	# stop playback
	mpc.mpc_stop()
	return True
