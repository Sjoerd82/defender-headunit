#!/usr/bin/python

# A car's Headunit Source Controller
#
# Venema, S.R.G.
# 2018-03-18
# License: MIT
#
# Loads source plugins from /sources folder
#

import sys
import json					# load json source configuration
from Queue import Queue		# queuing
import inspect				# dynamic module loading

import gobject				# main loop
from dbus.mainloop.glib import DBusGMainLoop

import time

#********************************************************************************
# Logging
from logging import getLogger
#import datetime
#import os

#********************************************************************************
# Headunit modules
from modules.hu_source import SourceController
from modules.hu_msg import MessageController
from modules.hu_utils import * #init_load_config

#********************************************************************************
# Third party and others...
from slugify import slugify

# *******************************************************************************
# Global variables and constants
#
CONFIG_FILE = '/etc/configuration.json'

# Logging
DAEMONIZED = None
LOG_TAG = 'SRCTRL'
LOGGER_NAME = 'srctrl'
LOG_LEVEL = LL_INFO

arMpcPlaylistDirs = [ ]			#TODO: should probably not be global...

hu_details = { 'track':None, 'random':'off', 'repeat':True, 'att':False }

sc_sources = None		# Source Controller
mpdc = None				# MPD Controller
messaging = None		# Messaging
logger = None			# Logging
configuration = None	# Configuration

arg_loglevel = 20
queue_actions = None


# ********************************************************************************
# Source Plugin Wrapper
#



# ********************************************************************************
# Headunit functions
#


def process_queue():
	if not queue_actions.empty(): 
 		item = queue_actions.get()
		# do smart stuff #TODO
		# - future actions that eliminate all priors: source_next, ...
		globals()[item[0]](item[1], item[2], item[3])
		queue_actions.task_done()
	return True


