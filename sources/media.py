
import os
import subprocess

from hu_utils import *
from hu_mpd import *

# Logging
sourceName='media'

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

# add a media source
def media_add( dir, label, uuid, sourceCtrl ):

	# get index (name is unique)
	ix = sourceCtrl.getIndex('name','media')
	
	# construct the subsource
	subsource = {}
	subsource['displayname'] = 'media: ' + dir
	subsource['order'] = 0		# no ordering
	subsource['mountpoint'] = dir
	subsource['label'] = label
	subsource['uuid'] = uuid

	sourceCtrl.addSub(ix, subsource)

# Stuff that needs to run once
def media_init( sourceCtrl ):
	printer('Initializing....')

	# do a general media_check to find any mounted drives
	#media_check( label=None )
	
	# add all locations as configured
	arMedia = media_getAll()
	for dev_mp in arMedia:
		mountpoint = dev_mp[1]
		sUsbLabel = os.path.basename(dev_mp[1]).rstrip('\n')
		uuid = dev_mp[0]  #use blkid  on this
		media_add(mountpoint, sUsbLabel, uuid, sourceCtrl)

	return True

# Returns a list of everything mounted on /media, but does not check if it has music.
# Returned is 2-dimension list
def media_getAll():

	try:
		print('Check if anything is mounted on /media...')
		# do a -f1 for devices, -f3 for mountpoints
		grepOut = subprocess.check_output(
			"mount | grep /media | cut -d' ' -f1,3",
			shell=True,
			stderr=subprocess.STDOUT,
		)
	except subprocess.CalledProcessError as err:
		print('ERROR:', err)
		pa_sfx('error')
		return None
	
	grepOut = grepOut.rstrip('\n')
	return [[x for x in ss.split(' ')] for ss in grepOut.split('\n')]
	
	
# media_check() returns True or False, depending on availability..
#  media_check without parameters returns if anything (meaningful or not!) is mounted on /media
#  media_check with a "label" parameter checks specific label on /media
def media_check( label=None ):
	
	printer('CHECK availability...',tag=sourceName)
	
	try:
		print(' .....  Check if anything is mounted on /media...')
		# do a -f1 for devices, -f3 for mountpoints
		grepOut = subprocess.check_output(
			"mount | grep /media | cut -d' ' -f3",
			shell=True,
			stderr=subprocess.STDOUT,
		)
	except subprocess.CalledProcessError as err:
		print('ERROR:', err)
		pa_sfx('error')
		return False
	
	arMedia = grepOut.split()

	# Return True/False for general check (when label is None)
	if label == None:
		if len(arMedia) > 0:
			print(' .....  /media has mounted filesystems.')
			return True
		else:
			print(' ..... nothing mounted on /media.')
			return False

	# Check if requested label is mounted
	label_found = False
	for mountpoint in arMedia:
		sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
		if sUsbLabel == label:
			label_found = True
			break

	# Requested label is not mounted
	if not label_found:
		print(' .....  label {0} is not mounted.'.format(label))
		return False
	
	print(' .....  Continuing to crosscheck with mpd database for music...')
	
	taskcmd = "mpc listall "+sUsbLabel+" | wc -l"
	task = subprocess.Popen(taskcmd, shell=True, stdout=subprocess.PIPE)
	mpcOut = task.stdout.read()
	assert task.wait() == 0
	
	if mpcOut.rstrip('\n') == '0':
		print(' ..... . {0}: nothing in the database for this source.'.format(sUsbLabel))
		return False
	else:
		print(' ..... . {0}: found {1:s} tracks'.format(sUsbLabel,mpcOut.rstrip('\n')))
		return True

	"""
	# playlist loading is handled by scripts that trigger on mount/removing of media
	# mpd database is updated on mount by same script.
	# So, let's check if there's anything in the database for this source:
	
	if len(arMedia) > 0:
		print(' .....  /media has mounted filesystems: ')
		for mountpoint in arMedia:
			print(' ... . {0}'.format(mountpoint))
		
		print(' .....  Continuing to crosscheck with mpd database for music...')
		for mountpoint in arMedia:
			sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
			
			if sUsbLabel == sLocalMusicMPD:
				print(' ..... . {0}: ignoring local music directory'.format(sLocalMusicMPD))
			if sUsbLabel == sSambaMusic:
				print(' ..... . {0}: ignoring samba music directory'.format(sSambaMusicMPD))
			else:		
				taskcmd = "mpc listall "+sUsbLabel+" | wc -l"
				task = subprocess.Popen(taskcmd, shell=True, stdout=subprocess.PIPE)
				mpcOut = task.stdout.read()
				assert task.wait() == 0
				
				if mpcOut.rstrip('\n') == '0':
					print(' ..... . {0}: nothing in the database for this source.'.format(sUsbLabel))
				else:
					print(' ..... . {0}: found {1:s} tracks'.format(sUsbLabel,mpcOut.rstrip('\n')))
					
					# Adding source
					Sources.addSource({'name': 'media',
									   'displayname': 'Removable Media',
									   'order': 1,
									   'available': True,
									   'type': 'mpd',
									   'depNetwork': False,
									   'controls': ctrlsMedia,
									   'mountpoint': mountpoint,
									   'label': sUsbLabel,
									   'uuid': None }
					)
					#REMOVE:
					arMediaWithMusic.append(mountpoint)
					#default to found media, if not set yet
					
					# Determine the active mediasource
					if prefered_label == sUsbLabel:
						#pleister
						dSettings['mediasource'] = len(arMediaWithMusic)-1
					elif dSettings['mediasource'] == -1:
						dSettings['mediasource'] = 0



		# if nothing useful found, then mark source as unavailable
		#if len(arMediaWithMusic) == 0:
		#	arSourceAvailable[1]=0

	else:
		print(' ..... nothing mounted on /media.')

	return False
	"""

