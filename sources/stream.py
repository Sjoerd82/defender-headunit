#
# SOURCE PLUGIN: Streaming URL's
# Venema, S.R.G.
# 2018-03-27
#
# Plays Streaming URL's
#

import os

from modules.hu_utils import *
from modules.hu_mpd import MpdController

sourceName = 'stream'
LOG_TAG = 'STREAM'
LOGGER_NAME = 'stream'


class sourceClass():

	mpc1 = None

	# output wrapper
	def __printer( self, message, level=LL_INFO, tag=LOG_TAG):
		self.logger.log(level, message, extra={'tag': tag})

	def __init__( self, logger ):
		self.logger = logger
		self.__printer('Source Class Init', level=LL_DEBUG)
		self.mpc = mpdController(self.logger)
		
	def __del__( self ):
		print('Source Class Deleted {0}'.format(sourceName))
		
	def init( self, sourceCtrl ):
		self.__printer('Initializing...')
		return True

	def check( self, sourceCtrl, subSourceIx=None  ):
		self.__printer('Checking availability...')
		subsource_availability_changes = []		# list of changes

		ix = sourceCtrl.index('name','stream')	# source index
		stream_source = sourceCtrl.source(ix)		
		original_availability = stream_source['available']

		#TODO!!
		sDirSave = "/mnt/PIHU_CONFIG"
		
		# Test internet connection
		connected = internet()
		if not connected:
			self.__printer(' > Internet: [FAIL]')
			self.__printer(' > Marking source not available')
			new_availability = False
		else:
			self.__printer(' > Internet: [OK]')

		# See if we have streaming URL's
		streams_file = sDirSave + "/streams.txt"
		if os.path.isfile(streams_file):
			self.__printer(' > Stream URL\'s: File found [OK]')
		else:
			self.__printer(' > Stream URL\'s: File not found [FAIL]')
			self.__printer(' > Marking source not available')
			new_availability = False

		# Check if at least one stream is good
		self.__printer('Checking to see we have at least one valid stream')
		with open(streams_file,'r') as streams:
			for l in streams:
				uri = l.rstrip()
				if not uri[:1] == '#' and not uri == '':
					uri_OK = url_check(uri)					
					if uri_OK:
						self.__printer(' > Stream [OK]: {0}'.format(uri))
						#arSourceAvailable[5]=1
						#Sources.setAvailable('name','stream',True)
						#break
						new_availability = True
					else:
						self.__printer(' > Stream [FAIL]: {0}'.format(uri))
						new_availability = False

		if new_availability is not None and new_availability != original_availability:
			sourceCtrl.set_available( ix, new_availability )
			subsource_availability_changes.append({"index":ix,"available":new_availability})

		return subsource_availability_changes
	
	def play( self, sourceCtrl, subSourceIx=None ):
		self.__printer('Start playing')
		
		#
		# variables
		#
		
		
		#
		# load playlist
		#
		
		# NOT ANYMORE - OR TODO: MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..

		# populate playlist
		self.mpc.playlistClear()
		self.mpc.playlistPop('stream',None)
		
		# check if succesful...
		playlistCount = self.mpc.playlistIsPop()
		if playlistCount == "0":
			self.__printer(' > Nothing in the playlist, aborting...')
			pa_sfx(LL_ERROR)
			return False	
		else:
			self.__printer(' .... . Found {0:s} items'.format(playlistCount))
			
		#
		# continue where left
		#
		
		#TODO!
		#playslist_pos = mpc.lastKnownPos( sLabel )
		
		self.__printer(' > Starting playback')
		#call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
		call(["mpc", "-q" , "play"])

		# double check if source is up-to-date
		# todo
		
		return True

	def stop( self ):
		self.__printer('Stopping source: stream. Saving playlist position and clearing playlist.')
		# save position and current file name for this drive
		self.mpc.mpc_save_pos_for_label( 'stream' )
		
		# stop playback
		self.mpc.mpc_stop()
		#mpc $params_mpc -q stop
		#mpc $params_mpc -q clear	
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