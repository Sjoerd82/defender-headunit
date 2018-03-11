#!/usr/bin/python

# A car's headunit.
#
# Author: Sjoerd Venema
# License: MIT
#

#********************************************************************************
#
# ISSUES:
#  - Plug-in Auto Start outside of this script.
#  - Not all next() source functions update the settings.

#********************************************************************************
# CONFIGURATION and SETTINGS
#
# configuration.json		Main configuration file (json)
# dSettings.json			Operational settings (json)
#
# Operational source settings, to continue playback (pickled):
#
# fm.p
# media /<uuid>.p
#       /<uuid>_dirs.txt
# locmus/<mountpoint>.p
#       /<mountpoint>_dirs.txt
# smb   /<ip_mountpoint>.p			172_16_8_11_music.p
#		/<ip_mountpoint>_dirs.txt	172_16_8_11_music_dirs.txt
#
# ?:
# stream, line, bt
#

#********************************************************************************
# LOGGING and CONSOLE output
#
# All output is channeled through the Python logger, in order to both be displayed
# on the console and written to a logfile.
#
# Please don't use the print() function. Instead use either:
#  - myprint( message, level="INFO", tag="")	# defined in hu_utils.py
#  - logger.info(message, extra={'tag': tag})	# or any other desired log level
#
# Default log level can be overridden via command line parameters. Default:
# > Log level INFO or higher is sent to the console.
# > Log level DEBUG or higher is sent to the log file.
#
# Output sent to the file is cleansed of any ANSI formatting.
#

#********************************************************************************
# DBUS
# 
# This script listens to a number of DBus sources.
# This script also emits signals on com.arctura.hu		#TODO

#********************************************************************************
# PLUGINS
# 
# Originally these were started via threading or multiprocessing, but in either
# case messed up the later introduced queing worker threads. For now we'll
# manually start the plugins
#
# Try: gobject.spawn_async
#

#********************************************************************************
# MODULES
#
# Automatically loaded:
#
# ./sources/* 			Source plugins
# ./plugin_control/*	Controller plugins	} NOT ANY MORE, SEE: ISSUES, PLUGINS
# ./plugin_other/*		Other plugins		}
#
# ./hu_utils.py			Misc. handy functions
# ./hu_volume.py		Volume control
# ./hu_....py

import sys
import os
from modules.hu_utils import *

#********************************************************************************
#
# Version
#
from version import __version__

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

from modules.hu_logger import ColoredFormatter
from modules.hu_logger import RemAnsiFormatter

# for logging to syslog
import socket


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

# dbus
import dbus.service
import dbus.exceptions

# main loop
import gobject
from dbus.mainloop.glib import DBusGMainLoop

# ZeroMQ
import zmq

# support modules
from modules.hu_pulseaudio import *
from modules.hu_volume import *
from modules.hu_source import SourceController
from modules.hu_settings import *
from modules.hu_mpd import *
#from hu_menu import *

#********************************************************************************
# Third party and others...
#

from slugify import slugify


# GLOBAL vars
#Sources = SourceController()	# --> micro-service
Sources = None #Temp..
disp = None
arMpcPlaylistDirs = [ ]			#TODO: should probably not be global...

# SEMI-CONSTANTS (set at startup):
SOURCE = None
SOURCE_SUB = None
BOOT = None

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

#********************************************************************************
# ZeroMQ
#
def zmq_connect():

	printer("Connecting to ZeroMQ forwarder")
	
	zmq_ctx = zmq.Context()
	subscriber = zmq_ctx.socket (zmq.SUB)
	port_server = "5560" #TODO: get port from config
	subscriber.connect ("tcp://localhost:{0}".format(port_server)) # connect to server

	port_client = "5559"
	publisher = zmq_ctx.socket(zmq.PUB)
	publisher.connect("tcp://localhost:{0}".format(port_client))

	#context = zmq.Context()
	#subscriber = context.socket (zmq.SUB)
	#subscriber.connect ("tcp://localhost:5556")	# TODO: get port from config
	#subscriber.setsockopt (zmq.SUBSCRIBE, '')

def zmq_send(path_send, message):
	data = json.dumps(message)
	printer("Sending message: {0} {1}".format(path_send, data))
	zmq_sck.send("{0} {1}".format(path_send, data))
	time.sleep(1)
	
	
def queue(q, item, sfx=None):
	#printer('Blocking Queue Size before: {0}'.format(qBlock.qsize()))
	try:
		if q == 'prio':
			qPrio.put(item, False)
		elif q == 'blocking':
			qBlock.put(item, False)
		elif q == 'async':
			qAsync.put(item, False)
	except queue.Full:
		printer('Queue is full.. ignoring button press.')
		return None
		
	# play sfx, if successfully added to queue and sfx defined
	if sfx:
		pa_sfx(sfx)
	
	#printer('Blocking Queue Size after: {0}'.format(qBlock.qsize()))
	return 0

# todo: rename? put in hu_settings?
def save_current_position(timeelapsed):

	global Sources
	global mpdc
	
	currSrc = Sources.getComposite()
	
	# create filename
	source_name = currSrc["name"]
	
	if not 'subsource' in currSrc:
		print "TODO: resume not (YET) supported for this source, sorry."
		print currSrc
		return None

	if 'filename_save' in currSrc:
		source_key = currSrc["filename_save"][0]	#eg "mountpoint"
		if source_key in currSrc["subsource"]:
			source_key_value = slugify( currSrc["subsource"][source_key] )
		else:
			printer("Error creating savefile, source_key ({0}) doesn't exist".format(source_key))
			source_key_value = "untitled"
	else:
		printer('Error: "filename_save" not defined in configuration, not saving.',level=LL_ERROR)
		return None

	# get time into track
	#timeelapsed = status['time']
	
	# get track name
	currSong = mpdc.mpc_get_currentsong()
	current_file = currSong['file']
	"""print currSong
	{'album': 'Exodus', 'composer': 'Andy Hunter/Tedd T.', 'title': 'Go', 'track': '1', 'duration': '411.480',
	'artist': 'Andy Hunter', 'pos': '0', 'last-modified': '2013-10-12T15:53:13Z', 'albumartist': 'Andy Hunter',
	'file': 'PIHU_SMB/music/electric/Andy Hunter/Andy Hunter - 2002 - Exodus/01 - Andy Hunter - Go.mp3',
	'time': '411', 'date': '2002', 'genre': 'Electronic/Dance', 'id': '44365'}
	"""

	# put it together
	dSave = {'file': current_file, 'time': timeelapsed}
					
	# save file
	printer('Saving playlist position for: {0}: {1}'.format(source_name,source_key_value))
	#print(' ...  file: {0}, time: {1}'.format(current_file,timeelapsed))

	# create path, if it doesn't exist yet..
	pckl_path = os.path.join('/mnt/PIHU_CONFIG',source_name)
	if not os.path.exists(pckl_path):
		os.makedirs(pckl_path)
	# pickle file will be created by dump, if it doesn't exist yet
	pckl_file = os.path.join(pckl_path,source_key_value + ".p")
	pickle.dump( dSave, open( pckl_file, "wb" ) )

