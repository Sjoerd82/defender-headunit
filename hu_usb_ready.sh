#!/bin/sh
# ---------------------------------------------------------------------------
#

#MPC
typeset params_mpc=""
typeset root_folder=""
typeset lkp="1" # Last Known Position
typeset lkf=""  # Last Known File

# todo test parameter is there..
folder_x='/root/defender-headunit'
root_folder=$(basename $1)


# the mp_ file is created by the hu_usb_removed.sh script.

# First line is the original position
lkp=$(head -n1 $(folder_x)/mp_$(root_folder).txt)

# Second line is the file name
lkf=$(tail -n1 $(folder_x)/mp_$(root_folder).txt)

# debugging stuff
#echo $1 > /root/test.txt
#echo $root_folder >> /home/hu/test.txt
#ls $1 >> /home/hu/test.txt
#echo $lkp > /home/hu/test.txt
#echo $lkf > /home/hu/test.txt

# Derive position from file name
lkp=$(mpc -f "%position% %file%" playlist | grep "$lkf" | cut -d' ' -f1)
#TODO: only use this if it yields a result, otherwise use the lkp

# Update the mpd database
mpc --wait $params_mpc update $root_folder

# Put the new stuff into the playlist.
# We have to do it here, because in the main script we don't have $root_folder
mpc $params_mpc -q stop
mpc $params_mpc -q clear
mpc $params_mpc listall $root_folder | mpc $params_mpc add
mpc $params_mpc sendmessage media_ready $root_folder

# Leave this to the main headunit script, because you only want to start playing if not in bluetooth, or line-in mode.
# also, the main script needs to keep track of which source we're playing.
#mpc $params_mpc play $lkp

#TODO: we can remove the lkp stuff from here, and put it in the main script

