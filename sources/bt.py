#
# SOURCE PLUGIN: Bluetooth
# Venema, S.R.G.
# 2018-04-03
#
# Plays Bluetooth
# Depends on the Bluetooth Daemon (?)
#

#
# Extends SourcePlugin
#

from yapsy.IPlugin import IPlugin
from modules.hu_utils import *
from modules.source_plugin import SourcePlugin

#BLUETOOTH
sBtPinCode = "0000"
sBtDev = "hci0"						#TODO
sBtAdapter = "org.bluez.Adapter1"	#TODO
#sBtPlayer = None					#TODO
sBtPlayer = "/org/bluez/hci0/dev_78_6A_89_FA_1C_95/player0"		# Huawei G700-U10
sBtPlayer = "/org/bluez/hci0/dev_08_D4_0C_62_08_DF/player0"		# DESKTOP-HUEL5LB

class MySource(SourcePlugin,IPlugin):

	def __init__(self):
		super(MySource,self).__init__()

	def check( self, subSourceIx=None  ):
		"""	Check source
		
			Checks to see if FM is available (SUBSOURCE INDEX will be ignored)
			Returns a list with dict containing changes in availability
			
			TODO: Will now simply return TRUE.
		"""
		self.__printer('CHECK availability...')

		subsource_availability_changes = []
		new_availability = True
		
		ix = self.sourceCtrl.index('name','bt')	# source index
		bt_source = self.sourceCtrl.source(ix)		
		original_availability = bt_source['available']
		
		if new_availability is not None and new_availability != original_availability:
			self.sourceCtrl.set_available( ix, new_availability )
			subsource_availability_changes.append({"index":ix,"available":new_availability})
		
		return subsource_availability_changes
		
	def play( self, subSourceIx=None ):
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

	def stop( self ):
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
		self.__printer('Update')
		#TODO IMPLEMENT
		return True
		
	def get_details(self, **kwargs ):
		details = {}
		track = copy.deep_copy(self.empty_track)
		track['display'] = "AUX"
		details['state'] = self.state
		return details
