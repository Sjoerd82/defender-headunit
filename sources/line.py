#********************************************************************************
#
# Source: AUX / Line-In
#

from hu_utils import *

# Logging
sourceName='line'

class sourceClass():

	# Wrapper for "myprint"
	def __printer( self, message, level=LL_INFO, continuation=False, tag=sourceName ):
		if continuation:
			myprint( message, level, '.'+tag )
		else:
			myprint( message, level, tag )

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

	def stop( self, sourceCtrl ):
		self.__printer('Stop')
		return True
		
	def next( self ):
		self.__printer('Not available')
		return False
		
	def prev( self ):
		self.__printer('Not available')
		return False
