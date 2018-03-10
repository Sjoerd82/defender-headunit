#!/usr/bin/python

# A car's headunit.
# Source Controller
#
# Author: Sjoerd Venema
# License: MIT
#

import sys

# load json source configuration
import json

# queuing
from Queue import Queue

# dynamic module loading
import inspect

# main loop
import gobject
from dbus.mainloop.glib import DBusGMainLoop

# sockets
import time

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

arg_loglevel = 20

#********************************************************************************
#
# Headunit modules
#

from modules.hu_source import SourceController
from modules.hu_utils import * #init_load_config

#********************************************************************************
#
# Third party and others...
#

import zmq
from slugify import slugify

#********************************************************************************
#
# GLOBAL vars & CONSTANTS
#

sc_sources = SourceController()
mpdc = None
arMpcPlaylistDirs = [ ]			#TODO: should probably not be global...
CONFIG_FILE = None
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
# Source Plugin Wrapper
#



# ********************************************************************************
# Headunit functions
#



# ********************************************************************************
# MQ functions
#
def zmq_send(path,message):
	#TODO
	path_send = '/data' + path
	printer("Sending message: {0} {1}".format(path, message))
	zmq_sck.send("{0} {1}".format(path, message))
	time.sleep(1)

def process_queue():
	if not queue_actions.empty(): 
 		item = queue_actions.get()
		# do smart stuff #TODO
		# - future actions that eliminate all priors: source_next, ...
		globals()[item[0]](item[1], item[2], item[3])
		queue_actions.task_done()
	return True

def mq_recv():
	message = subscriber.recv()
	parse_message(message)
	return True

#def check_args(args,count,types):
#	

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

def source(path,cmd,args):

	base_path = 'source'
	
	# in paths are concatenated using underscore
	# example:
	# \player\track\next must be processed by the function called:
	# track_next

	def get_source(args):
		# Retrieve list of, or specified source(s)
		#msg_return ={}
		if not args:
			# return all sources
			ret_sources = sc_sources.get(None)
			# build msg_return # needed?
		elif len(args) == 1:
			# return source
			ret_sources = sc_sources.get(args[0])
		elif len(args) == 2:
			# return source + subsource
			#ret_sources = sc_sources.get(args[0],args[1])
			ret_sources = None #function not implemented
		
		#message = msg_return
		#mq_send(path_send, msg_return)
		zmq_send('/source', ret_sources) # TODO: use base_path
		return True

	def set_source(args):
		# Set active (sub)source to <id> (<subid>)
		if not args:
			printer('Function arguments missing', level=LL_ERROR)
			return False
		elif len(args) > 1:
			sc_sources.setCurrent(args[0])
		elif len(args) > 2:
			printer('More than two arguments given, ignoring extra arguments', level=LL_WARNING)
			sc_sources.setCurrent(args[0],args[1])
		return True
		
	def get_subsource(args):
		# Retrieve list of subsources for current or specified source
		return True

	def set_available(args):
		# Retrieve list of available sources / Set available (F=Force)
		return True

	def set_next(args):
		# Set active (sub)source to the next available
		ret = sc_sources.next()
		return ret

	def set_prev(args):
		# Set active (sub)source to the prev available
		sc_sources.next(True)
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
		
	return True
		
def player(path,cmd,args):

	base_path = 'source'

	# in paths are concatenated using underscore
	# example:
	# \player\track\next must be processed by the function called:
	# track_next
	
	def get_player(args):
		#
		currmedia = source_get_media_details()
		print currmedia
		#TODO
		return True
	
	def set_player(args):
		#
		return True
	
	def get_track(args):
		#return track
		currmedia = source_get_media_details()
		print currmedia
		#TODO
		return True
		
	def set_track(args):
		#set playlist position
		if len(args) == 0:
			printer('Function arguments missing', level=LL_ERROR)
			return False
		elif len(args) > 1:
			printer('More than one argument given, ignoring', level=LL_WARNING)
			ret = sc_sources.source_play( args[0] )
			return ret
	
	def get_folders(args):
		# Retrieve list of folders
		return True

	def set_pause(args):
		# Set pause: on|off|toggle
		# TODO: validate input
		ret = sc_sources.source_pause( args[0] )
		return ret

	def get_state(args):
		# Get state: play|pause|stop, toggle random
		state = sc_sources.source_get_details()
		# TODO: ehmm, do something with the state
		print state
		return True

	def set_state(args):
		# Set state: play|pause|stop, toggle random
		# TODO
		return True

	def set_random(args):
		# Set random on|off|toggle|special modes
		# TODO: validate input
		ret = sc_sources.source_random( args[0] )
		return ret

	def get_randommode(args):
		# Get list of (supported) random modes
		details = sc_sources.source_get_details()
		# TODO: get random modes
		return True

	def set_next(args):
		# Next track
		# TODO: ignoring args, for now...
		#mpdc.trackNext()
		sc_sources.source_next()
		return True

	def set_prev(args):
		# Prev track
		# TODO: ignoring args, for now...
		sc_sources.source_prev()
		return True

	def set_seekfwd(args):
		# Seek fwd
		ret = sc_sources.source_seekfwd()
		return ret

	def set_seekrev(args):
		# Seek rev
		ret = sc_sources.source_seekprev()
		return ret

	def get_playlist(args):
		# Retrieve current or specified playlist
		playlist = sc_sources.source_get_playlist()
		print playlist
		# TODO: ehmm, do something with the state
		return True

	def set_update(args):
		# Update MPD, preferablly specify a location
		ret = sc_sources.source_update()
		return ret

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

	return True


