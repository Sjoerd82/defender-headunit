#!/usr/bin/python

# A car's headunit.
#
# Author: Sjoerd Venema
# License: MIT
#

#********************************************************************************
# CONFIGURATION
#
# configuration.json		Main configuration file
# dSettings.json			Operational settings (will be created if not found)
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

Sources = SourceController()

# CONSTANTS
CONFIG_FILE_DEFAULT = '/mnt/PIHU_APP/defender-headunit/config/configuration.json'
CONFIG_FILE = '/mnt/PIHU_CONFIG/configuration.json'
VERSION = "1.0.0"


def random( dummy ):
	disp.lcd_ding( 'random_on' )
	disp.lcd_ding( 'update_on' )
	return None

def volume_att_toggle():
	disp.lcd_ding( 'att_on' )
	disp.lcd_ding( 'src_usb' )
	disp.lcd_play( 'Dare', 'Waves', 1 )
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

	
def cb_remote_btn_press2 ( func ):
	print "cb_remote_btn_press2 {0}".format(func)

#
def cb_remote_btn_press ( func ):

	global Sources

	# Handle button press
	if func == 'SHUFFLE':
		print('\033[95m[BUTTON] Shuffle\033[00m')
		random( 'toggle' )
	elif func == 'SOURCE':
		print('\033[95m[BUTTON] Next source\033[00m')
		pa_sfx('button_feedback')
		# if more than one source available...
		if Sources.getAvailableCnt() > 1:
			Sources.sourceStop()
			Sources.next()
			Sources.sourcePlay()
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
		#seek_next()
	elif func == 'SEEK_PREV':
		print('\033[95m[BUTTON] Seek/Prev.\033[00m')
		pa_sfx('button_feedback')
		#seek_prev()
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
		#shutdown()
	else:
		print('Unknown button function')
		pa_sfx('error')

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
		if mountpoint != "":
			sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
			printer(" > Mounted on: {0} (label: {1})".format(mountpoint,sUsbLabel),tag=mytag)
			mpc_update(sUsbLabel, True)
			#add_a_source(sPluginDirSources, 'media')
			#media_check(sUsbLabel)
			#media_play()
			sources.media.media_add(mountpoint, Sources)
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

def init_load_ops( configuration ):
	# load default settings
	dDefaultSettings = configuration['default_settings']
	# operational settings file (e.g. dSettings.json)
	sFileSettings = os.path.join(configuration['directories']['config'],configuration['files']['settings'])
	# load into dSettings
	dSettings = settings_load( sFileSettings, dDefaultSettings )

	# increase the run counter (used for logging to file)
	dSettings['runcount']+=1

	# save run counter
	settings_save( sFileSettings, dSettings )
	
	return dSettings

# print a source summary
def printSummary():
	global Sources
	global logger
	#logger = logging.getLogger('headunit')
	logger.info('-- Summary -----------------------------------------------------------', extra={'tag':''})
	iCurrent = Sources.getIndexCurrent()
	if iCurrent == None:	
		logger.info('Current source: None', extra={'tag':''})
	else:
		logger.info('Current source: {0:d} {1}'.format(iCurrent,Sources[iCurrent]['displayname']), extra={'tag':''})
	i = 0
	for source in Sources.getAll():
		if not source['template']:
			if source['available']:
				available = colorize('available','light_green')
			else:
				available = colorize('not available','light_red')
			
			if 'mountpoint' in source:
				mountpoint = source['mountpoint']
			else:
				mountpoint = ""
				
			logger.info(' {0:d} {1:17} {2} {3}'.format(i,source['displayname'],available,mountpoint), extra={'tag':''})
		i += 1
	logger.info('----------------------------------------------------------------------', extra={'tag':''})

def add_a_source( plugindir, sourcePluginName ):
	configFileName = os.path.join(plugindir,sourcePluginName+'.json')
	if not os.path.exists( configFileName ):
		printer('Configuration not found: {0}'.format(configFileName))
		return False
		
	jsConfigFile = open( configFileName )
	config=json.load(jsConfigFile)
	sourceModule = sys.modules['sources.'+sourcePluginName]
	for execFunction in ('sourceInit','sourceCheck','sourcePlay','sourceStop'):
		if execFunction in config:
			#overwrite string with reference to module
			config[execFunction][0] = sys.modules['sources.'+sourcePluginName]
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
	# init source, if successfully added
	if isAdded:
		indexAdded = Sources.getIndex('name',config['name'], template=None)
		Sources.sourceInit(indexAdded)

# Load Source Plugins
def loadSourcePlugins( plugindir ):
	global Sources
	global configuration

	if not os.path.exists(plugindir):
		printer('Source path not found: {0}'.format(plugindir), level=LL_CRITICAL)
		exit()
	
	#todo, obviously this is bad..
	print plugindir
	#lookforthingy = '/mnt/PIHU_APP/defender-headunit/sources/'
	lookforthingy = plugindir
	
	for k, v in sys.modules.iteritems():
		if k[0:8] == 'sources.':
			sourcePluginName = k[8:]
			if not str(v).find(lookforthingy) == -1:
				add_a_source(plugindir, sourcePluginName)

def plugin_execute( script ):
	printer('Starting Plugin: {0}'.format(script))
	#os.system( 'python '+script )
	call(['python',script])
	

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
#
settings = init_load_ops( configuration )


#
# Start logging to file
#
#
init_logging_f( configuration['directories']['log'],
                configuration['files']['log'],
 				settings['runcount'] )

#
# Set/Restore volume level
#
#
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

# NOTE: Plugins are now loading in the background, in parallel to code below.
# NOTE: This can really interfere, in a way I don't understand.. executing the threads later helps... somehow..
# NOTE: For NOW, we'll just execute the threads after the loading of the "other" plugins...

#
# load other plugins
#
myprint('Loading Other Plugins...',tag='SYSTEM')
from plugin_other import *

# WORKAROUND...
for t in threads:
	t.start()

# LCD (TODO: move to plugins)
from hu_lcd import *
disp = lcd_mgr()
disp.lcd_text('Welcome v0.1.4.8')

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
# dbus
#

# on demand...
#plugin_sources.media.media_add('/media/USBDRIVE', Sources)

Sources.sourceCheckAll()
printSummary()

#myprint('A WARNING', level=logging.WARNING, tag="test")
#logger.warning('Another WARNING', extra={'tag':'test'})

# Save operational settings
#dSettings1 = {"source": -1, 'volume': 99, 'mediasource': -1, 'medialabel': ''}	 # No need to save random, we don't want to save that (?)
#settings_save( sFileSettings, dSettings1 )

#********************************************************************************
#
# Initialize the mainloop
#


DBusGMainLoop(set_as_default=True)
mainloop = gobject.MainLoop()
bus = dbus.SystemBus()



#bus.add_signal_receiver(cb_mpd_event, dbus_interface = "com.arctura.mpd")
bus.add_signal_receiver(cb_remote_btn_press, dbus_interface = "com.arctura.remote")
bus.add_signal_receiver(cb_remote_btn_press2, dbus_interface = "com.arctura.keyboard")
bus.add_signal_receiver(cb_udisk_dev_add, signal_name='DeviceAdded', dbus_interface="org.freedesktop.UDisks")
bus.add_signal_receiver(cb_udisk_dev_rem, signal_name='DeviceRemoved', dbus_interface="org.freedesktop.UDisks")

try:
	mainloop.run()
finally:
	mainloop.quit()



