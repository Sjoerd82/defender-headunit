#
# Source Plugin base class for MPD
# Venema, S.R.G.
# 2018-03-28
#
# This BASE CLASS contains shared code for MPD based source plugins.
#

import os
from modules.hu_utils import *
from modules.source_plugin import SourcePlugin
from modules.hu_mpd import MpdController

class MpdSourcePlugin(SourcePlugin):

	#def __init__(self, logger, name, displayname):
	def __init__(self):
		super(MpdSourcePlugin, self).__init__()
		#super(MpdSourcePlugin, self).__init__(logger, name, displayname)
		print('__INIT__ MPDSOURCECLASS')
		#self.printer('B Mpd Source Class Init', level=LL_DEBUG)
		self.mpdc = None

	def init(self, plugin_name, logger=None):
		super(MpdSourcePlugin, self).init()
		print("MPD MPD init()")
		print self.logger
		#self.mpdc = MpdController(self.logger)
	
	def check_mpd(self, locations, ix, ssIx):
	
		#locations = []							# list of tuples; index: 0 = mountpoint, 1 = mpd dir, 2 = availability.
		subsource_availability_changes = []		# list of changes

		# check mountpoint(s)
		for location in locations:
		
			mountpoint = location[0]
			mpd_dir = location[1]
			original_availability = location[2]
			new_availability = None

			self.printer('Checking local folder: {0}, current availability: {1}'.format(mountpoint,original_availability))
			
			# check if the dir exists:
			if not os.path.exists(mountpoint):
				self.printer(" > Local music directory does not exist.. creating {0}".format(mountpoint),LL_WARNING)
				os.makedirs(mountpoint)
				if not os.path.exists(mountpoint):
					self.printer(" > [FAIL] Could not create directory",LL_WARNING)
					
				# obviously there will no be any music in that new directory, so marking it unavailable..
				new_availability = False
				
			else:
				
				if not os.listdir(mountpoint):
					self.printer(" > Local music directory is empty.",LL_WARNING)
					new_availability = False
				else:
					self.printer(" > Local music directory present and has files.",LL_INFO)
					
					if not self.mpdc.is_dbdir( mpd_dir ):
						self.printer(" > Running MPD update for this directory.. (wait=True) ALERT! LONG BLOCKING OPERATION AHEAD...")
						self.mpdc.update_db( mpd_dir, True )	#TODO: don't wait! set available on return of update..
						if not self.mpdc.is_dbdir( mpd_dir ):
							self.printer(" > Nothing to play marking unavailable...")
							new_availability = False
						else:
							self.printer(" > Music found after updating")
							new_availability = True
					else:
						new_availability = True
			
				if new_availability is not None and new_availability != original_availability:
					subsource_availability_changes.append({"index":ix,"subindex":ssIx,"available":new_availability})

			ssIx+=1
			
		return subsource_availability_changes
	
	def play( self, sourceCtrl, resume={} ): #, subSourceIx=None ):
		self.printer('Start playing')
		
		#
		# variables
		#

		# get directory to play, directory is relative to MPD music dir.
		#ix = sourceCtrl.getIndex('name','locmus')
		arIx = sourceCtrl.index_current()
		subsource = sourceCtrl.subsource( arIx[0], arIx[1] )# subSourceIx )
		sLocalMusicMPD = subsource['mpd_dir']
		sLabel = subsource['label']
		
		#
		# load playlist
		#
		
		# NOT ANYMORE - OR TODO: MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..

		# populate playlist
		self.mpdc.pls_clear()
		playlistCount = self.mpdc.pls_pop(sLocalMusicMPD)

		# check if succesful...
		if playlistCount == "0":
			self.printer(' > Nothing in the playlist, trying to update database...')
			
			# update and try again...
			self.mpdc.update_db( sLocalMusicMPD, True )
			playlistCount = self.mpdc.pls_pop(sLocalMusicMPD)
			
			# check if succesful...
			if playlistCount == "0":
				# Failed. Returning false will cause caller to try next source
				self.printer(' > Nothing in the playlist, giving up. Marking source unavailable.')
				sourceCtrl.set_available( arIx[0], False, arIx[1] )
				pa_sfx(LL_ERROR)
				return False
			else:
				self.printer(' > Found {0:s} tracks'.format(playlistCount))
		else:
			self.printer(' > Found {0:s} tracks'.format(playlistCount))

		self.mpdc.play()
		return True
		#
		# continue where left
		#
		
		# TODO!!! !!!! !!!!!!
		"""
		
		if resume:
			playslist_pos = self.mpdc.lastKnownPos2( resume['file'], resume['time'] )	
		else:
			playslist_pos = {'pos': 1, 'time': 0}
			
		self.printer(' > Starting playback')
		#mpc.playStart( str(playslist_pos['pos']), playslist_pos['time'] )
		subprocess.call(["mpc", "-q" , "stop"])
		subprocess.call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
		if playslist_pos['time'] > 0:
			self.printer(' ...  Seeking to {0} sec.'.format(playslist_pos['time']))
			subprocess.call(["mpc", "-q" , "seek", str(playslist_pos['time'])])
			
		# double check if source is up-to-date
		
		# Load playlist directories, to enable folder up/down browsing.
		#mpc_get_PlaylistDirs()
		# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
	#	mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc.mpc_get_PlaylistDirs)
	#	mpc_get_PlaylistDirs_thread.start()
		return True
		"""
		
	def stop( self ):
		self.printer('Stopping source: locmus. Saving playlist position and clearing playlist.')
		# save playlist position (file name + position)
		# self.mpdc.mpc_save_pos_for_label( 'locmus' )
		self.mpdc.stop()
		return True
		
	def next( self ):
		self.printer('Next track')
		self.mpdc.next()
		return True
		
	def prev( self ):
		self.printer('Prev track')
		self.mpdc.prev()
		return True

	def pause( self, mode ):
		self.printer('Pause. Mode: {0}'.format(mode))
		self.mpdc.pause(mode)
		return True

	def random( self, mode ):
		self.printer('Random. Mode: {0}'.format(mode))
		self.mpdc.random(mode)
		return True

	def seekfwd( self ):
		self.printer('Seek FFWD')
		self.mpdc.seek('+1')
		return True

	def seekrev( self ):
		self.printer('Seek FBWD')
		self.mpdc.seek('-1')
		return True

	def update( self, location ):
		self.printer('Update. Location: {0}'.format(location))
		self.mpdc.update(location)
		return True
		
	def get_details():
		return False

	def get_state():
		return False

	def get_playlist():
		return False

	def get_folders():
		return False

	def source_get_media_details():
		return False
