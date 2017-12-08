#!/usr/bin/python

# Headunit, created to function as a car's headunit.
# Designed to be controlled by a Sony RM-X2S or RM-X4S resistor network style remote control.
# Music is played using MPD.
#
# Author: Sjoerd Venema
# License: MIT
#
# Contains parts of "blueagent5.py"
#
# Dependencies: python-gobject, ...
#

#
# Available sources:
# - Local music folder
# - Flash drive
# - FM radio
# - Bluetooth
# - Airplay (future plan)
# - Line-In (detection via ADC -- TODO)
#
# Remote control:
# - Sony RM-X2S, RM-X4S via ADS1x15 ADC module
# - Any MPD client, when in local/usb music mode
# - CAN bus (future plan)
#
# Future plans:
# - Add output for an LCD display
# - Pi Zero hat
# - Line-In hardware control

# Known issues/limitations
# - Audio channels don't seem to mute on start, but if they do, we don't have anything implemented to unmute them.
# - Long/Short press buttons

# dbus-send --system --type=method_call --dest=org.bluez /org/bluez/hci0/dev_78_6A_89_FA_1C_95/player0 org.bluez.MediaPlayer1.Next

import os
import time
import subprocess
from subprocess import call
from subprocess import Popen, PIPE
#from tendo import singleton -- not available in Buildroot, disabling for now
#from pidfile import PIDfile
import pickle
import alsaaudio
from select import select

# Import pulseaudio volume handler
from pa_volume import pa_volume_handler

# python-mpd2 0.5.1 (not sure if this is the forked mpd2)
# used mainly for getting the current song for lookup on reload
from mpd import MPDClient

# DBus, currently only used for Bluez5 bluetooth
import dbus
from dbus.mainloop.glib import DBusGMainLoop

# from blueagent5.py
import dbus.service
import dbus.mainloop.glib
import gobject

import logging
#from pid import PidFile
from optparse import OptionParser

#to check for an internet connection
import socket

#to check an URL
import httplib2

# Global variables
arSource = ['fm','media','locmus','bt','alsa','stream'] # source types; add new sources in the end
arSourceAvailable = [0,0,0,0,0,0]            # corresponds to arSource; 1=available
arMediaWithMusic = []						 # list of mountpoints that contains music, according to MPD
iAtt = 0									 # Att mode toggle
iRandom = 0									 # We're keeping track of it within the script, not checking with MPD
dSettings = {'source': -1, 'volume': 20, 'mediasource': -1, 'medialabel': ''}	 # No need to save random, we don't want to save that (?)
#sRootFolder = os.path.dirname(os.path.abspath(__file__))
#sDirSave = "/root"
sDirRoot = "/mnt/PIHU_APP/defender-headunit"
sDirSave = "/mnt/PIHU_CONFIG"
bBeep = 0									 # Use hardware beep?
sInternet = "www.google.com"				 # URL to test internet with

#DBUS
bus = None

#ALSA
sAlsaMixer = "Master"	# Pi without Phat DAC = "Master" or "PCM" ?
						# Pi with Phat DAC geen mixer?
iAlsaMixerStep=1000
params_amixer="-q" #-c card -D device, etc.

#ALSA, via alsaaudio
oAlsaMixer = None
## this replaces:
## call(["amixer", "-q", "-c", "0", "set", "Master", volpct, "unmute"])

#PULSEAUDIO
bPulseVolume = 1		# Use PulseAudio volume control, not ALSA

#LOCAL MUSIC
sLocalMusic="/media/PIHU_DATA"		# local music directory
sLocalMusicMPD="PIHU_DATA"			# directory from a MPD pov. #TODO: derive from sLocalMusic

#MPD-client (MPC)
oMpdClient = None
arMpcPlaylistDirs = [ ]
iMPC_OK = 0

#BLUETOOTH
sBluetoothDev = "hci0"						#TODO
sBluetoothAdapter = "org.bluez.Adapter1"	#TODO

#BLUAGENT5
SERVICE_NAME = "org.bluez"
AGENT_IFACE = SERVICE_NAME + '.Agent1'
ADAPTER_IFACE = SERVICE_NAME + ".Adapter1"
DEVICE_IFACE = SERVICE_NAME + ".Device1"
PLAYER_IFACE = SERVICE_NAME + '.MediaPlayer1'
TRANSPORT_IFACE = SERVICE_NAME + '.MediaTransport1'

LOG_LEVEL = logging.INFO
#LOG_FILE = "/var/log/syslog"
#LOG_LEVEL = logging.DEBUG
LOG_FILE = sDirSave+"/blueagent5.log"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(module)s] %(message)s"

#UDISKS
#lDevices = [['/dev/sda1','/dev/sdb1']['SJOERD','MUSIC']]

# ********************************************************************************
# Callback functions
#
#  - Remote control
#  - MPD events
#  - UDisk add/remove drive

def cb_remote_btn_press ( func ):

	# Feedback beep
	if bBeep:
		beep()
	else:
		pa_sfx('button_feedback')

	# Handle button press
	if func == 'SHUFFLE':
		print('\033[95m[BUTTON] Shuffle\033[00m')
		if dSettings['source'] == 1 or dSettings['source'] == 2:
			mpc_random()
	elif func == 'SOURCE':
		print('\033[95m[BUTTON] Next source\033[00m')
		source_next()
		source_play()
	elif func == 'ATT':
		print('\033[95m[BUTTON] ATT\033[00m')
		volume_att_toggle()
	elif func == 'VOL_UP':
		print('\033[95m[BUTTON] VOL_UP\033[00m')		
		volume_up()
		return 0
	elif func == 'VOL_DOWN':
		print('\033[95m[BUTTON] VOL_DOWN\033[00m')
		volume_down()
		return 0
	elif func == 'SEEK_NEXT':
		print('\033[95m[BUTTON] Seek/Next\033[00m')
		seek_next()
	elif func == 'SEEK_PREV':
		print('\033[95m[BUTTON] Seek/Prev.\033[00m')
		seek_prev()
	elif func == 'DIR_NEXT':
		print('\033[95m[BUTTON] Next directory\033[00m')
		if dSettings['source'] == 1 or dSettings['source'] == 2:
			mpc_next_folder()		
	elif func == 'DIR_PREV':
		print('\033[95m[BUTTON] Prev directory\033[00m')
		if dSettings['source'] == 1 or dSettings['source'] == 2:
			mpc_prev_folder()
	elif func == 'UPDATE_LOCAL':
		print('\033[95m[BUTTON] Updating local MPD database\033[00m')
		locmus_update()
	elif func == 'OFF':
		print('\033[95m[BUTTON] Shutting down\033[00m')
		shutdown()
	else:
		print('Unknown button function')

def cb_mpd_event( event ):
	print('[MPD] DBUS event received: {0}'.format(event))

	if event == "player":
		mpc_save_pos()
	#elif event == "media_removed":
	#elif event == "media_ready":
	else:
		print(' ...  Unknown event')

def cb_udisk_dev_add( device ):
	print('[UDISK] Device added: {0}'.format(str(device)))
	udisk_details( device, 'A' )

def cb_udisk_dev_rem( device ):
	print('[UDISK] Device removed: {0}'.format(str(device)))
	udisk_details( device, 'R' )
		
# ********************************************************************************
# bluezutils5.py
#

def getManagedObjects():
    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
    return manager.GetManagedObjects()

