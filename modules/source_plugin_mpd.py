#
# Source Plugin base class for MPD
# Venema, S.R.G.
# 2018-03-28
#
# This BASE CLASS contains shared code for MPD based source plugins.
#

import os

import sys
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from source_plugin import SourcePlugin
from hu_mpd import MpdController
from hu_datastruct import CircularModeset

class MpdSourcePlugin(SourcePlugin):

	def __init__(self):
		super(MpdSourcePlugin, self).__init__()
		self.mpdc = None
		self.random_modes = CircularModeset('off','folder','playlist') # genre, artist

	def on_init(self, plugin_name, sourceCtrl, logger=None):
		super(MpdSourcePlugin, self).on_init(plugin_name,sourceCtrl,logger)
		self.mpdc = MpdController(self.logger)
		
		# NO, CONFIGURE THIS VIA CONFIGURATION.JSON "ENABLED FIELD"
		"""
		print "DEBUG: AVAILABLE OUTPUTS:"
		all_outputs = self.mpdc.outputs()
		print "CONFIGURATION (TODO) set to: Jack"
		for output in all_outputs:
			print output
			print output['outputid']
			print output['outputenabled']
			print output['outputname']
			#self.mpdc.disableoutput()
			
		#self.mpdc.enableoutput()
		"""
		
	def on_activate(self, subindex):
		
		print "DEBUG: MPD: on_activate"
		
		index = self.sourceCtrl.index('name',self.name)
		subsource = self.sourceCtrl.subsource( index, subindex )
		
		mpd_dir = None
		streams = None
		
		if 'mpd_dir' in subsource:
			mpd_dir = subsource['mpd_dir']
		
		if 'mpd_streams' in subsource:
			streams = subsource['mpd_streams']
		
		playlistCount = 0
		
		if mpd_dir is not None:
			# load playlist
			# NOT ANYMORE - OR TODO: MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..
			# populate playlist
			self.mpdc.pls_clear()
			playlistCount = self.mpdc.pls_pop_dir(mpd_dir)
			self.play()

		if streams is not None:
			self.mpdc.pls_clear()
			playlistCount = self.mpdc.pls_pop_streams(streams)
			self.play()
			
		
	def check_availability(self, **kwargs):
	
		index = self.sourceCtrl.index('name',self.name)	#name is unique
		subindex = kwargs['subindex']
	
		locations = []							# list of tuples; index: 0 = mountpoint, 1 = mpd dir, 2 = availability.
		subsource_availability_changes = []		# list of changes
		
		if subindex is None:
			subsources = self.sourceCtrl.subsource_all( index )
			i = 0
		else:
			subsources = list(self.sourceCtrl.subsource( index, subindex ))
			i = subindex
		
		for subsource in subsources:
			mountpoint = subsource['mountpoint']			
			cur_availability = subsource['available']
			self.printer('Checking local folder: {0}, current availability: {1}'.format(mountpoint,cur_availability))
			new_availability = self.check_mpddb_mountpoint(mountpoint, createdir=True, waitformpdupdate=True)
			self.printer('Checked local folder: {0}, new availability: {1}'.format(mountpoint,new_availability))
			
			if new_availability is not None and new_availability != cur_availability:
				subsource_availability_changes.append({"index":index,"subindex":i,"available":new_availability})			
			
			i += 1
		
		return subsource_availability_changes	
	
	def get_mpd_dir(self, mountpoint):
		"""Return the directory, as seen from MPD (cut off the mpd root)"""
		mpd_root = '/media'	# TODO -- ASSUMING /media
		mpd_dir = mountpoint[len(mpd_root)+1:]
		return mpd_dir
	
	def check_mpddb_mountpoint(self, mountpoint, createdir=False, waitformpdupdate=False):
		mpd_dir = self.get_mpd_dir(mountpoint)
		new_availability = None
		
		# check if the dir exists:
		if not os.path.exists(mountpoint):
			self.printer(" > Directory does not exist, marking unavailable",LL_WARNING)
			if createdir:
				self.printer(" > Creating directory {0}".format(mountpoint))
				os.makedirs(mountpoint)
			if not os.path.exists(mountpoint) and createdir:
				self.printer(" > [FAIL] Could not create directory!",LL_WARNING)
				
			# obviously there will no be any music in that new directory, so marking it unavailable..
			new_availability = False
			
		else:			
			if not os.listdir(mountpoint):
				self.printer(" > Directory is empty, marking unavailable.",LL_WARNING)
				new_availability = False
			else:
				self.printer(" > Directory present and has files.",LL_INFO)
				
				# check if this folder exists in the MPD database, update db if not.
				if not self.mpdc.is_dbdir( mpd_dir ):
					self.printer(" > Running MPD update for this directory.. (wait=True) ALERT! LONG BLOCKING OPERATION AHEAD...")
					self.mpdc.update( mpd_dir, waitformpdupdate )
					
					# re-check
					if not self.mpdc.is_dbdir( mpd_dir ):
						self.printer(" > Nothing to play, marking unavailable...")
						new_availability = False
					else:
						self.printer(" > Music found after updating")
						new_availability = True
				else:
					new_availability = True
		return new_availability
	
	def play(self, index=None, subindex=None, **kwargs): #sourceCtrl, index, subindex, resume={}): # , **kwargs ):
		""" Play MPD
		"""
		print "DEBUG: MPD: play"
		self.printer('Start playing')
		
		#index = kwargs['index']
		#subindex = kwargs['subindex']
		
		"""
		sourceCtrl = kwargs['srcCtrl']
		
			
		#
		# variables
		#

		# get directory to play, directory is relative to MPD music dir.
		#ix = sourceCtrl.getIndex('name','locmus')
		#arIx = sourceCtrl.index_current()
		#subsource = sourceCtrl.subsource( arIx[0], arIx[1] )# subSourceIx )
		subsource = sourceCtrl.subsource( index, subindex )
		sLocalMusicMPD = subsource['mpd_dir']
		sLabel = subsource['label']
		
		playlistCount =0
		
		# IF we have an mpd_dir:
		if sLocalMusicMPD is not None:
			#
			# load playlist
			#
			
			# NOT ANYMORE - OR TODO: MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..

			# populate playlist
			self.mpdc.pls_clear()
			playlistCount = self.mpdc.pls_pop(sLocalMusicMPD)
		elif streamsssssss:
			self.mpdc.pls_clear()
			#playlistCount = self.mpdc.pls_pop(xxx)
			
		"""
		'''
		# check if succesful...
		if playlistCount == "0":
			self.printer(' > Nothing in the playlist, trying to update database...')
			
			# update and try again...
			self.mpdc.update( sLocalMusicMPD, True )
			playlistCount = self.mpdc.pls_pop(sLocalMusicMPD)
			
			# check if succesful...
			if playlistCount == "0":
				# Failed. Returning false will cause caller to try next source
				self.printer(' > Nothing in the playlist, giving up. Marking source unavailable.')
				#sourceCtrl.set_available( arIx[0], False, arIx[1] )
				sourceCtrl.set_available( index, False, subindex )
				pa_sfx(LL_ERROR)
				return False
			else:
				self.printer(' > Found {0:s} tracks'.format(playlistCount))
		else:
			self.printer(' > Found {0:s} tracks'.format(playlistCount))
		'''
		self.mpdc.play()
		self.state['state'] = 'playing'
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
		
	def stop(self, **kwargs):
		self.printer('Stopping source: locmus. Saving playlist position and clearing playlist.')
		# save playlist position (file name + position)
		# self.mpdc.mpc_save_pos_for_label( 'locmus' )
		self.mpdc.stop()
		return True
		
	def next(self, **kwargs):
		self.printer('Next track. Available parameters: {0}'.format(kwargs))
		#TODO, implement advance track count
		self.mpdc.next()
		return True
		
	def prev(self, **kwargs):
		self.printer('Prev track. Available parameters: {0}'.format(kwargs))
		#TODO, implement advance track count
		self.mpdc.prev()
		return True

	def next_folder(self, **kwargs):
		self.printer('Next folder. Available parameters: {0}'.format(kwargs))
		self.mpdc.next_folder()
		return True
		
	def prev_folder(self, **kwargs):
		# not implemented
		return True
		
	def pause( self, mode ):
		self.printer('Pause. Mode: {0}'.format(mode))
		self.mpdc.pause(mode)
		return True

	def random( self, mode ):
		if mode in ('next','toggle'):
			self.random_modes.next()
		elif mode == 'prev':
			self.random_modes.prev()
		else:
			mode_ix = self.random_modes.index(mode)
			if mode_ix is not None:
				self.random_modes.activate(mode_ix)
			else:
				return False
				
		self.printer('Random. Mode: {0}'.format(self.random_modes.active))
		if 'off' in self.random_modes.active:
			self.mpdc.random('off')
		elif 'playlist' in self.random_modes.active:
			self.mpdc.random('on')
		elif 'folder' in self.random_modes.active:
			pass
		elif 'artist' in self.random_modes.active:
			pass
		elif 'genre' in self.random_modes.active:
			pass
		else:
			return False
		
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
		
	def get_state(self, **kwargs):
		cur_state = {}
		mpd_state = self.mpdc.state()
		cur_state.update(self.state)
		cur_state.update(mpd_state)
		return cur_state		

	def get_details(self, **kwargs ):
		self.printer('Details ?')
		details = {}
		track = dict_track()
		track['source'] = self.name
		
		mpdtrack = self.mpdc.track()
		track.update(mpdtrack) 			#convert MPD track{} to HU track{} format

		details['funfact'] = "bla"
		details['track'] = track
		
		# state
		cur_state = {}
		mpd_state = self.mpdc.state()
		cur_state.update(self.state)
		cur_state.update(mpd_state)
		details['state'] = cur_state
		return details