def load_current_resume():

	global Sources
	global mpdc
	
	currSrc = Sources.getComposite()
	
	# create filename
	source_name = currSrc["name"]
	
	if not 'subsource' in currSrc:
		print "TODO: resume not (YET) supported for this source, sorry."
		print currSrc
		return None
	
	if 'filename_save' in currSrc:
		source_key = currSrc["filename_save"][0]	#eg "mountpoint"
		if source_key in currSrc["subsource"]:
			source_key_value = slugify( currSrc["subsource"][source_key] )
		else:
			printer("Error creating savefile, source_key ({0}) doesn't exist".format(source_key))
			source_key_value = "untitled"
	else:
		printer('Error: "filename_save" not defined in configuration, not saving.',level=LL_ERROR)
		return None
				
	# load file
	printer('Loading playlist position for: {0}: {1}'.format(source_name,source_key_value))

	# check if there's a save file..
	pckl_file = os.path.join('/mnt/PIHU_CONFIG',source_name,source_key_value + ".p")
	if not os.path.exists(pckl_file):
		printer('ERROR: Save file not found',level=LL_WARNING)
		return None
	else:
		dLoad = pickle.load( open( pckl_file, "rb" ) )
	return dLoad
	
	
# ********************************************************************************
# Callback functions
#
#  - Remote control
#  - MPD events
#  - Timer
#  - UDisk add/remove drive
#

def cb_remote_btn_press2 ( func ):
	print "cb_remote_btn_press2 {0}".format(func)

#

	#def seek_next():
	#	Sources.sourceSeekNext()
		
		#global dSettings
		#if dSettings['source'] == 1 or dSettings['source'] == 2 or dSettings['source'] == 5 or dSettings['source'] == 6:
		#	mpc_next_track()
		#elif dSettings['source'] == 3:
		#	bt_next()
		#fm_next ofzoiets

	"""
	def seek_prev():
		global dSettings
		if dSettings['source'] == 1 or dSettings['source'] == 2 or dSettings['source'] == 5 or dSettings['source'] == 6:
			mpc_prev_track()
		elif dSettings['source'] == 3:
			bt_prev()
	"""

# Handle button press
def cb_remote_btn_press ( func ):

	queue_func = {'command':func}
	
	if func == 'SHUFFLE':
		printer('\033[95m[BUTTON] Shuffle\033[00m')
		queue('blocking',queue_func)
		
	elif func == 'SOURCE':
		printer('\033[95m[BUTTON] Next source\033[00m')
		queue('blocking',queue_func,'button_feedback')
		
	elif func == 'ATT':
		printer(colorize('[BUTTON] ATT','light_magenta'))
		queue('prio',queue_func,'button_feedback')

	elif func == 'VOL_UP':
		printer(colorize('VOL_UP','light_magenta'),tag='button')
		queue('prio',queue_func,'button_feedback')
		
	elif func == 'VOL_DOWN':
		print('\033[95m[BUTTON] VOL_DOWN\033[00m')
		queue('prio',queue_func,'button_feedback')

	elif func == 'SEEK_NEXT':
		print('\033[95m[BUTTON] Seek/Next\033[00m')
		queue('blocking',queue_func,'button_feedback')
		
	elif func == 'SEEK_PREV':
		print('\033[95m[BUTTON] Seek/Prev.\033[00m')
		queue('blocking',queue_func,'button_feedback')
		
	elif func == 'DIR_NEXT':
		print('\033[95m[BUTTON] Next directory\033[00m')
		queue('blocking',queue_func)

	elif func == 'DIR_PREV':
		print('\033[95m[BUTTON] Prev directory\033[00m')
		queue('blocking',queue_func)

	elif func == 'UPDATE_LOCAL':
		print('\033[95m[BUTTON] Updating local MPD database\033[00m')
		queue('async',queue_func,'button_feedback')

	elif func == 'OFF':
		print('\033[95m[BUTTON] Shutting down\033[00m')
		queue('prio',queue_func,'button_feedback')
		
	else:
		print('Unknown button function')
		pa_sfx('error')

def cb_mpd_event( event ):
	global settings
	global mpdc

	#def mpc_save_pos_for_label ( label, pcklPath ):
	"""
	def save_pos_for_label ( label, pcklPath ):

		oMpdClient.command_list_ok_begin()
		oMpdClient.status()
		results = oMpdClient.command_list_end()

		songid = None
		testje = None
		current_song_listdick = None
		# Dictionary in List
		try:
			for r in results:
				songid = r['songid']
				timeelapsed = r['time']
			
			current_song_listdick = oMpdClient.playlistid(songid)
		except:
			print(' ...  Error, key not found!')
			print results

		#print("DEBUG: current song details")
		debugging = oMpdClient.currentsong()
		try:
			#print debugging
			testje = debugging['file']
			#print testje
		except:
			print(' ...  Error, key not found!')
			print debugging
			

		if testje == None:
			print('DEBUG: BREAK BREAK')
			return 1

		if songid == None:
			current_file=testje
		else:	
			for f in current_song_listdick:
					current_file = f['file']

		dSavePosition = {'file': current_file, 'time': timeelapsed}
		print(' ...  file: {0}, time: {1}'.format(current_file,timeelapsed))

		#if os.path.isfile(pickle_file):
		pickle_file = pcklPath + "/mp_" + label + ".p"
		pickle.dump( dSavePosition, open( pickle_file, "wb" ) )
	"""
	printer('DBUS event received: {0}'.format(event), tag='MPD')

	# anything related to the player	
	if event == "player":
	
		printer('Detected MPD event: player. Retrieving MPD state.')
		# first let's determine the state:	
		status = mpdc.mpc_get_status()
		#print "STATUS: {0}.".format(status)
		#print "STATE : {0}.".format(status['state'])
		
		"""status:
		{'songid': '14000', 'playlistlength': '7382', 'playlist': '8', 'repeat': '1', 'consume': '0', 'mixrampdb': '0.000000',
		'random': '1', 'state': 'play', 'elapsed': '0.000', 'volume': '100', 'single': '0', 'nextsong': '806', 'time': '0:239',
		'duration': '239.020', 'song': '6545', 'audio': '44100:24:2', 'bitrate': '0', 'nextsongid': '8261'}
		"""
		
		if 'state' in status:
			if status['state'] == 'stop':
				print ' > MPD playback has stopped.. ignoring this'
			elif status['state'] == 'pause':
				print ' > MPD playback has been paused.. ignoring this'
			elif status['state'] == 'play':
				printer(' > MPD playback is playing, saving to file. (SEEK/NEXT/PREV)')
				
				# one of the following possible things have happened:
				# - prev track, next track, seek track
						
				#
				# Save position
				#
				timeelapsed = status['time']
				save_current_position(timeelapsed)

				""" PROBLEMS AHEAD
				
				LCD DISPLAY
				
				#hu_details
				mpcSong = mpdc.mpc_get_currentsong()
				#mpcStatus = mpdc.mpc_get_status()
				mpcTrackTotal = mpdc.mpc_get_trackcount()
					
				if 'artist' in mpcSong:
					artist = mpcSong['artist']
				else:
					artist = None

				if 'title' in mpcSong:
					title = mpcSong['title']
				else:
					title = None
					
				if 'track' in mpcSong:
					track = mpcSong['track']
				else:
					track = None
				
				file = os.path.basename(mpcSong['file'])
				
				#disp.lcd_play( artist, title, file, track, mpcTrackTotal )
				"""
				
	elif event == "update":
		printer(" ...  database update started or finished (no action)", tag='MPD')

	elif event == "database":
		printer(" ...  database updated with new music #TODO", tag='MPD')

		# let's determine what has changed
		
		
		""" TODO: UNCOMMENT THIS
		#IF we're already playing local music: Continue playing without interruption
		# and add new tracks to the playlist
		# Source 2 = locmus
		if dSettings['source'] == 2:
			print(' ......  source is already playing, trying seamless update...')
			# 1. "crop" playlist (remove everything, except playing track)
			call(["mpc", "-q" , "crop"])

			yMpdClient = MPDClient()
			yMpdClient.connect("localhost", 6600)
					
			# 2. songid is not unique, get the full filename
			current_song = yMpdClient.currentsong()
			curr_file = current_song['file']
			print(' ......  currently playing file: {0}'.format(curr_file))
			
			# 3. reload local music playlist
			mpc_populate_playlist(sLocalMusicMPD)
			
			# 4. find position of song that we are playing, skipping the first position (pos 0) in the playlist, because that's where the currently playing song is
			delpos = '0'
			for s in yMpdClient.playlistinfo('1:'):
				if s['file'] == curr_file:
					print(' ......  song found at position {0}'.format(s['pos']))
					delpos = s['pos']
			
			if delpos != '0':
				print(' ......  moving currently playing track back in place')
				yMpdClient.delete(delpos)
				yMpdClient.move(0,int(delpos)-1)
			else:
				print(' ......  ERROR: something went wrong')
				pa_sfx('error')

			yMpdClient.close()
			
		#IF we were not playing local music: Try to switch to local music, but check if the source is OK.
		else:
			#We cannot check if there's any NEW tracks, but let's check if there's anything to play..
			locmus_check()
			# Source 2 = locmus
			#if arSourceAvailable[2] == 1:
			if Sources.getAvailable('name','locmus')
				dSettings['source'] = 2
				source_play()
			else:
				print('[LOCMUS] Update requested, but no music available for playing... Doing nothing.')
		"""
		
	elif event == "playlist":
		priner(" ...  playlist changed (no action)", tag='MPD')
	#elif event == "media_removed":
	#elif event == "media_ready":
	
	# TEMPORARY --  DON'T DEPEND ON MPD FOR THIS -- USE DBUS #
	elif event == "ifup":
		cb_ifup()
		
	elif event == "ifdown":
		cb_ifdn()

	else:
		printer(' ...  unknown event (no action)', tag='MPD')
		
