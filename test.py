#!/usr/bin/python

# A car's headunit.
#
# Author: Sjoerd Venema
# License: MIT
#

#********************************************************************************
#
# ISSUES:
#  - Not all next() source functions update the settings

#********************************************************************************
# CONFIGURATION and SETTINGS
#
# configuration.json		Main configuration file (json)
# dSettings.json			Operational settings (json)
# mp_<id>.p					Operational source settings, to continue playback (pickled)
# 

#********************************************************************************
# LOGGING and CONSOLE output
#
# All output is channeled through the Python logger, in order to both be displayed on the console and written to a logfile.
# Please don't use the print() function. Instead use either:
#  - myprint( message, level="INFO", tag="")	# defined in hu_utils.py
#  - logger.info(message, extra={'tag': tag})	# or any other desired log level
#
# Log level INFO or higher is sent to the console.
# Log level DEBUG or higher is sent to the log file.
#
# Output sent to the file is cleansed of any ANSI formatting.
#

#********************************************************************************
# DBUS
# 
# This script listens to a number of DBus sources.
# This script also emits signals on com.arctura.hu		#TODO
#

#********************************************************************************
# MODULES
#
# Automatically loaded:
#
# ./sources/* 			Source plugins
# ./plugin_control/*	Controller plugins
# ./plugin_other/*		Other plugins
#
# ./hu_utils.py			Misc. handy functions
# ./hu_volume.py		Volume control
# ./hu_....py

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
import time

#load json source configuration
import json


#dynamic module loading
import sys, inspect

#starting plugins in separate thread
import threading
import subprocess

# support modules
from hu_pulseaudio import *
from hu_volume import *
from hu_utils import *
from hu_source import SourceController
from hu_settings import *
from hu_mpd import *
#from hu_menu import *

# DBUS STUUF,, ALL REQUIRED???
import dbus, dbus.service, dbus.exceptions
import sys
from dbus.mainloop.glib import DBusGMainLoop
import gobject

# GLOBAL vars
Sources = SourceController()	#TODO: rename "Sources" -- confusing name
mpdc = None
disp = None

# CONSTANTS
CONFIG_FILE_DEFAULT = '/mnt/PIHU_APP/defender-headunit/config/configuration.json'
CONFIG_FILE = '/mnt/PIHU_CONFIG/configuration.json'
VERSION = "1.0.0"

hu_details = { 'track':None, 'random':False, 'repeat':True }


def random( dummy ):
	hudispdata = {}
	hudispdata['rnd'] = '1'
	disp.dispdata(hudispdata)
	return None

def volume_att_toggle():
	hudispdata = {}
	hudispdata['att'] = '1'
	disp.dispdata(hudispdata)
	return None

def volume_up():
	return None

def volume_down():
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

def cb_remote_btn_press ( func ):

	global Sources
	global cSettings

	# Handle button press
	if func == 'SHUFFLE':
		print('\033[95m[BUTTON] Shuffle\033[00m')
		random( 'toggle' )
	elif func == 'SOURCE':
		print('\033[95m[BUTTON] Next source\033[00m')
		pa_sfx('button_feedback')
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
				if arCurrIx[1] == None:
					currSrc = Sources.get(None)
				else:
					currSrc = Sources.get(None)
					currSSrc = Sources.getSubSource(arCurrIx[0],arCurrIx[1])
				
				# update source
				cSettings.set('source',currSrc['name'])
				
				# update sub-source key (in case of sub-source)
				if not arCurrIx[1] == None:
					subsource_key = {}
					for key in currSrc['subsource_key']:
						subsource_key[key] = currSSrc[key]
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
				elif currSrc['name'] == 'locmus':
					hudispdata['src'] = 'INT'
				elif currSrc['name'] == 'bt':
					hudispdata['src'] = 'BT'
				elif currSrc['name'] == 'line':
					hudispdata['src'] = 'AUX'
				elif currSrc['name'] == 'stream':
					hudispdata['src'] = 'WEB'
				elif currSrc['name'] == 'smb':
					hudispdata['src'] = 'NET'
				disp.dispdata(hudispdata)

				
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
			

		elif Sources.getAvailableCnt() == 1:
			print('Only one source availble. Ignoring button.')
		elif Sources.getAvailableCnt() == 0:
			print('No available sources.')
	elif func == 'ATT':
		print('\033[95m[BUTTON] ATT\033[00m')
		pa_sfx('button_feedback')
		volume_att_toggle()
	elif func == 'VOL_UP':
		print('\033[95m[BUTTON] VOL_UP\033[00m')		
		pa_sfx('button_feedback')
		volume_up()
		return 0
	elif func == 'VOL_DOWN':
		print('\033[95m[BUTTON] VOL_DOWN\033[00m')
		pa_sfx('button_feedback')
		volume_down()
		return 0
	elif func == 'SEEK_NEXT':
		print('\033[95m[BUTTON] Seek/Next\033[00m')
		pa_sfx('button_feedback')
		Sources.sourceSeekNext()
	elif func == 'SEEK_PREV':
		print('\033[95m[BUTTON] Seek/Prev.\033[00m')
		pa_sfx('button_feedback')
		Sources.sourceSeekPrev()
	elif func == 'DIR_NEXT':
		print('\033[95m[BUTTON] Next directory\033[00m')
		if dSettings['source'] == 1 or dSettings['source'] == 2 or dSettings['source'] == 6:
			pa_sfx('button_feedback')
			#mpc_next_folder()
		else:
			pa_sfx('error')
			print(' No function for this button! ')
	elif func == 'DIR_PREV':
		print('\033[95m[BUTTON] Prev directory\033[00m')
		if dSettings['source'] == 1 or dSettings['source'] == 2 or dSettings['source'] == 6:
			pa_sfx('button_feedback')
			#mpc_prev_folder()
		else:
			pa_sfx('error')
			print(' No function for this button! ')
	elif func == 'UPDATE_LOCAL':
		print('\033[95m[BUTTON] Updating local MPD database\033[00m')
		pa_sfx('button_feedback')
		#locmus_update()
	elif func == 'OFF':
		print('\033[95m[BUTTON] Shutting down\033[00m')
		pa_sfx('button_feedback')
		shutdown()
	else:
		print('Unknown button function')
		pa_sfx('error')


