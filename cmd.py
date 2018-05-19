#!/usr/bin/python

# TODO:
# - add list of process status
# - request list of registered USB devices

import os
import json
import sys
from time import sleep

sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "Headunit CLI"
#WELCOME = 
LOG_TAG = None
LOGGER_NAME = "None"

DESCRIPTION = "Send a MQ command"
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559
RETURN_PATH = '/cmdpy/'

args = None
args1 = None
messaging = None

cfg_main = None		# main
cfg_zmq = None		# Zero MQ

commands = []

mq_cmd = None
mq_path = None
mq_args = None
mq_rpath = None


app_commands =	[
	{	'name': 'source-check',
		'params': [
			{'name':'index','required':False, 'help':''},
			{'name':'subindex','required':False, 'help':''}
		],
		'description': 'Check source availability',
		'command': 'PUT',
		'path': '/source/check'
	},
	{	'name': 'source-select',
		 'params': [
			{'name':'index', 'required':True, 'help':''},
			{'name':'subindex','required':False, 'help':''}
		],
		 'description': 'Select a source',
		 'command':'PUT',
		 'path': '/source/subsource'
	},
	{	'name': 'source-next-primary',
		'params': None,
		'description': 'Select next primary source',
		'command': 'PUT',
		'path': '/source/next_primary'
	},
	{	'name': 'source-prev-primary',
		'params': None,
		'description': 'Select previous primary source',
		'command': 'PUT',
		'path': '/source/prev_primary'
	},	
	{	'name': 'source-next',
		'params': None,
		'description': 'Select next source',
		'command': 'PUT',
		'path': '/source/next'
	},
	{	'name': 'source-prev',
		'params': None,
		'description': 'Select previous source',
		'command': 'PUT',
		'path': '/source/prev'
	},
	{	'name': 'source-available',
		 'params': [
			{'name':'availability', 'required':True, 'help':''},
			{'name':'index', 'required':True, 'help':''},
			{'name':'subindex','required':True, 'help':''}
		],
		'description': 'Set source availability',
		'command': 'PUT',
		'path': '/source/available'
	},
	{	'name': 'source-details',
		'params': [
			{'name':'index','required':False, 'help':'Source index'},
			{'name':'subindex','required':False, 'help':'Source subindex'}
		],
		'description': 'Get source details',
		'command': 'GET',
		'path': '/source/subsource'
	},
	{	'name': 'source-update',
		'params': [
			{'name':'index','required':False, 'help':'Source index'},
			{'name':'subindex','required':False, 'help':'Source subindex'}
		],
		'description': 'Update source (MPD: Source Database)',
		'command': 'PUT',
		'path': '/source/update'
	},
	{	'name': 'source-update-location',
		'params': [
			{'name':'location','required':True, 'help':'Relative location, as seen from MPD'}
		],
		'description': 'Update MPD database for given location',
		'command': 'PUT',
		'path': '/source/update-location'
	},
	{	'name': 'player-play',
		'params': None,
		'description': 'Start playback',
		'command': 'PUT',
		'path': '/player/state',
		'params_override': '{"state":"play"}'
	},
	{	'name': 'player-pause',
		'params': None,
		'description': 'Pause playback',
		'command': 'PUT',
		'path': '/player/state',
		'params_override': '{"state":"pause"}'
	},
	{	'name': 'player-stop',
		'params': None,
		'description': 'Stop playback',
		'command': 'PUT',
		'path': '/player/state',
		'params_override': '{"state":"stop"}'
	},
	{	'name': 'player-state',
		'params': None,
		'description': 'Get state',
		'command': 'GET',
		'path': '/player/state'
	},
	{	'name': 'player-next',
		'params': None,
		'description': 'Play next song',
		'command': 'PUT',
		'path': '/player/next'
	},
	{	'name': 'player-prev',
		'params': None,
		'description': 'Play previous song',
		'command': 'PUT',
		'path': '/player/prev'
	},
	{	'name': 'player-seek',
		'params': [ {'name':'seconds', 'required':True, 'help':'Use a + or - sign to seek forward or reverse'} ],
		'description': 'Seek',
		'command': 'PUT',
		'path': '/player/seek'
	},
	{	'name': 'player-folders',
		'params': None,
		'description': 'List folders',
		'command': 'GET',
		'path': '/player/folders'
	},
	{	'name': 'player-nextfolder',
		'params': None,
		'description': 'Next folder',
		'command': 'PUT',
		'path': '/player/nextfolder'
	},
	{	'name': 'player-prevfolder',
		'params': None,
		'description': 'Prev folder',
		'command': 'PUT',
		'path': '/player/prevfolder'
	},
	{	'name': 'player-update',
		'params': [ {'name':'location', 'required':False, 'help':'Location to update'} ],
		'description': 'Update MPD database',
		'command': 'PUT',
		'path': '/player/update'
	},
	{	'name': 'player-random-modes',
		'params': None,
		'description': 'Get available random modes',
		'command': 'GET',
		'path': '/player/randommode'
	},
	{	'name': 'player-random',
		'params': [ {'name':'mode', 'required':False, 'help':'ON | OFF | TOGGLE (default)'} ],
		'description': 'Set random',
		'command': 'PUT',
		'path': '/player/random'
	},
	{	'name': 'player-details',
		'params': None,
		'description': 'Get player details',
		'command': 'GET',
		'path': '/player/track'
	},
	{	'name': 'volume',
		'params': [ {'name':'volume', 'required':True,'help':'Volume in percentage'} ],
		'description': 'Set volume',
		'command': 'PUT',
		'path': '/volume'
	},
	{	'name': 'volume-att',
		'params': [ {'name':'mode', 'required':False, 'help':'ON (default) | OFF | TOGGLE'} ],
		'description': 'Set volume to ATT level',
		'command': 'PUT',
		'path': '/volume/att'
	},
	{	'name': 'volume-mute',
		'params': [ {'name':'mode', 'required':False, 'help':'ON | OFF | TOGGLE (default)'} ],
		'description': 'Mute volume',
		'command': 'PUT',
		'path': '/volume/mute'
	},
	{	'name': 'system-reboot',
		'params': [ {'name':'timer', 'required':False, 'help':'Time in seconds to shutdown. Default: 0'} ],
		'description': 'Reboot system',
		'command': 'PUT',
		'path': '/system/reboot'
	},
	{	'name': 'system-shutdown',
		'params': [ {'name':'timer', 'required':False, 'help':'Time in seconds to shutdown. Default: 0'} ],
		'description': 'Shutdown system' ,
		'command': 'PUT',
		'path': '/system/shutdown'
	}
	]
	