def findAdapter():
    objects = getManagedObjects();
    bus = dbus.SystemBus()
    for path, ifaces in objects.iteritems():
        adapter = ifaces.get(ADAPTER_IFACE)
        if adapter is None:
            continue
        obj = bus.get_object(SERVICE_NAME, path)
        return dbus.Interface(obj, ADAPTER_IFACE)
    raise Exception("Bluetooth adapter not found")


def properties_changed(interface, changed, invalidated, path):
	if interface != "org.bluez.Device1":
		return

	if path in devices:
		dev = devices[path]

		if compact and skip_dev(dev, changed):
			return
		devices[path] = dict(devices[path].items() + changed.items())
	else:
		devices[path] = changed

	if "Address" in devices[path]:
		address = devices[path]["Address"]
	else:
		address = "<unknown>"

	if compact:
		print_compact(address, devices[path])
	else:
		print_normal(address, devices[path])

class BluePlayer(dbus.service.Object):
    AGENT_PATH = "/blueplayer/agent"
#    CAPABILITY = "DisplayOnly"
    CAPABILITY = "NoInputNoOutput"

    lcd = None
    bus = None
    adapter = None
    device = None
    deviceAlias = None
    player = None
    transport = None
    connected = None
    state = None
    status = None
    discoverable = None
    track = None
    mainloop = None

    def __init__(self, lcd):
        self.lcd = lcd


    def start(self):
        """Initialize gobject, start the LCD, and find any current media players"""
        gobject.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self.bus = dbus.SystemBus()
        dbus.service.Object.__init__(self, dbus.SystemBus(), BluePlayer.AGENT_PATH)

        self.bus.add_signal_receiver(self.playerHandler,
                bus_name="org.bluez",
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged",
                path_keyword="path")

        self.registerAgent()

        adapter_path = findAdapter().object_path
        self.bus.add_signal_receiver(self.adapterHandler,
                bus_name = "org.bluez",
                path = adapter_path,
                dbus_interface = "org.freedesktop.DBus.Properties",
                signal_name = "PropertiesChanged",
                path_keyword = "path")


        self.findPlayer()
        self.updateDisplay()

        """Start the BluePlayer by running the gobject mainloop()"""
        self.mainloop = gobject.MainLoop()
        self.mainloop.run()

    def findPlayer(self):
        """Find any current media players and associated device"""
        manager = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()

        player_path = None
        transport_path = None
        for path, interfaces in objects.iteritems():
            if PLAYER_IFACE in interfaces:
                player_path = path
            if TRANSPORT_IFACE in interfaces:
                transport_path = path

        if player_path:
            logging.debug("Found player on path [{}]".format(player_path))
            self.connected = True
            self.getPlayer(player_path)
            player_properties = self.player.GetAll(PLAYER_IFACE, dbus_interface="org.freedesktop.DBus.Properties")
            if "Status" in player_properties:
                self.status = player_properties["Status"]
            if "Track" in player_properties:
                self.track = player_properties["Track"]
        else:
            logging.debug("Could not find player")

        if transport_path:
            logging.debug("Found transport on path [{}]".format(player_path))
            self.transport = self.bus.get_object("org.bluez", transport_path)
            logging.debug("Transport [{}] has been set".format(transport_path))
            transport_properties = self.transport.GetAll(TRANSPORT_IFACE, dbus_interface="org.freedesktop.DBus.Properties")
            if "State" in transport_properties:
                self.state = transport_properties["State"]

    def getPlayer(self, path):
        """Get a media player from a dbus path, and the associated device"""
        self.player = self.bus.get_object("org.bluez", path)
        logging.debug("Player [{}] has been set".format(path))
        device_path = self.player.Get("org.bluez.MediaPlayer1", "Device", dbus_interface="org.freedesktop.DBus.Properties")
        self.getDevice(device_path)

    def getDevice(self, path):
        """Get a device from a dbus path"""
        self.device = self.bus.get_object("org.bluez", path)
        self.deviceAlias = self.device.Get(DEVICE_IFACE, "Alias", dbus_interface="org.freedesktop.DBus.Properties")

    def playerHandler(self, interface, changed, invalidated, path):
        """Handle relevant property change signals"""
        logging.debug("Interface [{}] changed [{}] on path [{}]".format(interface, changed, path))
        iface = interface[interface.rfind(".") + 1:]

        if iface == "Device1":
            if "Connected" in changed:
                self.connected = changed["Connected"]
        if iface == "MediaControl1":
            if "Connected" in changed:
                self.connected = changed["Connected"]
                if changed["Connected"]:
                    logging.debug("MediaControl is connected [{}] and interface [{}]".format(path, iface))
                    self.findPlayer()
        elif iface == "MediaTransport1":
            if "State" in changed:
                logging.debug("State has changed to [{}]".format(changed["State"]))
                self.state = (changed["State"])
            if "Connected" in changed:
                self.connected = changed["Connected"]
        elif iface == "MediaPlayer1":
            if "Track" in changed:
                logging.debug("Track has changed to [{}]".format(changed["Track"]))
                self.track = changed["Track"]
            if "Status" in changed:
                logging.debug("Status has changed to [{}]".format(changed["Status"]))
                self.status = (changed["Status"])
    
        self.updateDisplay()

    def adapterHandler(self, interface, changed, invalidated, path):
        """Handle relevant property change signals"""
        if "Discoverable" in changed:
                logging.debug("Adapter dicoverable is [{}]".format(self.discoverable))
                self.discoverable = changed["Discoverable"]
                self.updateDisplay()

    def updateDisplay(self):
        """Display the current status of the device on the LCD"""
        logging.debug("Updating display for connected: [{}]; state: [{}]; status: [{}]; discoverable [{}]".format(self.connected, self.state, self.status, self.discoverable))
        if self.discoverable:
            self.wake()
            self.showDiscoverable()
        else:
            if self.connected:
                if self.state == "idle":
                    self.sleep()
                else:
                    self.wake()
                    if self.status == "paused":
                        self.showPaused()
                    else:
                        self.showTrack()
            else:
                self.sleep()

    def showDevice(self):
        """Display the device connection info on the LCD"""
        self.lcd.clear()
        self.lcd.writeLn("Connected to:", 0)
        self.lcd.writeLn(self.deviceAlias, 1)
        time.sleep(2)

    def showTrack(self):
        """Display track info on the LCD"""
        lines = []
        if "Artist" in self.track:
            lines.append(self.track["Artist"])
            if self.track["Title"]:
                lines.append(self.track["Title"])
        elif "Title" in self.track:
            lines = self.lcd.wrap(self.track["Title"])

        self.lcd.clear()
        for i, line in enumerate(lines):
            if i >= self.lcd.numlines: break
            self.lcd.writeLn(lines[i], i)

    def showPaused(self):
        self.lcd.clear()
        self.lcd.writeLn("Device is paused", 0)

    def showDiscoverable(self):
        self.lcd.clear()
        self.lcd.writeLn("Waiting to pair", 0)
        self.lcd.writeLn("with device", 1)


    def next(self):
        self.player.Next(dbus_interface=PLAYER_IFACE)

    def previous(self):
        self.player.Previous(dbus_interface=PLAYER_IFACE)

    def play(self):
        self.player.Play(dbus_interface=PLAYER_IFACE)

    def pause(self):
        self.player.Pause(dbus_interface=PLAYER_IFACE)

    def volumeUp(self):
        self.control.VolumeUp(dbus_interface=CONTROL_IFACE)
        self.transport.VolumeUp(dbus_interface=TRANSPORT_IFACE)

    def wake(self):
        """Wake up the LCD"""
        self.lcd.backlight(Lcd.TEAL)

    def shutdown(self):
        logging.debug("Shutting down BluePlayer")
        self.lcd.end()
        if self.mainloop:
            self.mainloop.quit()

    def sleep(self):
        """Put the LCD to sleep"""
        self.lcd.clear()
        self.lcd.backlight(Lcd.OFF)

    def getStatus(self):
        return self.status


