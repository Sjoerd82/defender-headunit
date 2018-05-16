#!/usr/bin/python

import os
import json
from time import sleep
from modules.hu_msg import MqPubSubFwdController

DESCRIPTION = "Send a MQ command"
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559
RETURN_PATH = '/bladiebla/'

args = None
messaging = None
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
	{	'name': 'player-play',
		'params': None,
		'description': 'Start playback',
		'command': 'PUT',
		'path': '/player/state'
	},
	{	'name': 'player-pause',
		'params': None,
		'description': 'Pause playback',
		'command': 'PUT',
		'path': '/player/state'
	},
	{	'name': 'player-stop',
		'params': None,
		'description': 'Stop playback',
		'command': 'PUT',
		'path': '/player/state'
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
	

def parse_args():

	def msg(name=None):
		return '''Headunit Command Interpreter
	   %(prog)s -h
	   %(prog)s [options] [help] <command> [args]
	   %(prog)s [options] <mq> <-p path> <-c mq-command> [-a] [-r]
	'''

	def epi(name=None):
		epilog = "List of commands:\n"
		epilog += list_of_commands_descr()
		epilog += '\n"{0} help <command>" explains how to use the command\n'.format(os.path.basename(__file__))
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
	global cmd_exec
	global cmd_params

	for command in app_commands:
		commands.append(command['name'])
	
	# cmd.py -h										Show available commands and switches
	# cmd.py [options] [help] <command> [args]		Execute command, with optional parmeter
	# cmd.py [options] <mq> <-p> <-c> [-a] [-r] 	Execute specified path and command, with optional parameters and return path
	
	parser = argparse.ArgumentParser(description=None, usage=msg(), epilog=epi(), formatter_class=argparse.RawDescriptionHelpFormatter) #, add_help=False)
	
	# options:
	parser.add_argument('-v', action='store_true', help='Verbose')
	parser.add_argument('--port_pub',  action='store')
	parser.add_argument('--port_sub', action='store')
	
	p2 = argparse.ArgumentParser( parents = [ parser ], add_help=False )
	subparsers = p2.add_subparsers()
	
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
		print "{0} [options] [help] <command> [args]".format(program)
		print "{0} [options] <mq> <-p path> <-c mq-command> [-a] [-r]".format(program)
		print 'Run "{0} -h" for a list of commands'.format(program)		
		exit(0)

	args = p2.parse_args()
	
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
		exit(0)
	
	# Pre-defined command
	if args.which in commands:
		ix = commands.index(args.which)

		mq_cmd = app_commands[ix]['command']
		mq_path = app_commands[ix]['path']
		params = {}
		for pix, command_arg in enumerate(args.command_args):
			key = app_commands[ix]['params'][pix]['name']
			params[key] = command_arg
		
		mq_param = json.dumps(params)
		print type(mq_param)
		
	print "excuting command! {0} {1} with params {2}".format(mq_cmd,mq_path,mq_param)

#********************************************************************************
# Setup
#
def setup():

	#
	# ZMQ
	#
	global messaging
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	messaging.create_publisher()
	messaging.create_subscriber()
	#messaging.create_subscriber(SUBSCRIPTIONS)
	sleep(1)

	
def main():

	if mq_rpath is not None:
		#ret = messaging.publish_command(args.p,args.c,response_path=RETURN_PATH)
		ret = messaging.publish_command(mq_path,mq_cmd,response_path=RETURN_PATH)
	else:
		#ret = messaging.publish_command(args.p,args.c,params)
		ret = messaging.publish_command(mq_path,mq_cmd,mq_param)
		
	print ret

	
	exit(0)
	cmd = 'PUT'
	params = None
	
	if args.command is not None:
		for command in commands2:
			if args.command == command[0]:
				cmd = command[3]
				path = command[4]
				
				#if cmd == 'source-details':
				#	if args.command_arg is not None:
				#		
				if cmd == 'player-play':
					params = '{"state":"play"}'
				elif cmd == 'player-pause':
					params = '{"state":"pause"}'
				elif cmd == 'player-stop':
					params = '{"state":"stop"}'
				elif cmd == 'player-update':
					if args.command_arg is None:
						path = '/player/update_source'
					else:
						path = '/player/update_location'
				
				if args.command_arg is not None:
					params = args.command_arg
					
	"""
	if args.command == 'source-check':
		path = '/source/check'
	elif args.command == 'source-select':
		path = '/source/subsource'
		params = args.command_arg
	elif args.command == 'source-next':
		path = '/source/next'
	elif args.command == 'source-prev':
		path = '/source/prev'
	elif args.command == 'player-play':
		path = '/player/state'
		params = '{"state":"play"}'
	elif args.command == 'player-pause':
		path = '/player/state'
		params = '{"state":"pause"}'
	elif args.command == 'player-stop':
		path = '/player/state'
		params = '{"state":"stop"}'
	elif args.command == 'player-next':
		path = '/player/next'
	elif args.command == 'player-prev':
		path = '/player/prev'
	elif args.command == 'player-nextfolder':
		path = '/player/nextfolder'
	elif args.command == 'player-prevfolder':
		path = '/player/prevfolder'
	elif args.command == 'player-update':
		path = '/player/update'
	elif args.command == 'player-random':
		path = '/player/random'
		params = '{"mode":"toggle"}'
	elif args.command == 'volume':
		path = '/volume'
		params = None	#todo
	elif args.command == 'volume-att':
		path = '/volume/att'
	elif args.command == 'volume-mute':
		path = '/volume/mute'
	elif args.command == 'system-reboot':
		path = '/system/reboot'
	elif args.command == 'system-shutdown':
		path = '/system/shutdown'

	# FOR DEBUGGING PURPOSES
	elif args.command == 'events-udisks-add':
		cmd = 'DATA'
		path = '/events/udisks/added'
		params = '{"device":"/dev/sda1", "mountpoint":"","uuid":"f9dc11d6-01","label":""}'
	"""
	
	print path
	print cmd
	print params
	
	ret = messaging.publish_command(path,cmd,params)
	print ret

	exit(0)

	#ret = messaging.publish_command('/source/primary','GET', None, True, 5000, RETURN_PATH)
	#print ret
	
	params = args.a
	#if args.j is True:
	#params = u'{"state":"play"}'
	
	if args.r:
		ret = messaging.publish_command(args.p,args.c,response_path=RETURN_PATH)
	else:
		ret = messaging.publish_command(args.p,args.c,params)
		
	print ret

	
if __name__ == '__main__':
	parse_args()
	setup()
	main()
