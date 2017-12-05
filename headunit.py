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
from pid import PidFile
from optparse import OptionParser

# Global variables
arSource = ['fm','media','locmus','bt','alsa'] # source types; add new sources in the end
arSourceAvailable = [0,0,0,0,0]              # corresponds to arSource; 1=available
arMediaWithMusic = []						 # list of mountpoints that contains music, according to MPD
iAtt = 0									 # Att mode toggle
iRandom = 0									 # We're keeping track of it within the script, not checking with MPD
iDoSave	= 0									 # Indicator to do a save anytime soon
dSettings = {'source': -1, 'volume': 20, 'mediasource': -1, 'medialabel': ''}	 # No need to save random, we don't want to save that (?)
sRootFolder = os.path.dirname(os.path.abspath(__file__))
bBeep = 0									 # Use hardware beep?

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
#TODO

#LOCAL MUSIC
#sLocalMusic="/media/local_music"		# symlink to /home/hu/music
sLocalMusic="/media/PIHU_DATA"
sLocalMusicMPD="local_music"			# directory from a MPD pov.

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
LOG_FILE = sRootFolder+"/blueagent5.log"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(module)s] %(message)s"

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
	call(["halt"])
	#call(["systemctl", "poweroff", "-i"])

# ********************************************************************************
# Remote control
#

def button_press ( func ):
	# Feedback beep
	if bBeep:
		beep()
	else:
		pa_sfx('button_feedback')

	pavol = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')
	
	# Handle button
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
		pavol.vol_up()
		#volume_up()
		return 0
	elif func == 'VOL_DOWN':
		print('\033[95m[BUTTON] VOL_DOWN\033[00m')
		pavol.vol_down()
		#volume_down()
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
	
# ********************************************************************************
# ALSA, using python-alsaaudio
#

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
#
def pa_init():
	print('[PULSE] Loading sound effects')
	call(["pactl","upload-sample","/root/defender-headunit/sfx/b1_66.wav", "b166"])

def pa_sfx(sfx):
	if sfx == 'button_feedback':
		call(["pactl", "play-sample", "b166", "alsa_output.platform-soc_sound.analog-stereo"])
	elif sfx == 'mpd_update_db':
		call(["pactl", "play-sample", "b166", "alsa_output.platform-soc_sound.analog-stereo"])
	
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
		alsa_set_volume( dSettings['volume'] )
		
	elif iAtt == 0:
		print('Setting att volume (25%)')
		# We're not saving this volume level, as it is temporary.
		# ATT will be reset by pressing ATT again, or changing the volume
		iAtt = 1
		alsa_set_volume( 25 )
		
	else:
		print('Uhmmm.. this shouldn\'t have happened')
		iAtt = 0

def volume_up():
	global dSettings
	global iAtt
	global iDoSave

	print('Volume up; +5%')
	volume_new = alsa_get_volume()+5
	alsa_set_volume(volume_new)
	#call(["amixer", "-q", "-c", "0", "set", "Master", "5+", "unmute"])
	dSettings['volume'] = volume_new

	# always reset Att. state at manual vol. change
	iAtt = 0

	# Save volume change
	#pipe = subprocess.check_output("amixer get Master | awk '$0~/%/{print $5}' | tr -d '[]%'", shell=True)
	#pipe = subprocess.check_output("amixer get Master | awk '$0~/%/{print $4}' | tr -d '[]%'", shell=True)
	#dSettings['volume'] = int(pipe.splitlines()[0]) #LEFT CHANNEL	
	
	# Delayed save
	#save_settings() #too slow
	iDoSave = 1

def volume_down():
	global dSettings
	global iAtt
	global iDoSave

	print('Volume down; 5%')
	volume_new = alsa_get_volume()-5
	alsa_set_volume(volume_new)
	dSettings['volume'] = volume_new
	
	# always reset Att. state at manual vol. change
	iAtt = 0
	
	# Delayed save
	iDoSave = 1
	
# ********************************************************************************
# Save & Load settings, using pickle
#

def save_settings():
	global dSettings
	print('[PICKLE] Saving settings')
	pickle.dump( dSettings, open( "headunit.p", "wb" ) )