# Timer 1: executed every 30 seconds
def cb_timer1():

	global cSettings
	#global disp

	printer('Interval function [30 second]', level=LL_DEBUG, tag="TIMER1")

	# save current position
	# TODO: ONLY WHEN WE'RE ACTUALLY PLAYING SOMETHING...
	#save_current_position()
	
	# WHAT'S THE POINT OF THIS?:
	# save settings (hu_settings)
	cSettings.save()
	
	#hudispdata = {}
	#hudispdata['src'] = "USB"		#temp.
	#disp.dispdata(hudispdata)

	return True

# called when the ifup script is called (interface up)
def cb_ifup():
	global Sources
	printer("WiFi interface UP: checking network related sources")

	ix = 0
	for source in Sources.getAll():
		if source['depNetwork']:
			#Sources.sourceCheck(ix)
			Sources.sourceInit(ix)	#TODO -- Add a re-init or something... or extend check() with init stuff
		ix += 1

	# display overview
	printSummary(Sources)

# called when the ifdown script is called (interface down)
def cb_ifdn():
	global Sources
	printer("WiFi interface DOWN: marking network related sources unavailable")

	# set all network dependend sources to unavailable
	# TODO: We're assuming we only have wlan, add a check for any remaining interfaces in case we have other
	Sources.setAvailable('depNetwork',True,False)

	# display overview
	printSummary(Sources)
	
def cb_udisk_dev_add( device ):
	printer('Device added: {0}'.format(str(device)),tag='UDISKS')
	item = {}
	item['command'] = 'DEVADD'
	item['device'] = device
	queue('blocking',item,'button_devadd')

def cb_udisk_dev_rem( device ):
	printer('Device removed: {0}'.format(str(device)),tag='UDISKS')
	item = {}
	item['command'] = 'DEVREM'
	item['device'] = device
	queue('blocking',item,'button_devrem')

def udisk_add( device ):

	global Sources

	device_obj = bus.get_object("org.freedesktop.UDisks", device)
	device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)
	#
	#  beware.... anything after this may or may not be defined depending on the event and state of the drive. 
	#  Attempts to get a prop that is no longer set will generate a dbus.connection:Exception
	#

	# HANDY DEBUGGING TIP, DISPLAY ALL AVAILABLE PROPERTIES:
	# WILL *NOT* WORK FOR DEVICE REMOVAL
	#data = device_props.GetAll('')
	#for i in data: print i+': '+str(data[i])
	
	# Variables
	DeviceFile = ""
	mountpoint = ""
	mytag = "UDISKS"
	
	try:
		DeviceFile = device_props.Get('org.freedesktop.UDisks.Device',"DeviceFile")
		printer(" > DeviceFile: {0}".format(DeviceFile),tag=mytag)
		
	except:
		printer(" > DeviceFile is unset... Aborting...",tag=mytag)
		return None
	
	# Check if DeviceIsMediaAvailable...
	try:
		is_media_available = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsMediaAvailable")
		if is_media_available:
			printer(" > Media available",tag=mytag)
		else:
			printer(" > Media not available... Aborting...",tag=mytag)
			return None
	except:
		printer(" > DeviceIsMediaAvailable is not set... Aborting...",tag=mytag)
		return None
	
	# Check if it is a Partition...
	try:
		is_partition = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsPartition")
		if is_partition:
			printer(" > Device is partition",tag=mytag)
	except:
		printer(" > DeviceIsPartition is not set... Aborting...",tag=mytag)
		return None

	if not is_partition:
		printer(" > DeviceIsPartition is not set... Aborting...",tag=mytag)
		return None

	# Please Note:
	# DeviceFile = dbus.String(u'/dev/sda1', variant_level=1)
		
	ix = Sources.getIndex('name','media')
	
	#return DeviceFile
	parameters = {}
	parameters['index'] = ix
	parameters['device'] = str(DeviceFile)
	isAdded = Sources.sourceAddSub(ix,parameters)
	
	if isAdded:
	
		#get ix, ix_ss
		ix_ss = Sources.getIndexSub(ix,'device',str(DeviceFile))
		
		# check, and if available play
		if Sources.sourceCheck( ix, ix_ss ):
			#Sources.setCurrent( ix, ix_ss )
			#TODO: move to queue
			#Sources.sourcePlay()
			hu_play(ix, ix_ss)

			
		printSummary(Sources)
		return True
	else:
		return False
	
	#queue('blocking','DEVREM','button_devrem')

	#IdLabel: SJOERD
	#DriveSerial: 0014857749DCFD20C7F95F31
	#DeviceMountPaths: dbus.Array([dbus.String(u'/media/SJOERD')], signature=dbus.Signature('s'), variant_level=1)
	#DeviceFileById: dbus.Array([dbus.String(u'/dev/disk/by-id/usb-Kingston_DataTraveler_SE9_0014857749DCFD20C7F95F31-0:0-part1'), dbus.String(u'/dev/disk/by-uuid/D2B6-F8B3')], signature=dbus.Signature('s'), variant_level=1)
	
	#
	# DeviceFile contains the device name of the added device..
	#


	# check source, if added successfully
	

		

