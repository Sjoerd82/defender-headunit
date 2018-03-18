#********************************************************************************
#
# Source: AUX / Line-In
#

from modules.hu_utils import *

# Logging
sourceName='line'
LOG_TAG = 'LINE'
LOGGER_NAME = 'line'

class sourceClass():

	# output wrapper
	def __printer( self, message, level=LL_INFO, continuation=False, tag=LOG_TAG, logger_name=LOGGER_NAME ):
		logger = logging.getLogger(logger_name)
		logger.log(level, message, extra={'tag': tag})

	def __init__( self ):
		self.__printer('Source Class Init', level=LL_DEBUG)
		
	def __del__( self ):
		print('Source Class Deleted {0}'.format(sourceName))
		
	def init( self, sourceCtrl ):
		self.__printer('Initializing...', level=15)
		return True

	def check( self, sourceCtrl, subSourceIx=None  ):
		self.__printer('Checking availability...', level=15)
		#global Sources
		self.__printer('Checking if Line-In is available... not available')
		#arSourceAvailable[4]=0 # not available
		#Sources.setAvailable('name','alsa',False) # not available
		#echo "Source 4 Unavailable; Line-In / ALSA"
		return False
		
	def play( self, sourceCtrl, subSourceIx=None ):
		self.__printer('Start playing')
		return True	

	def stop( self ):
		self.__printer('Stop')
		return True
		
	def next( self ):
		self.__printer('Not available')
		return False
		
	def prev( self ):
		self.__printer('Not available')
		return False

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

	def update( self ):
		self.__printer('Update not supported')
		return False

	def get_details():
		return False

	def get_state():
		return False

	def get_playlist():
		return False

	#def get_folders():

	def source_get_media_details():
		return False