# Python port, but without menu

import os
import time
import subprocess
from subprocess import call

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

#LOCAL MUSIC
sLocalMusic="/media/local_music"		# symlink to /home/hu/music
sLocalMusicMPD="local_music"			# directory from a MPD pov.

#MPC
arMpcPlaylistDirs = [ ]


def button_press ( func ):
	if func == 'SHUFFLE':
		print('Toggling shuffle')
		call(["mpc", "random"])
	elif func == 'SOURCE':
		print('Next source')
		source_next()
		source_play()
	elif func == 'ATT':
		print('ATT mode')
	elif func == 'TRACK_NEXT':
		print('Next track')
		call(["mpc", "next"])
	elif func == 'TRACK_PREV':
		print('Prev. track')
		call(["mpc", "prev"])
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


def mpc_get_PlaylistDirs():
	global arMpcPlaylistDirs
	dirname_current = ''
	dirname_prev = ''
	iPos = 0

	pipe = Popen('mpc -f %file% playlist', shell=True, stdout=PIPE)

	del arMpcPlaylistDirs

	for line in pipe.stdout:
		dirname_current=os.path.dirname(line.strip())
		t = iPos, dirname_current
		if dirname_prev != dirname_current:
			arMpcPlaylistDirs.append(t)
		dirname_prev = dirname_current
		iPos += 1


def mpc_next_folder():
	print('Next folder')
	print(arMpcPlaylistDirs[3])

	
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
	arSourceAvailable[3]=0 # not available
	#echo "Source 3 Unavailable; bluetooth"

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
		bt_play()
	elif iSource == 4:
		linein_play()
	else:
		print('ERROR: Invalid source.')
				
def init():
	print('Initializing ...')

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
		print('BUTTON01')
		#Bottom button
	elif BUTTON02_LO <= value_0 <= BUTTON02_HI:
		print('BUTTON02')
		#Side button, met streepje
	elif BUTTON03_LO <= value_0 <= BUTTON03_HI:
		print('BUTTON03')
		#VOL
	elif BUTTON04_LO <= value_0 <= BUTTON04_HI:
		print('BUTTON04')
		#VOL
	elif BUTTON05_LO <= value_0 <= BUTTON05_HI:
		print('BUTTON05')
		print(value_1)
		button_press('TRACK_NEXT')
		button_press('DIR_NEXT')
	elif BUTTON06_LO <= value_0 <= BUTTON06_HI:
		print('BUTTON06')
		print(value_1)
		button_press('TRACK_PREV')
		button_press('DIR_PREV')
	elif BUTTON07_LO <= value_0 <= BUTTON07_HI:
		print('BUTTON07')
		button_press('SHUFFLE')
	elif BUTTON08_LO <= value_0 <= BUTTON08_HI:
		print('BUTTON08')
		button_press('ATT')
	elif BUTTON09_LO <= value_0 <= BUTTON09_HI:
		print('BUTTON09')
		button_press('SOURCE')
	elif BUTTON10_LO <= value_0 <= BUTTON10_HI:
		print('BUTTON10')
		button_press('OFF')

	time.sleep(0.1)