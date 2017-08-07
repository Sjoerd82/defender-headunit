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

import os
import time
import subprocess
from subprocess import call
from subprocess import Popen, PIPE

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
arSource = ['fm','usb','locmus','bt','alsa'] # source types; add new sources in the end
arSourceAvailable = [0,0,0,0,0]              # corresponds to arSource; 1=available
iSource = -1                        	  	 	# active source, -1 = none

#ALSA
iVolume = 50
sAlsaMixer = "Master"
iAlsaMixerStep=1000
params_amixer="-q" #-c card -D device, etc.


#LOCAL MUSIC
sLocalMusic="/media/local_music"		# symlink to /home/hu/music
sLocalMusicMPD="local_music"			# directory from a MPD pov.

#MPC
arMpcPlaylistDirs = [ ]

def check_already_running():
	print('Checking if we\'re already runnning')

	# pgrep exit status:
	#
    #   0      One or more processes matched the criteria.
    #   1      No processes matched.
    #   2      Syntax error in the command line.
    #   3      Fatal error: out of memory etc.
	#
	# If the exit code is non-zero it raises a CalledProcessError.

	# grep exit status:
    #   The exit status is 0 if selected lines are found, and 1 if not found.  If an error occurred the exit status is 2.
	# (Note: POSIX error handling code should check for '2' or greater.)
	
	#p1 = subprocess.Popen(["pgrep", "-a", "python"], stdout=subprocess.PIPE)
	#p2 = subprocess.Popen(["grep", "headunit.py"], stdin=p1.stdout, stdout=subprocess.PIPE)
	#p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
	#output,err = p2.communicate()

	#print('DEBUG')
	#print(p1.returncode)
	#print(p2.returncode)
	
	#if p2.returncode == 0:
		#print('already running... aborting')
		#exit()
	
	#try:
	#	grepOut = subprocess.check_output("pgrep -a python | grep headunit.py", shell=True)
	#except subprocess.CalledProcessError as grepexc:                                                                                                   
	#	print('already running... aborting')

	grepOut = subprocess.check_output("pgrep -a python | grep headunit.py", shell=True)
	print(subprocess.CalledProcessError)

def button_press ( func ):
	if func == 'SHUFFLE':
		print('Toggling shuffle')
		call(["mpc", "random"])
	elif func == 'SOURCE':
		print('Next source')
		source_next()
		source_play()
	elif func == 'ATT':
		print('ATT')
		volume_set(20)
	elif func == 'VOL_UP':
		print('VOL_UP')
		volume_up(1000)
	elif func == 'VOL_DOWN':
		print('VOL_DOWN')
		volume_down(1000)
	elif func == 'TRACK_NEXT':
		print('Next track')
		call(["mpc", "next"])
	elif func == 'TRACK_PREV':
		print('Prev. track')
		call(["mpc", "prev"])
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
		#todo: save state
		call(["systemctl", "poweroff", "-i"])

	# Feedback beep
	call(["gpio", "write", "6", "1"])
	time.sleep(0.05)
	call(["gpio", "write", "6", "0"])

	# Wait until button is released

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

def alsa_play_fx( fx ):
	print('Playing effect')
	#TODO

def volume_set( percentage ):
	print('Setting volume')
	call(["amixer", "-q", "-c", "0", "set", "Master", "20%", "unmute"])

def volume_up( step ):
	print('Volume up')
	call(["amixer", "-q", "-c", "0", "set", "Master", "5+", "unmute"])


def volume_down( step ):
	print('Volume down')
	call(["amixer", "-q", "-c", "0", "set", "Master", "5-", "unmute"])

	
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

	#DEBUG
	#for x in arMpcPlaylistDirs:
	#	print x

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

	
def mpc_next_folder():
	print('Next folder')
	call(["mpc", "play", str(mpc_next_folder_pos())])

def mpc_prev_folder():
	print('Prev folder')
	call(["mpc", "play", str(mpc_prev_folder_pos())])
	
def mpc_stop():
	print('Stopping MPC [pause]')
	call(["mpc", "pause"])

# updates arSourceAvailable[0] (fm) --- TODO
def fm_check():
	print('Checking if FM is available')
	arSourceAvailable[0]=0 # not available
	#echo "Source 0 Unavailable; FM"

def fm_play():
	print('Start playing FM radio...')
	#TODO
	
# updates arSourceAvailable[3] (bt) -- TODO
def bt_check():
	print('Checking if Bluetooth is available')
	arSourceAvailable[3]=1 # Available
	#TODO: How to check???? When to decide it's avaiable?

def bt_play():
	print('Start playing Bluetooth...')
	#TODO
	
# updates arSourceAvailable[4] (alsa) -- TODO
def linein_check():
	print('Checking if Line-In is available')
	arSourceAvailable[4]=0 # not available
	#echo "Source 4 Unavailable; Line-In / ALSA"

def linein_play():
	print('Start playing from line-in...')
	#TODO

