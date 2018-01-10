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
from hu_menu import *

Sources = SourceController()
VolPulse = VolumeController('alsa_output.platform-soc_sound.analog-stereo')

# CONSTANTS
CONFIG_FILE = '/mnt/PIHU_APP/defender-headunit/configuration.json'
VERSION = "1.0.0"

# Initiate logging.
# Use logger.info instead of print.
def init_logging( logdir, logfile, runcount ):

	global logger

	iCounterLen = 6
	currlogfile = os.path.join(logdir, logfile+'.'+str(runcount).rjust(iCounterLen,'0')+'.log')
	
	# logging is global
	logger = logging.getLogger('headunit')
	logger.setLevel(logging.DEBUG)

	# create console handler
	ch = logging.StreamHandler()
	ch.setLevel(logging.INFO)

	# create file handler
	fh = logging.FileHandler(currlogfile)
	fh.setLevel(logging.DEBUG)

	# create formatters
	fmtr_ch = ColoredFormatter("%(tag)s%(message)s")
	fmtr_fh = RemAnsiFormatter("%(asctime)-9s [%(levelname)-8s] %(tag)s %(message)s")
		
	# add formatter to handlers
	ch.setFormatter(fmtr_ch)
	fh.setFormatter(fmtr_fh)

	# add ch to logger
	logger.addHandler(ch)
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

	for k, v in sys.modules.iteritems():
		if k[0:15] == 'plugin_sources.':
			sourcePluginName = k[15:]
			if not str(v).find('D:\\Python\\plugin_sources\\') == -1:
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

				
#####
"""
DEFAULT_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': { 
        'standard': { 
            'format': '%(asctime)s - %(message)s'
        },
		'custom': {
			
		},
        'complete': {
            'format': '%(asctime)s - PID: %(process)d - PNAME: %(processName)s' \
                      ' - TID: %(thread)d - TNAME: %(threadName)s' \
                      ' - %(levelname)s - %(filename)s - %(message)s',
        },
    },
    'handlers': { 
        'default': { 
            'level': LL_INFO,
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': { 
            'level': LL_INFO,
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': datetime.datetime.now().strftime('%Y%m%d.log'),
        },
        'rewrite': { 
            'level': LL_INFO,
            'formatter': 'complete',
            'class': 'logging.FileHandler',
            'filename': datetime.datetime.now().strftime('%Y%m%d2.log'),
            'mode': 'w',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default', 'file', 'rewrite'],
            'level': LL_INFO,
            'propagate': True
        },
        'another.module': {
            'level': 'DEBUG',
        },
    }
}
 
logging.config.dictConfig(DEFAULT_LOGGING)
logging.info('Hello, log')

#####
"""

#********************************************************************************
#
# Initialization
#
#def init():
#
# Load main configuration
#
configuration = configuration_load( CONFIG_FILE )

#
# Load operational settings
#
sFileSettings = configuration['directories']['config']+'\\'+configuration['files']['settings']
dDefaultSettings = configuration['default_settings']
dSettings = settings_load( sFileSettings, dDefaultSettings )
dSettings['runcount']+=1
settings_save( sFileSettings, dSettings )

#
# Initiate logging
#
sLogDir = configuration['directories']['log']
sLogFile = configuration['files']['log']
init_logging(sLogDir,sLogFile,dSettings['runcount'])
myprint('Headunit.py version {0}'.format(VERSION),tag='SYSTEM')

#
# create menu structure
#
#print configuration[
huMenu = Menu()
testentry = { "entry": "Browse tracks",
  "entry_name": "browse_track"}
huMenu.add( testentry )


#
# App. Init
#

# import sources directory
import plugin_sources

# read source config files and start source inits
sPluginDirSources = configuration['directories']['plugin-sources']
loadSourcePlugins(sPluginDirSources)

#debug
huMenu.menuDisplay( header=True )
huMenu.menuDisplay( entry=1, header=True )
print huMenu.getMenu( [1,0] )

#
# import control plugins
#
from plugin_control import *


#
# load other plugins
#
from plugin_other import *


myprint('INITIALIZATION FINISHED', level=logging.INFO, tag="SYSTEM")

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

