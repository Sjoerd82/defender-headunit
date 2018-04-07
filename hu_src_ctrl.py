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
# Switches:
# -r, --resume		Resume source
# -p, --play		Start playback (ignore resume)
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

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
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

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# NOT USED AT THE MOMENT...
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

	print "DEBUG: ret = {0}".format(ret)

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
			
		#	settings['source'] = curr_source['name']
		#	save_settings()
			save_resume()
			
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
			print "INVALID ARGS"
			return None

		ret = sc_sources.select_next()
		
		# returns None if cannot change source
		if ret is not None:
	
			# LL_DEBUG
			printSummary()

			data = get_data(ret,False,'/events/source/active')
			print data
		
		# TODO, Should we return a 4xx or 5xx maybe?
		#return data
	
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

	ret = None
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
			ret = sc_sources.source_get_details()

		# only keep the track section
		if ret is not None and 'track' in ret:
			ret = ret['track']
			
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
			ret = sc_sources.source_play(position=args[0])

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
			ret = sc_sources.source_get_state()
			
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
			
		# PARSE STATE -- IS THIS THE RIGHT PLACE TO DO THIS?
		if not isinstance(state,dict):
			#return False	#?
			printer ("argument is not a dictionary")
			return None
					
		if 'state' in state:
			if state['state'] in ('play','playing'):
				ret = sc_sources.source_play()
			elif state['state'] in ('stop'):
				ret = sc_sources.source_stop()
			elif state['state'] in ('pause','paused'):
				ret = sc_sources.source_pause()
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
			print "PUT NEXT NO ARGS"
			ret = sc_sources.source_next()
		elif len(args) == 1:
			print "PUT NEXT 1 ARG"
			ret = sc_sources.source_next(adv=args[0])

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

	ret = None
	if function_to_call in locals():
		ret = locals()[function_to_call](args)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret))
	else:
		printer('Function {0} does not exist'.format(function_to_call))

	return ret

def handle_path_events(path,cmd,args):

	base_path = 'events'
	# remove base path
	del path[0]
	
	def data_source_active(args):
		pass
	def data_source_available(args):
		pass
	def data_player_state(args):
		pass
	def data_player_track(args):
		pass
	def data_player_elapsed(args):
		pass
	def data_player_updating(args):
		pass
	def data_player_updated(args):
		pass
	def data_volume_changed(args):
		pass
	def data_volume_att(args):
		pass
	def data_volume_mute(args):
		pass
	def data_system_shutdown(args):
		pass
	def data_system_reboot(args):
		pass
	def data_udisks_added(args):
		payload = json.loads(args[0])
		sc_sources.do_event('udisks',path,payload)
		printSummary()
		return None
		
	def data_udisks_removed(args):
		pass

	if path:
		function_to_call = cmd + '_' + '_'.join(path)
	else:
		# called without sub-paths
		function_to_call = cmd + '_' + base_path

	ret = None
	if function_to_call in locals():
		ret = locals()[function_to_call](args)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret))
	else:
		printer('Function {0} does not exist'.format(function_to_call))

	return ret

# ********************************************************************************
# On Idle
#
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

		# send message to dispatcher for handling	
		retval = dispatcher(parsed_msg['path'],parsed_msg['cmd'],parsed_msg['args'])
		
		if parsed_msg['resp_path']:
			#print "DEBUG: Resp Path present.. returing message.."
			messaging.publish_command(parsed_msg['resp_path'],'DATA',retval)
		
	return True # Important! Returning true re-enables idle routine.

# ********************************************************************************
# Save resume file
#
# todo: consider splitting this method in two
# todo: consider writing to the end of the file and reading backwards instead
#
def save_resume():
	cur_comp_subsource = sc_sources.composite()
	if cur_comp_subsource is False or cur_comp_subsource is None:
		return cur_comp_subsource

	# TODO: check if dir. present, create if not
	
	# Save System resume source indicator
	resume_file = os.path.join(configuration['directories']['resume'],configuration['files']['resume'])
	printer('Saving resume file to: {0}'.format(resume_file))
	with open(resume_file, 'wb') as f_resume_file:
		f_resume_file.write('{0}\n'.format( cur_comp_subsource['name'] ))

	# sub-source
	
	ss_resume_file = os.path.join(configuration['directories']['resume'], cur_comp_subsource['name']+"."+cur_comp_subsource['keyvalue']+".json")
	printer('Saving resume file to: {0}'.format(ss_resume_file))
	state = sc_sources.source_get_state()
	state = {}
	state['id'] = 2
	state['filename'] = 'bla.mp3'
	state['time'] = 23
	resume_data = {}
	resume_data['id'] = state['id']
	resume_data['filename'] = state['filename']
	resume_data['time'] = state['time']
	print resume_data
	try:
		json.dump( resume_data, open( ss_resume_file, "wb" ) )
	except:
		printer(' > ERROR saving resume file',level=LL_ERROR)
		pa_sfx(LL_ERROR)
		
