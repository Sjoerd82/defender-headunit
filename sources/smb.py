#********************************************************************************
#
# Source: Samba Network Shares
#
# Plays everything mounted on /media/PIHU_SMB
#

import os
import subprocess

from hu_utils import *
from hu_mpd import *

# Logging
sourceName='smb'

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

	# Returns a list of everything mounted on /media, but does not check if it has music.
	# Returned is 2-dimension list
	def __smb_getAll( self ):

		try:
			self.__printer('Check if anything is mounted on /media/PIHU_SMB...')
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
	
	# add a smb source
	def __smb_add( self, dir, path, sourceCtrl ):

		# get index (name is unique)
		ix = sourceCtrl.getIndex('name','smb')
		
		# construct the subsource
		subsource = {}
		subsource['name'] = 'smb'
		subsource['displayname'] = 'smb: ' + dir
		subsource['order'] = 0		# no ordering
		subsource['mountpoint'] = dir
		subsource['mpd_dir'] = dir[7:]		# TODO -- ASSUMING /media/PIHU_SMB
		subsource['path'] = path

		sourceCtrl.addSub(ix, subsource)

	def init( self, sourceCtrl ):
		self.__printer('Initializing...', level=15)
		# do a general media_check to find any mounted drives
		#media_check( label=None )
		
		# add all locations as configured
		arSmb = self.__smb_getAll()
		for dev_mp in arSmb:
			if dev_mp[0].startswith('//'):
				smbAddr = dev_mp[0]
				mountpoint = dev_mp[1]
				self.__smb_add( mountpoint
						       ,smbAddr
						       ,sourceCtrl)

		return True

	def check( self, sourceCtrl, subSourceIx=None  ):
		self.__printer('Checking availability...', level=15)
		
		ix = sourceCtrl.getIndex('name','smb')
		mountpoints = []
		locations = []
		foundStuff = 0

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
			
			self.__printer('SMB folder: {0}'.format(mountpoint))
			if not os.listdir(mountpoint):
				self.__printer(" > SMB directory is empty.",LL_WARNING,True)
			else:
				self.__printer(" > SMB directory present and has files.",LL_INFO,True)
				
				if not self.mpc.dbCheckDirectory( mpd_dir ):
					self.__printer(" > Running MPD update for this directory.. ALERT! LONG BLOCKING OPERATION AHEAD...")
					self.mpc.update( sLocalMusicMPD )
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

		if foundStuff > 0:
			return True
		else:
			return False

		
	def play( self, sourceCtrl, resume={} ):
		self.__printer('Start playing')
		#
		# variables
		#
		
		arIx = sourceCtrl.getIndexCurrent()
		subsource = sourceCtrl.getSubSource( arIx[0], arIx[1] )
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
		else:
			playslist_pos = {'pos': 1, 'time': 0}
		
		self.__printer(' > Starting playback')
		#mpc.playStart( str(playslist_pos['pos']), playslist_pos['time'] )
		call(["mpc", "-q" , "stop"])
		call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
		if playslist_pos['time'] > 0:
			self.__printer(' ...  Seeking to {0} sec.'.format(playslist_pos['time']))
			call(["mpc", "-q" , "seek", str(playslist_pos['time'])])


		# double check if source is up-to-date
		
		# Load playlist directories, to enable folder up/down browsing.
		#mpc_get_PlaylistDirs()
		# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
	#	mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc_get_PlaylistDirs)
	#	mpc_get_PlaylistDirs_thread.start()

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
		