def cb_mpd_event( event ):
	global Sources
	global settings
	global mpdc

	printer('DBUS event received: {0}'.format(event), tag='MPD')

	if event == "player":
		currSrc = Sources.get( None )
		
		if not currSrc == None:
			if 'label' in currSrc:
				mpc_save_pos_for_label( currSrc['label'], "/mnt/PIHU_CONFIG" )
			else:
				mpc_save_pos_for_label( currSrc['name'], "/mnt/PIHU_CONFIG" )

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
		
				
	elif event == "update":
		printer(" ...  database update started or finished (no action)", tag='MPD')
		
	elif event == "database":
		printer(" ...  database updated with new music #TODO", tag='MPD')
		
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
	global disp

	printer('Interval function [30 second]', level=LL_DEBUG, tag="TIMER1")

	# save settings (hu_settings)
	cSettings.save()
	
	hudispdata = {}
	hudispdata['src'] = "USB"		#temp.
	disp.dispdata(hudispdata)

	return True

def cb_udisk_dev_add( device ):
	printer('Device added: {0}'.format(str(device)),tag='UDISKS')
	udisk_details( device, 'A' )

def cb_udisk_dev_rem( device ):
	printer('Device removed: {0}'.format(str(device)),tag='UDISKS')
	udisk_details( device, 'R' )

def udisk_details( device, action ):
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
	
	DeviceFile = ""
	mountpoint = ""
	mytag = ".UDISKS"
	
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

	if action == 'A':
		# Find out its mountpoint...
		#IdLabel: SJOERD
		#DriveSerial: 0014857749DCFD20C7F95F31
		#DeviceMountPaths: dbus.Array([dbus.String(u'/media/SJOERD')], signature=dbus.Signature('s'), variant_level=1)
		#DeviceFileById: dbus.Array([dbus.String(u'/dev/disk/by-id/usb-Kingston_DataTraveler_SE9_0014857749DCFD20C7F95F31-0:0-part1'), dbus.String(u'/dev/disk/by-uuid/D2B6-F8B3')], signature=dbus.Signature('s'), variant_level=1)
		
		mountpoint = subprocess.check_output("mount | egrep "+DeviceFile+" | cut -d ' ' -f 3", shell=True).rstrip('\n')
		partuuid = subprocess.check_output("blkid "+DeviceFile+" -s PARTUUID -o value", shell=True).rstrip('\n')
		if mountpoint != "":
			sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
			printer(" > Mounted on: {0} (label: {1})".format(mountpoint,sUsbLabel),tag=mytag)
			mpc_update(sUsbLabel, True)
			#add_a_source(sPluginDirSources, 'media')
			#media_check(sUsbLabel)
			#media_play()
			sources.media.media_add(mountpoint, sUsbLabel, partuuid, Sources)
			if sources.media.media_check(sUsbLabel):
				Sources.setAvailable('mountpoint',mountpoint,True)
			printSummary()
		else:
			printer(" > No mountpoint found. Stopping.",tag=mytag)
		
	elif action == 'R':
		# Find out its mountpoint...
		#We cannot retrieve many details from dbus about a removed drive, other than the DeviceFile (which at this point is no longer available).
