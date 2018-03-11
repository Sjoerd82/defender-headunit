#!/usr/bin/python

#
# ZeroMQ forwarder device
# Venema, S.R.G.
# 2018-03-10
#
# FORWARDER is like the pub-sub proxy server. It allows both publishers and
# subscribers to be moving parts and it self becomes the stable hub for 
# interconnecting them.
#
# FORWARDER collects messages from a set of publishers and forwards these to
# a set of subscribers.
#
# http://learning-0mq-with-pyzmq.readthedocs.io/en/latest/pyzmq/devices/forwarder.html
#

import zmq
import sys
sys.path.append('../modules')
from modules.hu_utils import *

DEFAULT_PORT_CLIENT = 5559
DEFAULT_PORT_SERVER = 5560

def load_configuration():

	ENV_CONFIG_FILE = os.getenv('HU_CONFIG_FILE')
	
	configuration = {}
	#configuration = configuration_load(CONFIG_FILE)
	
	if not 'zeromq' in configuration:
		print('Error: ZeroMQ not in configuration, using defaults:')
		print('Client port: {0}'.format(DEFAULT_PORT_CLIENT))
		print('Server port: {0}'.format(DEFAULT_PORT_SERVER))
		configuration = { "zeromq": { "port_client": DEFAULT_PORT_CLIENT, "port_server":DEFAULT_PORT_SERVER } }
	
	return configuration

def main():

	#
	# Load main configuration
	#
	
	configuration = load_configuration()

	
	port_client = configuration['zeromq']['port_client']
	port_server = configuration['zeromq']['port_server']

	try:
		context = zmq.Context(1)
		# Socket facing clients
		frontend = context.socket(zmq.SUB)
		frontend.bind("tcp://*:{0}".format(port_client))

		# Don't filter!
		frontend.setsockopt(zmq.SUBSCRIBE, "")

		# Socket facing services
		backend = context.socket(zmq.PUB)
		backend.bind("tcp://*:{0}".format(port_server))

		zmq.device(zmq.FORWARDER, frontend, backend)
		print("Zero MQ forwarding enabled")
	except Exception, e:
		print e
		print "Bringing down zmq device"
	finally:
		pass
		frontend.close()
		backend.close()
		context.term()

if __name__ == "__main__":
	main()