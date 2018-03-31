#!/usr/bin/python

# MUSIC SOURCE CONTROLLER is used as part of a music playing platform.
# Similar to the source knob on a HiFi receiver or car headunit, this
# script can cycle through its connected sources.
#
# The Source Controller can be used to control playback of the source.
#
# Venema, S.R.G.
# 2018-03-23
# License: MIT
#
# Loads source plugins from /sources folder
#


## IGNORING QUEUING FOR NOW ! ##


import sys
import json					# load json source configuration
from Queue import Queue		# queuing
import inspect				# dynamic module loading

import gobject				# main loop
from dbus.mainloop.glib import DBusGMainLoop

#********************************************************************************
# Logging
from logging import getLogger

#********************************************************************************
# Headunit modules
from modules.hu_source import SourceController
from modules.hu_msg import MqPubSubFwdController
from modules.hu_msg import parse_message
from modules.hu_utils import * #init_load_config

#********************************************************************************
# Third party and others...
from slugify import slugify

#********************************************************************************
# Version
#
from version import __version__

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "Source Controller"
LOG_TAG = 'SRCTRL'
LOGGER_NAME = 'srctrl'

DEFAULT_CONFIG_FILE = '/etc/hu/configuration.json'
#SETTINGS = '/etc/hu/source.json'
SETTINGS = '/mnt/PIHU_CONFIG/source.json'
DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560
SUBSCRIPTIONS = ['/source/','/player/','/events/udisks/']

logger = None			# logging
args = None				# command line arguments
messaging = None		# mq messaging
configuration = None	# configuration
settings = None			# operational settings
sc_sources = None		# source controller

# still used?
queue_actions = None
#hu_details = { 'track':None, 'random':'off', 'repeat':True, 'att':False }


# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})


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


def validate_args(args, min_args, max_args):

	if len(args) < min_args:
		printer('Function arguments missing', level=LL_ERROR)
		return False
		
	if len(args) > max_args:
		printer('More than {0} argument(s) given, ignoring extra arguments'.format(max_args), level=LL_WARNING)
		#args = args[:max_args]
		
	return True

def get_data(ret,returndata=False,eventpath=None):

	data = {}
	
	if ret is None:
		data['retval'] = 500
		data['payload'] = None
		
	elif ret is False:
		data['retval'] = 500
		data['payload'] = None
		
	elif ret is True:
		data['retval'] = 200
		data['payload'] = None

	else:
		data['retval'] = 200
		data['payload'] = ret

	if eventpath is not None:
	
		#TODO: AVAILABLE EVENTS FOR EVERY AVAILABLE SOURCE ON CHECK() !!! !!! !!!
	
		if eventpath == '/events/source/active': # or eventpath == '/events/source/available':
			curr_source = sc_sources.source()
			data['payload'] = curr_source
			messaging.publish_command(eventpath,'DATA',data)
			
			settings['source'] = curr_source['name']
			save_settings()
			
		#if eventpath == '/events/source/available':
		#	now_available, now_unavailable = sc_sources.che
		#	data['payload'] = None

	if not returndata:
		data['payload'] = None
		
	return data
		
