#!/bin/bash
# ---------------------------------------------------------------------------
#
# This script does not mount the USB drive, this should be handled outside of
# the script.

# Script starts with init(), see bottom of the script.

# capture CTRL+C, CTRL+Z and quit singles using the trap
trap '' SIGINT
trap '' SIGQUIT
trap '' SIGTSTP

screen -X multiuser on
screen -X acladd pi

typeset -a arSource=(fm mpc bt alsa)
typeset -a arSourceAvailable=(1 1 1 1)
typeset -i iSourceArrayLen=3
typeset -i iSource=-1
#USB
typeset -r sMountPoint="/media/usb"
#typeset sMpcDir="/"
typeset -a arDirStruct
typeset -i iDirectory=0
typeset -i iDirectoryArrayLen
typeset -a arDirStartPos
#ALSA
typeset -i iVolume=50
typeset params_amixer="" #-c card -D device, etc.
#MPC
typeset params_mpc="" #--host 172.16.8.138"
typeset -i bRandom=0
#typeset music_ext="( -iname *.mp3 -o -iname *.ogg )"
typeset -a arMpcPlaylist
typeset -a arMpcPlaylistDirs
typeset -i iMpcPos
typeset sMpcRepeat="off"
typeset sMpcRandom="off"

#FM
typeset -a arStations
typeset -i iFMStation=0
typeset params_fm=""
typeset -i bPlayingFM=0
typeset -i bPlaying=0
typeset -i bUSBMounted=0


alsa_debug(){
        echo "Displaying ALSA details:"
	#speaker-test
	aplay -l
	#maybe some more usefull stuff..
}

# Pass the effect ID as parameter
alsa_play_fx(){
        echo "Playing effect"

        case $1 in
        0) aplay -vv welcome.wav;;
        1) aplay beep-3.wav;;
        *) echo "Unknown FX";;
        esac
}

check_mount_usb(){
	#USB is auto-mounted
	echo "Check if USB drive is mounted"
	#todo

	if mount | grep $sMountPoint0 > /dev/null; then
		echo "USB drive seems to be mounted."
		bUSBMounted=1
	else
		echo "No USB drive mounted."
		bUSBMounted=0
		return 1
	fi

	#Get UUID
	blkid -o value $sMountPoint

	return 0
}

settings_write() {
	echo "Writing settings"
	echo "#!/bin/bash" > /home/hu/hu_settings.sh
	echo iSource=$iSource >> /home/hu/hu_settings.sh
	echo sMpcRepeat=$sMpcRepeat >> /home/hu/hu_settings.sh
	#echo "mpc \$params_mpc repeat off" >> /home/hu/hu_settings.sh
	echo sMpcRandom=$sMpcRandom >> /home/hu/hu_settings.sh
}

get_settings(){
	echo "Retrieving settings"
#volume
#source
#directory (only use if it matches with dir. name - or - find dir name on same usb drive)
#fm freq
#mode (shuffle)

}

volume_up(){
	echo "Volume up"
#        if [ "${iVolume}" -lt 100 ]; then
#                iVolume=$iVolume+1
#        fi
#	echo "Setting volume to: ${iVolume}"
	#amixer $params_amixer set "Master d" $iVolume; amixer $params_amixer set PCM $iVolume unmute
	amixer $params_mixer set PCM 20+ unmute
}

volume_down(){
#	echo "Volume down"
#        if [ "${iVolume}" -gt 0 ]; then
#                iVolume=$iVolume-1
#        fi
#        echo "Setting volume to: ${iVolume}"
        #amixer $params_amixer set "Master d" $iVolume; amixer $params_amixer set PCM $iVolume unmute
	amixer $params_mixer set PCM 20- unmute
}

## FM #######

fm_play(){
	echo "FM play"
	bPlayingFM=1
}

fm_pause(){
	echo "FM pause"
	bPlayingFM=0
	#fm has no "pause" -> stopping
}

fm_play_pause() {
	echo "Toggling FM"

        case $bPlayingFM in
        0) fm_play;;
        1) fm_pause;;
        esac

	echo "FM player state is now: ${bPlayingFM}"
}

fm_next(){
	echo "FM Next Station"

	iFMStation=$iFMStation+1
        if [ "$iFMStation" = 11 ]; then
        	iFMStation=0
        fi
	fm ${arStations[$iFMStation]}
}

fm_prev(){
	echo "FM Prev Station"
}

bt_play(){
	echo "BT play"
}

bt_init(){
	/home/hu/blueagent5.py --pin 0000 &
}

linein_play(){
	echo "Play line-in"
}

#############
## MPC ########
#################

