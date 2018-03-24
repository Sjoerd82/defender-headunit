#!/usr/bin/python

from modules.hu_msg import MqPubSubFwdController

DESCRIPTION = "Send a MQ command"
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559

args = None

#********************************************************************************
# Parse command line arguments
#
def parse_args():

	import argparse
	global args

	parser = argparse.ArgumentParser(description=DESCRIPTION)
	parser.add_argument('-p', action='store', required=True)
	parser.add_argument('-c', action='store', required=True)
	parser.add_argument('-r', action='store_true')
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
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

	
def main():
	if args.r:
		ret = messaging.publish_command(args.p,args.c,response_path='/bladiebla/')
	else:
		ret = messaging.publish_command(args.p,args.c)
		
	print ret

	
if __name__ == '__main__':
	parse_args()
	setup()
	main()