# ********************************************************************************
# Load configuration
#
def load_configuration():

	# utils # todo, present with logger
	configuration = configuration_load(LOGGER_NAME,args.config)
	
	if not configuration or not 'zeromq' in configuration:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Default Pub port: {0}'.format(DEFAULT_PORT_PUB))
		printer('Default Sub port: {0}'.format(DEFAULT_PORT_SUB))
		configuration = { "zeromq": { "port_subscriber": DEFAULT_PORT_SUB, "port_publisher":DEFAULT_PORT_PUB } }
	
	return configuration

# ********************************************************************************
# Execute a check_availability() on all sources
#
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

# ********************************************************************************
# Print a source summary
#
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
		
		if source['enabled'] == False:
			printer(' {0} {1:2d}   {2:17} {3} {4:20}'.format(" ",i,source['displayname'],colorize("not available",'dark_gray'),colorize("disabled",'dark_gray')), tag='')		
		elif not subsources:
			printer(' {0} {1:2d}   {2:17} {3} {4:20}'.format(" ",i,source['displayname'],colorize("not available",'dark_gray'),colorize("no subsources",'dark_gray')), tag='')
		else:
			j = 0
			for subsource in subsources:
			
				# Availability
				if subsource['available']:
					available = colorize('available    ','light_green')
				else:
					available = colorize('not available','light_red')
		
				# Active indicator
				if i == arCurrIx[0] and j == arCurrIx[1]:
					active = colorize(">",'light_green')
					cur_state = sc_sources.source_get_state()
					if cur_state['state'] is None:
						state = colorize("None",'dark_gray')
					else:
						state = colorize(cur_state['state'],'light_green')
				else:
					state = ""
					active = " "
						
				# SubSource data
				if 'mountpoint' in subsource:
					mountpoint = subsource['mountpoint']
				else:
					mountpoint = ""

				printer(' {0} {1:2d}.{2} {3:17} {4} {5:20} {6}'.format(active,i,j,source['displayname'],available,mountpoint,state), tag='')
				
				j += 1
				
		i += 1
	printer('----------------------------------------------------------------------', tag='')


def QuickPlay( prevSource, prevSourceSub ):
	"""Resume playing
	"""

	if prevSource == "" or prevSource is None:
		printer ('No previous source.', tag='QPLAY')
		return None
	
	if prevSourceSub == "" or prevSourceSub is None:
		printer ('No previous subsource.', tag='QPLAY')
		return None

	printer("Previous source: {0} {1}".format(prevSource, prevSourceSub), tag='QPLAY' )

	def get_prev_index( prevSourceName, prevSourceSub, doCheck ):
		""" loop through sources, find source by name, find subsource by key """

		retSource = []
		
		ix = 0
		for source in sc_sources.source_all():
			#print "{0} Source {1}".format(ix,source["name"])
			#print source
			if source['name'] == prevSourceName:
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
									if not sc_sources.sourceCheck( ix, ix_ss ): #subsource['mountpoint'] ):
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
									if not sc_sources.sourceCheck( ix ):
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

	prevIx = get_prev_index( prevSource, prevSourceSub, True ) #PlayPrevSource()
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
	parser.add_argument('--resume','-r', action='store_true')
	parser.add_argument('--play','-p', action='store_true')	
	args = parser.parse_args()

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
	#pa_sfx_load( configuration['directories']['sfx'] )

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
	
	#
	# Resume playback
	#
	if args.resume is True:
		#QuickPlay()
		printSummary()
		
	#
	# Start playback
	#
	if args.play is True:
		sc_sources.source_play()
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