# SLOW, so first start playback before calling this function!
mpc_get_PlaylistDirs() {

        # IFS
        SAVEIFS=$IFS
        IFS=$(echo -en "\n\b")

	# populate arMpcPlaylist
        arMpcPlaylist=( $(mpc -f %file% playlist) )

        # local vars
        local dirname_prev=""
	local dirname_current=""
	local id=0
        local d=0

	# loop through playlist, populate arMpcPlaylistDirs
        for ((i=0; i < ${#arMpcPlaylist[@]}; i++))
	do
		dirname_current=$(dirname ${arMpcPlaylist[$i]})
		if [[ "$dirname_prev" != "$dirname_current" ]]; then
			let id=$i+1
			arMpcPlaylistDirs[$d]=$id
			let d=$d+1
		fi
		dirname_prev=$dirname_current
	done

	# restore IFS
	IFS=$SAVEIFS
}

mpc_check(){
	local ret

	# playlist loading is handled by scripts that trigger on mount/removing of media

        echo "Check if anything is mounted on /media"
	if mount | grep -q /media; then
		echo "Media is ready!"

		if mpc | grep -q "#"; then
			echo "Playlist is ready"
			arSourceAvailable[1]=0
			return 0
		else
			"No playlist ready"
			arSourceAvailable[1]=1
			return 1
		fi
	else
		echo "No media mounted"
		arSourceAvailable[1]=1
		return 1
	fi

}

mpc_init(){
	# setting either defaults or retrieved from hu_settings.sh
	mpc $params_mpc repeat $sMpcRepeat
	return 0;
}

mpc_play(){
	echo "Play mpc"

	# if playlist is empty, start by playing the root

	sMpcDir="."

}

mpc_stop(){
	echo "Stopping mpc playback"
	mpc $params_mpc stop
}

mpc_play_pause(){
	echo "Toggling mpc play/pause"
	mpc $params_mpc toggle
}

mpc_next(){
	echo "Next track"
	mpc $params_mpc next
}

mpc_prev(){
	echo "Previous track"
	mpc $params_mpc prev
}

mpc_random_on(){
	echo "Setting random mode on (MPC)"
	sMpcRandom="on"
	settings_write
	mpc $params_mpc random $sMpcRandom
}

mpc_random_off(){
	echo "Turning random mode off (MPC)"
        sMpcRandom="off"
        settings_write
        mpc $params_mpc random $sMpcRandom

}

mpc_random_toggle(){
	echo "Toggeling Random"

	if [[ $sMpcRandom = "on" ]]; then
		sMpcRandom="off"
	else
		sMpcRandom="on"
	fi
	settings_write
	mpc $params_mpc random $sMpcRandom
}

mpc_play_folder(){
        echo "Loading: ${arDirStruct[$iDirectory]}"

#	mpc $params_mpc clear #crop? - to continue playing?

	# ONLY LOAD REQUESTED FOLDER (and check for status via idle/idleloop)
        #mpc $params_mpc ls ${arDirStruct[$iDirectory]} | mpc $params_mpc add

	# -or- LOAD EVERYTHING FROM THIS FOLDER ONWARDS..
#	mpc $params_mpc repeat on #todo, does this repeat the track or the playlist?
#	for ((i=${iDirectory}; i < ${#arDirStruct}; i++))
#	do
#		mpc $params_mpc ls ${arDirStruct[$iDirectory]} | mpc $params_mpc add
#	done
#	# Add whatever is before the selected folder on the end of the playlist to have a complete playlist of the USB drive
#	for ((i=0; i < ${iDirectory}; i++))
#        do
#                mpc $params_mpc ls ${arDirStruct[$iDirectory]} | mpc $params_mpc add
#        done
#
	# Start playing new folder
	#mpc $params_mpc play 1

	# ALTERNATIVELY, create an indexed list of position in playlist for every directory in the arDirStruct, so you can simply jump to that position.
	mpc $params_mpc play ${arDirStartPos[$iDirectory]}

}

mpc_next_folder(){
	echo "Next folder"

	# get current position in playlist
	local iMpcPos="$(mpc | sed -n 2p | grep -Po '(?<=#)[^/]*')"
	local iNewPos=1

	# find position of next directory
	for ((i=0; i < ${#arMpcPlaylistDirs[@]}; i++))
	do
		if [[ ${arMpcPlaylistDirs[$i]} -gt $iMpcPos ]]; then
			iNewPos=${arMpcPlaylistDirs[$i]}
			break
		fi
	done

	mpc $params_mpc play $iNewPos
}

mpc_prev_folder(){
	echo "Prev folder"
        # get current position in playlist
        local iMpcPos="$(mpc | sed -n 2p | grep -Po '(?<=#)[^/]*')"
	local iNewPos=${arMpcPlaylistDirs[-1]}

        # find position of prev. directory
        for ((i=${#arMpcPlaylistDirs[@]}-1; i >= 0; i--))
        do
		echo $i
                if [[ ${arMpcPlaylistDirs[$i]} -lt $iMpcPos ]]; then
                        iNewPos=${arMpcPlaylistDirs[$i]}
                        break
                fi
        done

        mpc $params_mpc play $iNewPos
}

play_pause(){
	echo "Toggling Play/Pause"
	case $iSource in
        0) fm_play_pause;;
        1) mpc_play_pause;;
        *) echo "Not Supported";;
        esac
}

next(){
	case $iSource in
	0) fm_next;;
	1) mpc_next;;
	*) echo "Not Supported";;
	esac
}

prev(){
        case $iSource in
        0) fm_prev;;
        1) mpc_prev;;
        *) echo "Not Supported";;
        esac
}

