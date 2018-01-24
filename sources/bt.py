
from hu_utils import *

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

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=sourceName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


# updates arSourceAvailable[3] (bt) -- TODO
def bt_check( sourceCtrl ):
	printer('CHECK availability... ')
	#arSourceAvailable[3]=0 # NOT Available
	#done at bt_init()
	return True

def bt_play():
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

def bt_stop():
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
