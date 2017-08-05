# Python port

from pynput import keyboard


# Global variables
arSource = ['fm','mpc','locmus','bt','alsa'] # source types; add new sources in the end
arSourceAvailable = [0,0,0,0,0]              # corresponds to arSource; 1=available
iSource =-1                        			 # active source, -1 = none

# Keyboard listener
def on_release(key):
    print('{0} released'.format(
        key))
    if key == keyboard.Key.esc:
        # Stop listener
        return False

def source_check:
	print('Checking sources')

def init:
	print('Initializing ...')

	# play startup sound
	#alsa_play_fx 1

    # load previous state
    #source /home/hu/hu_settings.sh

	# check available sources
	source_check

	# initialize sources
	#bt_init
	#mpc_init
	#get_state
	#source_play

	#not the best place...
	#mpc_get_PlaylistDirs

	# Play/Pause button may not be implemented on control panel,
	# therefore, always try to play if a source becomes avaiable.

	# turn on remote control
	#if [[ $(ps -ef | grep "python ads1x15_remote.py" | wc -l)  < 2 ]]; then
	#	echo "Starting ADS1x15 remote"
	#	python ads1x15_remote.py &
	#else
	#	echo "ADS1x15 remote already running"
	#fi
	
	print('Initialization finished')

	
# Main loop
while True:
	# display menu
	print('Current source : ${arSource[$iSource]}')
	print('---------------------------------')
	print('1. Next Source')
	print('2. Play / Pause')
	print('3. Next track (USB) / station (Radio)')
	print('4. Prev track (USB) / station (Radio)')
	print('5. Volume up')
	print('6. Volume down')
	print('7. Prev Folder (USB)')
	print('8. Next Folder (USB)')
	print('9. Mode: Shuffle (all) / Normal')
	print('0. Exit')
	print('DEBUG OPTIONS:')
	print('C. check_source')
	print('---------------------------------')

	# Collect events until released
	with keyboard.Listener(
        on_release=on_release) as listener:
    listener.join()
	