source_play(){
        # Check if sources available
        if [ "$iSource" = -1 ]; then
                echo "No sources available."
                return 1
        fi

	case $iSource in
	0) fm_play;;
	1) mpc_play;;
	2) bt_play;;
	3) linein_play;;
	*) echo "Unknown source";;
	esac
}

check_source(){
	echo "Checking sources"

	#todo
	arSourceAvailable[0]=0
	mpc_check # make up your mind man...
	#arSourceAvailable[1]=$(mpc_check)
	arSourceAvailable[2]=1
	arSourceAvailable[3]=1

	# if iSource is not -1 then check if requested source is available
	if $iSource > -1; then
		if [[ "${arSourceAvailable[$iSource]" == 0 ]]; then
			# requested source is available.
			echo "Source set to: ${arSource[$iSource]}"
			return 0
		fi
	fi

	# Otherwise, try in order..
	for (( i=3; i>=0; i--))
	do
		if [ "${arSourceAvailable[$i]}" == 0 ]; then
			echo "${arSource[$i]}:	available." 
			iSource=$i
		else
			echo "${arSource[$i]}:	not available."
		fi
	done

	# Ok, bad case, but possible..
	if $iSource == -1; then
		echo "No sources available"
	else
		echo "Source set to: ${arSource[$iSource]}"
	fi
}

source_next(){
	echo ""
	local iSourceCount=0
	local a=$iSource

	# Check if sources available
	if $iSource == -1; then
		echo "No sources available."
		return 1
	fi

	echo "Switching from ${arSource[$iSource]}"
	for (( i=0; i<=3; i++))
	do
	        if [ "$iSource" = "$iSourceArrayLen" ]; then
        	        iSource=0
	        else
        	        iSource=$iSource+1
	        fi
	
		if [ "${arSourceAvailable[$iSource]}" == 0 ]; then
			echo "Switching to ${arSource[$iSource]}"
			settings_write
			return 0
		fi
	done

#not reached!

	# update source change in settings
	settings_write

	#stop all sources and play active source
        alsa_play_fx 1
	fm_stop
	mpc_stop
	source_play
}

mode_change(){
	#only Random on/off, currently, and only for mpc
	echo "Toggeling random mode"

        case $iSource in
        1) mpc_random_toggle;;
        *) echo "Not Supported";;
        esac
}

init(){
	echo "Initializing ..."

arStations[0]="89.10"
arStations[1]="91.10"
arStations[2]="92.10"
arStations[3]="93.10"
arStations[4]="98.90"
arStations[5]="101.70"
arStations[6]="101.30"
arStations[7]="102.10"
arStations[8]="103.10"
arStations[9]="104.90"
arStations[10]="105.10"
iFMStation=0

	# play startup sound
	alsa_play_fx 1

        # check available sources
	check_source

	# load previous state
	/home/hu/hu_settings.sh

	# initialize sources
	#bt_init
	#mpc_init
	#get_state
	source_play

	#not the best place...
	mpc_get_PlaylistDirs

	# Play/Pause button may not be implemented on control panel,
	# therefore, always try to play if a source becomes avaiable.

	echo "Initialization finished"

}

 
init
while :
do
	# display menu
        echo "Current source : ${arSource[$iSource]}"
        echo "---------------------------------"
        echo "1. Next Source"
        echo "2. Play / Pause"
        echo "3. Next track (USB) / station (Radio)"
        echo "4. Prev track (USB) / station (Radio)"
        echo "5. Volume up"
        echo "6. Volume down"
        echo "7. Prev Folder (USB)"
        echo "8. Next Folder (USB)"
	echo "9. Mode: Shuffle (all) / Normal"
        echo "0. Exit"
	echo "---------------------------------"
	read -r -N 1 -p "Enter your choice [0-8] : " c
	# take action
	case $c in
		1) source_next;;
		2) play_pause;;
		3) next;;
		4) prev;;
		5) volume_up;;
		6) volume_down;;
		7) mpc_prev_folder;;
		8) mpc_next_folder;;
		9) mode_change;;
		0) break;;
		*) Pause "Select between 0 to 8 only"
	esac
done