def media_play():
	printer('Play (MPD)',tag=sourceName)

	#debug/test:
	sUsbLabel = "SJOERD"
	
	"""
	global dSettings
	global arMediaWithMusic
	global Sources

	if not mySources.getAvailable('name','media'):
		print('Aborting playback, trying next source.')
		pa_sfx('error')
		#source_next()
		Sources.sourceNext()
		source_play()
		
	else:
	"""
	print(' ... Emptying playlist')
	call(["mpc", "-q", "stop"])
	call(["mpc", "-q", "clear"])
	#todo: how about cropping, populating, and removing the first? item .. for faster continuity???

#	sUsbLabel = os.path.basename(arMediaWithMusic[dSettings['mediasource']])
#	dSettings['medialabel'] = sUsbLabel

	print(' ... Populating playlist, media: {0}'.format(sUsbLabel))
	mpc_populate_playlist(sUsbLabel)

	print(' ... Checking if playlist is populated')
	task = subprocess.Popen("mpc playlist | wc -l", shell=True, stdout=subprocess.PIPE)
	mpcOut = task.stdout.read()
	assert task.wait() == 0
	
	if mpcOut.rstrip('\n') == "0":
		print(' ... . Nothing in the playlist, marking source unavailable.')
		pa_sfx('error')
		Sources.setAvailable('label',sUsbLabel,False)
		#source_next()
		Sources.sourceNext()
		source_play()
	else:
		print(' ... . Found {0:s} tracks'.format(mpcOut.rstrip('\n')))

		# continue where left
		playslist_pos = mpc_lkp(sUsbLabel)

		print(' ...  Starting playback')
		call(["mpc", "-q" , "stop"])
		call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
		if playslist_pos['time'] > 0:
			print(' ...  Seeking to {0} sec.'.format(playslist_pos['time']))
			call(["mpc", "-q" , "seek", str(playslist_pos['time'])])

		# Load playlist directories, to enable folder up/down browsing.
		#mpc_get_PlaylistDirs()
		# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
#		mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc_get_PlaylistDirs)
#		mpc_get_PlaylistDirs_thread.start()

	return True
 
def media_stop():
	return True