# ********************************************************************************
# Initialization functions
#
#  - Loggers
#  - Load source plugins
#  - Summary printer
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

# Load Source configurations and add to source list
def load_sources( plugindir ):
	global sc_sources
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
		#for execFunction in ('sourceInit','sourceCheck','sourcePlay','sourceStop','sourceNext','sourcePrev'):
		#	if execFunction in config:
		#		#overwrite string with reference to module
		#		config[execFunction][0] = sys.modules['sources.'+sourcePluginName]

		# add a sourceModule item with a ref. to the module
		config['sourceModule'] = sys.modules['sources.'+sourcePluginName]
		
		# register the source
		isAdded = sc_sources.add(config)
		
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
			indexAdded = sc_sources.getIndex('name',config['name'])
			sc_sources.sourceInit(indexAdded)
	
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


#********************************************************************************
#
# Initialization
#
#def setup():


#********************************************************************************
#
# Parse command line arguments and environment variables
# Command line takes precedence over environment variables and settings.json
#
import os
import argparse

ENV_CONFIG_FILE = os.getenv('HU_CONFIG_FILE')

parser = argparse.ArgumentParser(description='Source Controller')
parser.add_argument('--config','-c', required=False, action='store', help='Configuration file')
parser.add_argument('--loglevel', action='store', default=LL_INFO, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
parser.add_argument('-b', action='store_true')	# background, ie. no output to console
args = parser.parse_args()

arg_config = args.config
arg_loglevel = args.loglevel
arg_b = args.b

if arg_config:
	CONFIG_FILE = arg_config
elif ENV_CONFIG_FILE:
	CONFIG_FILE = ENV_CONFIG_FILE
else:
	print("No configuration file given.")
	exit(0)

#
# Start logging to console
#
# TODO: get settings from configuration.json
init_logging()
init_logging_c()

#
# Load main configuration
#
configuration = configuration_load(CONFIG_FILE)

#
# Load PulseAudio SFX
#
#
pa_sfx_load( configuration['directories']['sfx'] )

	
#
# Start logging to file
#
# TODO: get settings from configuration.json
#init_logging_f( configuration['directories']['log'],
#				configuration['files']['log'],
#				cSettings.incrRunCounter( max=999999 ) )
#				#settings['runcount'] )

#
# Start logging to syslog
#
# TODO: get settings from configuration.json
init_logging_s( address='/dev/log' )

#
# "Splash Screen": Display version
#
#
myprint('{0} version {1}'.format('Source Controller',__version__),tag='SYSTEM')


#
# ZeroMQ
#
zmq_ctx = zmq.Context()
subscriber = zmq_ctx.socket (zmq.SUB)
port_server = 5560 #TODO: get port from config
subscriber.connect ("tcp://localhost:{0}".format(port_server)) # connect to server

port_client = "5559"
zmq_sck = zmq_ctx.socket(zmq.PUB)
zmq_sck.connect("tcp://localhost:{0}".format(port_client))


#
# Subscribe to topics
#
topics = ['/source','/player']
for topic in topics:
	subscriber.setsockopt (zmq.SUBSCRIBE, topic)

#
# App. Init
#
#
myprint('Loading Source Plugins...',tag='SYSTEM')
# import sources directory
import sources
# read source config files and start source inits
load_sources( os.path.join(os.path.dirname(os.path.abspath(__file__)),'sources') )

sc_sources.sourceCheckAll()
printSummary(sc_sources)

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
# Initialize the mainloop
DBusGMainLoop(set_as_default=True)


#
# main loop
mainloop = gobject.MainLoop()

#
# Queue handler
# NOTE: Remember, everything executed through the qBlock queue blocks, including qPrio!
# IDEALLY, WE'D PUT THIS BACK IN A THREAD, IF THAT WOULD PERFORM... (which for some reason it doesn't!)
gobject.idle_add(mq_recv)
queue_actions = Queue(maxsize=40)		# Blocking stuff that needs to run in sequence
gobject.idle_add(process_queue)

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
	