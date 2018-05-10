#!/usr/bin/python

from time import sleep

from modules.hu_msg import MqPubSubFwdController

DESCRIPTION = "Send a MQ command"
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559
RETURN_PATH = '/bladiebla/'

args = None
messaging = None

commands = [
	'source-check',
	'source-select',
	'source-next',
	'source-prev',
	'player-play',
	'player-pause',
	'player-stop',
	'player-next',
	'player-prev',
	'player-nextfolder',
	'player-prevfolder',
	'player-update',
	'player-random',
	'volume',
	'volume-att',
	'volume-mute',
	'system-reboot',
	'system-shutdown',
	'events-udisks-add'	]

#	   COMMAND, PARAMETERS                     DESCRIPTION, REST COMMAND, PATH
commands2 = [
	 ('source-check',  '[index, subindex]',   'Check source availability','PUT','/source/check',)
	,('source-select', 'index, [subindex]',   'Select a source','PUT','/source/subsource',)
	,('source-next-primary', None,            'Select next primary source','PUT','/source/next_primary',)
	,('source-prev-primary', None,            'Select previous primary source','PUT','/source/prev_primary',)
	,('source-next', None,                    'Select next source','PUT','/source/next',)
	,('source-prev', None,                    'Select previous source','PUT','/source/prev',)
	,('source-available', 'true|false, index, subindex',  'Set source availability','PUT','/source/available',)
	,('source-details', '[index, subindex]',  'Get source details','GET','/source/subsource',)
	,('player-play', None,                    'Start playback','PUT','/player/state',)
	,('player-pause', None,                   'Pause playback','PUT','/player/state',)
	,('player-stop', None,                    'Stop playback','PUT','/player/state',)
	,('player-state', None,                   'Get state','GET','/player/state',)
	,('player-next', None,                    'Play next song','PUT','/player/next',)
	,('player-prev', None,                    'Play previous song','PUT','/player/prev',)
	,('player-seek', '[+/-]seconds',          'Seek','PUT','/player/seek',)
	,('player-folders', None,                 'List folders','GET','/player/folders',)
	,('player-nextfolder', None,              'Next folder','PUT','/player/nextfolder',)
	,('player-prevfolder',None,               'Prev folder','PUT','/player/prevfolder',)
	,('player-update', '[location]',          'Update MPD database','PUT','/player/update',)
	,('player-random-modes', None,            'Get available random modes','GET','/player/randommode',)
	,('player-random', '[on | off | mode]',   'Set random','PUT','/player/random',)
	,('player-details', None,                 'Get player details','GET','/player/track',)
	,('volume', 'volume',                     'Set volume','PUT','/volume',)
	,('volume-att', '[on | off]',             'Set volume to ATT level','PUT','/volume/att',)
	,('volume-mute', '[on | off]',            'Mute volume','PUT','/volume/mute',)
	,('system-reboot', '[timer]',             'Reboot system','PUT','/system/reboot',)
	,('system-shutdown', '[timer]',           'Shutdown system' ,'PUT','/system/shutdown',)
	,('events-udisks-add', 'payload',         'Emulate a udisks-add event','DATA','/events/udisks/added',)
	,('events-udisks-rem', 'payload',         'Emulate a udisks-rem event','DATA','/events/udisks/removed',)
	,('events-network-up', 'payload',         'Emulate a network-up event','DATA','/events/network/up',)
	,('events-network-down', 'payload',       'Emulate a network-down event','DATA','/events/network/down',)
	]


#********************************************************************************
# Parse command line arguments
#
def parse_args():

	import argparse
	global args
	
	# cmd.py										Show available commands and switches
	# cmd.py [options] <command> [args]				Execute command, with optional parmeter
	# cmd.py [options] [-x <-p> <-c> [-a] [-r] ]	Execute specified path and command, with optional parameters and return path
	
	description_with_commands = DESCRIPTION
	for command in commands2:
		description_with_commands = description_with_commands +'\n {0} {1} {2}'.format(command[0],command[1],command[2])
	
	parser = argparse.ArgumentParser(description=description_with_commands)
	subparsers = parser.add_subparsers(help='Specify MQ message')
	# options:
	parser.add_argument('-v', action='store_true', help='Verbose')
	parser.add_argument('--port_publisher','-pp',  action='store')
	parser.add_argument('--port_subscriber','-ps', action='store')

	x_parser = subparsers.add_parser("-x")

	# -x
	#parser.add_argument('-x', action='store', help='Specify MQ message')
	x_parser.add_argument('-p', action='store', required=True)
	x_parser.add_argument('-c', action='store', required=True)
	x_parser.add_argument('-a', action='store')
	x_parser.add_argument('-r', action='store_true')
	x_parser.add_argument('-j','--json', action='store_true')
	
	# command
	cmd_parser = subparsers.add_parser("command")
	parser.add_argument('command', action='store', choices=commands)
	parser.add_argument('command_arg', action='store') # how to make this positional optional??
	
	args = parser.parse_args()
	print args
	exit(0)

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
