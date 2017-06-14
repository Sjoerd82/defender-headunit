#!/bin/bash

typeset -a arMpcPlaylist

#arDirStruct=( $(mpc -f %file%) )
#shopt -s globstar nullglob
#arDirStruct=( *$(mpc -f \%file\% playlist)* )

SAVEIFS=$IFS
IFS=$(echo -en "\n\b")

arDirStruct=( $(mpc -f %file% playlist) )

# restore $IFS
IFS=$SAVEIFS

        for ((i=0; i <= ${#arDirStruct}; i++))
        do
		echo "${arDirStruct[$i]}"
	done