# ********************************************************************************
# BlueAgent5
#
class BlueAgent(dbus.service.Object):
    AGENT_PATH = "/blueagent5/agent"
    #CAPABILITY = "DisplayOnly"
    CAPABILITY = "NoInputNoOutput"
    pin_code = None

    def __init__(self, pin_code):
        dbus.service.Object.__init__(self, dbus.SystemBus(), BlueAgent.AGENT_PATH)
        self.pin_code = pin_code

        logging.basicConfig(filename=LOG_FILE, format=LOG_FORMAT, level=LOG_LEVEL)
        logging.info("Starting BlueAgent with PIN [{}]".format(self.pin_code))
        
    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        logging.debug("BlueAgent DisplayPinCode invoked")

    @dbus.service.method(AGENT_IFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        logging.debug("BlueAgent DisplayPasskey invoked")

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        logging.info("BlueAgent is pairing with device [{}]".format(device))
        self.trustDevice(device)
        return self.pin_code

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        """Always confirm"""
        logging.info("BlueAgent is pairing with device [{}]".format(device))
        self.trustDevice(device)
        return

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        """Always authorize"""
        logging.debug("BlueAgent AuthorizeService method invoked")
        return

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        logging.debug("RequestPasskey returns 0")
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        """Always authorize"""
        logging.info("BlueAgent is authorizing device [{}]".format(self.device))
        return

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self):
        logging.info("BlueAgent pairing request canceled from device [{}]".format(self.device))

    def trustDevice(self, path):
        bus = dbus.SystemBus()
        device_properties = dbus.Interface(bus.get_object(SERVICE_NAME, path), "org.freedesktop.DBus.Properties")
        device_properties.Set(DEVICE_IFACE, "Trusted", True)

    def registerAsDefault(self):
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object(SERVICE_NAME, "/org/bluez"), "org.bluez.AgentManager1")
        manager.RegisterAgent(BlueAgent.AGENT_PATH, BlueAgent.CAPABILITY)
        manager.RequestDefaultAgent(BlueAgent.AGENT_PATH)

    def startPairing(self):
        bus = dbus.SystemBus()
        adapter_path = findAdapter().object_path
        adapter = dbus.Interface(bus.get_object(SERVICE_NAME, adapter_path), "org.freedesktop.DBus.Properties")
        adapter.Set(ADAPTER_IFACE, "Discoverable", True)
        
        logging.info("BlueAgent is waiting to pair with device")

def beep():
	call(["gpio", "write", "6", "1"])
	time.sleep(0.05)
	call(["gpio", "write", "6", "0"])

def shutdown():
	save_settings()
	source_stop()
	#call(["systemctl", "poweroff", "-i"])
	call(["halt"])

def internet():
    try:
        # connect to the host -- tells us if the host is actually reachable
        socket.create_connection((sInternet, 80))
        return True
    except OSError:
        pass
    return False

def url_check( url ):
	# TODO!!, next build has httplib2
	#h = httplib2.Http()
	#resp = h.request(url, 'HEAD')
	#assert int(resp[0]['status']) < 400
	return True
	

# ********************************************************************************
# ALSA, using python-alsaaudio
#

def set_volume( volume ):
	if bPulseVolume:
		pa_set_volume(volume)
	else:
		alsa_set_volume(volume)

def get_volume( volume ):
	if bPulseVolume:
		return pa_get_volume()
	else:
		return alsa_get_volume()

def alsa_init():
	global oAlsaMixer
	print("[ALSA] Initializing mixer")
	
	try:
		oAlsaMixer = alsaaudio.Mixer(sAlsaMixer, cardindex=0)
	except alsaaudio.ALSAAudioError:
		print('No such mixer')

def alsa_unmute():
	print('[ALSA] Unmuting...')
	#TODO

def alsa_get_volume():
	global oAlsaMixer
	print("[ALSA] Retrieving volume from mixer")

	# TODO --- UNTESTED WITH ACTUAL ALSA MIXER !!!!
	
	volumes = []
	volumes.append(0)
	
	if oAlsaMixer is None:
		print("ALSA mixer unavailable")
		volumes[0] = 0
	else:
		volumes = oAlsaMixer.getvolume()
		for i in range(len(volumes)):
			print("Channel {0:d} volume: {1:d}%".format(i,volumes[i]))

		#We're keeping L&R in sync, so just return the first channel.
	
	return volumes[0]
	
def alsa_set_volume( volume ):
	global oAlsaMixer
	#Only allow volume 5-100%
	if volume > 100:
		volume = 100
	
	if volume < 5:
		volume = 5
	
	if oAlsaMixer is None:
		print("[ALSA] Mixer unavailable, cannot set volume")
	else:
		print('[ALSA] Setting volume to {0:d}%'.format(volume))
		oAlsaMixer.setvolume(volume, alsaaudio.MIXER_CHANNEL_ALL)

def alsa_play_fx( fx ):
	print('Playing effect')
	#TODO

# ********************************************************************************
# PulseAudio
# Use 0-100 for volume.
#
def pa_init():
	print('[PULSE] Loading sound effects')
	call(["pactl","upload-sample",sDirRoot+"/sfx/startup.wav", "startup"])
	call(["pactl","upload-sample",sDirRoot+"/sfx/beep_60.wav", "beep_60"])
	call(["pactl","upload-sample",sDirRoot+"/sfx/beep_70.wav", "beep_70"])
	call(["pactl","upload-sample",sDirRoot+"/sfx/beep_60_70.wav", "beep_60_70"])

def pa_set_volume( volume ):
	print('[PULSE] Setting volume')
	pavol = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')
	pavol.vol_set_pct(volume)

def pa_get_volume():
	print('[PULSE] Getting volume')
	pavol = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')
	return pavol.vol_get()

def pa_sfx(sfx):
	if sfx == 'startup':
		call(["pactl", "play-sample", "startup", "alsa_output.platform-soc_sound.analog-stereo"])
	elif sfx == 'button_feedback':
		call(["pactl", "play-sample", "beep_60", "alsa_output.platform-soc_sound.analog-stereo"])
	elif sfx == 'mpd_update_db':
		call(["pactl", "play-sample", "beep_60_70", "alsa_output.platform-soc_sound.analog-stereo"])
	
# ********************************************************************************
# Volume wrappers
#

def volume_att_toggle():
	global dSettings
	global iAtt
	print('Toggling ATT volume')
	
	if iAtt == 1:
		print('Restoring previous volume')
		iAtt = 0
		volpct = str(dSettings['volume'])+'%'
		set_volume( dSettings['volume'] )
		
	elif iAtt == 0:
		print('Setting att volume (25%)')
		# We're not saving this volume level, as it is temporary.
		# ATT will be reset by pressing ATT again, or changing the volume
		iAtt = 1
		set_volume( 25 )
		
	else:
		print('Uhmmm.. this shouldn\'t have happened')
		iAtt = 0

