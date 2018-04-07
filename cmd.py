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

#********************************************************************************
# Parse command line arguments
#
def parse_args():

	import argparse
	global args
	
	parser = argparse.ArgumentParser(description=DESCRIPTION)
	#parser.add_argument('-p', action='store', required=True)
	#parser.add_argument('-c', action='store', required=True)
	#parser.add_argument('-a', action='store')
	#parser.add_argument('-r', action='store_true')
	#parser.add_argument('-j','--json', action='store_true')
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
	parser.add_argument('command', action='store', choices=commands)
	parser.add_argument('command_arg', action='store') # how to make this positional optional??
	
	args = parser.parse_args()

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