def handle_path_source(path,cmd,args):

	base_path = 'source'

	# remove base path
	del path[0]
	
	# -------------------------------------------------------------------------
	
	# Sub Functions must return None (invalid params) or a {data} object.
	def get_primary(args):
		"""	Retrieve Primary Sources

			Arguments:
				None			Retrieve list of all sources
			Return data:
				List of Sources
				
			Arguments:
				<source_id>		Retrieve specified source
			Return data:
				Specified source
				
			Return codes:
				200		OK
				500		Error
		"""
		valid = validate_args(args,0,1)
		if not valid:
			return None
		
		if not args:
			ret = sc_sources.source_all()
		elif len(args) == 1:
			ret = sc_sources.source(args[0])
		
		data = get_data(ret,True)
		return data

	def put_primary(args):
		""" Set active (sub)source to <id> (<subid>). If "P" then also start playing.

			? Starts playback if P is specified, or not (default)
			? Does not start playback if S specified
			
			Arguments:
				<int:source_id>,[int:subsource_id][,S|P]
			Return data:
				Nothing
			Return codes:
				200		OK
				500		Error
		"""
		valid = validate_args(args,0,3)
		if not valid:
			return None
			
		elif len(args) == 1:
			ret = sc_sources.select(args[0])
		elif len(args) == 2:
			ret = sc_sources.select(args[0],args[1])
		elif len(args) == 3:
			ret = sc_sources.select(args[0],args[1])
			#TODO: not implemented

		data = get_data(ret,False,'/events/source/active')
		return data
	
	def post_primary(args):
		"""	Add a new source
			Arguments:
				{source}
			Return data:
				Nothing
			Return codes:
				200		OK
				500		Error
		"""
		#TODO
		return None
		ret = sc_sources.add(args[0])	
		data = get_data(ret)
		return data
		
	def del_primary(args):
		""" Remove a source
			Arguments:
				None:			Remove current source
				source_id		Remove specified source
			Return data:
				Nothing
			Return codes:
				200		OK
				500		Error
		"""
		
		valid = validate_args(args,0,1)
		if not valid:
			return None

		if not args:
			ret = sc_sources.rem()
		elif len(args) == 1:
			ret = sc_sources.rem(args[0])
		
		# LL_DEBUG:
		printSummary()

		data = get_data(ret)
		return data
	
	def get_subsource(args):
		"""
			Arguments:
				None						Return list of sub-sources for current index
				source_id					Return list of sub-sources for specified index
				source_id, subsource_id		Return specified subsource
			Return data:
				List of sub-sources
				Sub-source
			Return codes:
				200		OK
				500		Error
		"""
		valid = validate_args(args,0,2)
		if not valid:
			return None

		if not args:
			ret = sc_sources.subsource_all()
		elif len(args) == 1:
			ret = sc_sources.subsource_all(args[0])
		elif len(args) == 2:
			ret = sc_sources.subsource(args[0],args[1])

		data = get_data(ret,True)
		return data

	def put_subsource(args):
		"""Set active subsource to <subid>. If "P" then also start playing.

			? Starts playback if P is specified, or not (default)
			? Does not start playback if S specified
			
			Arguments:
				<int:source_id>,<int:subsource_id>[,S|P]
			Return data:
				Nothing
			Return codes:
				200		OK
				500		Error
		"""
		valid = validate_args(args,1,3)
		if not valid:
			return None
			
		if len(args) == 2:
			ret = sc_sources.select(args[0],args[1])
		elif len(args) == 3:
			ret = sc_sources.select(args[0],args[1])
			#TODO: not implemented

		data = get_data(ret,False,'/events/source/active')
		return data

	def post_subsource(args):
		#TODO
		return None

	def del_subsource(args):
		""" Remove a subsource
			Arguments:
				None:							Remove current subsource
				<source_id>, <subsource_id>		Remove specified subsource
			Return data:
				Nothing
			Return codes:
				200		OK
				500		Error
		"""
		valid = validate_args(args,0,2)
		if not valid:
			return None

			
		if not args:
			ret = sc_sources.rem_sub()
		elif len(args) == 1:
			printer('This function requires an index and subindex', level=LL_ERROR)
			return None
		elif len(args) == 2:
			ret = sc_sources.rem_sub(args[0],args[1])
		
		# LL_DEBUG:
		printSummary()
			
		data = get_data(ret)
		return data
		
	def put_available(args):
		"""	Mark (sub)source as (un)available
			Arguments:
				True|False, source_id					Mark Source ID
				True|False, source_id, sub-source_id	Mark Sub-Source ID
			Return data:
				None
			Return codes:
				200		OK
				500		Error
		"""
		valid = validate_args(args,2,3)
		if not valid:
			return None

		if len(args) == 2:
			ret = sc_sources.set_available(args[1],str2bool(args[0]))
		elif len(args) == 3:
			ret = sc_sources.set_available(args[1],str2bool(args[0]),args[2])
		
		# LL_DEBUG
		printSummary()

		data = get_data(ret,False,'/events/source/available')
		return data

	def put_next(args):
		"""	Change to next available (sub)source and start playing
			Arguments:
				None
			Return data:
				None
			Return codes:
				200		OK
				500		Error
		"""
		valid = validate_args(args,0,0)
		if not valid:
			return None

		ret = sc_sources.select_next()

		# LL_DEBUG
		printSummary()

		data = get_data(ret,False,'/events/source/active')
		return data
	
	def put_prev(args):
		"""	Change to prev available (sub)source and start playing
			Arguments:
				None
			Return data:
				None
			Return codes:
				200		OK
				500		Error
		"""
		valid = validate_args(args,0,0)
		if not valid:
			return None

		ret = sc_sources.select_prev()

		# LL_DEBUG
		printSummary()

		data = get_data(ret,False,'/events/source/active')
		return data
		
	def put_check(args):
		"""	Do an availability check on given or current source
			Arguments:
				None						Check current source
				source_id					Check source
				source_id, sub-source_id	Check sub-source
			Return data:
				None
			Return codes:
				200		OK
				500		Error
		"""
		valid = validate_args(args,0,2)
		if not valid:
			return None

		if not args:
			ret = sc_sources.check()
		elif len(args) == 1:
			ret = sc_sources.check(args[0])
		elif len(args) == 2:
			ret = sc_sources.check(args[0],args[1])

		if ret != False:
			
			printSummary()		# LL_DEBUG
			
			# TODO: MOVE "check_all" LOOP HERE SO WE CAN SEND OUT EVENTS EARLIER !
			# TODO-INSTEAD: local def function check_all()
			
			for change in ret:
				print "CHANGED: {0}".format(change)
				#available_source = {}
				#available_source['index'] = change['index']
				#available_source['subindex'] = change['subindex']
				#available_source['available'] = change['available']
				#messaging.publish_command('/events/source/available','DATA',available_source)
				messaging.publish_command('/events/source/available','DATA',change)
				
			
			"""
			for indexes in ret:
				print "FOR INDEX IN RET: index={0}".format(indexes)	# [1,0], [1]
				index = indexes[0]
				if len(indexes) > 1:
					for subindex in indexes[1:]:
						print "FOR SUBINDEX IN {0}".format(indexes[1:])
						subsource = sc_sources.subsource(index,subindex)
						available_source = {}
						available_source['index'] = index
						available_source['subindex'] = subindex
						available_source['available'] = subsource['available']
						messaging.publish_command('/events/source/available','DATA',available_source)
				else:
					source = sc_sources.source(index)
					available_source = {}
					available_source['index'] = index
					available_source['available'] = source['available']
					messaging.publish_command('/events/source/available','DATA',available_source)
					
			"""
		
		data = get_data(ret)
		return data

	# -------------------------------------------------------------------------
	if path:
		function_to_call = cmd + '_' + '_'.join(path)
	else:
		# called without sub-paths
		function_to_call = cmd + '_' + base_path

	if function_to_call in locals():
		ret = locals()[function_to_call](args)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret)) # TODO: LL_DEBUG
	else:
		printer('Function {0} does not exist'.format(function_to_call))
		
	return ret
		