def volume_up():
	global dSettings
	global iAtt

	# PulseAudio volume control
	pavol = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')

	# always reset Att. state at manual vol. change
	iAtt = 0

	if bPulseVolume:
		pavol.vol_up()
		dSettings['volume'] = pavol.vol_get()
	else:
		print('Volume up; +5%')
		volume_new = alsa_get_volume()+5
		set_volume(volume_new)
		#call(["amixer", "-q", "-c", "0", "set", "Master", "5+", "unmute"])
		dSettings['volume'] = volume_new

		# Save volume change
		#pipe = subprocess.check_output("amixer get Master | awk '$0~/%/{print $5}' | tr -d '[]%'", shell=True)
		#pipe = subprocess.check_output("amixer get Master | awk '$0~/%/{print $4}' | tr -d '[]%'", shell=True)
		#dSettings['volume'] = int(pipe.splitlines()[0]) #LEFT CHANNEL	
	
	# Save new volume level
	save_settings()

def volume_down():
	global dSettings
	global iAtt
	global iDoSave

	# PulseAudio volume control
	pavol = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')

	# always reset Att. state at manual vol. change
	iAtt = 0
	
	if bPulseVolume:
		pavol.vol_down()
		dSettings['volume'] = pavol.vol_get()
	else:
		print('Volume down; 5%')
		volume_new = alsa_get_volume()-5
		set_volume(volume_new)
		dSettings['volume'] = volume_new
		
	# Save new volume level
	save_settings()

def udisk_details( device, action ):
	device_obj = bus.get_object("org.freedesktop.UDisks", device)
	device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)
	#
	#  beware.... anything after this may or may not be defined depending on the event and state of the drive. 
	#  Attempts to get a prop that is no longer set will generate a dbus.connection:Exception
	#

	# HANDY DEBUGGING TIP, DISPLAY ALL AVAILABLE PROPERTIES:
	# WILL *NOT* WORK FOR DEVICE REMOVAL
	#data = device_props.GetAll('')
	#for i in data: print i+': '+str(data[i])
	
	DeviceFile = ""
	mountpoint = ""
	
	try:
		DeviceFile = device_props.Get('org.freedesktop.UDisks.Device',"DeviceFile")
		print(" .....  DeviceFile: {0}".format(DeviceFile))
		
	except:
		print(" .....  DeviceFile is unset... Aborting...")
		return 1
	
	# Check if DeviceIsMediaAvailable...
	try:    
		is_media_available = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsMediaAvailable")
		if is_media_available:
			print(" .....  Media available")
		else:
			print(" .....  Media not available... Aborting...")
			return 1
	except:
		print(" .....  DeviceIsMediaAvailable is not set... Aborting...")
		return 1
	
	# Check if it is a Partition...
	try:
		is_partition = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsPartition")
		if is_partition:
			print(" .....  Device is partition")
	except:
		print(" .....  DeviceIsPartition is not set... Aborting...")
		return 1

	if not is_partition:
		print(" .....  DeviceIsPartition is not set... Aborting...")
		return 1

	if action == 'A':
		# Find out its mountpoint...
		#IdLabel: SJOERD
		#DriveSerial: 0014857749DCFD20C7F95F31
		#DeviceMountPaths: dbus.Array([dbus.String(u'/media/SJOERD')], signature=dbus.Signature('s'), variant_level=1)
		#DeviceFileById: dbus.Array([dbus.String(u'/dev/disk/by-id/usb-Kingston_DataTraveler_SE9_0014857749DCFD20C7F95F31-0:0-part1'), dbus.String(u'/dev/disk/by-uuid/D2B6-F8B3')], signature=dbus.Signature('s'), variant_level=1)
		
		mountpoint = subprocess.check_output("mount | egrep "+DeviceFile+" | cut -d ' ' -f 3", shell=True).rstrip('\n')
		if mountpoint != "":
			sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
			print(" .....  Mounted on: {0} (label: {1})".format(mountpoint,sUsbLabel))
			mpc_update(sUsbLabel)
			media_check()
			media_play()
		else:
			print(" .....  No mountpoint found. Stopping.")
		
	elif action == 'R':
		# Find out its mountpoint...
		#We cannot retrieve many details from dbus about a removed drive, other than the DeviceFile (which at this point is no longer available).
		media_check()
		# Determine if we were playing this media (source: usb=1)
		#if dSettings['source'] == 1 and
		
		#TODO!
		
	else:
		print(" .....  ERROR: Invalid action.")

# ********************************************************************************
# Save & Load settings, using pickle
#

def save_settings():
	global dSettings
	global sDirSave
	print('[PICKLE] Saving settings')
	pickle.dump( dSettings, open( sDirSave+"/headunit.p", "wb" ) )
	#TODO: try-except

def load_settings():
	global dSettings
	global sDirSave

	sPickleFile = sDirSave+"/headunit.p"
	
	print('\033[96m[PICKLE] Loading previous settings\033[00m')

	#TODO: Check if sDirSave exists
	try:
		dSettings = pickle.load( open( sPickleFile, "rb" ) )
	except:
		print('[PICKLE] Loading headunit.p failed. First run? - Creating headunit.p with default values.')
		#assume: fails because it's the first time and no settings saved yet? Setting default:
		pickle.dump( dSettings, open( sPickleFile, "wb" ) )

	# Apply settings:
	
	#VOLUME
	#check if the value is valid
	if dSettings['volume'] < 0 or dSettings['volume'] > 100:
		dSettings['volume'] = 40
		pickle.dump( dSettings, open( sPickleFile, "wb" ) )
		print('[PICKLE] No setting found, defaulting to 40%')
	# also don't restore a too low volume
	elif dSettings['volume'] < 30:
		print('[PICKLE] Volume too low, defaulting to 30%')
		dSettings['volume'] = 30
	else:
		print('[PICKLE] Volume: {0:d}%'.format(dSettings['volume']))
	set_volume( dSettings['volume'] )
	
	#SOURCE
	if dSettings['source'] < 0:
		print('[PICKLE] Source: not available')
	else:
		print('[PICKLE] Source: {0:s}'.format(arSource[dSettings['source']]))

	print('\033[96m[PICKLE] DONE\033[00m')


def seek_next():
	global dSettings
	if dSettings['source'] == 1 or dSettings['source'] == 2:
		mpc_next_track()
	elif dSettings['source'] == 3:
		bt_next()
	#fm_next ofzoiets

def seek_prev():
	global dSettings
	if dSettings['source'] == 1 or dSettings['source'] == 2:
		mpc_prev_track()
	elif dSettings['source'] == 3:
		bt_prev()

# ********************************************************************************
# MPC

def mpc_init():
	global oMpdClient
	print('[MPC] Initializing MPD client')
	oMpdClient = MPDClient() 

	oMpdClient.timeout = 10                # network timeout in seconds (floats allowed), default: None
	oMpdClient.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
	oMpdClient.connect("localhost", 6600)  # connect to localhost:6600
	print(oMpdClient.mpd_version)          # print the MPD version
	
	print('[MPC] Subscribing to channel: media_ready')
	oMpdClient.subscribe("media_ready")

	print('[MPC] Subscribing to channel: media_removed')
	oMpdClient.subscribe("media_removed")
	
	print('[MPC] Random: OFF, Repeat: ON')
	oMpdClient.random(0)
	oMpdClient.repeat(1)
	#call(["mpc", "-q", "random", "off"])
	#call(["mpc", "-q", "repeat", "on"])
	
	print('[MPC-debug] send_idle()')
	oMpdClient.send_idle()

	
	