# updates arSourceAvailable[1] (mpc)
def usb_check():
	print('Checking if USB is available')

	print('  Check if anything is mounted on /media...')
	arSourceAvailable[1]=1 # Available, unless:
	
	# Check if there's anything mounted:
	try:
		grepOut = subprocess.check_output("mount | grep -q /media", shell=True)
	except subprocess.CalledProcessError as grepexc:                                                                                                   
		arSourceAvailable[1]=0

	# playlist loading is handled by scripts that trigger on mount/removing of media
	# mpd database is updated on mount by same script.
	# So, let's check if there's anything in the database for this source:
	
	if arSourceAvailable[1] == 1:
		print('  Media is mounted. Continuing to check if there''s music...')	
		task = subprocess.Popen("mpc listall SJOERD | wc -l", shell=True, stdout=subprocess.PIPE)
		mpcOut = task.stdout.read()
		assert task.wait() == 0
		
		if mpcOut == 0:
			print('  Nothing in the database for this source.')
			arSourceAvailable[1]=0
		else:
			print('  Found {0:s} tracks'.format(mpcOut))
			#TODO: remove the trailing line feed..
	else:
		print('  Nothing mounted on /media.')
	

def usb_play():
	print('[PLAY] USB (MPD)')

	print('Checking if source is still good')
	usb_check()
	
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

		print('Populating playlist')
		p1 = subprocess.Popen(["mpc", "listall", "SJOERD"], stdout=subprocess.PIPE)
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


# updates arSourceAvailable[2] (locmus)
def locmus_check():

	# THIS WILL FAIL IF DIRECTORY IS NOT PRESENT
	# TODO: CHECK FOR PRESENCE..
	
	if not os.listdir(sLocalMusic):
		print("Local music directory is empty.")
		arSourceAvailable[2]=0
	else:
		print("Local music directory present and has files.")
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

			#TODO: get latest position..	
			print('Starting playback')
			call(["mpc", "-q" , "stop"])
			#mpc $params_mpc -q play $lkp
			call(["mpc", "-q" , "play"])
		
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
	
		
# updates arSourceAvailable
def source_updateAvailable():

	# 0; fm
	fm_check()

	# 1; mpc, USB
	usb_check()
	
	# 2; locmus, local music
	locmus_check()
	
	# 3; bt, bluetooth
	bt_check()
	
	# 4; alsa, play from aux jack
	linein_check()

	# Display source availability.
	print('---------------------------------')
	print('Current source: {0:d}'.format(iSource))
	
	i = 0
	for source in arSource:
		print(source)
		if arSourceAvailable[i] == 1:
			print(' ...Available')
		else:
			print(' ...Not available')
		i += 1
	
	print('---------------------------------')

def source_check():
	print('Checking sources')
	source_updateAvailable()

def source_next():
	global iSource
	
	print('Switching to next source')
	
	# TODO: sources may have become (un)available -> check this!
	
	if iSource == -1:
		#No current source, switch to the first available, starting at 0
		i = 0
		for source in arSource:		
			if arSourceAvailable[i] == 1:
				print('Switching to {0:s}'.format(source))
				iSource = i
				break
			i += 1
			
		if iSource == -1:
			print('No sources available!')

	else:
	
		#start at beginning, if we're at the end of the list
		if iSource == len(arSource)-1:
			i = 0
		else:
			#start at next source in line
			i = iSource+1
		
		for source in arSource[i:]:
			print(source)
			if arSourceAvailable[i] == 1:
				print('Switching to {0:s}'.format(source))
				iSource = i
				break
			i += 1
		
		#if end of list reached, but no new source was found, then start again on the beginning of the list
		print (i)
		print (len(arSource))
		if i == len(arSource):
			i = 0
			for source in arSource[:iSource]:
				print(source)
				if arSourceAvailable[i] == 1:
					print('Switching to {0:s}'.format(source))
					iSource = i
					break
				i += 1

def source_play():
	print('Start playback: {0:s}'.format(arSource[iSource]))
	if iSource == 0:
		fm_play()
	elif iSource == 1:
		usb_play()
	elif iSource == 2:
		locmus_play()
	elif iSource == 3:
		mpc_stop()
		bt_play()
	elif iSource == 4:
		linein_play()
	else:
		print('ERROR: Invalid source.')
				
def init():
	print('Initializing ...')

	check_already_running()
	
	# set volume
	volume_set( 60 )
	
	# play startup sound
	alsa_play_fx( 1 )

    # load previous state
    #source /home/hu/hu_settings.sh

	# check available sources
	source_check()
	source_next()
	source_play()

	# initialize sources
	#bt_init
	#mpc_init
	#get_state
	#source_play

	#not the best place...
	#mpc_get_PlaylistDirs

	# Play/Pause button may not be implemented on control panel,
	# therefore, always try to play if a source becomes avaiable.
	
	print('Initialization finished')

	
# Main loop
init()
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
			button_press('TRACK_NEXT')
		else:
			button_press('DIR_NEXT')

	elif BUTTON06_LO <= value_0 <= BUTTON06_HI:
		if value_1 < 300:
			button_press('TRACK_PREV')
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

	time.sleep(0.1)