# ********************************************************************************
# Load configuration
#
def load_cfg_main():
	""" load main configuration """
	config = configuration_load(LOGGER_NAME,args1.config)
	return config

def load_cfg_zmq():
	""" load zeromq configuration """	
	if not 'zeromq' in cfg_main:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		#cfg_main["zeromq"] = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB } }
		config = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB }
		return config
	else:
		config = {}
		# Get portnumbers from either the config, or default value
		if 'port_publisher' in cfg_main['zeromq']:
			config['port_publisher'] = cfg_main['zeromq']['port_publisher']
		else:
			config['port_publisher'] = DEFAULT_PORT_PUB
		
		if 'port_subscriber' in cfg_main['zeromq']:
			config['port_subscriber'] = cfg_main['zeromq']['port_subscriber']		
		else:
			config['port_subscriber'] = DEFAULT_PORT_SUB
			
		return config
				
# ********************************************************************************
# 
#
def print_dict(obj, nested_level=0):
	spacing = '   '
	key_line = 20
	if type(obj) == dict:
		print '{0}{{'.format((nested_level) * spacing)
		for k, v in obj.items():
			uitlijnen = 20 - (nested_level*2) - len(k) - nested_level
			uitlijn = ' ' * uitlijnen
			if hasattr(v, '__iter__'):
				print '{0}{1}:'.format((nested_level + 1) * spacing, k)
				print_dict(v, nested_level + 1)
			else:
				print '{0}{1}{2}: "{3}"'.format((nested_level + 1) * spacing, k, uitlijn, v)
		print '{0}}}'.format(nested_level * spacing)
	elif type(obj) == list:
		print '{0}['.format((nested_level) * spacing)
		for v in obj:
			if hasattr(v, '__iter__'):
				print_dict(v, nested_level + 1)
			else:
				print '{0}"{1}"'.format((nested_level + 1) * spacing, v)
		print '{0}]'.format((nested_level) * spacing)
	else:
		print '{0}{1}'.format(nested_level * spacing, obj)
		