#def check_args(args,count,types):
#	
"""
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

def handle_path_source(path,cmd,args):

	base_path = 'source'

	# remove base path
	del path[0]

	# in paths are concatenated using underscore
	# example:
	# \player\track\next must be processed by the function called:
	# track_next

	def get_primary(args):
		"""
		Retrieve Primary Sources
		
		Arguments:
			None			Retrieve list of all sources
			<source_id>		Retrieve list of specified source
			
		Returns:
			List of Sources
			Specified Source
		"""
		if not args:
			# return all sources
			ret_sources = sc_sources.get_all_simple()
		elif len(args) == 1:
			# return source
			ret_sources = sc_sources.get(args[0])
		elif len(args) == 2:
			# return source + subsource
			#ret_sources = sc_sources.get(args[0],args[1])
			ret_sources = None #function not implemented
		
		data_path = "/data/sources" # TODO: use base_path
		messaging.send_data(data_path,ret_sources)
		return True

	def put_primary(args):
		"""
		Set active (sub)source to <(sub)source_id>
		Starts playback if P is specified, or not (default)
		Does not start playback if S specified
		
		Arguments:
			<source_id>
			<source_id>,[subsource_id]
			<source_id>,[subsource_id],[S|P]

		Returns:
			Nothing
		"""
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
	
	def post_primary(args):
		"""
		Arguments:
		Returns:
		"""
		return True
		
	def del_primary(args):
		"""
		Arguments:
		Returns:
		"""
		return True
	
	def get_subsource(args):
		"""
		Arguments:
		Returns:
		"""
		# Retrieve list of subsources for current or specified source
		return True

	def put_subsource(args):
		"""
		Arguments:
		Returns:
		"""
		return True

	def post_subsource(args):
		"""
		Arguments:
		Returns:
		"""
		return True

	def del_subsource(args):
		"""
		Arguments:
		Returns:
		"""
		return True
		
	def get_available(args):
		"""
		Arguments:
		Returns:
		"""
		# Retrieve list of available sources / Set available (F=Force)
		return True

	def set_available(args):
		"""
		Arguments:
		Returns:
		"""
		# Retrieve list of available sources / Set available (F=Force)
		return True

	def put_next(args):
		"""
		Arguments:
		Returns:
		"""
		# Set active (sub)source to the next available
		ret = sc_sources.next()
		printSummary(sc_sources)
		return ret

	def put_prev(args):
		"""
		Arguments:
		Returns:
		"""
		# Set active (sub)source to the prev available
		sc_sources.next(True)
		printSummary(sc_sources)
		return True
		
	def put_check(args):
		"""
		Arguments:
		Returns:
		"""
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
		
def handle_path_player(path,cmd,args):

	base_path = 'player'

	# remove base path
	del path[0]

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
		if args[0] == "play":
			ret = sc_sources.source_play()
			return ret
		else:
			print("not supported: {0}".format(args))
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

"""
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
"""
	
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


def dispatcher(path, command, arguments):
	print("[MQ] Received Path: {0}; Command: {1}; Parameters: {2}".format(path,command,arguments))
	handler_function = 'handle_path_' + path[0]
	if handler_function in globals():
		globals()[handler_function](path, command, arguments)
	else:
		print("No handler for: {0}".format(handler_function))

def idle_msg_receiver():
	global messaging
	
	msg = messaging.receive_async()
	if msg:
		print "Received message: {0}".format(msg)
		parsed_msg = messaging.parse_message(msg)
		dispatcher(parsed_msg['path'],parsed_msg['cmd'],parsed_msg['args'])
		
	return True

#********************************************************************************
# Version
#
from version import __version__

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

#********************************************************************************
# Parse command line arguments
#
def parse_args():

	import argparse
	
	global LOG_LEVEL
	global DAEMONIZED

	parser = argparse.ArgumentParser(description='Source Controller')
	parser.add_argument('--config','-c', required=False, action='store', help='Configuration file')
	parser.add_argument('--loglevel', action='store', default=LL_INFO, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('-b', action='store_true')	# background, ie. no output to console
	args = parser.parse_args()

	LOG_LEVEL = args.loglevel
	DAEMONIZED = args.b	

	if args.config:
		CONFIG_FILE = args.config

# ********************************************************************************
# Load configuration
#
def load_configuration():

	# utils # todo, present with logger
	configuration = configuration_load(LOGGER_NAME,CONFIG_FILE)
	
	if not configuration or not 'zeromq' in configuration:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Default Client port: {0}'.format(DEFAULT_PORT_CLIENT))
		printer('Default Server port: {0}'.format(DEFAULT_PORT_SERVER))
		configuration = { "zeromq": { "port_client": DEFAULT_PORT_CLIENT, "port_server":DEFAULT_PORT_SERVER } }
	
	return configuration

#********************************************************************************
# Setup
#
def setup():

	global logger
	global messaging
	global configuration
	global sc_sources

	#
	# Logging
	#
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)

	# Start logging to console or syslog
	if DAEMONIZED:
		# output to syslog
		logger = log_create_syslog_loghandler(logger, LOG_LEVEL, LOG_TAG, address='/dev/log' )
		
	else:
		# output to console
		logger = log_create_console_loghandler(logger, LOG_LEVEL, LOG_TAG)
	
	#
	# ZMQ
	#
	printer("ZeroMQ: Connecting to ZeroMQ forwarder")
	messaging = MessageController()
	if not messaging.connect():
		printer("Failed to connect to messenger", level=LL_CRITICAL)

	topics = ['/source','/player']
	for topic in topics:
		messaging.subscribe(topic)

	printer("ZeroMQ: Starting server at port 5555")
	messaging.start_server('tcp://127.0.0.1:5555')
	printer("ZeroMQ: Register for polling")
	messaging.poll_register()
	
	#
	# Load main configuration
	#
	configuration = load_configuration()

	#
	# Load PulseAudio SFX
	#
	pa_sfx_load( configuration['directories']['sfx'] )

	#
	# "Splash Screen": Display version
	#
	printer('{0} version {1}'.format('Source Controller',__version__))


	#
	# Initialize Source Controller
	#
	sc_sources = SourceController(logger)
	
	#
	# Load Source Plugins
	#
	printer('Loading Source Plugins...')
	import sources
	load_sources( os.path.join(os.path.dirname(os.path.abspath(__file__)),'sources') )

	#
	# end of initialization
	#
	#********************************************************************************
	printer('Initialized [OK]')

	while True:
		
		message = messaging.poll()
		if message:
			print message
			messaging.send_to_client('OK')
		

#********************************************************************************
# Mainloop
#
def main():

	global queue_actions

	sc_sources.sourceCheckAll()
	printSummary(sc_sources)
	
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
	gobject.idle_add(idle_msg_receiver)
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

if __name__ == '__main__':
	parse_args()
	setup()
	main()

	