def mpc_random():
	global iRandom
	print('[MPC] Toggling random')
	
	if dSettings['source'] < 1 or dSettings['source'] > 2:
		print(' Random is only available for MPD sources ... aborting.')
	else:	
		# Random is ON, turning it OFF
		if iRandom == 1:
			print('[MPC] Turning random: off')
			iRandom = 0
			call(["mpc", "-q", "random", "off"])

		# Random is OFF, turning it ON + putting it in effect.
		else:
			print('[MPC] Turning random: on')
			iRandom = 1
			call(["mpc", "-q", "random", "on"])
			call(["mpc", "-q", "next"])

def mpc_get_PlaylistDirs():
	global arMpcPlaylistDirs
	dirname_current = ''
	dirname_prev = ''
	iPos = 1

	print('[DEBUG] Loading directory structure; mpc_get_PlaylistDirs')
	
	pipe = Popen('mpc -f %file% playlist', shell=True, stdout=PIPE)

	#del arMpcPlaylistDirs
	arMpcPlaylistDirs = []

	for line in pipe.stdout:
		dirname_current=os.path.dirname(line.strip())
		t = iPos, dirname_current
		if dirname_prev != dirname_current:
			arMpcPlaylistDirs.append(t)
		dirname_prev = dirname_current
		iPos += 1

def mpc_current_folder():
	# Get current folder
	pipe = subprocess.check_output("mpc -f %file%", shell=True)
	return os.path.dirname(pipe.splitlines()[0])

def mpc_next_folder_pos():
	global arMpcPlaylistDirs
	dirname_current = mpc_current_folder()
	print('Current folder: {0:s}'.format(dirname_current))
	
	try:
		iNextPos = arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)+1)][0]
		print('New folder = {0:s}'.format(arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)+1)][1]))
	except IndexError:
		# I assume the end of the list has been reached...
		iNextPos = 1

	return iNextPos

def mpc_prev_folder_pos():
	global arMpcPlaylistDirs
	dirname_current = mpc_current_folder()
	print('Current folder: {0:s}'.format(dirname_current))

	try:
		iNextPos = arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)-1)][0]
		print('New folder = {0:s}'.format(arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)-1)][1]))
	except IndexError:
		# I assume we past the beginning of the list...
		print len(arMpcPlaylistDirs)
		iNextPos = arMpcPlaylistDirs[len(arMpcPlaylistDirs)][0]

	return iNextPos

def mpc_next_track():
	print('Next track')
	call(["mpc", "next"])
	
def mpc_prev_track():
	print('Prev. track')
	call(["mpc", "prev"])

def mpc_next_folder():
	print('Next folder')
	call(["mpc", "play", str(mpc_next_folder_pos())])

def mpc_prev_folder():
	print('Prev folder')
	call(["mpc", "play", str(mpc_prev_folder_pos())])
	
def mpc_stop():
	print('Stopping MPC [pause]')
	call(["mpc", "pause"])

def mpc_update( location ):
	#Sound effect
	pa_sfx('mpd_update_db')
	#Debug info
	print('[MPC] Updating database for location: {0}'.format(location))
	#Update
	call(["mpc", "--wait", "-q", "update", location])
	print(' ...  Update finished')

def mpc_save_pos():
	global dSettings
	if dSettings['source'] == 1:
		mpc_save_pos_for_label ( dSettings['medialabel'] )	
	elif dSettings['source'] == 2:
		mpc_save_pos_for_label ('locmus')

def mpc_save_pos_for_label ( label ):
	print('[MPC] Saving playlist position for label: {0}'.format(label))
	oMpdClient = MPDClient() 
	oMpdClient.timeout = 10                # network timeout in seconds (floats allowed), default: None
	oMpdClient.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
	oMpdClient.connect("localhost", 6600)  # connect to localhost:6600

	oMpdClient.command_list_ok_begin()
	oMpdClient.status()
	results = oMpdClient.command_list_end()

	# Dictionary in List
	for r in results:
		songid = r['songid']
		timeelapsed = r['time']

	current_song_listdick = oMpdClient.playlistid(songid)
	oMpdClient.close()
	oMpdClient.disconnect()

	for f in current_song_listdick:
			current_file = f['file']
	
	print current_file
	print(' ...  file: {0}, time: {1}'.format(current_file,timeelapsed))
	pickle_file = sDirSave + "/mp_" + label + ".p"
	pickle.dump( current_file, open( pickle_file, "wb" ) )

def mpc_lkp( label ):

	#default
	pos = 1
	
	# open pickle_file, if it exists
	pickle_file = sDirSave + "/mp_" + label + ".p"
	if os.path.isfile(pickle_file):
		print('[MPC] Retrieving last known position from lkp file: {0:s}'.format(pickle_file))
		try:
			current_file = pickle.load( open( pickle_file, "rb" ) )
		except:
			print('[PICKLE] Loading {0:s} failed!'.format(pickle_file))
			return pos

		#otherwise continue:
		oMpdClient = MPDClient() 
		oMpdClient.timeout = 10                # network timeout in seconds (floats allowed), default: None
		oMpdClient.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
		oMpdClient.connect("localhost", 6600)  # connect to localhost:6600
		playlist = oMpdClient.playlistid()
		oMpdClient.close()
		oMpdClient.disconnect()

		for x in playlist:
				if x['file'] == current_file:
						pos = int(x['pos'])+1
						print('[MPC] Match found! Continuing playback at #{0}'.format(pos))

	else:
		print('[MPC] No position file available for this medium (first run?)')

	return pos

def mpc_populate_playlist ( label ):
	#global oMpdClient

	# Stop idle, in order to send a command
	#oMpdClient.noidle()
	
	xMpdClient = MPDClient() 
	xMpdClient.connect("localhost", 6600)  # connect to localhost:6600
		
	if label == 'locmus':
		xMpdClient.findadd('base',sLocalMusicMPD)
	elif label == 'streams':
		# Using the command line:
		#  ..but this generates some problems with special characters
		streams_file = sDirSave + "/streams.txt"
		p1 = subprocess.Popen(["cat", streams_file], stdout=subprocess.PIPE)
		p2 = subprocess.Popen(["mpc", "add"], stdin=p1.stdout, stdout=subprocess.PIPE)
		p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
		output,err = p2.communicate()		
	else:
		xMpdClient.findadd('base',label)
	
	xMpdClient.close()
	
	#oMpdClient.send_idle()


def mpc_playlist_is_populated():
	task = subprocess.Popen("mpc playlist | wc -l", shell=True, stdout=subprocess.PIPE)
	mpcOut = task.stdout.read()
	assert task.wait() == 0
	return mpcOut.rstrip('\n')

# updates arSourceAvailable[0] (fm) --- TODO
def fm_check():
	print('[FM] CHECK availability... not available.')
	arSourceAvailable[0]=0 # not available
	#echo "Source 0 Unavailable; FM"

def fm_play():
	print('[FM] Start playing FM radio...')
	#TODO

def fm_stop():
	print('[FM] Stop')
	
