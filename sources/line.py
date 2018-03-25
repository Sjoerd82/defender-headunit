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
	def __printer( self, message, level=LL_INFO, tag=LOG_TAG):
		self.logger.log(level, message, extra={'tag': tag})

	def __init__( self, logger ):
		self.logger = logger
		
	def __del__( self ):
		print('Source Class Deleted {0}'.format(sourceName))
		
	def init( self, sourceCtrl ):
		self.__printer('Initializing...', level=15)
		return True

	def check( self, sourceCtrl, subSourceIx=None  ):
		"""	Check source
		
			Checks to see if AUX is available (SUBSOURCE INDEX will be ignored)
			Returns a list with dict containing changes in availability
			
			TODO: Will now simply return TRUE.
		"""
		self.__printer('CHECK availability...')

		subsource_availability_changes = []
		new_availability = True
		
		ix = sourceCtrl.index('name','alsa')	# source index
		line_source = sourceCtrl.source(ix)		
		original_availability = line_source['available']
		
		if new_availability is not None and new_availability != original_availability:
			sourceCtrl.set_available( ix, new_availability )
			subsource_availability_changes.append({"index":ix,"available":new_availability})
		
		return subsource_availability_changes
		
		
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