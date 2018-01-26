
import os
import subprocess

from hu_utils import *
from hu_mpd import *

# Logging
mytag='smb'
sourceName='smb'


# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

# add a smb source
def smb_add( dir, path, sourceCtrl ):

	# get index (name is unique)
	ix = sourceCtrl.getIndex('name','smb')
	
	# construct the subsource
	subsource = {}
	subsource['displayname'] = 'smb: ' + dir
	subsource['order'] = 0		# no ordering
	subsource['mountpoint'] = dir
	subsource['mpd_dir'] = dir[16:]		# TODO -- ASSUMING /media/PIHU_SMB
	subsource['path'] = path

	sourceCtrl.addSub(ix, subsource)

	
#nothing to init
def smb_init( sourceCtrl ):
	printer('Initializing....')

	# do a general media_check to find any mounted drives
	#media_check( label=None )
	
	# add all locations as configured
	arSmb = smb_getAll()
	for dev_mp in arSmb:
		if dev_mp[0].startswith('//'):
			smbAddr = dev_mp[0]
			mountpoint = dev_mp[1]
			smb_add( mountpoint
					,smbAddr
				    ,sourceCtrl)

	return True

# Returns a list of everything mounted on /media, but does not check if it has music.
# Returned is 2-dimension list
def smb_getAll():

	try:
		printer('Check if anything is mounted on /media/PIHU_SMB...')
		# do a -f1 for devices, -f3 for mountpoints
		grepOut = subprocess.check_output(
			"mount | grep /media/PIHU_SMB | cut -d' ' -f1,3",
			shell=True,
			stderr=subprocess.STDOUT,
		)
	except subprocess.CalledProcessError as err:
		print('ERROR:', err)
		pa_sfx('error')
		return None
	
	grepOut = grepOut.rstrip('\n')
	return [[x for x in ss.split(' ')] for ss in grepOut.split('\n')]


def smb_check( sourceCtrl, subSourceIx=None  ):
	printer('CHECKING availability... TODO!')

	#Check if wlan is up
	#TODO
	
	# ASSUME FOR NOW, THAT THE CONNECTIONS ARE CREATED BY THE SYSTEM, ON /media/PIHU_SMB,
	# SO WE ONLY NEED TO CHECK /media/PIHU_SMB...
	
	
	
	#See if we have smb location(s)
	#TODO

	#Check if any of those locations could be on our current network
	#TODO
	
	#Check if at least one stream is good
	#TODO

	#OVERRIDE
	#printer(' > Not implemented yet, presenting source as available ',level=LL_CRITICAL)
	#arSourceAvailable[6]=1
	#Sources.setAvailable('name','smb', True)
	return True

def smb_play( sourceCtrl, subSourceIx=None ):
	printer('Play (MPD)')

	#
	# variables
	#
	
	mpc = mpdController()
	sLocalMusicMPD = "PIHU_SMB/music"

	#
	# load playlist
	#

	# populate playlist
	mpc.playlistClear()
	mpc.playlistPop('smb',sLocalMusicMPD)
	
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
	
	playslist_pos = mpc.lastKnownPos( sUsbLabel )
	
	printer(' > Starting playback')
	#mpc.playStart( str(playslist_pos['pos']), playslist_pos['time'] )
	call(["mpc", "-q" , "stop"])
	call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
	if playslist_pos['time'] > 0:
		printer(' > Seeking to {0} sec.'.format(playslist_pos['time']))
		call(["mpc", "-q" , "seek", str(playslist_pos['time'])])

	# double check if source is up-to-date
	
	# Load playlist directories, to enable folder up/down browsing.
	#mpc_get_PlaylistDirs()
	# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
#	mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc_get_PlaylistDirs)
#	mpc_get_PlaylistDirs_thread.start()

def smb_stop():
	printer('stop')
	return True