# ********************************************************************************
# BLUETOOTH
def bt_init():
	global arSourceAvailable
	global bus

	# default to not available
	arSourceAvailable[3]=0

	print('[BT] Initializing')
	print(' ..  Getting on the DBUS')
	#bus = dbus.SystemBus()
	manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
 	objects = manager.GetManagedObjects()
	print(' ..  Bluetooth devices:')
	for path in objects.keys():
		print(' ..  .. {0}'.format(path))
		interfaces = objects[path]
		for interface in interfaces.keys():
			if interface == 'org.bluez.Adapter1':
				print(' ..  .. Required interface (org.bluez.Adapter1) found!')
				arSourceAvailable[3]=1
				print(' ..  .. Properties:')
				properties = interfaces[interface]
				for key in properties.keys():
					print(' ..  .. .. {0:19} = {1}'.format(key, properties[key]))
			elif interface == 'org.bluez.MediaControl1':
				print(' ..  .. MediaControl1 (deprecated):')
				properties = interfaces[interface]
				for key in properties.keys():
					print(' ..  .. .. {0:19} = {1}'.format(key, properties[key]))				
			elif interface == 'org.bluez.MediaPlayer1':
				print(' ..  .. TEST! MediaPlayer:')
				properties = interfaces[interface]
				for key in properties.keys():
					print(' ..  .. .. {0:19} = {1}'.format(key, properties[key]))
				#player = dbus.Interface(bus.get_object("org.bluez", "/org/bluez/hci0/dev_78_6A_89_FA_1C_95/player0"), "org.freedesktop.DBus.Properties")
				#player.
			else:
				print(' ..  .. Interface: {0}'.format(interface))
				properties = interfaces[interface]
				for key in properties.keys():
					print(' ..  .. .. {0:19} = {1}'.format(key, properties[key]))
				

	# continue init, if interface is found
	if arSourceAvailable[3] == 1:
	
		# Get the device
		adapter = dbus.Interface(bus.get_object("org.bluez", "/org/bluez/" + sBluetoothDev), "org.freedesktop.DBus.Properties")

		#dbus.exceptions.DBusException: org.freedesktop.DBus.Error.PropertyReadOnly: Property 'Name' is not writable
		#vi /var/lib/bluetooth/B8\:27\:EB\:96\:88\:67/config
		#name LandRoverDefender
		#adapter.Set("org.bluez.Adapter1", "Name", "Land Rover Defender")
		
		# Make sure the device is powered on
		print(' ..  Turning on Bluetooth')
		adapter.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
		#if #TODO
		#print "Powered ", adapter.Get("org.bluez.Adapter1", "Powered")
		
		# Test NEXT
		#PLAYER_IFACE


# updates arSourceAvailable[3] (bt) -- TODO
def bt_check():
	print('[BT] CHECK availability... ')
	#arSourceAvailable[3]=0 # NOT Available
	#done at bt_init()

def bt_play():
	print('Start playing Bluetooth...')
	#TODO

def bt_next():

	bus = dbus.SystemBus()
	manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
	objects = manager.GetManagedObjects()

	print('NOT IMPLEMENTED!!')
	# TODO
	# https://kernel.googlesource.com/pub/scm/bluetooth/bluez/+/5.43/doc/media-api.txt
	# 
	# MediaPlayer1 hierarchy
	# ======================
	# Service		org.bluez (Controller role)
	# Interface	org.bluez.MediaPlayer1
	# Object path	[variable prefix]/{hci0,hci1,...}/dev_XX_XX_XX_XX_XX_XX/playerX

def bt_prev():
	print('NOT IMPLEMENTED!!')

	
# updates arSourceAvailable[4] (alsa) -- TODO
def linein_check():
	print('[LINE] Checking if Line-In is available... not available')
	arSourceAvailable[4]=0 # not available
	#echo "Source 4 Unavailable; Line-In / ALSA"

def linein_play():
	print('Start playing from line-in...')
	#TODO

def linein_stop():
	print('[LINE] Stop')

# updates arSourceAvailable[1] (mpc)
def media_check():
	global arMediaWithMusic
	
	print('[USB] CHECK availability...')

	arSourceAvailable[1]=1 	# Available, unless proven otherwise in this procedure
	arMedia = []			# list of mountpoints on /media
	arMediaWithMusic = []  	# Reset (will be rebuild in this procedure)
	
	try:
		print(' ... Check if anything is mounted on /media...')
		# do a -f1 for devices, -f3 for mountpoints
		grepOut = subprocess.check_output(
			"mount | grep /media | cut -d' ' -f3",
			shell=True,
			stderr=subprocess.STDOUT,
		)
	except subprocess.CalledProcessError as err:
		print('ERROR:', err)
		arSourceAvailable[1]=0
	else:
		arMedia = grepOut.split()
		
	# playlist loading is handled by scripts that trigger on mount/removing of media
	# mpd database is updated on mount by same script.
	# So, let's check if there's anything in the database for this source:
	
	if arSourceAvailable[1] == 1:
		print(' ... /media has mounted filesystems: ')
		for mountpoint in arMedia:
			print(' ... . {0}'.format(mountpoint))
		
		print(' ... Continuing to crosscheck with mpd database for music...')
		for mountpoint in arMedia:
			sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
			
			if sUsbLabel == sLocalMusicMPD:
				print(' ... . {0}: ignoring local music directory'.format(sLocalMusicMPD))
			else:		
				taskcmd = "mpc listall "+sUsbLabel+" | wc -l"
				task = subprocess.Popen(taskcmd, shell=True, stdout=subprocess.PIPE)
				mpcOut = task.stdout.read()
				assert task.wait() == 0
				
				if mpcOut.rstrip('\n') == '0':
					print(' ... . {0}: nothing in the database for this source.'.format(sUsbLabel))
				else:
					print(' ... . {0}: found {1:s} tracks'.format(sUsbLabel,mpcOut.rstrip('\n')))		
					arMediaWithMusic.append(mountpoint)
					#default to found media, if not set yet
					if dSettings['mediasource'] == -1:
						dSettings['mediasource'] = 0

		# if nothing useful found, then mark source as unavailable
		if len(arMediaWithMusic) == 0:
			arSourceAvailable[1]=0

	else:
		print(' ... nothing mounted on /media.')
	

def media_play():
	global dSettings
	global arMediaWithMusic
	print('[USB] Play (MPD)')

	#if dSettings['mediasource'] == -1:
	#	print('First go, doing a media check...')
	#	media_check()
	
	if arSourceAvailable[1] == 0:
		print('Aborting playback, trying next source.')
		source_next()
		source_play()
		#TODO: error sound
		
	else:

		print(' ... Emptying playlist')
		call(["mpc", "-q", "stop"])
		call(["mpc", "-q", "clear"])
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???

		sUsbLabel = os.path.basename(arMediaWithMusic[dSettings['mediasource']])
		dSettings['medialabel'] = sUsbLabel

		print(' ... Populating playlist, media: {0}'.format(sUsbLabel))
		mpc_populate_playlist(sUsbLabel)

		print(' ... Checking if playlist is populated')
		task = subprocess.Popen("mpc playlist | wc -l", shell=True, stdout=subprocess.PIPE)
		mpcOut = task.stdout.read()
		assert task.wait() == 0
		
		if mpcOut.rstrip('\n') == "0":
			print(' ... . Nothing in the playlist, marking source unavailable.')
			arSourceAvailable[1]=0
			source_next()
			source_play()
			#TODO: error sound
		else:
			print(' ... . Found {0:s} tracks'.format(mpcOut.rstrip('\n')))

			#TODO: get latest position..	
			# continue where left
			playslist_pos = mpc_lkp(sUsbLabel)

			print(' ... Starting playback')
			call(["mpc", "-q" , "stop"])
			call(["mpc", "-q" , "play", str(playslist_pos)])

			# Load playlist directories, to enable folder up/down browsing.
			mpc_get_PlaylistDirs()

