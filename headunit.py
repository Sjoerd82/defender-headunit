#!/usr/bin/python

# Headunit, created to function as a car's headunit.
# Designed to be controlled by a Sony RM-X2S or RM-X4S resistor network style remote control.
# Music is played using MPD.
#
# Author: Sjoerd Venema
# License: MIT
# 
# Available sources:
# - Local music folder
# - Flash drive
# - FM radio
# - Bluetooth
# - Airplay (future plan)
# - Line-In (passive)
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
# - Only one USB drive at a time
# - Long/Short press buttons

import os
import time
import subprocess
from subprocess import call
from subprocess import Popen, PIPE
#from tendo import singleton -- not available in Buildroot, disabling for now
import pickle
import alsaaudio
from select import select

# python-mpd2 0.5.1 (not sure if this is the forked mpd2)
# used mainly for getting the current song for lookup on reload
from mpd import MPDClient

# Import the ADS1x15 module.
import Adafruit_ADS1x15

# Or create an ADS1015 ADC (12-bit) instance.
adc = Adafruit_ADS1x15.ADS1015()

# ADC remote variables
GAIN = 2/3
BUTTON01_LO = 180
BUTTON01_HI = 190
BUTTON02_LO = 220
BUTTON02_HI = 260
BUTTON03_LO = 310
BUTTON03_HI = 330
BUTTON04_LO = 380
BUTTON04_HI = 410
BUTTON05_LO = 460
BUTTON05_HI = 490
BUTTON06_LO = 560
BUTTON06_HI = 580
BUTTON07_LO = 640
BUTTON07_HI = 670
BUTTON08_LO = 740
BUTTON08_HI = 770
BUTTON09_LO = 890
BUTTON09_HI = 910
BUTTON10_LO = 1050
BUTTON10_HI = 1100

# Global variables
#arSource = ['fm','usb','locmus','bt','alsa'] # source types; add new sources in the end --> renamed usb to media
arSource = ['fm','media','locmus','bt','alsa'] # source types; add new sources in the end
arSourceAvailable = [0,0,0,0,0]              # corresponds to arSource; 1=available
arMedia = []								 # list of mountpoints on /media
arMediaWithMusic = []						 # list of mountpoints that contains music, according to MPD
iAtt = 0									 # Att mode toggle
iRandom = 0									 # We're keeping track of it within the script, not checking with MPD
iDoSave	= 0									 # Indicator to do a save anytime soon
sUsbLabel = ''
dSettings = {'source': -1, 'volume': 20, 'mediasource': -1}	 # No need to save random, we don't want to save that (?)

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

#LOCAL MUSIC
sLocalMusic="/media/local_music"		# symlink to /home/hu/music
sLocalMusicMPD="local_music"			# directory from a MPD pov.

#MPD-client (MPC)
oMpdClient = None
arMpcPlaylistDirs = [ ]
iMPC_OK = 0

def beep():
	call(["gpio", "write", "6", "1"])
	time.sleep(0.05)
	call(["gpio", "write", "6", "0"])

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

	if oAlsaMixer is None:
		print("ALSA mixer unavailable")
		volumes = 0
	else:
		volumes = oAlsaMixer.getvolume()
		for i in range(len(volumes)):
			print("Channel {0:d} volume: {1:d}%".format(i,volumes[i]))

		#We're keeping L&R in sync, so just return the first channel.
		
	return volumes[0]
	
def alsa_set_volume( volume ):
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

