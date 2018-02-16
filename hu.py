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
# media/<uuid>.p			
# locmus/<mountpoint>.p		
# smb/<ip_mountpoint>.p		172_16_8_11_music
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
from hu_logger import *

#********************************************************************************
#
# Parse command line arguments
#
#

import argparse

parser = argparse.ArgumentParser(description='Uhmmmsssszzz...')
parser.add_argument('--loglevel', action='store', default=LL_INFO, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
args = parser.parse_args()

arg_loglevel = args.loglevel

#********************************************************************************
#
#
#

# temporary / debugging:
import time

# load json source configuration
import json

# dynamic module loading
import sys
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


# GLOBAL vars
Sources = SourceController()	#TODO: rename "Sources" -- confusing name
mpdc = None
disp = None
arMpcPlaylistDirs = [ ]			#TODO: should probably not be global...

# CONSTANTS
CONFIG_FILE_DEFAULT = '/mnt/PIHU_APP/defender-headunit/config/configuration.json'
CONFIG_FILE = '/mnt/PIHU_CONFIG/configuration.json'
VERSION = "1.0.0"

hu_details = { 'track':None, 'random':'off', 'repeat':True }

def volume_att_toggle():
	hudispdata = {}
	hudispdata['att'] = '1'
	disp.dispdata(hudispdata)
	return None

def volume_up():
	print('Vol Up')
	return None

def volume_down():
	print('Vol Down')
	return None
	
# ********************************************************************************
# Output wrapper
#
def printer( message, level=20, continuation=False, tag='SYSTEM' ):
	#TODO: test if headunit logger exist...
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

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
def save_current_position():

	global Sources
	global mpdc
	
	currSrc = Sources.getComposite()
	
	# create filename
	source_name = currSrc["name"]
	if 'filename_save' in currSrc:
		source_key = currSrc["filename_save"][0]	#eg "mountpoint"
		if source_key in currSrc["subsource"]:
			source_key_value = slugify( currSrc["subsource"][source_key] )
		else:
			printer("Error creating savefile, source_key ({0}) doesn't exist".format(source_key))
			source_key = "untitled"
	else:
		source_key = "untitled"

	# get time into track
	timeelapsed = status['time']
	
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
	if 'filename_save' in currSrc:
		source_key = currSrc["filename_save"][0]	#eg "mountpoint"
		if source_key in currSrc["subsource"]:
			source_key_value = slugify( currSrc["subsource"][source_key] )
		else:
			printer("Error creating savefile, source_key ({0}) doesn't exist".format(source_key))
			source_key = "untitled"
	else:
		source_key = "untitled"
				
	# load file
	printer('Loading playlist position for: {0}: {1}'.format(source_name,source_key_value))

	# create path, if it doesn't exist yet..
	pckl_path = os.path.join('/mnt/PIHU_CONFIG',source_name)
	if not os.path.exists(pckl_path):
		printer('ERROR: Save file path not found',level=LL_ERROR)
		return None
	# TODO: check if file exists
	pckl_file = os.path.join(pckl_path,source_key_value + ".p")
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

	global Sources

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
	global Sources
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
				save_current_position()

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
	
	elif event == "ifup":
		printer(" ...  WiFi interface up: checking network related sources", tag='MPD')
		stream_check()
		smb_check()
		
	elif event == "ifdown":
		printer(" ...  WiFi interface down: marking network related sources unavailable", tag='MPD')
		Sources.setAvailable('depNetwork',True,False)
		
	else:
		printer(' ...  unknown event (no action)', tag='MPD')
		
# Timer 1: executed every 30 seconds
def cb_timer1():

	global cSettings
	#global disp

	printer('Interval function [30 second]', level=LL_DEBUG, tag="TIMER1")

	# save current position
	save_current_position()
	
	# WHAT'S THE POINT OF THIS?:
	# save settings (hu_settings)
	cSettings.save()
	
	#hudispdata = {}
	#hudispdata['src'] = "USB"		#temp.
	#disp.dispdata(hudispdata)

	return True

#Timer 2: Test the queuing
def cb_timer2():
	qPrio.put('VOL_UP',False)
	return True

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

def udisk_details( device, action ):

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
	mytag = ".UDISKS"
	ix = Sources.getIndex('name','media')
	
	if action == 'A':

		try:
			DeviceFile = device_props.Get('org.freedesktop.UDisks.Device',"DeviceFile")
			printer(" > DeviceFile: {0}".format(DeviceFile),tag=mytag)
			
		except:
			printer(" > DeviceFile is unset... Aborting...",tag=mytag)
			return 1
		
		# Check if DeviceIsMediaAvailable...
		try:    
			is_media_available = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsMediaAvailable")
			if is_media_available:
				printer(" > Media available",tag=mytag)
			else:
				printer(" > Media not available... Aborting...",tag=mytag)
				return 1
		except:
			printer(" > DeviceIsMediaAvailable is not set... Aborting...",tag=mytag)
			return 1
		
		# Check if it is a Partition...
		try:
			is_partition = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsPartition")
			if is_partition:
				printer(" > Device is partition",tag=mytag)
		except:
			printer(" > DeviceIsPartition is not set... Aborting...",tag=mytag)
			return 1

		if not is_partition:
			printer(" > DeviceIsPartition is not set... Aborting...",tag=mytag)
			return 1


		#queue('blocking','DEVREM','button_devrem')
	
		#IdLabel: SJOERD
		#DriveSerial: 0014857749DCFD20C7F95F31
		#DeviceMountPaths: dbus.Array([dbus.String(u'/media/SJOERD')], signature=dbus.Signature('s'), variant_level=1)
		#DeviceFileById: dbus.Array([dbus.String(u'/dev/disk/by-id/usb-Kingston_DataTraveler_SE9_0014857749DCFD20C7F95F31-0:0-part1'), dbus.String(u'/dev/disk/by-uuid/D2B6-F8B3')], signature=dbus.Signature('s'), variant_level=1)
		
		#
		# DeviceFile contains the device name of the added device..
		#
		
		# get mountpoint from "mount" command
		mountpoint = subprocess.check_output("mount | egrep "+DeviceFile+" | cut -d ' ' -f 3", shell=True).rstrip('\n')

		# check if we have a mountpoint..
		if mountpoint == "":
			printer(" > No mountpoint found. Stopping.",tag=mytag)
			return 1
		
		# get the partition uuid from the "blkid" command
		partuuid = subprocess.check_output("blkid "+DeviceFile+" -s PARTUUID -o value", shell=True).rstrip('\n')

		# derive USB label from mountpoint
		sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
		
		# logging
		printer(" > Mounted on: {0} (label: {1})".format(mountpoint,sUsbLabel),tag=mytag)
		
		# add source
		# TODO, DRY-conflict met __media_add_subsource in media.py
		
		# construct the subsource
		subsource = {}
		subsource['name'] = 'media'
		subsource['displayname'] = 'media: ' + mountpoint
		subsource['order'] = 0		# no ordering
		subsource['mountpoint'] = mountpoint
		subsource['mpd_dir'] = mountpoint[7:]		# TODO -- ASSUMING /media
		subsource['label'] = sUsbLabel
		subsource['uuid'] = partuuid
		subsource['device'] = DeviceFile
		isAdded = Sources.addSub(ix, subsource)

		# check source, if added successfully
		if isAdded:
			# get subsource index
			ix_ss = Sources.getIndexSub(ix, 'device', DeviceFile)
			
			# check, and if available play
			if Sources.sourceCheck( ix, ix_ss ):
				Sources.setCurrent( ix, ix_ss )
				Sources.sourcePlay()
		
		# display overview
		printSummary(Sources)
		
	elif action == 'R':
		# The removed mountpoint can be derived from str(device)
	
		# WHAT IF IT'S PLAYING??
		# TODO CHECK IF PLAYING!!
	
		# TODO ignore /dev/sda
		
		# form the partition device name
		partition = "/dev/"+os.path.basename(str(device))

		# search for the subsource index
		ix_ss = Sources.getIndexSub(ix, 'device', partition)
		if not ix_ss is None:
		
			printer(' > Found {0}. Removing...'.format(partition))
			
			# remove subsource
			Sources.remSub(ix, ix_ss)
		
			# display overview
			printSummary(Sources)
		else:
			printer(' > Not a subsource: {0}'.format(partition))	
		
	else:
		printer(" > ERROR: Invalid action.",tag=mytag)
		pa_sfx('error')

# ********************************************************************************
# Headunit functions
#

def do_source():

	global Sources
	global cSettings
		
	# if more than one source available...	
	if Sources.getAvailableCnt() > 1:
		# go to next source
		res = Sources.next()
		if not res == None:

			#
			# if succesful, play new source
			#
			
			Sources.sourceStop()
			Sources.sourcePlay()
			#
			# update operational settings
			#
			
			# get current index(es)
			arCurrIx = Sources.getIndexCurrent()
			#if arCurrIx[1] == None:
			currSrc = Sources.get(None)
			#else:
			#	currSrc = Sources.get(None)
			#	currSSrc = Sources.getSubSource(arCurrIx[0],arCurrIx[1])
			#
			#print "currSrc:"
			#print currSrc
			
			#print "currSSrc:"
			#print currSSrc
			
			#print "++:"
			#print Sources.getComposite()
			
			# update source
			cSettings.set('source',currSrc['name'])
			
			# update sub-source key (in case of sub-source)
			if not arCurrIx[1] == None:
				subsource_key = {}
				for key in currSrc['subsource_key']:
					subsource_key[key] = currSrc['subsources'][arCurrIx[1]][key]
				cSettings.set('subsourcekey', subsource_key)
			
			# commit changes
			cSettings.save()

			#
			# update display
			#
			
			hudispdata = {}
			if currSrc['name'] == 'fm':
				hudispdata['src'] = 'FM'
			elif currSrc['name'] == 'media':
				hudispdata['src'] = 'USB'
				hudispdata['info'] = "Removable Media"
				hudispdata['info1'] = "label: " + currSrc['subsources'][arCurrIx[1]]['label']
			elif currSrc['name'] == 'locmus':
				hudispdata['src'] = 'INT'
				hudispdata['info'] = "Internal Storage"
				if len(currSrc['subsources']) > 1:
					hudispdata['info1'] = "folder: " + currSrc['subsources'][arCurrIx[1]]['label']
			elif currSrc['name'] == 'bt':
				hudispdata['src'] = 'BT'
				hudispdata['info'] = "Bluetooth"
			elif currSrc['name'] == 'line':
				hudispdata['src'] = 'AUX'
				hudispdata['info'] = "AUX Line-In"
			elif currSrc['name'] == 'stream':
				hudispdata['src'] = 'WEB'
				hudispdata['info'] = "Internet Radio"
			elif currSrc['name'] == 'smb':
				hudispdata['src'] = 'NET'
				hudispdata['info'] = "Network Shares"
			disp.dispdata(hudispdata)

			# if source is MPD and supports directories (don't they all?), gather list of dirs, in separate thread..
			dirList = mpdc.mpc_get_PlaylistDirs()
			print dirList
			
			# TODO: make this better... somehow.
			"""
			if currSrc['name'] == 'fm':
				source_settings = {'freq':'101.10'}	# TODO
			elif currSrc['name'] == 'media':
				source_settings = { 'label':currSrc['label'], 'uuid':currSrc['uuid'] }
			elif currSrc['name'] == 'locmus':
				source_settings = { 'mountpoint':currSrc['mountpoint'] }
			elif currSrc['name'] == 'bt':
				source_settings = {}
			elif currSrc['name'] == 'line':
				source_settings = {}				
			elif currSrc['name'] == 'stream':
				source_settings = { 'uri':'' }	#TODO
			elif currSrc['name'] == 'smb':
				source_settings = { 'mpd_dir':'music' }	#TODO
			
			cSettings.set('source_settings',source_settings)
			"""
			
			# TODO!!
			#printer('TODO!! save subsoure to settings') # add to source_stop() functionss.. #no better to handle it here.. source has no notion of operational settings..

			#testSs = {'mountpoint':'/media/SJOERD'}
			#cSettings.set('source','media')
			#cSettings.set('subsource',testSs)
			
			"""
			if currSrc['name'] == 'fm':
				source_settings = {'freq':'101.10'}	# TODO
			elif currSrc['name'] == 'media':

				if 'label' in currSrc:
					cSettings.set('label',currSrc['label'])
				else:
					cSettings.set('label',"")
				if 'uuid' in currSrc:
					cSettings.set('uuid',currSrc['uuid'])
				else:
					cSettings.set('uuid',"")

			elif currSrc['name'] == 'locmus':

				if 'label' in currSrc:
					cSettings.set('label',currSrc['label'])
				else:
					cSettings.set('label',"")
				if 'uuid' in currSrc:
					cSettings.set('uuid',currSrc['uuid'])
				else:
					cSettings.set('uuid',"")
			
			elif currSrc['name'] == 'bt':
				source_settings = {}
			elif currSrc['name'] == 'line':
				source_settings = {}				
			elif currSrc['name'] == 'stream':
				source_settings = { 'uri':'' }	#TODO
			elif currSrc['name'] == 'smb':
				source_settings = { 'mpd_dir':'music' }	#TODO
				
			"""
		
		printer('Done switching source [OK]')
	elif Sources.getAvailableCnt() == 1:
		printer('Only one source availble. Ignoring button.')
	elif Sources.getAvailableCnt() == 0:
		printer('No available sources.')

	printSummary(Sources)

		
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


# print a source summary
def printSummary(Sources):
	#global Sources
	printer('-- Summary -----------------------------------------------------------', tag='')
	arCurrIx = Sources.getIndexCurrent()
	sCurrent = Sources.get(None)
	
	if not arCurrIx[0] == None and arCurrIx[1] == None:
		sCurrDisplay = sCurrent['displayname']
	elif not arCurrIx[1] == None:
		sCurrDisplay = "" #TODO
		#sCurrDisplay = sCurrent['subsources'][arCurrIx[1]]['displayname']
	else:
		sCurrDisplay = ""
	
	if len(arCurrIx) == 0:
		printer('Current source: None', tag='')
	else:
		printer('Current source: {0} {1}'.format(arCurrIx[0],sCurrDisplay), tag='')
	
	i = 0
	for source in Sources.getAll():

		if 'subsources' in source and len(source['subsources']) > 0:
			for subsource in source['subsources']:
			
				if subsource['available']:
					available = colorize('available    ','light_green')
				else:
					available = colorize('not available','light_red')
		
				if 'mountpoint' in subsource:
					mountpoint = subsource['mountpoint']
					printer(' {0:2d} {1:17} {2} {3}'.format(i,source['displayname'],available,mountpoint), tag='')
		else:
			if source['available']:
				available = colorize('available    ','light_green')
			else:
				available = colorize('not available','light_red')
			printer(' {0:2d} {1:17} {2}'.format(i,source['displayname'],available), tag='')
		
		i += 1
	printer('----------------------------------------------------------------------', tag='')

# Load Source Plugins
def loadSourcePlugins( plugindir ):
	global Sources
	global configuration

	#
	# adds the source:
	# - Load source json configuration
	# - 
	#
	def add_a_source( plugindir, sourcePluginName ):
		configFileName = os.path.join(plugindir,sourcePluginName+'.json')
		if not os.path.exists( configFileName ):
			printer('Configuration not found: {0}'.format(configFileName))
			return False
		
		# load source configuration file
		jsConfigFile = open( configFileName )
		config=json.load(jsConfigFile)
		
		# test if name is unique
		# #TODO

		# fetch module from sys.modules
		# sourceModule = sys.modules['sources.'+sourcePluginName] # MENU..
		
		# 
		for execFunction in ('sourceInit','sourceCheck','sourcePlay','sourceStop','sourceNext','sourcePrev'):
			if execFunction in config:
				#overwrite string with reference to module
				config[execFunction][0] = sys.modules['sources.'+sourcePluginName]

		###if 'sourceClass' in config:
		###	#overwrite string with reference to module
		# add a sourceModule item with a ref. to the module
		config['sourceModule'] = sys.modules['sources.'+sourcePluginName]
		
		# register the source
		isAdded = Sources.add(config)
		# check if the source has a configuration
		if 'defaultconfig' in config:
			# check if configuration is present in the main configuration file
			if not sourcePluginName in configuration['source_config']:
				# insert defaultconfig
				configuration['source_config'][sourcePluginName] = config['defaultconfig']
				configuration_save( CONFIG_FILE, configuration )

		# check if the source has menu items
		"""
		if 'menuitems' in config:
			for menuitem in config['menuitems']:
				# do we have a sub menu that needs to be populated?
				if 'sub' in menuitem:
					if menuitem['sub'].startswith('!'):
						func = menuitem['sub'].lstrip('!')
						menuitem['sub'] = getattr(sourceModule,func)()
						#menuitem['uuid']
				#TODO: re-enable
				#huMenu.add( menuitem )
		"""
		# init source, if successfully added
		if isAdded:
			indexAdded = Sources.getIndex('name',config['name'])
			Sources.sourceInit(indexAdded)
	
	# check if plugin dir exists
	if not os.path.exists(plugindir):
		printer('Source path not found: {0}'.format(plugindir), level=LL_CRITICAL)
		exit()
	
	#
	# loop through all imported modules, picking out the sources
	# execute add_a_source() for every found source
	# #TODO: remove hardcoded reference to "sources.", derive it...
	#
	list_of_sources = []
	for k, v in sys.modules.iteritems():
		if k[0:8] == 'sources.':
			sourcePluginName = k[8:]
			if not str(v).find(plugindir) == -1:
				list_of_sources.append(sourcePluginName)

	# dictionary of modules may change during the adding of the sources, raising a runtime error..
	# therefore we save them in a list and iterate over them in a second loop:
	for sourcePluginName in list_of_sources:
		add_a_source(plugindir, sourcePluginName)

def plugin_execute( script ):
	printer('Starting Plugin: {0}'.format(script))
	#os.system( 'python '+script )
	call(['python',script])


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
			Sources.setCurrent(prevIx[0])
			#EXPERIMENTAL
			dLoaded = load_current_resume()
			print dLoaded
			Sources.sourcePlay(dLoaded)
			#EXPERIMENTAL
			return True
						
		elif len(prevIx) == 2:
			printer ('Continuing playback (subsource)', tag='QPLAY')
			Sources.setCurrent(prevIx[0],prevIx[1])
			#EXPERIMENTAL
			dLoaded = load_current_resume()
			print dLoaded
			Sources.sourcePlay(dLoaded)
			#EXPERIMENTAL
			return True

		else:
			printer ('Continuing playback not available.', tag='QPLAY')
			return False
		

def worker_queue_prio():
	while True:
	#	while not qPrio.empty():
		item = qPrio.get()
		#item = qPrio.get_nowait()
		
		printer("Priority Queue: Picking up: {0}".format(item), tag='QUEUE')
		if item == 'VOL_UP':
			volume_up()
		elif item == 'VOL_DOWN':
			volume_down()
		elif item == 'ATT':
			volume_att_toggle()
		elif item == 'OFF':
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
			udisk_details( device, 'A' )
		elif command == 'DEVREM':
			device = item['device']
			udisk_details( device, 'R' )
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

#********************************************************************************
#
# Initialization
#
#def setup():

#
# Start logging to console
#
#
init_logging()
init_logging_c()

#
# Load main configuration
#
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
#
init_logging_f( configuration['directories']['log'],
				configuration['files']['log'],
				cSettings.incrRunCounter( max=999999 ) )
				#settings['runcount'] )


#
# Set/Restore volume level
#
#
# Legacy: #TODO
settings = cSettings.get()
VolPulse = VolumeController('alsa_output.platform-soc_sound.analog-stereo')
VolPulse.set( settings['volume'] )


#
# "Splash Screen": Display version and play startup tune
#
#
myprint('Headunit.py version {0}'.format(__version__),tag='SYSTEM')
pa_sfx('startup')

#
# create menu structure
#
#print configuration[
#huMenu = Menu()
#testentry = { "entry": "Browse tracks",
#  "entry_name": "browse_track"}
#huMenu.add( testentry )


#
# App. Init
#
#
myprint('Loading Source Plugins...',tag='SYSTEM')
# import sources directory
import sources
# read source config files and start source inits
loadSourcePlugins(os.path.join( os.path.dirname(os.path.abspath(__file__)), 'sources'))


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

# MPD
mpdc = mpdController()

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

prevSource = cSettings.get_key('source')
prevSourceSub = cSettings.get_key('subsourcekey')

if prevSource == "":
	printer ('No previous source.', tag='QPLAY')
	Sources.sourceCheckAll()
	printSummary(Sources)
	printer ('Starting first available source', tag='QPLAY')
	Sources.next()
	Sources.sourcePlay()
	
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
		Sources.sourcePlay()


	   
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
t.start()


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
gobject.idle_add(cb_queue)

#
# DBus: system bus
# On a root only embedded system there may not be a usable session bus
#
bus = dbus.SystemBus()

# Output
disp = dbusDisplay(bus)


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
bus.add_signal_receiver(cb_mpd_event, dbus_interface = "com.arctura.mpd")
bus.add_signal_receiver(cb_remote_btn_press, dbus_interface = "com.arctura.remote")
bus.add_signal_receiver(cb_remote_btn_press2, dbus_interface = "com.arctura.keyboard")
bus.add_signal_receiver(cb_udisk_dev_add, signal_name='DeviceAdded', dbus_interface="org.freedesktop.UDisks")
bus.add_signal_receiver(cb_udisk_dev_rem, signal_name='DeviceRemoved', dbus_interface="org.freedesktop.UDisks")


#
# Start the blocking main loop...
#
try:
	mainloop.run()
finally:
	mainloop.quit()


# TODO
# problem is that the setup() imports modules, yielding: SyntaxWarning: import * only allowed at module level
# another issue is that all global vars need to be defined (not really a problem i think..)
"""
if __name__ == '__main__':
	setup()
	main()
"""
	
