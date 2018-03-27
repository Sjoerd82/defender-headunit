#
# SOURCE PLUGIN: Local Music
# Venema, S.R.G.
# 2018-03-27
#
# Plays local music folder(s), as defined in the main configuration.
#
# Extends SourceClass
#

# LOGGING
sourceName = 'locmus'
LOG_TAG = 'LOCMUS'
LOGGER_NAME = 'locmus'

# MISC (myprint, colorize)
from modules.hu_utils import *
from modules.hu_settings import getSourceConfig
from modules.hu_mpd import MpdController

# SETTINGS
#LOCAL MUSIC (now also in locmus.py)
#sLocalMusic="/media/PIHU_DATA"		# local music directory
#sLocalMusicMPD="PIHU_DATA"			# directory from a MPD pov. #TODO: derive from sLocalMusic
sSambaMusic="/media/PIHU_SMB/music"
sSambaMusicMPD="PIHU_SMB"			# directory from a MPD pov.

class BaseSourceClass(object):

	# output wrapper
	def __printer( self, message, level=LL_INFO, tag=LOG_TAG):
		self.logger.log(level, message, extra={'tag': tag})
		
	def check( self, sourceCtrl, subSourceIx=None ):
		self.__printer('Checking availability...')
		ix = sourceCtrl.index('name','locmus')	# source index
		locations = []							# list of tuples; index: 0 = mountpoint, 1 = mpd dir, 2 = availability.
		subsource_availability_changes = []		# list of changes
						
		if subSourceIx is None:
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
		
			mountpoint = location[0]
			mpd_dir = location[1]
			original_availability = location[2]
			new_availability = None

			self.__printer('Checking local folder: {0}, current availability: {1}'.format(mountpoint,original_availability))
			
			# check if the dir exists:
			if not os.path.exists(mountpoint):
				self.__printer(" > Local music directory does not exist.. creating {0}".format(mountpoint),LL_WARNING)
				os.makedirs(mountpoint)
				if not os.path.exists(mountpoint):
					self.__printer(" > [FAIL] Could not create directory",LL_WARNING)
					
				# obviously there will no be any music in that new directory, so marking it unavailable..
				new_availability = False
				
			else:
				
				if not os.listdir(mountpoint):
					self.__printer(" > Local music directory is empty.",LL_WARNING)
					new_availability = False
				else:
					self.__printer(" > Local music directory present and has files.",LL_INFO)
					
					if not self.mpdc.is_dbdir( mpd_dir ):
						self.__printer(" > Running MPD update for this directory.. (wait=True) ALERT! LONG BLOCKING OPERATION AHEAD...")
						self.mpdc.update_db( mpd_dir, True )	#TODO: don't wait! set available on return of update..
						if not self.mpdc.is_dbdir( mpd_dir ):
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
		
		return subsource_availability_changes
		
	def init( self, sourceCtrl ):
		self.__printer('Initializing...')
		
		# get source configuration from main configuration
		locmusConfig = getSourceConfig('locmus')
		
		# add all locations as configured
		for location in locmusConfig:
			self.__locmus_add( location['label']
					          ,location['musicdir']
					          ,location['musicdir_mpd']
					          ,sourceCtrl )

		return True
	
class MpdSourceClass(object):

	def __init__( self ):
		self.mpdc = MpdController(self.logger)

	def play( self ):
		return True
		
	def stop( self ):
		self.__printer('Stopping source: locmus. Saving playlist position and clearing playlist.')
		# save playlist position (file name + position)
		# self.mpdc.mpc_save_pos_for_label( 'locmus' )
		self.mpdc.stop()
		return True
		
	def next( self ):
		self.__printer('Next track')
		self.mpdc.next()
		return True
		
	def prev( self ):
		self.__printer('Prev track')
		self.mpdc.prev()
		return True

	def pause( self, mode ):
		self.__printer('Pause. Mode: {0}'.format(mode))
		self.mpdc.pause(mode)
		return True

	def random( self, mode ):
		self.__printer('Random. Mode: {0}'.format(mode))
		self.mpdc.random(mode)
		return True

	def seekfwd( self ):
		self.__printer('Seek FFWD')
		self.mpdc.seek('+1')
		return True

	def seekrev( self ):
		self.__printer('Seek FBWD')
		self.mpdc.seek('-1')
		return True

	def update( self, location ):
		self.__printer('Update. Location: {0}'.format(location))
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

class sourceClass(BaseSourceClass,MpdSourceClass):

	def __init__( self, logger ):
		self.logger = logger
		self.__printer('Source Class Init', level=LL_DEBUG)
		MpdSourceClass.__init__()
		
	def __locmus_add( self, label, dir, mpd_dir, sourceCtrl ):

		#TODO:
		mpd_musicdir = '/media'

		# get index (name is unique)
		ix = sourceCtrl.index('name','locmus')

		# construct the subsource
		subsource = {}
		subsource['name'] = 'locmus'
		subsource['displayname'] = 'local: ' + dir
		subsource['order'] = 0			# no ordering
		subsource['mountpoint'] = dir
		subsource['mpd_dir'] = mpd_dir
		subsource['label'] = label
		#subsource['uuid'] = None		# not relevant for local sources

		sourceCtrl.add_sub( ix, subsource )

	def init( self, sourceCtrl ):
		super(self, init)(sourceCtrl)

	# Source Check: Return True/False (available/not available)
	# Optionally, provide list of mountpoint(s) to check
	#def locmus_check( sourceCtrl, mountpoint=None ):
	
	def check( self, sourceCtrl, subSourceIx=None ):
		super(self, check)(sourceCtrl, subSourceIx)
		"""	Check source
		
			Checks all configured mountpoints
			if SUBSOURCE INDEX given, will only check mountpoint of that subsource index.
			Returns a list with dict containing changed subsources
		
			TODO: check if new mountpoints were added in the configuration.
		"""

	def play( self, sourceCtrl, resume={} ): #, subSourceIx=None ):
		self.__printer('Start playing')
		
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
			self.__printer(' > Nothing in the playlist, trying to update database...')
			
			# update and try again...
			self.mpdc.update_db( sLocalMusicMPD, True )
			playlistCount = self.mpdc.pls_pop(sLocalMusicMPD)
			
			# check if succesful...
			if playlistCount == "0":
				# Failed. Returning false will cause caller to try next source
				self.__printer(' > Nothing in the playlist, giving up. Marking source unavailable.')
				sourceCtrl.set_available( arIx[0], False, arIx[1] )
				pa_sfx(LL_ERROR)
				return False
			else:
				self.__printer(' > Found {0:s} tracks'.format(playlistCount))
		else:
			self.__printer(' > Found {0:s} tracks'.format(playlistCount))

		#
		# continue where left
		#
		
		# TODO!!! !!!! !!!!!!
		
		if resume:
			playslist_pos = self.mpdc.lastKnownPos2( resume['file'], resume['time'] )	
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
	#	mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc.mpc_get_PlaylistDirs)
	#	mpc_get_PlaylistDirs_thread.start()
		return True


		
	