def load_settings():
	global dSettings
	print('[PICKLE] Loading previous settings')

	try:
		dSettings = pickle.load( open( "headunit.p", "rb" ) )
	except:
		print('[PICKLE] Loading headunit.p failed. First run? - Creating headunit.p with default values.')
		#assume: fails because it's the first time and no settings saved yet? Setting default:
		pickle.dump( dSettings, open( "headunit.p", "wb" ) )

	# Apply settings:
	
	#VOLUME
	#check if the value is valid
	if dSettings['volume'] < 0 or dSettings['volume'] > 100:
		dSettings['volume'] = 40
		pickle.dump( dSettings, open( "headunit.p", "wb" ) )
		print('[PICKLE] No setting found, defaulting to 40%')
	# also don't restore a too low volume
	elif dSettings['volume'] < 30:
		print('[PICKLE] Volume too low, defaulting to 30%')
		dSettings['volume'] = 30
	else:
		print('[PICKLE] Volume: {0:d}%'.format(dSettings['volume']))
	alsa_set_volume( dSettings['volume'] )
	
	#SOURCE
	if dSettings['source'] < 0:
		print('[PICKLE] Source: not available')
	else:
		print('[PICKLE] Source: {0:s}'.format(arSource[dSettings['source']]))



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
	call(["mpc", "-q", "random", "off"])
	call(["mpc", "-q", "repeat", "on"])
	
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


def mpc_save_pos ( label ):

	print('[MPC] Saving playlist position for label {0}'.format(label))
	oMpdClient = MPDClient() 
	oMpdClient.timeout = 10                # network timeout in seconds (floats allowed), default: None
	oMpdClient.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
	oMpdClient.connect("localhost", 6600)  # connect to localhost:6600

	oMpdClient.command_list_ok_begin()
	oMpdClient.status()
	results = oMpdClient.command_list_end()

	# I find this a very stupid way ... i mean a dict in a list? really? anyway...
	for r in results:
			songid = r['songid']

	current_song_listdick = oMpdClient.playlistid(songid)
	oMpdClient.close()
	oMpdClient.disconnect()

	for f in current_song_listdick:
			current_file = f['file']
	
	print current_file
	pickle_file = sRootFolder + "/mp_" + label + ".p"
	pickle.dump( current_file, open( pickle_file, "wb" ) )

def mpc_lkp( label ):

	#default
	pos = 1
	
	pickle_file = sRootFolder + "/mp_" + label + ".p"
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

	return pos


def mpc_save_posX ( label ):
	global oMpdClient
	print('[MPC] Saving playlist position')

	# get current song
	try:
		oMpdClient.noidle()
	except:
		print('debug: idle not set')
		#can't we do this nicerly?
		
	oMpdClient.command_list_ok_begin()
	oMpdClient.status()
	results = oMpdClient.command_list_end()

	# I find this a very stupid way ... i mean a dict in a list? really? anyway...
	for r in results:
			songid = r['songid']

	current_song_listdick = oMpdClient.playlistid(songid)
	oMpdClient.send_idle() # continue idling

	for f in current_song_listdick:
			current_file = f['file']
	
	print current_file
	pickle_file = sRootFolder + "/mp_" + label + ".p"
	pickle.dump( current_file, open( pickle_file, "wb" ) )

def mpc_lkpX( label ):
	global oMpdClient
	
	#default
	pos = 1
	
	pickle_file = sRootFolder + "/mp_" + label + ".p"
	print('[MPC] Retrieving last known position from lkp file: {0:s}'.format(pickle_file))

	try:
		current_file = pickle.load( open( pickle_file, "rb" ) )
	except:
		print('[PICKLE] Loading {0:s} failed!'.format(pickle_file))
		return pos
	
	#otherwise continue:
	try:
		oMpdClient.noidle()
	except:
		print('debug: idle not set')
		#can't we do this nicerly?
		
	playlist = oMpdClient.playlistid()
	oMpdClient.send_idle() # continue idling

	for x in playlist:
			if x['file'] == current_file:
					pos = int(x['pos'])+1
					print('[MPC] Match found! Continuing playback at #{0}'.format(pos))

	return pos
	