def parse_args():

	def msg(name=None):
		return '''Headunit Command Interpreter
	   %(prog)s -h
	   %(prog)s [options] [help] <command> [args]
	   %(prog)s [options] mq <-p path> <-c mq-command> [-a] [-r]
	'''

	def epi(name=None):
		epilog = "List of commands:\n"
		epilog += list_of_commands_descr()
		epilog += '\nRun "{0} help <command>" explains how to use the command\n'.format(os.path.basename(__file__))
		return epilog

	def list_of_commands():
		cmd_list = ""
		for command in app_commands:
			cmd_list += command['name'] +"\n"
		return cmd_list

	def list_of_commands_descr():
		cmd_list = ""
		for command in app_commands:
			cmd_list += " {0:20} {1}\n".format(command['name'],command['description'])
		return cmd_list

	import argparse
	global commands
	global args1
	global args
	DEFAULT_LOG_LEVEL = LL_INFO
	DEFAULT_CONFIG_FILE = '/etc/configuration.json'

	for command in app_commands:
		commands.append(command['name'])
	
	# cmd.py -h										Show available commands and switches
	# cmd.py [options] [help] <command> [args]		Execute command, with optional parmeter
	# cmd.py [options] <mq> <-p> <-c> [-a] [-r] 	Execute specified path and command, with optional parameters and return path
	
	parser = argparse.ArgumentParser(description=None, usage=msg(), epilog=epi(), formatter_class=argparse.RawDescriptionHelpFormatter) #, add_help=False)
	
	# options:
	parser.add_argument('-v', action='store_true', help='Verbose')
	#parser.add_argument('--debug', action='store_true', help='Debug on')
	parser.add_argument('--loglevel', action='store', default=DEFAULT_LOG_LEVEL, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('--config','-c', action='store', help='Configuration file', default=DEFAULT_CONFIG_FILE)
	parser.add_argument('--port_pub',  action='store')
	parser.add_argument('--port_sub', action='store')
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
	
	p2 = argparse.ArgumentParser( parents = [ parser ], add_help=False )
	subparsers = p2.add_subparsers()
	
	# status
	parser_status = subparsers.add_parser('status')
	parser_status.set_defaults(which='status')
	
	# command help
	parser_help = subparsers.add_parser('help')
	parser_help.add_argument('command', action='store', nargs='*')
	parser_help.set_defaults(which='help')

	# MQ
	parser_mq = subparsers.add_parser('mq')
	parser_mq.add_argument('-p', action='store', nargs='?', const='None')	# required, but not marking here to avoid argparse feedback
	parser_mq.add_argument('-c', action='store', nargs='?', const='None')	# required, but not marking here to avoid argparse feedback
	parser_mq.add_argument('-a', action='store')
	parser_mq.add_argument('-r', action='store_true')
	#parser_mq.add_argument('-j','--json', action='store_true')
	parser_mq.set_defaults(which='mq')

	# commands
	for command in app_commands:
		parser_cmd = subparsers.add_parser(command['name'])
		parser_cmd.add_argument('command_args', action='store', nargs='*')
		parser_cmd.set_defaults(which=command['name'])
	
	args1, unknown_args = parser.parse_known_args()
	
	if not unknown_args:
		program = os.path.basename(__file__)
		print "Headunit Command Interpreter"
		print "{0} -h".format(program)
		print "{0} [options] status".format(program)
		print "{0} [options] [help] <command> [args]".format(program)
		print "{0} [options] mq <-p path> <-c mq-command> [-a] [-r]".format(program)
		print 'Run "{0} -h" for a list of commands'.format(program)		
		exit(0)

	args = p2.parse_args()
	

def setup():
	
	#
	# ZMQ
	#
	"""
	global messaging
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	messaging.create_publisher()
	messaging.create_subscriber()
	#messaging.create_subscriber(SUBSCRIPTIONS)
	sleep(1)
	"""

	global logger
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)
	logger = log_create_console_loghandler(logger, args1.loglevel, LOG_TAG) 	# output to console

	#
	# Configuration
	#
	global cfg_main
	#global cfg_zmq	#only used here(?)

	cfg_main = load_cfg_main()
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)

	# zeromq
	if not args1.port_publisher and not args1.port_subscriber:
		cfg_zmq = load_cfg_zmq()
	else:
		if args1.port_publisher and args1.port_subscriber:
			pass
		else:
			load_cfg_zmq()
	
		# Pub/Sub port override
		if args1.port_publisher:
			configuration['zeromq']['port_publisher'] = args1.port_publisher
		if args1.port_subscriber:
			configuration['zeromq']['port_subscriber'] = args1.port_subscriber

	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
		
	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Subscriber: {0}".format(DEFAULT_PORT_SUB))
	messaging.create_subscriber()

	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()
	
