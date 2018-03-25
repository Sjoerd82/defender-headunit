#!/usr/bin/python

#
# A car's headunit.
# Venema, S.R.G.
# 2018-03-17
# License: MIT
#
# HEADUNIT is the main script in a constellation of micro-services.
# This script acts as a watchdog and serves some basic system functions.
#
# The microservices are either started via init.d or via this script.
#
# ARGUMENTS:
#? --resume
#? --source		resume|source name
#? --subsource	
#

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
# on the console and written to the syslog or a logfile.
#
# When given the -b ("background") argument all output is written to the syslog,
# otherwise it's written to the console.
#
# The logfile writer is currently not used.
#
# Please don't use the print() function. Instead use the printer() function. Or:
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

from version import __version__		# Version
from logging import getLogger		# Logging


import time					# temporary / debugging:
import json					# load json source configuration
import inspect				# dynamic module loading
from Queue import Queue		# queuing

import threading			# multithreading
import subprocess			# multithreading

# dbus
import dbus.service
import dbus.exceptions

# main loop
import gobject
from dbus.mainloop.glib import DBusGMainLoop

# support modules
from modules.hu_msg import MqPubSubFwdController
from modules.hu_pulseaudio import *
from modules.hu_volume import *
from modules.hu_settings import *
from modules.hu_mpd import *

#********************************************************************************
# Third party and others...
#
from slugify import slugify

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "Headunit"
LOG_TAG = 'HEDUNT'
LOGGER_NAME = 'hedunt'

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
CONFIG_FILE_DEFAULT = '/mnt/PIHU_APP/defender-headunit/config/configuration.json'
DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559
SUBSCRIPTIONS = ['/events/']

logger = None			# logging
args = None				# command line arguments
messaging = None		# mq messaging
configuration = None	# configuration
sc_sources = None		# source controller
mpdc = None				# mpd controller

# SEMI-CONSTANTS (set at startup)
SOURCE = None
SOURCE_SUB = None

#OLD AND REMOVE:
PID_FILE = "hu"
ENV_SOURCE = os.getenv('HU_SOURCE')
Sources = None			#Temp.. REMOVE
disp = None				# REMOVE
hu_details = { 'track':None, 'random':'off', 'repeat':True, 'att':False }
arMpcPlaylistDirs = [ ]			#TODO: should probably not be global...

#def volume_att_toggle():
#	hudispdata = {}
#	hudispdata['att'] = '1'
#	disp.dispdata(hudispdata)
#	return None
	
# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})
	
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
	

def dispatcher(path, command, arguments):
	print("[MQ] Received Path: {0}; Command: {1}; Parameters: {2}".format(path,command,arguments))
	handler_function = 'handle_path_' + path[0]
	if handler_function in globals():
		globals()[handler_function](path, command, arguments)
	else:
		print("No handler for: {0}".format(handler_function))
	
# Handler for path: /system/
def handle_path_system(path,cmd,args):
	base_path = 'system'
	
	# remove base path
	del path[0]
	
	def put_reboot(**kwargs):
		print("Rebooting!")
		return True
	
	def put_halt(**kwargs):
		print("Halting!")
		return True
		
	if path:
		function_to_call = cmd + '_' + '_'.join(path)
	else:
		# called without sub-paths
		function_to_call = cmd + '_' + base_path

	if function_to_call in locals():
		ret = locals()[function_to_call](args)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret))
	else:
		printer('Function {0} does not exist'.format(function_to_call))

	
	
# ********************************************************************************
# euuhh.

