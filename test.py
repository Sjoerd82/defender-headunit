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
# ./plugin_sources/* 	Source plugins
# ./plugin_control/*	Controller plugins
# ./plugin_other/*		Other plugins
#
# ./hu_utils.py			Misc. handy functions
# ./hu_volume.py		Volume control
# ./hu_....py

#load json source configuration
import json

#logging
import logging
import logging.config
import datetime
import os
logger = None

#dynamic module loading
import sys, inspect

# support modules
from hu_utils import *
from hu_source import SourceController
from hu_volume import *
from hu_settings import *
from hu_logger import *
from hu_mpd import *
#from hu_menu import *

# DBUS STUUF,, ALL REQUIRED???
import dbus, dbus.service, dbus.exceptions
import sys
from dbus.mainloop.glib import DBusGMainLoop
import gobject


Sources = SourceController()
VolPulse = VolumeController('alsa_output.platform-soc_sound.analog-stereo')

# CONSTANTS
CONFIG_FILE_DEFAULT = '/mnt/PIHU_APP/defender-headunit/config/configuration.json'
CONFIG_FILE = '/mnt/PIHU_CONFIG/configuration.json'
VERSION = "1.0.0"

def pa_sfx( dummy ):
	return None

def random( dummy ):
	return None

def volume_att_toggle():
	return None

def volume_up():
	return None

def volume_down():
	return None

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
			Sources.sourceNext()
			Sources.sourcePlay()
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
	ch.setLevel(logging.INFO)

	# create formatters
	fmtr_ch = ColoredFormatter("%(tag)s%(message)s")

	# add formatter to handlers
	ch.setFormatter(fmtr_ch)

	# add ch to logger
	logger.addHandler(ch)
	
	logger.info('Logging started',extra={'tag':'log'})

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
	
	logger.info('Logging started',extra={'tag':'log'})
	
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

# Load Source Plugins
def loadSourcePlugins( plugindir ):
	global Sources
	global configuration

	#todo, obviously this is bad..
	lookforthingy = '/mnt/PIHU_APP/defender-headunit/plugin_sources/'
	
	for k, v in sys.modules.iteritems():
		if k[0:15] == 'plugin_sources.':
			sourcePluginName = k[15:]
			if not str(v).find(lookforthingy) == -1:
				jsConfigFile = open(plugindir+'//'+sourcePluginName+'.json')	#TODO make more stable, given trailing // or not.. also add try/ or test for folder/file existence
				config=json.load(jsConfigFile)
				sourceModule = sys.modules['plugin_sources.'+sourcePluginName]
				for execFunction in ('sourceInit','sourceCheck','sourcePlay','sourceStop'):
					if execFunction in config:
						#overwrite string with reference to module
						config[execFunction][0] = sys.modules['plugin_sources.'+sourcePluginName]
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
						huMenu.add( menuitem )
				# init source, if successfully added
				if isAdded:
					indexAdded = Sources.getIndex('name',config['name'], template=None)
					Sources.sourceInit(indexAdded)


#********************************************************************************
#
# Initialization
#

#
# Start logging to console
#
init_logging()
init_logging_c()

#
# Load main configuration
#
configuration = configuration_load( CONFIG_FILE, CONFIG_FILE_DEFAULT )
if configuration == None:
	exit()

#
# Load operational settings
#
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

#
# Start logging to file
#
sLogDir = configuration['directories']['log']
sLogFile = configuration['files']['log']
init_logging_f( sLogDir, sLogFile, dSettings['runcount'] )
myprint('Headunit.py version {0}'.format(VERSION),tag='SYSTEM')

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
myprint('Loading Source Plugins...',tag='SYSTEM')

# import sources directory
import plugin_sources
#from plugin_source import *

# read source config files and start source inits
sPluginDirSources = configuration['directories']['plugin-sources']
loadSourcePlugins(sPluginDirSources)

#debug
#huMenu.menuDisplay( header=True )
#huMenu.menuDisplay( entry=1, header=True )
#print huMenu.getMenu( [1,0] )

#
# import control plugins
#
myprint('Loading Control Plugins...',tag='SYSTEM')
from plugin_control import *

#
# load other plugins
#
myprint('Loading Other Plugins...',tag='SYSTEM')
from plugin_other import *


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

myprint('A WARNING', level=logging.WARNING, tag="test")
logger.warning('Another WARNING', extra={'tag':'test'})

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


try:
	remote_bus_name = dbus.service.BusName("com.arctura.remote",
                                           bus=dbus.SystemBus(),
                                           do_not_queue=True)
except dbus.exceptions.NameExistsException:
	printer("service is already running")
	sys.exit(1)


#bus.add_signal_receiver(cb_remote_btn_press, dbus_interface = "com.arctura.remote")
#bus.add_signal_receiver(cb_mpd_event, dbus_interface = "com.arctura.mpd")
#bus.add_signal_receiver(cb_udisk_dev_add, signal_name='DeviceAdded', dbus_interface="org.freedesktop.UDisks")
#bus.add_signal_receiver(cb_udisk_dev_rem, signal_name='DeviceRemoved', dbus_interface="org.freedesktop.UDisks")

bus.add_signal_receiver(cb_remote_btn_press, dbus_interface = "com.arctura.remote")
dbus_ads1x15.RemoteControl(remote_bus_name)

try:
	mainloop.run()
finally:
	mainloop.quit()