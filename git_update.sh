#!/bin/sh

#GIT_DIR="/mnt/PIHU_APP/git"
GIT_DIR="/root/defender-headunit/git"

git --git-dir=$GIT_DIR fetch --all
git --git-dir=$GIT_DIR reset --hard origin/master
git --git-dir=$GIT_DIR clean --force