def udisk_rem( device ):

	global Sources

	device_obj = bus.get_object("org.freedesktop.UDisks", device)
	device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)
	#
	#  beware.... anything after this may or may not be defined depending on the event and state of the drive. 
	#  Attempts to get a prop that is no longer set will generate a dbus.connection:Exception
	#

	# HANDY DEBUGGING TIP, DISPLAY ALL AVAILABLE PROPERTIES:
	# WILL *NOT* WORK FOR DEVICE REMOVAL
	#data = device_props.GetAll('')
	#for i in data: print i+': '+str(data[i])
	
	# Variables
	DeviceFile = ""
	mountpoint = ""
	mytag = "UDISKS"
	ix = Sources.getIndex('name','media')
	
	# The removed mountpoint can be derived from str(device)

	# WHAT IF IT'S PLAYING??
	# TODO CHECK IF PLAYING!!

	# TODO ignore /dev/sda
	
	# form the partition device name
	partition = "/dev/"+os.path.basename(str(device))

	# search for the subsource index
	ix_ss = Sources.getIndexSub(ix, 'device', partition)
	if not ix_ss is None:
	
		# check current index, to check if we're playing this to-be removed sub-source
		arIxCurr = Sources.getIndexCurrent()
	
		# remove sub-source
		printer(' > Removing {0}...'.format(partition))
		Sources.remSub(ix, ix_ss)
		
		# stop playing, if removed source is current source
		print "DEBUG 1: {0}".format(arIxCurr)
		if ix == arIxCurr[0] and ix_ss == arIxCurr[1]:
			print "DEBUG 2"
			Sources.sourceStop()
			print "DEBUG 3"
			x = Sources.next(reverse=True)
			#x = Sources.next()
			print "DEBUG 4: {0}".format(x)
			hu_play()
			print "DEBUG 5"

	
		# display overview
		printSummary(Sources)
	else:
		printer(' > Not a subsource: {0}'.format(partition))	
		

# ********************************************************************************
# Headunit functions
#

def volume_att():

	global volm
	global hu_details
	
	if 'att' in hu_details:
		hu_details['att'] = not hu_details['att']
	else:
		hu_details['att'] = True

	if hu_details['att']:
		volm.set('20%')
	else:
		pre_att_vol = '60%' #TODO	#VolPulse.get()
		volm.set(pre_att_vol)

def do_source():
	pass

		

def hu_play( index=None, index_sub=None, resume=True ):

	global Sources
	global cSettings

	# set current index, if given
	if not index is None:
		Sources.setCurrent(index, index_sub)
		

	if resume:
		dLoaded = load_current_resume()
		if not dLoaded is None:
			Sources.sourcePlay(dLoaded)
		else:
			Sources.sourcePlay()
	else:
		Sources.sourcePlay()

	
	# get current index(es)
	arCurrIx = Sources.getIndexCurrent()

	# get current source
	currSrc = Sources.get(None)
	
	# update source name
	cSettings.set('source',currSrc['name'])
	
	# update sub-source key (in case of sub-source)
	if not arCurrIx[1] == None:
		subsource_key = {}
		for key in currSrc['subsource_key']:
			subsource_key[key] = currSrc['subsources'][arCurrIx[1]][key]
		cSettings.set('subsourcekey', subsource_key)
	
	# commit changes
	cSettings.save()
		

def dir_next():
	global Sources
	global arMpcPlaylistDirs
	
	# get current source
	currSrc = Sources.get(None)

	# check if the source supports dirnext
	if 'dirnext' in currSrc['controls'] and currSrc['controls']['dirnext']:
		pa_sfx('button_feedback')

		if not arMpcPlaylistDirs:
			printer(' > Building new dirlist.. standby!', tag='nxtdir')
			# TESTING
			dir_to_file( True )
			
			# TESTING
			#ardirs = load_dirlist()
		else:
			printer(' > Reusing dirlist', tag='nxtdir')
		
		# TESTING
		nextpos = mpc_next_folder_pos(arMpcPlaylistDirs)
		
		printer(' > Next folder @ {0}'.format(nextpos))
		call(["mpc", "-q", "random", "off"])
		call(["mpc", "-q", "play", str(nextpos)])
		
	else:
		pa_sfx('error')
		printer('Function not available for this source.', level=LL_WARNING)


# change? instead pass a variable to be filled with the dirlist?
def dir_to_file( current=True ):

	global arMpcPlaylistDirs

	# local variables
	dirname_current = ''
	dirname_prev = ''
	iPos = 1
	
	pipe = Popen('mpc -f %file% playlist', shell=True, stdout=PIPE)

	# if current == True, then update the global current dirlist, so first clear it:
	if current:
		arMpcPlaylistDirs = [ ]
	
	# todo: future, create them per (sub)source
	dirfile = '/mnt/PIHU_CONFIG/dl_current.txt'
	with open(dirfile,'w') as dirs:
		for line in pipe.stdout:
			dirname_current=os.path.dirname(line.strip())
			t = iPos, dirname_current
			if dirname_prev != dirname_current:
				# if current == True, then update the global current dirlist
				if current:
					arMpcPlaylistDirs.append(t)
				dirs.write("{0}|{1}\n".format(iPos,dirname_current))
			dirname_prev = dirname_current
			iPos += 1

def load_dirlist():
	dirfile = '/mnt/PIHU_CONFIG/dl_current.txt'
	with open(dirfile,'r') as dirs:
		for l in dirs:
			#t  = l.split('|')
			t = [x.strip() for x in l.split('|')]
			arMpcPlaylistDirs.append(t)
	
	print arMpcPlaylistDirs
	return arMpcPlaylistDirs


def mpc_next_folder_pos(arMpcPlaylistDirs):


	# Get current folder
	pipe = subprocess.check_output("mpc -f %file%", shell=True)
	dirname_current = os.path.dirname(pipe.splitlines()[0])
	
	print(' ...  Current folder: {0:s}'.format(dirname_current))
	
	#print(' >>> DEBUG info:')
	#print mpc_get_PlaylistDirs_thread.isAlive()
	
	try:
		iNextPos = arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)+1)][0]
		print(' ...  New folder = {0:s}'.format(arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)+1)][1]))
	except IndexError:
		# I assume the end of the list has been reached...
		print(' ...  ERROR: IndexError - restart at 1')
		iNextPos = 1

	return iNextPos
	
		
