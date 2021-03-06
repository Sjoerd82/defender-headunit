#!/usr/bin/python

from time import sleep

from modules.hu_msg import MqPubSubFwdController

DESCRIPTION = "Receive all MQ traffic"
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560
SUBSCRIPTIONS = ['']

args = None
messaging = None

#********************************************************************************
# Parse command line arguments
#
def parse_args():

	import argparse
	global args

	print "Displays all MQ messages."
	
	parser = argparse.ArgumentParser(description=DESCRIPTION)
	parser.add_argument('-p','--parse', action='store_true', help='Parse MQ message')
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
	messaging.create_subscriber(SUBSCRIPTIONS)
	sleep(1)

	
def main():

	while(True):
		if args.parse:
			parsed_msg = messaging.poll(timeout=None, parse=True)	#None=Blocking
			print "Path    : {0}".format(parsed_msg['path'])
			print "Command : {0}".format(parsed_msg['cmd'])
			print "Args    : {0}".format(parsed_msg['args'])
			print "Data    : {0}\n".format(parsed_msg['data'])
			print "Origin  : {0}\n".format(parsed_msg['origin'])
		else:
			rawmsg = messaging.poll(timeout=None, parse=False)		#None=Blocking
			if rawmsg:
				print "Message: {0}".format(rawmsg)

if __name__ == '__main__':
	parse_args()
	setup()
	main()
