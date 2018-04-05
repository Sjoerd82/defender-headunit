#!/usr/bin/python

from time import sleep

from modules.hu_msg import MqPubSubFwdController

DESCRIPTION = "Send a MQ command"
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559
RETURN_PATH = '/bladiebla/'

args = None
messaging = None

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
	parser.add_argument('command', action='store')
	
	
	
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


	if args.command == 'source-next':
		path = '/source/next'
		cmd = 'PUT'
		params = None
		ret = messaging.publish_command(path,cmd,params)
	elif args.command == 'player-play':
		path = '/player/next'
		cmd = 'PUT'
		params = None
		ret = messaging.publish_command(path,cmd,params)
		

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
