#!/usr/bin/python

#
# Network interface up/down event generator
# Call with check argument to generete an event for each interface
#

from time import sleep

from modules.hu_msg import MqPubSubFwdController

DESCRIPTION = "Send a MQ event"
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559

args = None
messaging = None

#********************************************************************************
# Parse command line arguments
#
def parse_args():

	import argparse
	global args
	
	parser = argparse.ArgumentParser(description=DESCRIPTION)
	parser.add_argument('-v', action='store_true', help='Verbose')
	parser.add_argument('-i', action='store_true', help='Check if internet available')
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
	parser.add_argument('ifupdown', action='store', choices=['ifup','ifdown','check']) #, required=True ?
	#parser.add_argument('interface', action='store')
	
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
	sleep(1)
	
def main():

	cmd = 'DATA'
	state = None
	
	if args.ifupdown == 'ifup':
		path = '/events/network/up'
		state = "up"
	elif args.ifupdown == 'ifdown':
		path = '/events/network/down'
		state = "down"
	elif args.ifupdown == 'check':
		print "check not supported"
		exit(0)
	
	internet_available = internet()
	
	if args.interface is not None:
		params.append('"interface":"{0}"'.format(args.interface))
		
	if state is not None:
		params.append('"state":"{0}"'.format(state))
	
	if internet_available is not None:
		params.append('"internet":"{0}"'.format(internet_available))
		
	param = "\{{0}\}".format(','.join(params))

	print param
	
	ret = messaging.publish_command(path,cmd,param)
	print ret
	
if __name__ == '__main__':
	parse_args()
	setup()
	main()