# set random; req_state: <toggle | on | off>
# todo: implement "special random"-modes: random within album, artist, folder
def set_random( req_state ):
	#global dSettings
	global mpdc
	global hu_details
	global Sources
	
	# get current random state
	curr_state = hu_details['random']
	printer('Random/Shuffle: Current:{0}, Requested:{1}'.format(curr_state, req_state), tag='random')
	
	if req_state == curr_state:
		printer('Already at requested state', tag='random')
		return False
	
	# get current source
	currSrc = Sources.get(None)
	
	# check if the source supports random
	if not 'random' in currSrc or len(currSrc['random']) == 0:
		printer('Random not available for this source', tag='random')
		return False

	# check type, we only support mpd at this time
	if not 'type' in currSrc or not currSrc['type'] == 'mpd':
		printer('Random not available for this source type (only mpd)', tag='random')
		return False
	
	# set newState
	if req_state in currSrc['random']:
		newState = req_state
	elif req_state == 'toggle':
		if curr_state == 'off':
			newState = 'on'
		elif curr_state == 'on':
			newState = 'off'
		else:
			#newState = ''	#mpc will toggle
			printer('Can only toggle when state is on or off', tag='random')
			return False
		
	# sound effect
	if newState == 'on':
		pa_sfx('button_feedback')
	elif newState == 'off':
		pa_sfx('reset_shuffle')
	
	# update display
	printer('Setting Random/Shuffle to: {0}'.format(newState), tag='random')
	hudispdata = {}
	hudispdata['rnd'] = newState
	disp.dispdata(hudispdata)

	# apply newState
	hu_details['random'] = newState
	mpdc.random( newState )
		
	# bluetooth:
	"""
	elif dSettings['source'] == 3:
		pa_sfx('button_feedback')
		bt_shuffle()
	
	else:
		print(' ...  Random/Shuffle not supported for this source.')
	"""
	
	return True

def do_update():

	global Sources

	def locmus_update( folder ):
		
		global mpdc
		
		#Update database
		mpdc.update( folder, False ) # False = Don't wait for completion (will be picked up by the mpd callback)

	# get local folders
	for source in Sources.getAll():
	
		if source['name'] == 'locmus':
			if 'subsources' in source and len(source['subsources']) > 0:
				printer('Updating local database')
				for subsource in source['subsources']:
					if 'mpd_dir' in subsource:
						mpd_dir = subsource['mpd_dir']
						locmus_update(mpd_dir)
			else:
				printer('No local databases configured', level=LL_WARNING)
		else:
			printer('No local source available', level=LL_WARNING)

			
	# the only update is an locmus_update ;-)
	#locmus_update()

# ********************************************************************************
# Misc. functions
#

# turn off the device
def shutdown():
	global configuration
	global cSettings
	global Sources

	# save settings (hu_settings)
	cSettings.save()

	# stop source (hu_source)
	Sources.sourceStop()
	
	# call shutdown command
	"""  This command may be different on different distributions, therefore it's saved in the configuration
	     Debian:    call(["systemctl", "poweroff", "-i"])
	     Buildroot: call(["halt"])
	"""
	call(configuration['shutdown_cmd'])

# ********************************************************************************
# Initialization functions
#
#  - Loggers
#  - Configuration
#  - Operational settings
#

# Initiate logger.
def init_logging():

	global logger

	# logging is global
	logger = logging.getLogger('headunit')
	logger.setLevel(logging.DEBUG)

# Initiate logging to console.
# Use logger.info instead of print.
def init_logging_c():

	global logger

	# create console handler
	ch = logging.StreamHandler()
	ch.setLevel(arg_loglevel)

	# create formatters
	fmtr_ch = ColoredFormatter("%(tag)s%(message)s")

	# add formatter to handlers
	ch.setFormatter(fmtr_ch)

	# add ch to logger
	logger.addHandler(ch)
	
	logger.info('Logging started: Console',extra={'tag':'log'})

# Initiate logging to log file.
# Use logger.info instead of print.
def init_logging_f( logdir, logfile, runcount ):

	global logger

	# create the log dir, if it doesn't exist yet
	if not os.path.exists(logdir):
		os.makedirs(logdir)
	
	iCounterLen = 6
	currlogfile = os.path.join(logdir, logfile+'.'+str(runcount).rjust(iCounterLen,'0')+'.log')
	
	# create file handler
	fh = logging.FileHandler(currlogfile)
	fh.setLevel(logging.DEBUG)

	# create formatters
	fmtr_fh = RemAnsiFormatter("%(asctime)-9s [%(levelname)-8s] %(tag)s %(message)s")
		
	# add formatter to handlers
	fh.setFormatter(fmtr_fh)

	# add fh to logger
	logger.addHandler(fh)
	
	logger.info('Logging started: File ({0})'.format(currlogfile),extra={'tag':'log'})
	
	#
	# housekeeping
	#
	
	# remove all but the last 10 runs
	iStart = len(logfile)+1
	iRemTo = runcount-10
	
	# loop through the logdir
	for filename in os.listdir(logdir):
		if filename.startswith(logfile) and filename.endswith('.log'):
			#print filename #(os.path.join(directory, filename))
			logCounter = filename[iStart:iStart+iCounterLen]
			if int(logCounter) <= iRemTo:
				#print os.path.join(logdir, filename)
				os.remove(os.path.join(logdir, filename))
				logger.debug('Removing old log file: {0}'.format(filename),extra={'tag':'log'})


# address may be a tuple consisting of (host, port) or a string such as '/dev/log'
def init_logging_s( address=('localhost', SYSLOG_UDP_PORT), facility="HEADUNIT", socktype=socket.SOCK_DGRAM ):

	global logger
	
	# create syslog handler
	#sh = logging.handlers.SysLogHandler(address=address, facility=facility, socktype=socktype)
	sh = logging.handlers.SysLogHandler(address=address, socktype=socktype)
	sh.setLevel(logging.DEBUG)

	# create formatters
	fmtr_sh = RemAnsiFormatter("%(asctime)-9s [%(levelname)-8s] %(tag)s %(message)s")
		
	# add formatter to handlers
	sh.setFormatter(fmtr_sh)

	# add sh to logger
	logger.addHandler(sh)
	
	logger.info('Logging started',extra={'tag':'log'})
	
	
def init_load_config():
	configuration = configuration_load( CONFIG_FILE, CONFIG_FILE_DEFAULT )
	if configuration == None:
		exit()

	def test_config( key, dict, descr="" ):
		if key in dict:
			printer('{0:20}:     {1}'.format(key+' '+descr,dict[key]), level=LL_DEBUG, tag="CONFIG")
		else:
			printer('{0} {1} missing in configuration!!'.format(key,descr), level=LL_CRITICAL, tag="CONFIG")
	
	# Print summary of loaded config TODO: output level = debug
	if 'directories' in configuration:
		test_config('controls', configuration['directories'], "directory")
		test_config('config', configuration['directories'], "directory")
		test_config('log', configuration['directories'], "directory")
		test_config('sfx', configuration['directories'], "directory")
	else:
		printer('Directory configuration missing!!', level=LL_CRITICAL)

	if 'files' in configuration:
		if 'log' in configuration['files']:
			pass
		else:
			printer('Log file missing in configuration!!', level=LL_CRITICAL)
		test_config('settings', configuration['files'], "file")		

	return configuration


def test_match( dTest, dMatchAgainst ):
	matches = set(dTest.items()) & set(dMatchAgainst.items())
	if len(matches) == len(dTest):
		return True
	else:
		return False