def idle_msg_receiver():
	global messaging
	
	msg = messaging.receive_async()
	if msg:
		print "Received message: {0}".format(msg)
		parsed_msg = messaging.parse_message(msg)
		dispatcher(parsed_msg['path'],parsed_msg['cmd'],parsed_msg['args'])
		
	return True

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

	configuration = configuration_load( LOGGER_NAME, args.config, CONFIG_FILE_DEFAULT )
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
	global args

	parser = argparse.ArgumentParser(description=DESCRIPTION)
	parser.add_argument('--loglevel', action='store', default=DEFAULT_LOG_LEVEL, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('--config','-c', action='store', help='Configuration file', default=DEFAULT_CONFIG_FILE)
	parser.add_argument('-b', action='store_true', default=False)
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
	#parser.add_argument('--source', action='store', required=True)
	#parser.add_argument('--subsource', action='store')
	#parser.add_argument('--boot', action='store_true')
	args = parser.parse_args()


#********************************************************************************
#
# Setting up prior to mainloop
#
def setup():

	#
	# Logging
	# -> Output will be logged to the syslog, if -b specified, otherwise output will be printed to console
	#
	global logger
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)

	if args.b:
		logger = log_create_syslog_loghandler(logger, args.loglevel, LOG_TAG, address='/dev/log') 	# output to syslog
	else:
		logger = log_create_console_loghandler(logger, args.loglevel, LOG_TAG) 						# output to console

	#
	# Load main configuration
	#
	configuration = init_load_config()

	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Subscriber: {0}".format(DEFAULT_PORT_SUB))
	messaging.create_subscriber(SUBSCRIPTIONS)

	#
	# Load PulseAudio SFX
	#
	#
	pa_sfx_load( configuration['directories']['sfx'] )

	#
	# Load operational settings
	#
	#			#TODO: change this name
	#cSettings = huSettings( os.path.join(configuration['directories']['config'],configuration['files']['settings']),
	#						defaultSettings=configuration['default_settings'] )

	#
	# Start logging to file
	#
	#init_logging_f( configuration['directories']['log'],
	#				configuration['files']['log'],
	#				cSettings.incrRunCounter( max=999999 ) )

	
	#
	# "Splash Screen": Display version and play startup tune
	#
	printer('Headunit.py version {0}'.format(__version__),tag='SYSTEM')
	pa_sfx('startup')

	#
	# Determine starting source
	#
	# Order:
	# 1) command line
	# 2) environment variable
	# 3) settings.json file
	'''
	if (not SOURCE
		    and ENV_SOURCE):
		SOURCE = ENV_SOURCE
		SOURCE_SUB = None
		
	else:
		print "TODO!"
		"""
		prevSource = cSettings.get_key('source')
		prevSourceSub = cSettings.get_key('subsourcekey')

		if prevSource:
			SOURCE = prevSource
			SOURCE_SUB = prevSourceSub
		else:
			SOURCE = None
			SOURCE_SUB = None
		"""
			
	print('SOURCE,SUBSOURCE: {0},{1}'.format(SOURCE,SOURCE_SUB))
	''' 
	
	#
	# i forgot, what's this for?
	#
	#if arg_boot:
	#	BOOT = args.boot
	#else:
	#	BOOT = False
	
	
	#
	# Set/Restore volume level
	#
	#
	# Legacy: #TODO
	#settings = cSettings.get()
	#VolPulse = VolumeController('alsa_output.platform-soc_sound.analog-stereo')
	#VolPulse.set( settings['volume'] )


	#
	# Connect to ZMQ
	#
	#zmq_connect()
	

	#
	# create menu structure
	#
	#print configuration[
	#huMenu = Menu()
	#testentry = { "entry": "Browse tracks",
	#  "entry_name": "browse_track"}
	#huMenu.add( testentry )


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
	printer('INITIALIZATION FINISHED', level=logging.INFO)


#********************************************************************************
#
# Mainloop
#
def main():

	#
	# Check if Source Controller started and available
	#
	printer('Checking if Source Controller is online...')	
	messaging.publish_command('/source/next', 'SET')
	
	# !! !! TODO IMPORTANT !! !!


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
		printer ('No previous source; starting first available source', tag='QPLAY')	
		messaging.send_command('/source/next', 'SET')
		messaging.send_command('/player/state', 'SET:play')
		
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


	
	"""
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

	"""
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
	gobject.idle_add(idle_msg_receiver)
	queue_actions = Queue(maxsize=40)		# Blocking stuff that needs to run in sequence
	#gobject.idle_add(process_queue)

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
	setup()
	main()

	