def handle_path_player(path,cmd,args):

	base_path = 'player'

	# remove base path
	del path[0]
	
	def get_track(args):
		"""	Retrieve Track details
			Arguments:		None
			Return data:	Track Details	
		"""
		valid = validate_args(args,0,0)
		if not valid:
			return None

		if not args:
			ret = sc_sources.source_get_media_details()

		data = get_data(ret,True)
		return data
		
	def put_track(args):
		"""	Play track at specified playlist position
			Arguments:		Playlist position
			Return data:	Nothing
		"""
		valid = validate_args(args,1,1)
		if not valid:
			return None

		if len(args) == 1:
			ret = sc_sources.source_play(args[0])

		data = get_data(ret,True)
		return data

	'''
	TODO
	def get_folders(args):
		"""	Retrieve list of playlist-folder mappings
			Arguments:		None
			Return data:	playlist-folder mapping
		"""
		valid = validate_args(args,0,0)
		if not valid:
			return None

		if not args:
			ret = sc_sources.()

		data = get_data(ret,True)
		return data
	'''

	def put_pause(args):
		"""	Enable/Disable Pause
			Arguments:		on|off|toggle
			Return data:	Nothing
		"""
		valid = validate_args(args,1,1)
		if not valid:
			return None
			
		if len(args) == 1:
			ret = sc_sources.source_pause(args[0])

		# Set pause: on|off|toggle
		
		data = get_data(ret,True)
		return data

	def get_state(args):
		"""	Get play state
			Arguments:		None
			Return data:	State
		"""
		valid = validate_args(args,0,0)
		if not valid:
			return None

		if not args:
			ret = sc_sources.get_state()

			
		# Get state: play|pause|stop, toggle random
		data = get_data(ret,True)
		return data


	def put_state(args):
		"""	Set play state
			Arguments:		{state}
			Return data:	Nothing
		"""
		valid = validate_args(args,1,1)
		if not valid:
			return None

		state = json.loads(args[0])
		print state
		print type(state)
			
		# PARSE STATE -- IS THIS THE RIGHT PLACE TO DO THIS?
		if not isinstance(state,dict):
			#return False	#?
			printer ("argument is not a dictionary")
			return None
					
		if 'state' in state:
			if state['state'] in ('play','playing'):
				ret = sc_sources.play()
			elif state['state'] in ('stop'):
				ret = sc_sources.stop()
			elif state['state'] in ('pause','paused'):
				ret = sc_sources.pause()
			else:
				print "UNKNOWN state: {0}".format(state['state'])
				return None #?
			
		# Set state: play|pause|stop, toggle random
		data = get_data(ret,True)
		return data


	def put_random(args):
		"""	Set random mode
			Arguments:		on|off|toggle|mode
			Return data:	Nothing
		"""
		valid = validate_args(args,1,1)
		if not valid:
			return None

		# Set random on|off|toggle|special modes

		if len(args) == 1:
			ret = sc_sources.source_random(args[0])

		data = get_data(ret,True)
		return data


	'''
	TODO
	def get_randommode(args):
		"""	Get list of supported random modes
			Arguments:		None
			Return data:	{randommodes}
		"""
		valid = validate_args(args,0,0)
		if not valid:
			return None

		if not args:
			ret = sc_sources.()

			# Get list of (supported) random modes
		data = get_data(ret,True)
		return data
	'''

	def put_next(args):
		"""	Next track
			Arguments:
				None		Advance by 1
				<int>		Advance by <int>
			Return data:	Nothing
		"""
		valid = validate_args(args,0,1)
		if not valid:
			return None

		if not args:
			ret = sc_sources.source_next()
		elif len(args) == 1:
			ret = sc_sources.source_next(args[0])

		data = get_data(ret,True)
		return data

	def put_prev(args):
		"""	Prev track
			Arguments:
				None		Go back 1
				<int>		Go back <int>
			Return data:	Nothing
		"""
		valid = validate_args(args,0,1)
		if not valid:
			return None

		if not args:
			ret = sc_sources.source_prev()
		elif len(args) == 1:
			ret = sc_sources.source_prev(args[0])

		data = get_data(ret,True)
		return data

	"""
	def put_nextfolder(args):
		return True
		
	def put_prevfolder(args):
		return True
	"""
	
	def put_seekfwd(args):
		"""	Seek FWD
			Arguments:
				None		Seek Fwd by ? seconds
				<int>		Seek Fwd by <int> seconds
			Return data:	Nothing
		"""
		valid = validate_args(args,0,1)

		if not args:
			ret = sc_sources.seekfwd()
		elif len(args) == 1:
			ret = sc_sources.seekfwd(args[0])

		data = get_data(ret,True)
		return data

	def put_seekrev(args):
		"""	Seek REV
			Arguments:
				None		Seek back by ? seconds
				<int>		Seek back by <int> seconds
			Return data:	Nothing
		"""
		valid = validate_args(args,0,1)

		if not args:
			ret = sc_sources.seekrev()
		elif len(args) == 1:
			ret = sc_sources.seekrev(args[0])

		data = get_data(ret,True)
		return data

	"""
	def get_playlist(args):
		# Retrieve current or specified playlist
		playlist = sc_sources.source_get_playlist()
		print playlist
		# TODO: ehmm, do something with the state
		return True
	"""

	'''
	TODO
	def put_update_location(args):
		"""	Update MPD, preferably set a location
			Arguments:
				None		Update entire database
				<location>	Update <location>
			Return data:	Nothing
		"""
		valid = validate_args(args,0,1)

		if not args:
			ret = sc_sources.()
		elif len(args) == 1:
			ret = sc_sources.(args[0])

		# Update MPD, preferablly specify a location
		ret = sc_sources.source_update()
		return ret
	'''
	
	def put_update_source(args):
		"""	Update MPD for source
			Arguments:		Source index
			Return data:	Nothing
		"""
		valid = validate_args(args,1,1)
		
		if not args:
			ret = sc_sources.source_update()
		elif len(args) == 1:
			ret = sc_sources.source_update(args[0])

		data = get_data(ret,True)
		return data

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

	return ret


