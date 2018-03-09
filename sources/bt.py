#********************************************************************************
#
# Source: Bluetooth
#

from modules/hu_utils import *

# Logging
sourceName='bt'
mytag='bt'

#BLUETOOTH
sBtPinCode = "0000"
sBtDev = "hci0"						#TODO
sBtAdapter = "org.bluez.Adapter1"	#TODO
#sBtPlayer = None					#TODO
sBtPlayer = "/org/bluez/hci0/dev_78_6A_89_FA_1C_95/player0"		# Huawei G700-U10
sBtPlayer = "/org/bluez/hci0/dev_08_D4_0C_62_08_DF/player0"		# DESKTOP-HUEL5LB

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
		return False
		
	def play( self, sourceCtrl, subSourceIx=None ):
		self.__printer('Start playing')
		global sBtPlayer
		print('[BT] Start playing Bluetooth...')
		print(' ..  Player: {0}'.format(sBtPlayer))

		# dbus-send --system --type=method_call --dest=org.bluez /org/bluez/hci0/dev_78_6A_89_FA_1C_95/player0 org.bluez.MediaPlayer1.Next
		try:
			player = bus.get_object('org.bluez',sBtPlayer)
			BT_Media_iface = dbus.Interface(player, dbus_interface='org.bluez.MediaPlayer1')
			BT_Media_iface.Play()
			return True
		except:
			print('[BT] FAILED -- TODO!')
			return False

	def stop( self, sourceCtrl ):
		self.__printer('Stop')
		print('[BT] Stop playing Bluetooth...')
		print(' ..  Player: {0}'.format(sBtPlayer))

		# dbus-send --system --type=method_call --dest=org.bluez /org/bluez/hci0/dev_78_6A_89_FA_1C_95/player0 org.bluez.MediaPlayer1.Next
		try:
			player = bus.get_object('org.bluez',sBtPlayer)
			BT_Media_iface = dbus.Interface(player, dbus_interface='org.bluez.MediaPlayer1')
			#BT_Media_iface.Pause() -- hangs Python!!
			BT_Media_iface.Stop()
			return True
		except:
			print('[BT] FAILED -- TODO!')
			return False

		
	def next( self ):
		self.__printer('Next track')
		return True
		
	def prev( self ):
		self.__printer('Prev track')
		return True