# ->	media_check( None )
		# Determine if we were playing this media (source: usb=1)
		#if dSettings['source'] == 1 and
		
		#TODO!
		print('todo!')
		
	else:
		printer(" > ERROR: Invalid action.",tag=mytag)
		pa_sfx('error')

# ********************************************************************************
# Misc. functions
#

# turn off the device
def shutdown():
	global configuration
	global settings
	global settingsfile

	# save settings (hu_settings)
	settings_save( settingsfile, settings )

	# stop source (hu_source)
	Source.sourceStop()
	
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
def printSummary():
	global Sources
	global logger
	printer('-- Summary -----------------------------------------------------------', tag='')
	arCurrIx = Sources.getIndexCurrent()
	sCurrent = Sources.get(None)
	
	if not arCurrIx[0] == None and arCurrIx[1] == None:
		sCurrDisplay = sCurrent['displayname']
	elif not arCurrIx[1] == None:
		sCurrDisplay = sCurrent['subsources'][arCurrIx[1]]['displayname']
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
			Sources.sourcePlay()
			return True
						
		elif len(prevIx) == 2:
			printer ('Continuing playback (subsource)', tag='QPLAY')
			Sources.setCurrent(prevIx[0],prevIx[1])
			Sources.sourcePlay()
			return True

		else:
			printer ('Continuing playback not available.', tag='QPLAY')
			return False
		

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
myprint('Headunit.py version {0}'.format(VERSION),tag='SYSTEM')
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
# import control plugins
#
myprint('Loading Control Plugins...',tag='SYSTEM')
from plugin_control import *

threads = []
# loop through the control plugin dir
for filename in os.listdir( configuration['directories']['controls'] ):
		#if filename.startswith('') and
		if filename.endswith('.py'):
			pathfilename = os.path.join( configuration['directories']['controls'], filename )
			t = threading.Thread(target=plugin_execute, args=(pathfilename,))
			t.setDaemon(True)
			threads.append(t)
			#t.start()	WORKAROUND

# loop through the output plugin dir
for filename in os.listdir( configuration['directories']['output'] ):
		#if filename.startswith('') and
		if filename.endswith('.py'):
			pathfilename = os.path.join( configuration['directories']['output'], filename )
			t = threading.Thread(target=plugin_execute, args=(pathfilename,))
			t.setDaemon(True)
			threads.append(t)
			#t.start()	WORKAROUND

# NOTE: Plugins are now loading in the background, in parallel to code below.
# NOTE: This can really interfere, in a way I don't understand.. executing the threads later helps... somehow..
# NOTE: For NOW, we'll just execute the threads after the loading of the "other" plugins...


#
# Load mpd dbus listener
#
#
t = threading.Thread(target=plugin_execute, args=('/mnt/PIHU_APP/defender-headunit/dbus_mpd.py',))
t.setDaemon(True)
threads.append(t)


#
# load other plugins
#
myprint('Loading Other Plugins...',tag='SYSTEM')
from plugin_other import *

# WORKAROUND...
for t in threads:
	t.start()

# LCD (TODO: move to plugins)
#from hu_lcd import *
#disp = lcd_mgr()
#disp.lcd_text('Welcome v0.1.4.8')

# MPD
mpdc = mpdController()

myprint('INITIALIZATION FINISHED', level=logging.INFO, tag="SYSTEM")

#
# end of initialization
#
#********************************************************************************


#********************************************************************************
#
# Mainloop
#

#
# QuickPlay
#

# TESTING....
#testSs = {'mountpoint':'/media/SJOERD'}
#cSettings.set('source','media')
#cSettings.set('subsource',testSs)
#cSettings.save()

prevSource = cSettings.get_key('source')
prevSourceSub = cSettings.get_key('subsourcekey')

if prevSource == "":
	printer ('No previous source.', tag='QPLAY')
	Sources.sourceCheckAll()
	printSummary()
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
		printSummary()
		
	else:
		printer ('Continuing playback not available, checking all sources...', tag='QPLAY')
		Sources.sourceCheckAll()
		printSummary()
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
gobject.timeout_add_seconds(30,cb_timer1)

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



