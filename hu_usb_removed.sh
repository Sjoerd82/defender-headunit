#!/bin/sh
# ---------------------------------------------------------------------------
#

mpcParams=""
rootFolder="/root/defender-headunit"
#os.path.dirname(os.path.abspath(__file__))
mountFolder=$(basename $1)


# save position and current file name for this drive
#mpc | sed -n 2p | grep -Po '(?<=#)[^/]*' > $rootFolder/mp_$mountFolder.txt
#mpc -f %file% current >> $rootFolder/mp_$mountFolder.txt

mpc $mpcParams sendmessage media_removed $mountFolder
