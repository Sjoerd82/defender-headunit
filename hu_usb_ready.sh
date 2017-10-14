#!/bin/sh
# ---------------------------------------------------------------------------
#

mpcParams = ""
rootFolder = os.path.dirname(os.path.abspath(__file__))
mountFolder=$(basename $1)


#MPC
typeset lkp="1" # Last Known Position
typeset lkf=""  # Last Known File

# the mp_ file is created by the hu_usb_removed.sh script.

# First line is the original position
lkp=$(head -n1 $(rootFolder)/mp_$(mountFolder).txt)

# Second line is the file name
lkf=$(tail -n1 $(rootFolder)/mp_$(mountFolder).txt)

# debugging stuff
#echo $1 > /root/test.txt
#echo $mountFolder >> /home/hu/test.txt
#ls $1 >> /home/hu/test.txt
#echo $lkp > /home/hu/test.txt
#echo $lkf > /home/hu/test.txt

# Derive position from file name
lkp=$(mpc -f "%position% %file%" playlist | grep "$lkf" | cut -d' ' -f1)
#TODO: only use this if it yields a result, otherwise use the lkp

# Update the mpd database
mpc --wait $mpcParams update $mountFolder

# Put the new stuff into the playlist.
# We have to do it here, because in the main script we don't have $root_folder
mpc $mpcParams -q stop
mpc $mpcParams -q clear
mpc $mpcParams listall $mountFolder | mpc $mpcParams add
mpc $mpcParams sendmessage media_ready $mountFolder

# Leave this to the main headunit script, because you only want to start playing if not in bluetooth, or line-in mode.
# also, the main script needs to keep track of which source we're playing.
#mpc $params_mpc play $lkp

#TODO: we can remove the lkp stuff from here, and put it in the main script

