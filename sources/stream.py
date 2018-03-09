
import os

from modules.hu_utils import *

# MPD
from modules.hu_mpd import *

sourceName = 'stream'

class sourceClass():

	mpc1 = None

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
		
	def init( self, sourceCtrl ):
		self.__printer('Initializing...')
		return True

	def check( self, sourceCtrl, subSourceIx=None  ):
		self.__printer('Checking availability...')
		
		#TODO!!
		sDirSave = "/mnt/PIHU_CONFIG"

		# Default to not available
		#arSourceAvailable[5]=0
		#Sources.setAvailable('name','strea',False)
		
		# Test internet connection
		connected = internet()
		if not connected:
			self.__printer(' > Internet: [FAIL]')
			self.__printer(' > Marking source not available')
			return False
		else:
			self.__printer(' > Internet: [OK]')

		# See if we have streaming URL's
		streams_file = sDirSave + "/streams.txt"
		if os.path.isfile(streams_file):
			self.__printer(' > Stream URL\'s: File found [OK]')
		else:
			self.__printer(' > Stream URL\'s: File not found [FAIL]')
			self.__printer(' > Marking source not available')
			return False

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
						return True
					else:
						self.__printer(' > Stream [FAIL]: {0}'.format(uri))
						return False

	
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

	def stop( self, sourceCtrl ):
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
