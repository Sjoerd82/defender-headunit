#!/bin/sh

git --git-dir=git fetch --all
git --git-dir=git reset --hard origin/master