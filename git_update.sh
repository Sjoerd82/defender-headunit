#!/bin/sh

GIT_DIR="/root/defender-headunit/git"

git --git-dir=$GIT_DIR fetch --all
git --git-dir=$GIT_DIR --hard origin/master