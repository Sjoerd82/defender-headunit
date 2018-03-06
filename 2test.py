import sys

#********************************************************************************
#
# Version
#

#********************************************************************************
#
# Logging
#
import logging
import logging.config
#from logging import Formatter
import datetime
import os
logger = None
from hu_logger import *
# for logging to syslog
import socket

#********************************************************************************
#
# Parse command line arguments and environment variables
# Command line takes precedence over environment variables and settings.json
#
import os
import argparse


#********************************************************************************
#
#
#

# temporary / debugging:
import time

# load json source configuration
import json

# dynamic module loading
import inspect

# queuing
from Queue import Queue

# multithreading
import threading
import subprocess

# multiprocessing (disabled)
#from multiprocessing import Process

# support modules
from hu_pulseaudio import *
from hu_volume import *
from hu_utils import *
from hu_source import SourceController
from hu_settings import *
from hu_mpd import *
#from hu_menu import *

# dbus
import dbus.service
import dbus.exceptions

# main loop
import gobject
from dbus.mainloop.glib import DBusGMainLoop

#********************************************************************************
#
# Third party and others...
#

from slugify import slugify

#********************************************************************************
#
# ZeroMQ
#

import zmq

context = zmq.Context()
subscriber = context.socket (zmq.SUB)
subscriber.connect ("tcp://localhost:5556")	# TODO: get port from config
subscriber.setsockopt (zmq.SUBSCRIBE, '')

# GLOBAL vars
Sources = SourceController()	#TODO: rename "Sources" -- confusing name
mpdc = None
disp = None
arMpcPlaylistDirs = [ ]			#TODO: should probably not be global...

# CONSTANTS
CONFIG_FILE_DEFAULT = '/mnt/PIHU_APP/defender-headunit/config/configuration.json'
CONFIG_FILE = '/mnt/PIHU_CONFIG/configuration.json'
VERSION = "1.0.0"
PID_FILE = "hu"
SYSLOG_UDP_PORT=514

hu_details = { 'track':None, 'random':'off', 'repeat':True, 'att':False }

#def volume_att_toggle():
#	hudispdata = {}
#	hudispdata['att'] = '1'
#	disp.dispdata(hudispdata)
#	return None
	
# ********************************************************************************
# Output wrapper
#
def printer( message, level=20, continuation=False, tag='SYSTEM' ):
	#TODO: test if headunit logger exist...
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


def mq_recv():
	message = subscriber.recv()
	if message == '/player/track/next':
		print("{0}".format(message))
	else:
		print("NO MESSAGE! sorry..")

		
#********************************************************************************
#
# Main loop
#

	
#
# Initialize the mainloop
#
DBusGMainLoop(set_as_default=True)


#
# main loop
#
mainloop = gobject.MainLoop()


#
# 30 second timer
#
# timer1:
# - Save settings
# - check if dbus services still online? (or make this a separate service?)
#gobject.timeout_add_seconds(30,cb_timer1)

#
# Queue handler
# NOTE: Remember, everything executed through the qBlock queue blocks, including qPrio!
# IDEALLY, WE'D PUT THIS BACK IN A THREAD, IF THAT WOULD PERFORM... (which for some reason it doesn't!)
# 
gobject.idle_add(mq_recv)
#gobject.idle_add(cb_queue)

#
# DBus: system bus
# On a root only embedded system there may not be a usable session bus
#
#m = MainInstance()


try:
	bus = dbus.SystemBus()
except dbus.DBusException:
	raise RuntimeError("No D-Bus connection")

# Declare a name where our service can be reached
try:
    bus_name = dbus.service.BusName("com.arctura.hu", bus, do_not_queue=True)
except dbus.exceptions.NameExistsException:
    print("service is already running")
    sys.exit(1)

# Output

#
# Connect Callback functions to DBus Signals
#

#
# Start the blocking main loop...
#
with PidFile(PID_FILE) as p:
	try:
		mainloop.run()
	finally:
		mainloop.quit()