def mpc_populate_playlist ( label ):
	p1 = subprocess.Popen(["mpc", "listall", label], stdout=subprocess.PIPE)
	p2 = subprocess.Popen(["mpc", "add"], stdin=p1.stdout, stdout=subprocess.PIPE)
	p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
	output,err = p2.communicate()

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
			#mountpoint = subprocess.check_output("mount | egrep media | cut -d ' ' -f 3", shell=True)
			sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
			
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

	print(' ... Checking if source is still good')
	locmus_check()
	
	if arSourceAvailable[2] == 0:
		print('Aborting playback, trying next source.') #TODO red color
		source_next()
		source_play()
		#TODO: error sound
		
	else:
		print(' ... Emptying playlist')
		call(["mpc", "-q", "stop"])
		call(["mpc", "-q", "clear"])
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???

		# MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..
		print(' ... Populating playlist')
		mpc_populate_playlist(sLocalMusicMPD)
	
		print(' ... Checking if playlist is populated')
		playlistCount = mpc_playlist_is_populated()
		if playlistCount == "0":
			print(' ... . Nothing in the playlist, trying to update database...')
			call(["mpc", "-q", "--wait", "update"])
			mpc_populate_playlist(sLocalMusicMPD)
			playlistCount = mpc_playlist_is_populated()
			if playlistCount == "0":
				print(' ... . Nothing in the playlist, giving up. Marking source unavailable.')
				arSourceAvailable[2]=0
				source_next()
				source_play()
				#TODO: error sound
				return
			else:
				print(' ... . Found {0:s} tracks'.format(playlistCount))
		else:
			print(' ... . Found {0:s} tracks'.format(playlistCount))

		# continue where left
		playslist_pos = mpc_lkp('locmus')
		
		print('Starting playback')
		call(["mpc", "-q" , "stop"])
		call(["mpc", "-q" , "play", str(playslist_pos)])
	
		print('Loading directory structure')
		mpc_get_PlaylistDirs()
		
def locmus_update():
	print('Updating local database')

	#Remember position and/or track in playlist
	#or.. also cool, start playing at the first next new track
	#TODO
	pa_sfx('mpd_update_db')
	
	#Update
	call(["mpc", "--wait", "update", sLocalMusicMPD])
	
	#Reload playlist
	locmus_play()

def locmus_stop():
	print('Stopping source: locmus. Saving playlist position and clearing playlist.')
	
	# save position and current file name for this drive
	mpc_save_pos( 'locmus' )
	
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
			locmus_stop()
			bt_play()
		elif dSettings['source'] == 4 and arSourceAvailable[4] == 1:
			linein_play()
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
	else:
		print('ERROR: Invalid source.')
		
def latesystemstuff():
	print('Starting less important system services')
	call(["", "write", "6", "0"])

# WORKS, but replaced by the python-mpd library
def OLD_mpc_save_pos ( label ):

	print('Saving playlist position')
	# save position and current file name for this drive
	mp_filename = sRootFolder + '/mp_' + label + '.txt'
	print mp_filename
	
	cmd1 = "mpc | sed -n 2p | grep -Po '(?<=#)[^/]*' > " + mp_filename
	cmd2 = "mpc -f %file% current >> " + mp_filename
	
	#subprocess.check_output("mpc | sed -n 2p | grep -Po '(?<=#)[^/]*' > /home/hu/mp_locmus.txt")
	#subprocess.check_output("mpc -f %file% current >> /home/hu/mp_locmus.txt")
	pipe1 = Popen(cmd1, shell=True, stdout=PIPE)
	pipe2 = Popen(cmd2, shell=True, stdout=PIPE)	
				
def OLD_mpc_lkp( lkp_file ):
	print('[MPC] Retrieving last known position from lkp file: {0:s}'.format(lkp_file))

	lkp=1 # Last Known Position
	lkf=""  # Last Known File

	# try to continue playing where left.
	# First line is the original position
	#bladiebla = "head -n1 /home/hu/mp_locmus.txt" #+lkp_file
	lkpOut = subprocess.check_output("head -n1 /home/hu/mp_locmus.txt", shell=True)
	
	lkp = int(lkpOut.splitlines()[0])
	#print lkpOut.splitlines()[0]

	# Second line is the file name
	#lkf=$(tail -n1 /home/hu/mp_locmus.txt)

	# Derive position from file name
	#lkp=$(mpc -f "%position% %file%" playlist | grep "$lkf" | cut -d' ' -f1)
	#TODO: only use this if it yields a result, otherwise use the lkp

	print('[MPC] Lookup found last known position: {0:d}'.format(lkp))
	return lkp

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
	alsa_play_fx( 1 )

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

DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()

# Initialize
init()

# Initialize a main loop
mainloop = gobject.MainLoop()
bus.add_signal_receiver(button_press, dbus_interface = "com.arctura.remote")
mainloop.run()