# ********************************************************************************
# Initialization functions
#
#  - Load source plugins
#  - Summary printer
#

"""
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

"""
	
def check_all_sources_send_event():

	all_sources = sc_sources.source_all()
	
	i=0
	for source in all_sources:
		check_result = sc_sources.check(i)
		#check_result = source['sourceClass'].check(self)	#returns a list of dicts with changes
		if check_result:
			for result in check_result:
				messaging.publish_command('/events/source/available','DATA',result)
		i+=1



# print a source summary
def printSummary():
	
	printer('-- Summary -----------------------------------------------------------', tag='')
	arCurrIx = sc_sources.index_current()
	sCurrent = sc_sources.source(None)
	
	if not arCurrIx[1] is None:
		sCurrDisplay = sCurrent['displayname']
	else:
		sCurrDisplay = ""
	
	if len(arCurrIx) == 0:
		printer('Current source: None', tag='')
	else:
		printer('Current source: {0}.{1} {2}'.format(arCurrIx[0],arCurrIx[1],sCurrDisplay), tag='')
	
	i = 0
	for source in sc_sources.source_all():
		# get subsources
		subsources = sc_sources.subsource_all(i)
		for subsource in subsources:
			if subsource['available']:
				available = colorize('available    ','light_green')
			else:
				available = colorize('not available','light_red')
	
			if 'mountpoint' in subsource:
				mountpoint = subsource['mountpoint']
				printer(' {0:2d} {1:17} {2} {3}'.format(i,source['displayname'],available,mountpoint), tag='')
			else:
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
				configuration_save( args.config, configuration )

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
			indexAdded = sc_sources.index('name',config['name'])
			sc_sources.source_init(indexAdded)
	
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
	