def QuickPlay( prevSource, prevSourceSub ):

	if prevSource == "":
		printer ('No previous source.', tag='QPLAY')
		return None


	def bla_refactored( prevSourceName, prevSourceSub, doCheck ):

		global Sources
		retSource = []
		
		ix = 0
		for source in Sources.getAll():
			#print "{0} Source {1}".format(ix,source["name"])
			#print source
			if source['name'] == prevSourceName:
				if not source['template']:
					#print "......... Previous Source: {0}; no subsources".format(source['name'])
					#print "......... Checking if available.."
					if not Sources.sourceCheck( ix ):
						#print "---END--- Play first available source."
						return []
						#return False
					else:
						#print "---END--- CONTINUING playback of this subsource!"
						retSource.append(ix)
						return retSource

				else:
					#print "......... Previous Source: {0}; is template, checking for subsources...>".format(source['name'])
					if not 'subsources' in source:
						#print "......... Previous Source: {0}; is template, but has no subsources.".format(source['name'])
						#print "---END--- no suitable source to continue playing... Play first available source."
						return []
						#return False
					else:
						#print "......... Previous Source: {0}; is template, and has subsources, testing match...>".format(source['name'])
						ix_ss = 0
						for subsource in source['subsources']:
							#print j
							#print subsource
							if test_match( prevSourceSub, subsource ):
								#print "> ..MATCH! (todo: stop)"
								if doCheck:
									# Check if REALLY available...
									# !!! TODO: MAKE THIS MORE UNIVERSAL..... !!!
									if source['name'] in ['media','locmus']:
										#print "OPTION 1 media/locmus"
										#if not Sources.sourceCheckParams( ix, ['/media/PIHU_DATA'] ):
										if not Sources.sourceCheck( ix, ix_ss ): #subsource['mountpoint'] ):
											#print "directory not present or empty [todo: or no music in mpd]"
											#print "---END--- Play first available source."
											return []
											#return False
										else:
											#print "---END--- CONTINUING playback of this subsource!"
											retSource.append(ix)
											retSource.append(ix_ss)
											return retSource
											#return True
									#TEMPORARY:
									else:
										if not Sources.sourceCheck( ix ):
											#print "---END--- Play first available source."
											return []
											#return False
										else:
											#print "---END--- CONTINUING playback of this subsource!"
											retSource.append(ix)
											retSource.append(ix_ss)
											return retSource
											#return True
										
								else:
									# No check, clear for available..
									#print "---END--- CONTINUING playback of this subsource!"
									retSource.append(ix)
									retSource.append(ix_ss)
									return retSource
									#return True
							else:
								pass
								#print "> ..no match on this one"
								#print "---END--- no suitable source or subsource to continue playing... Play first available source."
							ix_ss+=1
				# Nothing matched for this source name
				return []
				#return False
			ix+=1

		# Source name was not found.. (strange situation...)
		return []
		#return False

	if not prevSource == "":
		printer("Previous source: {0} {1}".format(prevSource, prevSourceSub), tag='QPLAY' )
		prevIx = bla_refactored( prevSource, prevSourceSub, True ) #PlayPrevSource()
		if len(prevIx) == 1:
			printer ('Continuing playback', tag='QPLAY')
			hu_play(prevIx[0])
			#Sources.setCurrent(prevIx[0])
			#dLoaded = load_current_resume()
			#Sources.sourcePlay(dLoaded)
			return True
						
		elif len(prevIx) == 2:
			printer ('Continuing playback (subsource)', tag='QPLAY')
			hu_play(prevIx[0],prevIx[1])
			#Sources.setCurrent(prevIx[0],prevIx[1])
			#dLoaded = load_current_resume()
			#Sources.sourcePlay(dLoaded)
			return True

		else:
			printer ('Continuing playback not available.', tag='QPLAY')
			return False
		

def worker_queue_prio():
	while True:
	#	while not qPrio.empty():
		item = qPrio.get()
		#item = qPrio.get_nowait()
		command = item['command']
		
		printer("Priority Queue: Picking up: {0}".format(item), tag='QUEUE')
		if command == 'VOL_UP':
			volm.set('+5%')
		elif command == 'VOL_DOWN':
			volm.set('-5%')
		elif command == 'ATT':
			#volm.set('20%')
			#volume_att_toggle()
			volume_att()
		elif command == 'OFF':
			shutdown()
		else:
			printer('Undefined task', level=LL_ERROR, tag='QUEUE')
		
		# sign off task
		qPrio.task_done()

def cb_queue():

	#while not qBlock.empty():
	if not qBlock.empty():
		item = qBlock.get()
		printer("Blocking Queue [CB-idle]: Picking up: {0}".format(item), tag='QUEUE')
		
		command = item['command']
		
		if command == 'SOURCE':
			do_source()
		elif command == 'SEEK_NEXT':
			Sources.sourceSeekNext()
		elif command == 'SEEK_PREV':
			Sources.sourceSeekPrev()
		elif command == 'DIR_NEXT':
			dir_next()
		elif command == 'DIR_PREV':
			print( "TODO!!" )
		elif command == 'SHUFFLE':
			set_random( 'toggle' )
		elif command == 'DEVADD':
			device = item['device']
			udisk_add(device)
			#ret = udisk_add(device)
			#if ret:
				#hu_play(
				# if autoplay: #TODO
				#print "TODO: auto-play"
				#print "TODO: determine dir-list"
		elif command == 'DEVREM':
			device = item['device']
			udisk_rem(device)
		else:
			printer('Undefined task', level=LL_ERROR, tag='QUEUE')

		qBlock.task_done()
	
	# return True to automatically be rescheduled
	return True

def worker_queue_async():
	while True:
		item = qAsync.get()
		printer("Async Queue: Picking up: {0}".format(item), tag='QUEUE')
		if item == 'UPDATE':
			do_update()
		
		# sign off task
		qAsync.task_done()

"""
def mq_recv():
	message = subscriber.recv()
	parse_message(message)
	
	#if message == '/player/track/next':
	#	Sources.sourceSeekNext()
	#else:
	#	print("NO MESSAGE! sorry..")
		
	return True

def parse_message(message):
		path = []
		params = []
		path_cmd = message.split(" ")
		for pathpart in path_cmd[0].split("/"):
			if pathpart:
				path.append(pathpart.lower())
			
		base_topic = path[0]
		cmd_par = path_cmd[1].split(":")

		if len(cmd_par) == 1:
			command = cmd_par[0].lower()
		elif len(cmd_par) == 2:
			command = cmd_par[0].lower()
			param = cmd_par[1]

			for parpart in param.split(","):
				if parpart:
					params.append(parpart)
		else:
			print("Malformed message!")
			return False

		print("[MQ] Received Path: {0}; Command: {1}; Parameters: {2}".format(path,command,params))
		

		item = []	# or set?
		# check if base_topic ('player','event', etc.) function exists
		if base_topic in globals():
			# remove first item (base topic)
			del path[0]
			# if queue is empty, execute right away, else add to queue
			if queue_actions.empty():
				# execute:
				globals()[base_topic](path, command, params)
			else:
				# put in queue:
				item.append(base_topic)
				item.append(path)
				item.append(command)
				item.append(params)
				queue_actions.put(item, False) # False=Non-Blocking
"""
	
