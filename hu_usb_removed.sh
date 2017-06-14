#!/bin/bash
# ---------------------------------------------------------------------------
#

#MPC
typeset params_mpc=""
typeset root_folder=""

# todo test parameter is there..
root_folder=$(basename $1)

# Safe position and current file name for this drive
mpc | sed -n 2p | grep -Po '(?<=#)[^/]*' > /home/hu/mp_$root_folder.txt
mpc -f %file% current >> /home/hu/mp_$root_folder.txt

mpc $params_mpc -q stop
mpc $params_mpc -q clear
