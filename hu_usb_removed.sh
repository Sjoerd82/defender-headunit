#!/bin/bash
# ---------------------------------------------------------------------------
#

#MPC
typeset params_mpc=""
typeset root_folder=""

# todo test parameter is there..
folder_x='/root/defender-headunit'
root_folder=$(basename $1)


# save position and current file name for this drive
mpc | sed -n 2p | grep -Po '(?<=#)[^/]*' > $folder_x/mp_$root_folder.txt
mpc -f %file% current >> $folder_x/mp_$root_folder.txt

mpc $params_mpc -q stop
mpc $params_mpc -q clear