# ********************************************************************************
# Remote control
#
def button_press ( func ):
	# Feedback beep
	beep()

	# Handle button
	if func == 'SHUFFLE':
		print('Shuffle')
		mpc_random()
	elif func == 'SOURCE':
		print('Next source')
		source_next()
		source_play()
	elif func == 'ATT':
		print('ATT')
		volume_att_toggle()
	elif func == 'VOL_UP':
		print('VOL_UP')
		volume_up()
	elif func == 'VOL_DOWN':
		print('VOL_DOWN')
		volume_down()
	elif func == 'SEEK_NEXT':
		print('Seek/Next')
		seek_next()
	elif func == 'SEEK_PREV':
		print('Seek/Prev.')
		seek_prev()
	elif func == 'DIR_NEXT':
		print('Next directory')
		mpc_next_folder()		
	elif func == 'DIR_PREV':
		print('Prev directory')
		mpc_prev_folder()
	elif func == 'UPDATE_LOCAL':
		print('Updating local MPD database')
		locmus_update()
	elif func == 'OFF':
		print('Shutting down')
		save_settings()
		call(["systemctl", "poweroff", "-i"])

	# Wait until button is released
	""" why did we do this again??
	value_0 = adc.read_adc(0)
	press_count = 0
	while value_0 > 600:
		value_0 = adc.read_adc(0)
		time.sleep(0.1)
		press_count+=1
		if func == 'TRACK_NEXT' and press_count == 10:
			break
		elif func == 'TRACK_PREV'  and press_count == 10:
			break
	"""


def seek_next():
	global dSettings
	if dSettings['source'] == 1 or dSettings['source'] == 2:
		mpc_next_track()
	#elif source == then
	#fm_next ofzoiets

def seek_prev():
	global dSettings
	if dSettings['source'] == 1 or dSettings['source'] == 2:
		mpc_prev_track()

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
	#TODO: handle usb/locmus
	mpc_save_pos( 'locmus' )

	
def mpc_prev_track():
	print('Prev. track')
	call(["mpc", "prev"])
	#TODO: handle usb/locmus
	mpc_save_pos( 'locmus' )


def mpc_next_folder():
	print('Next folder')
	call(["mpc", "play", str(mpc_next_folder_pos())])
	#TODO: handle usb/locmus
	mpc_save_pos( 'locmus' )

def mpc_prev_folder():
	print('Prev folder')
	call(["mpc", "play", str(mpc_prev_folder_pos())])
	#TODO: handle usb/locmus
	mpc_save_pos( 'locmus' )
	
def mpc_stop():
	print('Stopping MPC [pause]')
	call(["mpc", "pause"])

def mpc_save_pos ( label ):
	global oMpdClient
	print('[MPC] Saving playlist position')

	#TODO : REFINE THIS -- I THINK IT GETS EXECUTED SOMETIMES WITHOUT A PLAYLIST LOADED -- WHICH FAILS...
	try:
		# get current song
		#mpc_init()
		oMpdClient.command_list_ok_begin()
		oMpdClient.status()
		results = oMpdClient.command_list_end()

		# I find this a very stupid way ... i mean a dict in a list? really? anyway...
		for r in results:
				songid = r['songid']

		current_song_listdick = oMpdClient.playlistid(songid)
		for f in current_song_listdick:
				current_file = f['file']
		
		pickle_file = "/home/hu/mp_" + label + ".p"
		pickle.dump( current_file, open( pickle_file, "wb" ) )
	except:
		print('DEBUG -- FIX ME')

def mpc_lkp( label ):
	global oMpdClient
	
	#default
	pos = 1
	
	pickle_file = "/home/hu/mp_" + label + ".p"
	print('[MPC] Retrieving last known position from lkp file: {0:s}'.format(pickle_file))

	try:
		current_file = pickle.load( open( pickle_file, "rb" ) )
	except:
		print('[PICKLE] Loading {0:s} failed!'.format(pickle_file))
		return pos
	
	playlist = oMpdClient.playlistid()

	for x in playlist:
			if x['file'] == current_file:
					pos = int(x['pos'])+1

	return pos
	
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
	
# updates arSourceAvailable[3] (bt) -- TODO
def bt_check():
	print('[BT] CHECK availability... not available.')
	arSourceAvailable[3]=0 # NOT Available
	#TODO: How to check???? When to decide it's avaiable?

