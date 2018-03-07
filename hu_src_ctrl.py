#!/usr/bin/python

# A car's headunit.
# Source Controller
#
# Author: Sjoerd Venema
# License: MIT
#

import sys

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
#from hu_logger import *
from modules.hu_logger import ColoredFormatter
from modules.hu_logger import RemAnsiFormatter

# for logging to syslog
import socket


arg_loglevel = 20
arg_source = 'SMB'
arg_boot = False


#********************************************************************************
#
#
#

# load json source configuration
import json

# dynamic module loading
import inspect


# support modules, old style
from modules.hu_pulseaudio import *
from modules.hu_volume import *
from modules.hu_utils import *
from modules.hu_source import SourceController
from modules.hu_settings import *
from modules.hu_mpd import *

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

topics = ['/source','/player']
for topic in topics:
	subscriber.setsockopt (zmq.SUBSCRIBE, topic)
#subscriber.setsockopt (zmq.SUBSCRIBE, '/source')
#subscriber.setsockopt (zmq.SUBSCRIBE, '/player')

#thingy1['player'] = ['track','folders','pause','state','random','randommode']

thingy2 = {
 'player':['track','folders','pause','state','random','randommode']
}

thingy3 = {
 'player':[ {'path':'track','command':'GET'},
            {'path':'track','command':'SET'},
            {'path':'folders','command':'GET'} ]
}

#thingy4 = {
# 'player':[ { 'command':'GET', 'path': ['track','folders','pause','state','random','randommode'] }
#           ,{ 'command':'SET', 'path': ['track','pause','state','random','randommode'] }
#  
#}

#thingy5 = {
# 'player':[ { 'command':'GET', 'path': 'track', 'func':test_next_track } ]
#
#}

def test_next_track():
	print("WHOPPA! NEXTING!")

globals()['test_next_track']()

thingy6 = {
 'player': { 'track': { 'GET' : globals()['test_next_track'], 'SET' : globals()['test_next_track'] } }
}



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

			# play newly selected source
			hu_play()

			#
			# update display
			#
			""" dit werkt opzich wel... maar kan beter...
			currSrc = Sources.get(None)
			hudispdata = {}
			if currSrc['name'] == 'fm':
				hudispdata['src'] = 'FM'
			elif currSrc['name'] == 'media':
				hudispdata['src'] = 'USB'
				hudispdata['info'] = "Removable Media"
				#hudispdata['info1'] = "label: " + currSrc['subsources'][arCurrIx[1]]['label']
			elif currSrc['name'] == 'locmus':
				hudispdata['src'] = 'INT'
				hudispdata['info'] = "Internal Storage"
				#if len(currSrc['subsources']) > 1:
				#	hudispdata['info1'] = "folder: " + currSrc['subsources'][arCurrIx[1]]['label']
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
			"""

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

	
def parse_message(message):
	
	# Expected format:
	# /path/path/path Command:Param1,Param2
	
	path = []
	params = []
	
	path_cmd = message.split(" ")
	for pathpart in path_cmd[0].split("/"):
		if pathpart:
			path.append(pathpart)
	
	cmd_par = path_cmd[1].split(":")

	if len(cmd_par) == 1:
		command = cmd_par[0]
	elif len(cmd_par) == 2:
		command = cmd_par[0]
		param = cmd_par[1]

		for parpart in param.split(","):
			if parpart:
				params.append(parpart)
		
	else:
		print("Malformed message!")
	
	print("[MQ] Received Path: {0}; Command: {1}; Parameters: {2}".format(path,command,params))


def mq_recv():
	message = subscriber.recv()
	#print message
	#parse_message(message)
	#if message == '/player/track/next':
	#	Sources.sourceSeekNext()

	#
	# PARSE
	#
	path = []
	params = []
	
	path_cmd = message.split(" ")
	for pathpart in path_cmd[0].split("/"):
		if pathpart:
			path.append(pathpart)
	
	cmd_par = path_cmd[1].split(":")

	if len(cmd_par) == 1:
		command = cmd_par[0]
	elif len(cmd_par) == 2:
		command = cmd_par[0]
		param = cmd_par[1]

		for parpart in param.split(","):
			if parpart:
				params.append(parpart)
	
	#
	# ACT
	#
	if path[0] == 'player':
		print "DO STUFF FOR PLAYER"
		
	
	elif path[0] == 'event':
		print "DO STUFF FOR EVENT"

	
	print thingy6['player']['track']['GET']
			
	return True

	
#********************************************************************************
#
# Initialization
#
#def setup():


#
# Start logging to console
#
# TODO: get settings from configuration.json
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
# "Splash Screen": Display version
#
#
myprint('Headunit.py version {0}'.format(__version__),tag='SYSTEM')


#
# App. Init
#
#


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

"""
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

#
# Connect Callback functions to DBus Signals
#
bus.add_signal_receiver(cb_mpd_event, dbus_interface = "com.arctura.mpd")
bus.add_signal_receiver(cb_remote_btn_press, dbus_interface = "com.arctura.remote")
bus.add_signal_receiver(cb_remote_btn_press2, dbus_interface = "com.arctura.keyboard")
bus.add_signal_receiver(cb_udisk_dev_add, signal_name='DeviceAdded', dbus_interface="org.freedesktop.UDisks")
bus.add_signal_receiver(cb_udisk_dev_rem, signal_name='DeviceRemoved', dbus_interface="org.freedesktop.UDisks")
bus.add_signal_receiver(cb_ifup, signal_name='ifup', dbus_interface="com.arctura.ifup")
bus.add_signal_receiver(cb_ifdn, signal_name='ifdn', dbus_interface="com.arctura.ifdn")
"""

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
"""
if __name__ == '__main__':
	setup()
	main()
"""
	
