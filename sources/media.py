#********************************************************************************
#
# Source: Removable Media
#
# Plays everything mounted on /media, except in PIHU_*-folders
#

import os
import subprocess

from hu_utils import *
from hu_mpd import *

# Logging
sourceName='media'

class sourceClass():

	mpc = None

	# Wrapper for "myprint"
	def __printer( self, message, level=LL_INFO, continuation=False, tag=sourceName ):
		if continuation:
			myprint( message, level, '.'+tag )
		else:
			myprint( message, level, tag )

	def __init__( self ):
		self.__printer('Source Class Init', level=LL_DEBUG)
		self.mpc = mpdController()
		
	def __del__( self ):
		print('Source Class Deleted {0}'.format(sourceName))

	def remove_subsource( self ):
		print('REMOVE SUBSOURCE: TODO')
		
	def __media_add_subsource( self, dir, label, uuid, device, sourceCtrl ):
		# get index (name is unique)
		ix = sourceCtrl.getIndex('name','media')
		
		# construct the subsource
		subsource = {}
		subsource['name'] = 'media'
		subsource['displayname'] = 'media: ' + dir
		subsource['order'] = 0		# no ordering
		subsource['mountpoint'] = dir
		subsource['mpd_dir'] = dir[7:]		# TODO -- ASSUMING /media
		subsource['label'] = label
		subsource['uuid'] = uuid
		subsource['device'] = device

		sourceCtrl.addSub(ix, subsource)
	
	def init( self, sourceCtrl ):
		self.__printer('Initializing...', level=15)

		# Returns a list of everything mounted on /media, but does not check if it has music.
		# Returned is 2-dimension list
		def media_getAll():

			try:
				self.__printer('Check if anything is mounted on /media...')
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
			lst_mountpoints = [[x for x in ss.split(' ')] for ss in grepOut.split('\n')]

			# remove local data (locmus) and smb mounts:
			# TODO: this shouldn't be hardcoded:
			lst_mountpoints[:] = [tup for tup in lst_mountpoints if (not tup[1] == '/media/PIHU_DATA' and not tup[0].startswith('//'))]

			if not lst_mountpoints:
				self.__printer(' > No removable media found')
			else:
				self.__printer(' > Found {0} removable media'.format(len(lst_mountpoints)))
			
			return lst_mountpoints
		
		# do a general media_check to find any mounted drives
		#media_check( label=None )
		
		# add all locations as configured
		arMedia = media_getAll()
		for dev_mp in arMedia:
			
			mountpoint = dev_mp[1]
			sUsbLabel = os.path.basename(dev_mp[1]).rstrip('\n')
			#TODO: try-except for subprocess?
			uuid = subprocess.check_output("blkid "+dev_mp[0]+" -s PARTUUID -o value", shell=True).rstrip('\n')	
			self.__media_add_subsource( mountpoint
							           ,sUsbLabel
							           ,uuid
									   ,dev_mp[0]
							           ,sourceCtrl)

		return True

	# media_check() returns True or False, depending on availability..
	#  media_check without parameters returns if anything (meaningful or not!) is mounted on /media
	#  media_check with a "label" parameter checks specific label on /media
	#def media_check( label=None ):
	def check( self, sourceCtrl, subSourceIx=None  ):
		self.__printer('Checking availability...', level=15)
		# QUESTION.... SHOULD THIS MEDIA_CHECK GO LOOKING FOR POSSIBLE NEW MOUNTS?????
		"""
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
		"""

		ix = sourceCtrl.getIndex('name','media')	# index
		locations = []								# list of tuples; index: 0 = mountpoint, 1 = mpd dir.
		foundStuff = 0								#
						
		if subSourceIx == None:
			subsources = sourceCtrl.getSubSources( ix )
			for subsource in subsources:
				locations.append( (subsource['mountpoint'], subsource['mpd_dir']) )
			ssIx = 0
		else:
			subsource = sourceCtrl.getSubSource( ix, subSourceIx )
			locations.append( (subsource['mountpoint'], subsource['mpd_dir']) )
			ssIx = subSourceIx
			
		# check mountpoint(s)
		for location in locations:
			# get mountpoint and mpd dir
			mountpoint = location[0]
			mpd_dir = location[1]
			self.__printer('Media folder: {0}'.format(mountpoint))
			if not os.listdir(mountpoint):
				self.__printer(" > Removable music directory is empty.",LL_WARNING,True)
			else:
				self.__printer(" > Removable music directory present and has files.",LL_INFO,True)
				if not self.mpc.dbCheckDirectory( mpd_dir ):
					self.__printer(" > Running MPD update for this directory.. ALERT! LONG BLOCKING OPERATION AHEAD...")
					self.mpc.update( mpd_dir, True )	#TODO: don't wait! set available on return of update..
					if not self.mpc.dbCheckDirectory( mpd_dir ):
						self.__printer(" > Nothing to play marking unavailable...")
					else:
						self.__printer(" > Music found after updating")
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
			
		"""
		
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
		
	def play( self, sourceCtrl, resume={} ):
		self.__printer('Start playing (MPD)')
		
		#
		# variables
		#
		arIx = sourceCtrl.getIndexCurrent()
		subsource = sourceCtrl.getSubSource( arIx[0], arIx[1] )
		sLocalMusicMPD = subsource['mpd_dir']
		sUsbLabel = subsource['label']
		print sLocalMusicMPD
		print sUsbLabel
		
		#debug/test:
		sUsbLabel = "SJOERD"
		sLocalMusicMPD = "SJOERD"
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

		#
		# load playlist
		#

		# populate playlist
		self.mpc.playlistClear()
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???
	#	sUsbLabel = os.path.basename(arMediaWithMusic[dSettings['mediasource']])
		self.mpc.playlistPop('media',sLocalMusicMPD)

		# check if succesful...
		playlistCount = self.mpc.playlistIsPop()
		if playlistCount == "0":
			self.__printer(' > Nothing in the playlist, trying to update database...')
			
			# update and try again...
			self.mpc.update( sLocalMusicMPD, True )
			self.mpc.playlistPop('locmus',sLocalMusicMPD)
			
			# check if succesful...
			playlistCount = self.mpc.mpc_playlist_is_populated()
			if playlistCount == "0":
				# Failed. Returning false will cause caller to try next source
				self.__printer(' > Nothing in the playlist, giving up. Marking source unavailable.')
				sourceCtrl.setAvailableIx( ix, False, subSourceIx )
				pa_sfx(LL_ERROR)
				return False
			else:
				self.__printer(' > Found {0:s} tracks'.format(playlistCount))
		else:
			self.__printer(' > Found {0:s} tracks'.format(playlistCount))

		#
		# continue where left
		#
		if resume:
			playslist_pos = self.mpc.lastKnownPos2( resume['file'], resume['time'] )
			#playslist_pos = self.mpc.lastKnownPos( sUsbLabel )
		else:
			playslist_pos = {'pos': 1, 'time': 0}
		
		self.__printer(' > Starting playback')
		#mpc.playStart( str(playslist_pos['pos']), playslist_pos['time'] )
		call(["mpc", "-q" , "stop"])
		call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
		if playslist_pos['time'] > 0:
			self.__printer(' > Seeking to {0} sec.'.format(playslist_pos['time']))
			call(["mpc", "-q" , "seek", str(playslist_pos['time'])])

		# Load playlist directories, to enable folder up/down browsing.
		#mpc_get_PlaylistDirs()
		# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
	#		mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc_get_PlaylistDirs)
	#		mpc_get_PlaylistDirs_thread.start()

		return True

	def stop( self, sourceCtrl ):
		self.__printer('Stop')
		return True
		
	def next( self ):
		self.__printer('Next track')
		self.mpc.nextTrack()
		return True
		
	def prev( self ):
		self.__printer('Prev track')
		self.mpc.prevTrack()
		return True

