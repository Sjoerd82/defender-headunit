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
		rawmsg = messaging.poll(timeout=None)				#None=Blocking
		if rawmsg:
			print "Received: {0}".format(rawmsg)
			
	
if __name__ == '__main__':
	parse_args()
	setup()
	main()