#********************************************************************************
#
# DBus Dispay Signals
#

class dbusDisplay(dbus.service.Object):
	def __init__(self, conn, object_path='/com/arctura/display'):
		dbus.service.Object.__init__(self, conn, object_path)

	#decided to just send everything as string, should be easier to handle...:
	#dbus.service.signal("com.arctura.display", signature='a{sv}')
	@dbus.service.signal("com.arctura.display", signature='a{ss}')
	def dispdata(self, dispdata):
		pass

class dbusVolume(dbus.service.Object):
	def __init__(self, conn, object_path='/com/arctura/volume'):
		dbus.service.Object.__init__(self, conn, object_path)

	@dbus.service.signal("com.arctura.volume", signature='s')
	def set(self, volume):
		pass

server_name = "com.arctura.hu"
interface_name = "com.arctura.hu"
object_name = "/com/arctura/hu"
#class MainInstance(ExportedGObject):
class MainInstance(dbus.service.Object):

	def __init__(self):
		#super(mpdControl,self).__init__(bus_name, "/com/arctura/hu")

		#
		# DBus: system bus
		# On a root only embedded system there may not be a usable session bus
		#
		try:
			bus = dbus.SystemBus()
		except dbus.DBusException:
			raise RuntimeError("No D-Bus connection")

		if bus.name_has_owner(server_name):
			raise NameError
				
		bus_name = dbus.service.BusName(server_name, bus=bus)
		super(MainInstance, self).__init__(conn=bus,
											object_path=object_name,
											bus_name=bus_name)

		