def main():

	global mq_cmd
	global mq_path
	global mq_args
	global mq_rpath

	if args.which == 'status':
		if 'daemons' not in cfg_main:
			return
		else:
			print "Daemon status:"
			print "{0:20} {1:15} PID  Status".format("Service","init.d")
			for daemon in cfg_main['daemons']:
				if 'pid_file' in cfg_main['daemons']:
					pid_file = cfg_main['daemons']['pid_file']
					if os.path.exists(pid_file):
						with open(pid_file,'r') as dmn_pid:
							print dmn_pid
					dmn_status = "Uhm.."
				else:
					dmn_status = "Unknown"
					dmn_pid = "?"
				print "{0:20} {1:15} {2:4} {3}".format(daemon['name'],daemon['init.d'],dmn_pid,dmn_status)
				
		exit(0)

	
	if args.which == 'help':
		if not args.command:
			print "Available commands:"
			print list_of_commands_descr()
			print 'Run "{0} help <command>" for more details'.format(os.path.basename(__file__))
			exit(1)
		elif args.command[0] in commands:
			ix = commands.index(args.command[0])
			print "{0}".format(app_commands[ix]['description'])
			param_string = ""
			if 'params' in app_commands[ix]:
				param_help = ""
				for param in app_commands[ix]['params']:
					if param['required']:
						param_string += "<"+param['name']+"> "
					else:
						param_string += "["+param['name']+"] "
					if 'help' in param:
						param_help += " {0:12}{1}\n".format(param['name'], param['help'])
			print "Syntax:\n {0} {1}".format(args.command[0],param_string)
			if not param_help == "":
				print "Parameters:"
				print "{0}".format(param_help)
			exit(0)
		else:
			print "Unknown command: {0}".format(args.command[0])
			print 'Run "{0} help" for a list of commands'.format(os.path.basename(__file__))
			exit(1)
		
	# MQ command
	if args.which == 'mq':
	
		if not args.p:
			print "error: argument -p is required"
		elif args.p == 'None':
			print "error: argument -p syntax: -p path"
	
		if not args.c:
			print "error: argument -c is required"
		elif args.c == 'None':
			print "error: argument -c syntax: -c command; example: GET, PUT, DATA"
		
		#TODO
		mq_cmd = None
		mq_path = None
		mq_args = None
		mq_rpath = None
		mq_param = None
		exit(0)
	
	# Pre-defined command
	if args.which in commands:
		ix = commands.index(args.which)

		mq_cmd = app_commands[ix]['command']
		mq_path = app_commands[ix]['path']
		if 'params_override' in app_commands[ix]:
			mq_args = app_commands[ix]['params_override']
		else:
			params = {}
			for pix, command_arg in enumerate(args.command_args):
				key = app_commands[ix]['params'][pix]['name']
				params[key] = command_arg
			
			mq_args = json.dumps(params)
			if mq_cmd == 'GET':
				mq_rpath = RETURN_PATH
			
		if mq_args == "{}":
			mq_args = None
	
	# debug
	#print "excuting command! {0} {1} with params {2}".format(mq_cmd,mq_path,mq_args)

	# ******************************************************************************************************************
	
	
	# todo: check, is it ok to include an empty mq_args?
	if mq_rpath is not None:
		ret = messaging.publish_command(mq_path,mq_cmd,mq_args,wait_for_reply=True,response_path=RETURN_PATH)
	else:
		ret = messaging.publish_command(mq_path,mq_cmd,mq_args)
	
	if ret == True:
		print "Response: [OK]"
	elif ret == False or ret is None:
		print "Response: [FAIL]"
	else:
		if type(ret) == dict:
			if 'retval' in ret: print "Return code: {0}".format(ret['retval'])
			if 'payload' in ret:
				print "Return data:"
				print_dict(ret['payload'])
		elif type(ret) == str:
			print ret
					
	"""
	# FOR DEBUGGING PURPOSES
	elif args.command == 'events-udisks-add':
		cmd = 'DATA'
		path = '/events/udisks/added'
		params = '{"device":"/dev/sda1", "mountpoint":"","uuid":"f9dc11d6-01","label":""}'
	"""
	
	#ret = messaging.publish_command('/source/primary','GET', None, True, 5000, RETURN_PATH)
	#print ret
	exit(0)
	
if __name__ == '__main__':
	parse_args()
	setup()
	main()