def media_stop():
	print('[USB] Stop')
	call(["mpc", "-q" , "stop"])
	

# updates arSourceAvailable[2] (locmus)
def locmus_check():
	global arSourceAvailable
	global sLocalMusic
	print('[LOCMUS] CHECK availability...')

	try:
		if not os.listdir(sLocalMusic):
			print(" ... Local music directory is empty.")
			arSourceAvailable[2]=0
		else:
			print(" ... Local music directory present and has files.")
			arSourceAvailable[2]=1
	except:
		print(" ... Error checking for local music directory {0} ".format(sLocalMusic))
		arSourceAvailable[2]=0
		

def locmus_play():
	global sLocalMusicMPD
	global arSourceAvailable
	print('[LOCMUS] Play (MPD)')

	#TODO: no need to do it if we have just started
	print(' ... Checking if source is still good')
	locmus_check()
	
	if arSourceAvailable[2] == 0:
		print(' ......  Aborting playback, trying next source.') #TODO red color
		source_next()
		source_play()
		#TODO: error sound
		
	else:
		print(' ...... Emptying playlist')
		call(["mpc", "-q", "stop"])
		call(["mpc", "-q", "clear"])
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???

		# MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..
		print(' ...... Populating playlist')
		mpc_populate_playlist(sLocalMusicMPD)
	
		print(' ...... Checking if playlist is populated')
		playlistCount = mpc_playlist_is_populated()
		if playlistCount == "0":
			print(' ...... . Nothing in the playlist, trying to update database...')
			call(["mpc", "-q", "--wait", "update"])
			mpc_populate_playlist(sLocalMusicMPD)
			playlistCount = mpc_playlist_is_populated()
			if playlistCount == "0":
				print(' ...... . Nothing in the playlist, giving up. Marking source unavailable.')
				arSourceAvailable[2]=0
				source_next()
				source_play()
				#TODO: error sound
				return
			else:
				print(' ...... . Found {0:s} tracks'.format(playlistCount))
		else:
			print(' ...... . Found {0:s} tracks'.format(playlistCount))

		# continue where left
		playslist_pos = mpc_lkp('locmus')
		
		print('Starting playback')
		call(["mpc", "-q" , "stop"])
		call(["mpc", "-q" , "play", str(playslist_pos)])

		# double check if source is up-to-date
		
		print('Loading directory structure')
		mpc_get_PlaylistDirs()
		
def locmus_update():
	global dSettings
	global sLocalMusicMPD
	
	print('[LOCMUS] Updating local database [{0}]'.format(sLocalMusicMPD))

	#Update database
	mpc_update(sLocalMusicMPD)
	
	#IF we're already playing local music: Continue playing without interruption
	# and add new tracks to the playlist
	# Source 2 = locmus
	if dSettings['source'] == 2:
		print(' ......  source is already playing, trying seamless update...')
		# 1. "crop" playlist (remove everything, except playing track)
		call(["mpc", "-q" , "crop"])

		yMpdClient = MPDClient()
		yMpdClient.connect("localhost", 6600)
				
		# 2. songid is not unique, get the full filename
		current_song = yMpdClient.currentsong()
		curr_file = current_song['file']
		print(' ......  currently playing file: {0}'.format(curr_file))
		
		# 3. reload local music playlist
		mpc_populate_playlist(sLocalMusicMPD)
		
		# 4. find position of song that we are playing, skipping the first position (pos 0) in the playlist, because that's where the currently playing song is
		delpos = '0'
		for s in yMpdClient.playlistinfo('1:'):
			if s['file'] == curr_file:
				print(' ......  song found at position {0}'.format(s['pos']))
				delpos = s['pos']
		
		if delpos != '0':
			print(' ......  moving currently playing track back in place')
			yMpdClient.delete(delpos)
			yMpdClient.move(0,int(delpos)-1)
		else:
			print(' ......  ERROR: something went wrong')

		yMpdClient.close()
		
	#IF we were not playing local music: Try to switch to local music, but check if the source is OK.
	else:
		#We cannot check if there's any NEW tracks, but let's check if there's anything to play..
		locmus_check()
		# Source 2 = locmus
		if arSourceAvailable[2] == 1:
			dSettings['source'] = 2
			source_play()
		else:
			print('[LOCMUS] Update requested, but no music available for playing... Doing nothing.')

def locmus_stop():
	print('[LOCMUS] Stopping source: locmus. Saving playlist position and clearing playlist.')
	
	# save position and current file name for this drive
	mpc_save_pos_for_label( 'locmus' )
	
	# stop playback
	mpc_stop()
	#mpc $params_mpc -q stop
	#mpc $params_mpc -q clear	
	

def stream_check():
	global arSourceAvailable
	
	print('[STRM] Checking availability...')

	# Default to not available
	arSourceAvailable[5]=0
	
	# Test internet connection
	connected = internet()
	if not connected:
		print(' ....  Internet: FAIL')
		print(' ....  Marking source not available')
		return 1
	else:
		print(' ....  Internet: OK')

	# See if we have streaming URL's
	streams_file = sDirSave + "/streams.txt"
	if os.path.isfile(streams_file):
		print(' ....  Stream URL\'s: File found')
	else:
		print(' ....  Stream URL\'s: File not found')
		print(' ....  Marking source not available')
		return 1

	# Check if at least one stream is good
	print(' ....  Checking to see we have at least one valid stream')

	streams=open(streams_file,'r')
	for stream in streams:
		uri = stream.rstrip('\n')
		uri_OK = url_check(uri)
		if uri_OK:
			print(' ....  . Stream OK: {0}'.format(uri))
			arSourceAvailable[5]=1
			break
		else:
			print(' ....  . Stream FAIL: {0}'.format(uri))


def stream_play():
	print('[STRM] Play (MPD)')

	#TODO: no need to do it if we have just started
	print(' ....  Checking if source is still good')
	stream_check()

	if arSourceAvailable[5] == 0:
		print(' ....  Aborting playback, trying next source.') #TODO red color
		source_next()
		source_play()
		#TODO: error sound

	else:
		print(' .... Emptying playlist')
		call(["mpc", "-q", "stop"])
		call(["mpc", "-q", "clear"])
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???

		print(' .... Populating playlist')
		mpc_populate_playlist('streams')
		
		print(' .... Checking if playlist is populated')
		playlistCount = mpc_playlist_is_populated()
		if playlistCount == "0":
			print(' .... . Nothing in the playlist, aborting...')
			arSourceAvailable[5] = 0
			source_next()
			source_play()
			#TODO: error sound
			
		else:
			print(' .... . Found {0:s} tracks'.format(playlistCount))
			
		# continue where left
		playslist_pos = mpc_lkp('streams')
		
		print(' .... Starting playback')
		call(["mpc", "-q" , "play", str(playslist_pos)])

		# double check if source is up-to-date
		