#********************************************************************************
#
# Parse command line arguments and environment variables
# Command line takes precedence over environment variables and settings.json
#
def parse_args():
	import argparse

	ENV_CONFIG_FILE = os.getenv('HU_CONFIG_FILE')
	ENV_SOURCE = os.getenv('HU_SOURCE')

	parser = argparse.ArgumentParser(description='Uhmmmsssszzz...')
	parser.add_argument('--loglevel', action='store', default=LL_INFO, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('--source', action='store')
	parser.add_argument('--subsource', action='store')	
	parser.add_argument('--boot', action='store_true')
	parser.add_argument('-b', action='store_true')	# background, ie. no output to console
	args = parser.parse_args()

	arg_loglevel = args.loglevel
	arg_source = args.source
	arg_subsource = args.subsource
	arg_boot = args.boot


#********************************************************************************
#
# Essential Initialization
#
def init():
	#
	# Stop if we're already running
	#
	#if check_running(PID_FILE):
	#	exit()

	#
	# Start logging to console
	#
	# TODO: get settings from configuration.json
	init_logging()
	init_logging_c()	

#********************************************************************************
#
# Setting up prior to mainloop
#
def setup():

	global SOURCE
	global SOURCE_SUB

	#
	# Load main configuration
	#
	configuration = init_load_config()

	#
	# Load PulseAudio SFX
	#
	#
	pa_sfx_load( configuration['directories']['sfx'] )

	#
	# Load operational settings
	#
	#			#TODO: change this name
	cSettings = huSettings( os.path.join(configuration['directories']['config'],configuration['files']['settings']),
							defaultSettings=configuration['default_settings'] )

	#
	# Start logging to file
	#
	# TODO: get settings from configuration.json
	init_logging_f( configuration['directories']['log'],
					configuration['files']['log'],
					cSettings.incrRunCounter( max=999999 ) )
					#settings['runcount'] )

	#
	# Start logging to syslog
	#
	# TODO: get settings from configuration.json
	init_logging_s( address='/dev/log' )
	
	#
	# Determine starting source
	#
	# Order:
	# 1) command line
	# 2) environment variable
	# 3) settings.json file
	
	if arg_source:
		SOURCE = arg_source
		SOURCE_SUB = arg_sub_source
	elif ENV_SOURCE:
		SOURCE = ENV_SOURCE
		SOURCE_SUB = None
	else:
	
		prevSource = cSettings.get_key('source')
		prevSourceSub = cSettings.get_key('subsourcekey')

		if prevSource:
			SOURCE = prevSource
			SOURCE_SUB = prevSourceSub
		else:
			SOURCE = None
			SOURCE_SUB = None
			
	print('SOURCE,SUBSOURCE: {0},{1}'.format(SOURCE,SOURCE_SUB))
	
	#
	# i forgot, what's this for?
	#
	if arg_boot:
		BOOT = args.boot
	else:
		BOOT = False
	
	
	#
	# Set/Restore volume level
	#
	#
	# Legacy: #TODO
	#settings = cSettings.get()
	#VolPulse = VolumeController('alsa_output.platform-soc_sound.analog-stereo')
	#VolPulse.set( settings['volume'] )


	#
	# "Splash Screen": Display version and play startup tune
	#
	#
	myprint('Headunit.py version {0}'.format(__version__),tag='SYSTEM')
	pa_sfx('startup')

	#
	# ZeroMQ
	#
	zmq_connect()

	#
	# create menu structure
	#
	#print configuration[
	#huMenu = Menu()
	#testentry = { "entry": "Browse tracks",
	#  "entry_name": "browse_track"}
	#huMenu.add( testentry )



	#print "TESTING TESTING"
	#Sources.setAvailableIx(0,True)
	#Sources.setCurrent(0)
	#Sources.sourcePlay()
	#exit()

	""" DEBUGGING....
	print "DEBUG!"
	prevSource = {'name': 'fm'}
	prevSourceSub = {}

	print bla_refactored( prevSource, prevSourceSub )
		
	print "DEBUG!"
	prevSource = {'name': 'locmus'}
	prevSourceSub = {'mountpoint':'/media/PIHU_DATA'}
	bFound = False

	print bla_refactored( prevSource, prevSourceSub )


	print "DEBUG!"
	prevSource = {'name': 'locmus'}
	prevSourceSub = {'mountpoint':'/media/PIHU_DATA3'}
	bFound = False

	print bla_refactored( prevSource, prevSourceSub )
	"""


	#debug
	#huMenu.menuDisplay( header=True )
	#huMenu.menuDisplay( entry=1, header=True )
	#print huMenu.getMenu( [1,0] )

	#
	# import control plugins (disabled)
	#
	"""
	myprint('Loading Control Plugins...',tag='SYSTEM')
	from plugin_control import *

	threads = []
	# loop through the control plugin dir
	for filename in os.listdir( configuration['directories']['controls'] ):
			#if filename.startswith('') and
			if filename.endswith('.py'):
				pathfilename = os.path.join( configuration['directories']['controls'], filename )
				#t = threading.Thread(target=plugin_execute, args=(pathfilename,))
				#t.setDaemon(True)
				p = Process(target=plugin_execute, args=(pathfilename,))
				p.daemon = True
				threads.append(p)
				#t.start()	WORKAROUND

	# loop through the output plugin dir
	for filename in os.listdir( configuration['directories']['output'] ):
			#if filename.startswith('') and
			if filename.endswith('.py'):
				pathfilename = os.path.join( configuration['directories']['output'], filename )
				#t = threading.Thread(target=plugin_execute, args=(pathfilename,))
				#t.setDaemon(True)
				p = Process(target=plugin_execute, args=(pathfilename,))
				p.daemon = True
				threads.append(p)
				#t.start()	WORKAROUND

	# NOTE: Plugins are now loading in the background, in parallel to code below.
	# NOTE: This can really interfere, in a way I don't understand.. executing the threads later helps... somehow..
	# NOTE: For NOW, we'll just execute the threads after the loading of the "other" plugins...


	#
	# Load mpd dbus listener
	#
	#
	#t = threading.Thread(target=plugin_execute, args=('/mnt/PIHU_APP/defender-headunit/dbus_mpd.py',))
	#t.setDaemon(True)
	p = Process(target=plugin_execute, args=('/mnt/PIHU_APP/defender-headunit/dbus_mpd.py',))
	p.daemon = True
	threads.append(p)


	#
	# load other plugins
	#
	myprint('Loading Other Plugins...',tag='SYSTEM')
	from plugin_other import *

	# WORKAROUND...
	#for p in threads:
	#	p.start()
	"""

	# LCD (TODO: move to plugins)
	#from hu_lcd import *
	#disp = lcd_mgr()
	#disp.lcd_text('Welcome v0.1.4.8')


	#
	# end of initialization
	#
	#********************************************************************************
	myprint('INITIALIZATION FINISHED', level=logging.INFO, tag="SYSTEM")


#********************************************************************************
#
# Mainloop
#
#def main():

#
# QuickPlay
#



print "XX DEBUG XX"
print SOURCE
print SOURCE_SUB

print "XX DEBUG XX"
SOURCE = None

# BOOT is true for 'early boot'
#if BOOT and not prevSource = "" and not prevSource == SOURCE:

#if not prevSource == SOURCE and not prevSource:
#	print('Quickplay failed due mismatching source')
#	exit()

if not SOURCE:
	printer ('No previous source.', tag='QPLAY')
	# following is already done on start by source-controller:
	#zmq_send('/source/check')
	#Sources.sourceCheckAll()
	#printSummary(Sources)
	printer ('Starting first available source', tag='QPLAY')
	zmq_send('/source/next')
	#Sources.next()
	zmq_send('/source/state', 'SET:play')
	#hu_play(resume=False)
	
else:
	ret = QuickPlay( prevSource,
					 prevSourceSub )
					 
	if ret:
		printer ('Checking other sources...', tag='QPLAY')
		# TODO: the prev. source is now checked again.. this is not efficient..
		Sources.sourceCheckAll()
		printSummary(Sources)
		
	else:
		printer ('Continuing playback not available, checking all sources...', tag='QPLAY')
		Sources.sourceCheckAll()
		printSummary(Sources)
		printer ('Starting first available source', tag='QPLAY')
		Sources.next()
		hu_play(resume=False)

print "XX DEBUG XX"
exit()

# Save Settings
currSrc = Sources.getComposite()
cSettings.set('source',currSrc['name'])

# update sub-source key (in case of sub-source)
if 'subsource' in currSrc:
	subsource_key = {}
	for key in currSrc['subsource_key']:
		subsource_key[key] = currSrc['subsource'][key]
	cSettings.set('subsourcekey', subsource_key)

cSettings.save()

		
	   
"""
else:
	for source in Sources.getAll():
		if source['name'] == prevSource:
			print("!! PREVIOUS SOURCE: {0}".format(source['name']))
			#if 'label' in source:
			index = Sources.getIndex
			print("!! CHECKING IF IT IS AVAILABLE...")
			
			Sources.sourceCheck(
"""
# First, try previously active source


# on demand...
#plugin_sources.media.media_add('/media/USBDRIVE', Sources)


#myprint('A WARNING', level=logging.WARNING, tag="test")
#logger.warning('Another WARNING', extra={'tag':'test'})

# Save operational settings
#dSettings1 = {"source": -1, 'volume': 99, 'mediasource': -1, 'medialabel': ''}	 # No need to save random, we don't want to save that (?)
#settings_save( sFileSettings, dSettings1 )

#
# Setting up worker threads
#
printer('Setting up queues and worker threads')


qPrio = Queue(maxsize=4)	# Short stuff that can run anytime:
qBlock = Queue(maxsize=4)	# Blocking stuff that needs to run in sequence
qAsync = Queue(maxsize=4)	# Long stuff that can run anytime (but may occasionally do a reality check):

t = threading.Thread(target=worker_queue_prio)
#p = Process(target=worker_queue_prio)
t.setDaemon(True)
#p.daemon = True
t.start()
#p.join()

# disabled: see idle_add Queue Handler below
# t = threading.Thread(target=worker_queue_blocking)
# p = Process(target=worker_queue_blocking)
# t.setDaemon(True)
# p.daemon = True
# t.start()

t = threading.Thread(target=worker_queue_async)
#p = Process(target=worker_queue_async)
t.setDaemon(True)
#p.daemon = True


# DISABLED FOR ZMQ:
#t.start()


"""
qBlock.put("SOURCE")
qPrio.put("VOL_UP")
qBlock.put("NEXT")
qPrio.put("VOL_UP")
qPrio.put("VOL_ATT")
qBlock.put("SHUFFLE")
qPrio.put("SHUTDOWN")

exit()
"""

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
gobject.timeout_add_seconds(30,cb_timer1)

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
disp = dbusDisplay(bus)
volm = dbusVolume(bus)


"""
time.sleep(5)	#wait for the plugin to be ready

hudispdata = {}
hudispdata['rnd'] = "1"
hudispdata['artist'] = "The Midnight"
disp.dispdata(hudispdata)

time.sleep(5)
hudispdata = {}
hudispdata['rnd'] = "0"
disp.dispdata(hudispdata)

time.sleep(5)
hudispdata = {}
hudispdata['att'] = "1"
disp.dispdata(hudispdata)

exit()
"""

#
# Connect Callback functions to DBus Signals
#
#bus.add_signal_receiver(cb_mpd_event, dbus_interface = "com.arctura.mpd")
#bus.add_signal_receiver(cb_remote_btn_press, dbus_interface = "com.arctura.remote")
#bus.add_signal_receiver(cb_remote_btn_press2, dbus_interface = "com.arctura.keyboard")
#bus.add_signal_receiver(cb_udisk_dev_add, signal_name='DeviceAdded', dbus_interface="org.freedesktop.UDisks")
#bus.add_signal_receiver(cb_udisk_dev_rem, signal_name='DeviceRemoved', dbus_interface="org.freedesktop.UDisks")
#bus.add_signal_receiver(cb_ifup, signal_name='ifup', dbus_interface="com.arctura.ifup")
#bus.add_signal_receiver(cb_ifdn, signal_name='ifdn', dbus_interface="com.arctura.ifdn")


#
# Start the blocking main loop...
#
#with PidFile(PID_FILE) as p:
try:
	mainloop.run()
finally:
	mainloop.quit()


# TODO
# problem is that the setup() imports modules, yielding: SyntaxWarning: import * only allowed at module level
# another issue is that all global vars need to be defined (not really a problem i think..)

if __name__ == '__main__':
	parse_args()
	init()
	setup()
	main()

	