def bt_play():
	print('Start playing Bluetooth...')
	#TODO
	
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
	global sUsbLabel
	global arMedia
	global arMediaWithMusic
	
	print('[USB] CHECK availability...')

	print(' ... Check if anything is mounted on /media...')
	arSourceAvailable[1]=1 # Available, unless:
	
	# Check if there's anything mounted:
	#try:
	#	#grepOut = subprocess.check_output("mount | grep -q /media", shell=True)
	#	proc = subprocess.Popen("mount | grep /media | cut -d' ' -f1",stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	#	for x in proc.stdout:
	#		print x
	#except subprocess.CalledProcessError as grepexc:                                                                                                   
	#	arSourceAvailable[1]=0
	
	try:
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
		#i = 0
		for mountpoint in arMedia:	
			#mountpoint = subprocess.check_output("mount | egrep media | cut -d ' ' -f 3", shell=True)
			sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
			#print(' ... . label of this filesystem: {0:s}'.format(sUsbLabel))
			
			taskcmd = "mpc listall "+sUsbLabel+" | wc -l"
			#taskcmd = "mpc listall SJOERD | wc -l"
			task = subprocess.Popen(taskcmd, shell=True, stdout=subprocess.PIPE)
			mpcOut = task.stdout.read()
			assert task.wait() == 0
			
			if mpcOut == 0:
				print(' ... . {0}: nothing in the database for this source.'.format(sUsbLabel))
				arSourceAvailable[1]=0
			else:
				print(' ... . {0}: found {1:s} tracks'.format(sUsbLabel,mpcOut.rstrip('\n')))		
				arMediaWithMusic.append(mountpoint)
				#i += 1

	else:
		print(' ... nothing mounted on /media.')
	

def media_play():
	global dSettings
	global arMediaWithMusic
	print('[USB] Play (MPD)')

	if dSettings['mediasource'] = -1:
		print('First go, doing a media check...')
		media_check()
	
	if arSourceAvailable[1] == 0:
		print('Aborting playback, trying next source.')
		source_next()
		source_play()
		#TODO: error sound
		
	else:

		print('Emptying playlist')
		call(["mpc", "stop"])
		call(["mpc", "clear"])
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???

		sUsbLabel = os.path.basename(arMediaWithMusic[dSettings['mediasource']])
		print sUsbLabel
		
		print('Populating playlist')
		p1 = subprocess.Popen(["mpc", "listall", sUsbLabel], stdout=subprocess.PIPE)
		p2 = subprocess.Popen(["mpc", "add"], stdin=p1.stdout, stdout=subprocess.PIPE)
		p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
		output,err = p2.communicate()

		print('Checking playlist')
		task = subprocess.Popen("mpc playlist | wc -l", shell=True, stdout=subprocess.PIPE)
		mpcOut = task.stdout.read()
		assert task.wait() == 0
		
		if mpcOut == 0:
			print('Nothing in the playlist, marking source unavailable.')
			arSourceAvailable[1]=0
			source_next()
			source_play()
			#TODO: error sound
		else:
			print('Found {0:s} tracks'.format(mpcOut))
			#TODO: remove the trailing line feed..

			#TODO: get latest position..	
			print('Starting playback')
			call(["mpc", "-q" , "stop"])
			#mpc $params_mpc -q play $lkp
			call(["mpc", "-q" , "play"])

			print('Loading directory structure')
			mpc_get_PlaylistDirs()

def media_stop():
	print('[USB] Stop')

# updates arSourceAvailable[2] (locmus)
def locmus_check():

	print('[LOCMUS] CHECK availability...')

	# THIS WILL FAIL IF DIRECTORY IS NOT PRESENT
	# TODO: CHECK FOR PRESENCE..
	
	if not os.listdir(sLocalMusic):
		print(" ... Local music directory is empty.")
		arSourceAvailable[2]=0
	else:
		print(" ... Local music directory present and has files.")
		arSourceAvailable[2]=1