def stream_stop():
	print('[STRM] Stopping source: stream. Saving playlist position and clearing playlist.')
	
	# save position and current file name for this drive
	mpc_save_pos_for_label( 'stream' )
	
	# stop playback
	mpc_stop()
	#mpc $params_mpc -q stop
	#mpc $params_mpc -q clear	


# updates arSourceAvailable
def source_check():
	global dSettings
	print('\033[96mCHECKING SOURCE AVAILABILITY\033[00m')

	# 0; fm
	fm_check()

	# 1; mpc, USB
	media_check()
	
	# 2; locmus, local music
	locmus_check()
	
	# 3; bt, bluetooth
	bt_check()
	
	# 4; alsa, play from aux jack
	linein_check()

	# 5; internet radio
	stream_check()
	
	# Display source availability.
	print('-- Summary ------------------------')
	print('Current source: {0:d}'.format(dSettings['source']))
	
	i = 0
	for source in arSource:
		if arSourceAvailable[i] == 1:
			print(' {0:d} {1:8}\033[92mavailable \033[00m'.format(i,source))
		else:
			print(' {0:d} {1:8}\033[91mnot available \033[00m'.format(i,source))
		i += 1
	
	print('-----------------------------------')

def source_next():
	global dSettings
	global arMediaWithMusic

	if sum(arSourceAvailable) == 0:
		# we can stop now, no sources are available
		print('[SOURCE] No available sources.')
		dSettings['source'] = -1
		return

	print('[SOURCE] Switching to next source...')
	
	# TODO: sources may have become (un)available -> check this!
	
	if dSettings['source'] == -1:
		#No current source, switch to the first available, starting at 0
		i = 0
		for source in arSource:		
			if arSourceAvailable[i] == 1:
				print('[SOURCE] Switching to {0:s}'.format(source))
				dSettings['source'] = i
				save_settings()
				break
			i += 1
			
		if dSettings['source'] == -1:
			print('No sources available!')

	else:
		#TODO; hier klopt iets niet
		i = dSettings['source']
		
		#start at beginning, if we're at the end of the list
		if dSettings['source'] == len(arSource)-1:
			i = 0
		else:
			#only advance to next source, if not USB (source=1) or not at last avaiable media
			if dSettings['source'] <> 1:
				#start at next source in line
				i = dSettings['source']+1
			elif dSettings['mediasource'] == -1:
				#should not be the case, just to cover, if so, move to the next source
				i = dSettings['source']+1
			elif dSettings['mediasource'] == len(arMediaWithMusic)-1:
				#we are we at the last media, looping media back to first, but advance to next source
				dSettings['mediasource'] = 0
				i = dSettings['source']+1
			elif dSettings['mediasource'] < len(arMediaWithMusic)-1:
				#more media sources left, move to the next. Do not advance to next source
				dSettings['mediasource'] = dSettings['mediasource']+1
				print('Staying with USB. Switching to {0}'.format(arMediaWithMusic[dSettings['mediasource']]))		
				# we can stop now, no need to switch to next source
				return
			else:
				print('ERROR switching source! FIX ME!')
		
		for source in arSource[i:]:
			print(source)
			if arSourceAvailable[i] == 1:
				print('Switching to {0:s}'.format(source))
				dSettings['source'] = i
				save_settings()
				break
			i += 1
		
		#if end of list reached, but no new source was found, then start again on the beginning of the list
		if i == len(arSource):
			i = 0
			for source in arSource[:dSettings['source']]:
				print(source)
				if arSourceAvailable[i] == 1:
					print('Switching to {0:s}'.format(source))
					dSettings['source'] = i
					save_settings()
					break
				i += 1

def source_play():
	global dSettings

	if dSettings['source'] == -1:
		print('[SOURCE] Cannot start playback, no source available.')
	else:
		print('[SOURCE] Start playback: {0:s}'.format(arSource[dSettings['source']]))
		if dSettings['source'] == 0 and arSourceAvailable[0] == 1:
			fm_play()
		elif dSettings['source'] == 1 and arSourceAvailable[1] == 1:
			media_play()
		elif dSettings['source'] == 2 and arSourceAvailable[2] == 1:
			locmus_play()
		elif dSettings['source'] == 3 and arSourceAvailable[3] == 1:
			#locmus_stop()
			# TODO: stop anything already playing!?
			bt_play()
		elif dSettings['source'] == 4 and arSourceAvailable[4] == 1:
			linein_play()
		elif dSettings['source'] == 5 and arSourceAvailable[5] == 1:
			stream_play()
		else:
			print('ERROR: Invalid source or no sources available')

def source_stop():
	global dSettings

	print('Stopping playback: {0:s}'.format(arSource[dSettings['source']]))
	if dSettings['source'] == 0:
		fm_stop()
	elif dSettings['source'] == 1:
		media_stop()
	elif dSettings['source'] == 2:
		locmus_stop()
	elif dSettings['source'] == 3:
		bt_stop()
	elif dSettings['source'] == 4:
		linein_stop()
	elif dSettings['source'] == 5:
		stream_stop()
	else:
		print('ERROR: Invalid source.')
		
def init():
	print('--------------------------------------------------------------------------------')
	print('Initializing ...')

	# initialize gpio (beep)
	print('Enabling GPIO output on pin 6 (beeper)')
	call(["gpio", "write", "6", "0"])
	call(["gpio", "mode", "6", "out"])

	# initialize ALSA
	alsa_init()

	# initialize PulseAudio
	pa_init()
	
	# initialize MPD client
	mpc_init()

	# initialize BT
	bt_init()
	
    # load previous state
	load_settings()

	# play startup sound
	#alsa_play_fx( 1 )
	pa_sfx('startup')

	# startup USB check
	# if a USB drive is connected before booting, it will not be captured by a UDisk event, manually checking..
	# also possible that music has been uploaded offline, so let's do a MPD DB update on the /media
	call(["mpc", "--wait", "update"])
	
	# check available sources
	source_check()
	
	if dSettings['source'] == -1 and sum(arSourceAvailable) > 0:
		#No current source, go to the first available
		source_next()
		# Start playback
		source_play()
	elif arSourceAvailable[dSettings['source']] == 0:
		#Saved source not available, go to the first available
		source_next()
		# Start playback
		source_play()
	else:
		# Source available
		source_play()
	
	print('\033[96mInitialization finished\033[00m')
	print('--------------------------------------------------------------------------------')
	beep()

	
#-------------------------------------------------------------------------------
# Main loop
print('Headunit v0.1 2017-10-28')
print('Checking if we\'re already runnning')
#me = singleton.SingleInstance() # will sys.exit(-1) if other instance is running # uncomment when tendo available
#with PIDFile("/var/run/pihu.pid"):
#	pass
		
DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()

# Initialize
init()

# Initialize a main loop
mainloop = gobject.MainLoop()
bus.add_signal_receiver(cb_remote_btn_press, dbus_interface = "com.arctura.remote")
bus.add_signal_receiver(cb_mpd_event, dbus_interface = "com.arctura.mpd")
bus.add_signal_receiver(cb_udisk_dev_add, signal_name='DeviceAdded', dbus_interface="org.freedesktop.UDisks")
bus.add_signal_receiver(cb_udisk_dev_rem, signal_name='DeviceRemoved', dbus_interface="org.freedesktop.UDisks")

mainloop.run()