def idle_message_receiver():
	#print "DEBUG: idle_msg_receiver()"
	
	def dispatcher(path, command, arguments):
		handler_function = 'handle_path_' + path[0]
		if handler_function in globals():
			ret = globals()[handler_function](path, command, arguments)
			return ret
		else:
			print("No handler for: {0}".format(handler_function))
			return None
		
	rawmsg = messaging.poll(timeout=None)				#None=Blocking
	if rawmsg:
		printer("Received message: {0}".format(rawmsg))	#TODO: debug
		parsed_msg = parse_message(rawmsg)
		print parsed_msg
		# send message to dispatcher for handling
		
		retval = dispatcher(parsed_msg['path'],parsed_msg['cmd'],parsed_msg['args'])
		
		if parsed_msg['resp_path']:
			#print "DEBUG: Resp Path present.. returing message.."
			messaging.publish_command(parsed_msg['resp_path'],'DATA',retval)
		
	
	return True #important, returning true re-enables idle routine.
	
				

#********************************************************************************
# Parse command line arguments
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
	args = parser.parse_args()

# ********************************************************************************
# Load configuration
#
def load_configuration():

	# utils # todo, present with logger
	configuration = configuration_load(LOGGER_NAME,args.config)
	
	if not configuration or not 'zeromq' in configuration:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Default Client port: {0}'.format(DEFAULT_PORT_CLIENT))
		printer('Default Server port: {0}'.format(DEFAULT_PORT_SERVER))
		configuration = { "zeromq": { "port_client": DEFAULT_PORT_CLIENT, "port_server":DEFAULT_PORT_SERVER } }
	
	return configuration

def load_settings():

	settings = configuration_load(LOGGER_NAME,SETTINGS)
	if not settings:
		settings = {}
		settings['source'] = None
		settings['subsource_key'] = None
		
	return settings

def save_settings():

	printer('Saving Settings')
	try:
		json.dump( settings, open( SETTINGS, "wb" ) )
	except:
		printer(' > ERROR saving configuration',LL_CRITICAL,True)
		pa_sfx(LL_ERROR)


#********************************************************************************
# Setup
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
	global configuration
	configuration = load_configuration()
	
	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()

	printer("ZeroMQ: Creating Subscriber: {0}".format(DEFAULT_PORT_SUB))
	messaging.create_subscriber(SUBSCRIPTIONS)

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
	printer('Loading Source Plugins...')
	global sc_sources
	sc_sources = SourceController(logger)
	sc_sources.load_source_plugins( os.path.join(os.path.dirname(os.path.abspath(__file__)),'sources') )
	
	#
	# Load Source Plugins
	#
	#printer('Loading Source Plugins...')
	#import sources
	#load_sources( os.path.join(os.path.dirname(os.path.abspath(__file__)),'sources') )

	#
	# Load Operational Settings
	#
	global settings
	settings = load_settings()
	
	
	#
	# end of initialization
	#
	#********************************************************************************
	printer('Initialized [OK]')		

#********************************************************************************
# Mainloop
#
def main():

	global queue_actions

	#sc_sources.source_check()
	check_all_sources_send_event()
	printSummary()
	
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
	gobject.idle_add(idle_message_receiver)
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

if __name__ == '__main__':
	parse_args()
	setup()
	main()