def locmus_play():
	print('[PLAY] LOCAL (MPD)')

	print('Checking if source is still good')
	locmus_check()
	
	if arSourceAvailable[2] == 0:
		print('Aborting playback, trying next source.')
		source_next()
		source_play()
		#TODO: error sound
		
	else:
		# mpc --wait $params_mpc update $sLocalMusicMPD # <<<< -----  do this outside of this script using inotifywait ....
		print('Emptying playlist')
		call(["mpc", "stop"])
		call(["mpc", "clear"])
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???

		print('Populating playlist')
		p1 = subprocess.Popen(["mpc", "listall", sLocalMusicMPD], stdout=subprocess.PIPE)
		p2 = subprocess.Popen(["mpc", "add"], stdin=p1.stdout, stdout=subprocess.PIPE)
		p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
		output,err = p2.communicate()

		print('Checking playlist')
		task = subprocess.Popen("mpc playlist | wc -l", shell=True, stdout=subprocess.PIPE)
		mpcOut = task.stdout.read()
		assert task.wait() == 0
		
		if mpcOut == 0:
			print('Nothing in the playlist, marking source unavailable.')
			arSourceAvailable[2]=0
			source_next()
			source_play()
			#TODO: error sound
		else:
			print('Found {0:s} tracks'.format(mpcOut))
			#TODO: remove the trailing line feed..

			#Get last known position
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
	
	print('Switching to next source')
	
	# TODO: sources may have become (un)available -> check this!
	
	if dSettings['source'] == -1:
		#No current source, switch to the first available, starting at 0
		i = 0
		for source in arSource:		
			if arSourceAvailable[i] == 1:
				print('Switching to {0:s}'.format(source))
				dSettings['source'] = i
				save_settings()
				break
			i += 1
			
		if dSettings['source'] == -1:
			print('No sources available!')

	else:
	
		#start at beginning, if we're at the end of the list
		if dSettings['source'] == len(arSource)-1:
			i = 0
		else:
			#only advance to next source, if not USB (source=1) or not at last avaiable media
			if dSettings['source'] <> 1:
				#start at next source in line
				i = dSettings['source']+1
			elif dSettings['mediasource'] == -1
				#should not be the case, just to cover, if so, move to the next source
				i = dSettings['source']+1
			elif dSettings['mediasource'] == len(arMediaWithMusic)-1
				#are we at the last media?
				i = dSettings['source']+1
			elif dSettings['mediasource'] < len(arMediaWithMusic)-1
				#should be covered by all of the above, but just in case
				#stay within USB source, by move to next media
				print('Switching to next media')
				dSettings['mediasource'] = dSettings['mediasource']+1
				media_play()
			else
				print('ERROR switching source! Hier hadden we geen rekening mee gehouden...!? FIX ME')
				
		
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

	print('Start playback: {0:s}'.format(arSource[dSettings['source']]))
	if dSettings['source'] == 0:
		fm_play()
	elif dSettings['source'] == 1:
		media_play()
	elif dSettings['source'] == 2:
		locmus_play()
	elif dSettings['source'] == 3:
		locmus_stop()
		bt_play()
	elif dSettings['source'] == 4:
		linein_play()
	else:
		print('ERROR: Invalid source.')

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
	mp_filename = '/home/hu/mp_' + label + '.txt'
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
	print('Initializing ...')

	# initialize gpio (beep)
	print('Enabling GPIO output on pin 6 (beeper)')
	call(["gpio", "write", "6", "0"])
	call(["gpio", "mode", "6", "out"])

	# initialize ALSA
	alsa_init()

	# initialize MPD client
	mpc_init()
	
    # load previous state
    #source /home/hu/hu_settings.sh
	load_settings()

	# play startup sound
	alsa_play_fx( 1 )

	# check available sources
	source_check()
	
	if dSettings['source'] == -1:
		#No current source, go to the first available
		source_next()
	elif arSourceAvailable[dSettings['source']] == 0:
		#Saved source not available, go to the first available
		source_next()
	
	# Start playback
	source_play()
	
	print('Initialization finished')
	beep()
	
