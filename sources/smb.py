#********************************************************************************
#
# Source: Samba Network Shares
#
# Plays everything mounted on /media/PIHU_SMB
#

import os
import subprocess

from modules.hu_utils import *
from modules.hu_mpd import *

# Logging
sourceName='smb'
LOG_TAG = 'SMB'
LOGGER_NAME = 'smb'


class sourceClass():

	mpc = None

	# output wrapper
	def __printer( self, message, level=LL_INFO, tag=LOG_TAG):
		self.logger.log(level, message, extra={'tag': tag})

	def __init__( self, logger ):
		self.logger = logger
		self.__printer('Source Class Init', level=LL_DEBUG)
		self.mpc = mpdController()
		
	def __del__( self ):
		print('Source Class Deleted {0}'.format(sourceName))

	# Returns a list of everything mounted on /media, but does not check if it has music.
	# Returned is 2-dimension list
	def __smb_getAll( self ):

		lst_mountpoints = get_mounts( fs='cifs' )

		if not lst_mountpoints:
			self.__printer(' > No SMB network shares found')
		else:
			# filter out everything that's not mounted on /media/PIHU_SMB
			# TODO: remove hardcoded path
			for i, mp in enumerate(lst_mountpoints):
				if not mp['mountpoint'].startswith('/media/PIHU_SMB'):
					del lst_mountpoints[i]
			
			# check if anything left
			if not lst_mountpoints:
				self.__printer(' > No SMB network shares found on /media/PIHU_SMB')
			else:				
				self.__printer(' > Found {0} share(s)'.format(len(lst_mountpoints)))
		
		return lst_mountpoints

	
	# add a smb source
	def __smb_add( self, dir, path, sourceCtrl ):

		# get index (name is unique)
		ix = sourceCtrl.index('name','smb')
		
		# construct the subsource
		subsource = {}
		subsource['name'] = 'smb'
		subsource['displayname'] = 'smb: ' + dir
		subsource['order'] = 0		# no ordering
		subsource['mountpoint'] = dir
		subsource['mpd_dir'] = dir[7:]		# TODO -- ASSUMING /media/PIHU_SMB
		subsource['path'] = path

		sourceCtrl.add_sub(ix, subsource)

	def init( self, sourceCtrl ):
		self.__printer('Initializing...', level=15)
		# do a general media_check to find any mounted drives
		#media_check( label=None )
			
		# add all locations as configured
		arSmb = self.__smb_getAll()
		for mount in arSmb:
			if mount['spec'].startswith('//'):
				smbAddr = mount['spec']
				mountpoint = mount['mountpoint']
				self.__smb_add( mountpoint
						       ,smbAddr
						       ,sourceCtrl)

		return True

	def check( self, sourceCtrl, subSourceIx=None  ):
		self.__printer('Checking availability...')
		
		ix = sourceCtrl.index('name','smb')
		locations = []							# list of tuples; index: 0 = mountpoint, 1 = mpd dir, 2 = availability.
		subsource_availability_changes = []		# list of changes

		if subSourceIx == None:
			subsources = sourceCtrl.subsource_all( ix )
			for subsource in subsources:
				locations.append( (subsource['mountpoint'], subsource['mpd_dir'], subsource['available']) )
			ssIx = 0
		else:
			subsource = sourceCtrl.subsource( ix, subSourceIx )
			locations.append( (subsource['mountpoint'], subsource['mpd_dir'], subsource['available']) )
			ssIx = subSourceIx

		# check mountpoint(s)
		for location in locations:
		
			# get mountpoint and mpd dir
			mountpoint = location[0]
			mpd_dir = location[1]
			original_availability = location[2]
			new_availability = None

			self.__printer('SMB folder: {0}'.format(mountpoint))
			if not os.listdir(mountpoint):
				self.__printer(" > SMB directory is empty.",LL_WARNING,True)
				new_availability = False
			else:
				self.__printer(" > SMB directory present and has files.",LL_INFO,True)
				
				if not self.mpc.dbCheckDirectory( mpd_dir ):
					self.__printer(" > Running MPD update for this directory.. ALERT! LONG BLOCKING OPERATION AHEAD...")
					self.mpc.update( mpd_dir )
					if not self.mpc.dbCheckDirectory( mpd_dir ):
						self.__printer(" > Nothing to play marking unavailable...")
						new_availability = False
					else:
						self.__printer(" > Music found after updating")
						new_availability = True
				else:
					new_availability = True
					
			if new_availability is not None and new_availability != original_availability:
				sourceCtrl.set_available( ix, new_availability, ssIx )
				subsource_availability_changes.append({"index":ix,"subindex":ssIx,"available":new_availability})

			ssIx+=1
		
	
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

		return subsource_availability_changes

		
	def play( self, sourceCtrl, position=None, resume={} ):
		self.__printer('Start playing (MPD)')
		
		#
		# variables
		#
		arIx = sourceCtrl.index_current()
		subsource = sourceCtrl.subsource( arIx[0], arIx[1] )
		sLocalMusicMPD = subsource['mpd_dir']

		#
		# load playlist
		#

		# populate playlist
		self.mpc.playlistClear()
		self.mpc.playlistPop('smb',sLocalMusicMPD)
		
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
				sourceCtrl.set_available( ix, False, subSourceIx )
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
		else:
			playslist_pos = {'pos': 1, 'time': 0}
		
		self.__printer(' > Starting playback')
		#mpc.playStart( str(playslist_pos['pos']), playslist_pos['time'] )
		subprocess.call(["mpc", "-q" , "stop"])
		subprocess.call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
		if playslist_pos['time'] > 0:
			self.__printer(' ...  Seeking to {0} sec.'.format(playslist_pos['time']))
			subprocess.call(["mpc", "-q" , "seek", str(playslist_pos['time'])])


		# double check if source is up-to-date
		
		# Load playlist directories, to enable folder up/down browsing.
		#mpc_get_PlaylistDirs()
		# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
	#	mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc_get_PlaylistDirs)
	#	mpc_get_PlaylistDirs_thread.start()

		return True

	def stop( self ):
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
	def pause( self, mode ):
		self.__printer('Pause. Mode: {0}'.format(mode))
		#TODO IMPLEMENT
		return True

	def random( self, mode ):
		self.__printer('Random. Mode: {0}'.format(mode))
		#TODO IMPLEMENT
		return True

	def seekfwd( self ):
		self.__printer('Seek FFWD')
		#TODO IMPLEMENT
		return True

	def seekrev( self ):
		self.__printer('Seek FBWD')
		#TODO IMPLEMENT
		return True

	def update( self, location ):
		self.__printer('Update. Location: {0}'.format(location))
		#TODO IMPLEMENT
		return True

	def get_details():
		return False

	def get_state():
		return False

	def get_playlist():
		return False

	#def get_folders():

	def source_get_media_details():
		return False