
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
	return True
 
def media_stop():
	return True