#-------------------------------------------------------------------------------
# Main loop
print('Checking if we\'re already runnning')
#me = singleton.SingleInstance() # will sys.exit(-1) if other instance is running # uncomment when tendo available

# Initialize
init()

# Loop
iLoopCounter = 0
while True:
	# Read channel 0
	value_0 = adc.read_adc(0, gain=GAIN)
	value_1 = adc.read_adc(1, gain=GAIN)
	#print(value_0)

	if BUTTON01_LO <= value_0 <= BUTTON01_HI:
		#Bottom button
		print('BUTTON01')
		button_press('UPDATE_LOCAL')

	elif BUTTON02_LO <= value_0 <= BUTTON02_HI:
		#Side button, met streepje
		print('BUTTON02')

	elif BUTTON03_LO <= value_0 <= BUTTON03_HI:
		button_press('VOL_UP')
		
	elif BUTTON04_LO <= value_0 <= BUTTON04_HI:
		button_press('VOL_DOWN')
		
	elif BUTTON05_LO <= value_0 <= BUTTON05_HI:
		if value_1 < 300:
			button_press('SEEK_NEXT')
		else:
			button_press('DIR_NEXT')

	elif BUTTON06_LO <= value_0 <= BUTTON06_HI:
		if value_1 < 300:
			button_press('SEEK_PREV')
		else:
			button_press('DIR_PREV')

	elif BUTTON07_LO <= value_0 <= BUTTON07_HI:
		button_press('SHUFFLE')

	elif BUTTON08_LO <= value_0 <= BUTTON08_HI:
		button_press('ATT')

	elif BUTTON09_LO <= value_0 <= BUTTON09_HI:
		button_press('SOURCE')

	elif BUTTON10_LO <= value_0 <= BUTTON10_HI:
		button_press('OFF')

	# Check if there's a change in settings that we want to save.
	if iLoopCounter % 100 == 0  and iDoSave == 1:
		iDoSave = 0
		save_settings()

	# In case of a dirty exit, we want to be able to continue close to where we left before crashing
	# Every x seconds, check where we're at in the playlist and save it to disk
	if dSettings['source'] == 1 and iLoopCounter %5000 == 0:
		mpc_save_pos(sUsbLabel)

	if dSettings['source'] == 2 and iLoopCounter %5000 == 0:
		mpc_save_pos('locmus')
	
	# Check for mpd database update (this message is sent AFTER the update) -- for new music over SMB
	# TODO
	
	# Check for /media inserts or removals
	
	canRead = select([oMpdClient], [], [], 0)[0]
	if canRead:
		mpdChanges = oMpdClient.fetch_idle()
		
		for c in mpdChanges:
			print('[MPD] {0}'.format(c))
			if c == 'message':
				mpdMessages = oMpdClient.readmessages()
				for m in mpdMessages:
					print('[MPD] Channel {0} sends message: {1}'.format(m['channel'],m['message']))
					if m['channel'] == 'media_ready':
						source_stop()
						# switch to source: USB
						# TODO: check availability, but this is a bit redundant...
						dSettings['source'] = 1
						source_play()
					elif m['channel'] == 'media_removed':
						print 'TODO'
						#if source = 1 source_stop()
						# switch to next source

		oMpdClient.send_idle() # continue idling
	
	# Tenzij local music... (misschien ook USB uitsluiten?)
	# Check if MPD database has changed
	# if database has changed, then start playing that specific root folder
	# root folder can either be local_music or a usb drive. What if we're already playing that folder?
	# ALWAYS wait until database update has finished
	
	time.sleep(0.1)
	iLoopCounter += 1