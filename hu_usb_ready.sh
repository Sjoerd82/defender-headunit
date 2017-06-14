#!/bin/bash
# ---------------------------------------------------------------------------
#

#MPC
typeset params_mpc=""
typeset root_folder=""
typeset lkp="1" # Last Known Position
typeset lkf=""  # Last Known File

# todo test parameter is there..

root_folder=$(basename $1)

# First line is the original position
lkp=$(head -n1 /home/hu/mp_$root_folder.txt)

# Second line is the file name
lkf=$(tail -n1 /home/hu/mp_$root_folder.txt)

# debugging stuff
#echo $1 > /home/hu/test.txt
#echo $root_folder >> /home/hu/test.txt
#ls $1 >> /home/hu/test.txt
#echo $lkp > /home/hu/test.txt
#echo $lkf > /home/hu/test.txt

# Derive position from file name
lkp=$(mpc -f "%position% %file%" playlist | grep "$lkf" | cut -d' ' -f1)
#TODO: only use this if it yields a result, otherwise use the lkp

mpc $params_mpc -q stop
mpc $params_mpc -q clear

mpc --wait $params_mpc update $root_folder
mpc $params_mpc listall $root_folder | mpc $params_mpc add
mpc $params_mpc play $lkp

