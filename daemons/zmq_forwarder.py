#!/usr/bin/python

#
# ZeroMQ forwarder device
# Venema, S.R.G.
# 2018-03-17
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

import zmq				# ZeroMQ
import sys				# path
import datetime			# logging
import os				#
#import logging			#
#import logging.config	#
from logging import getLogger


#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
#from hu_logger import ColoredFormatter
#from hu_logger import RemAnsiFormatter
from hu_msg import MessageController

# Global variables and constants
DEFAULT_PORT_CLIENT = 5559
DEFAULT_PORT_SERVER = 5560
CONFIG_FILE = '/etc/configuration.json'
configuration = None
DAEMONIZED = None

# for logging to syslog
#SYSLOG_UDP_PORT=514
LOG_LEVEL = LL_INFO

#logging
LOG_TAG = 'ZMQFWD'
LOGGER_NAME = 'zmqfwd'
logger = None


# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# ********************************************************************************
# Load configuration
#
def load_configuration():

	# utils # todo, present with logger
	configuration = configuration_load(LOGGER_NAME,CONFIG_FILE)
	
	if not configuration or not 'zeromq' in configuration:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Client port: {0}'.format(DEFAULT_PORT_CLIENT))
		printer('Server port: {0}'.format(DEFAULT_PORT_SERVER))
		configuration = { "zeromq": { "port_client": DEFAULT_PORT_CLIENT, "port_server":DEFAULT_PORT_SERVER } }
	
	return configuration

#********************************************************************************
# Parse command line arguments and environment variables
#
def parse_args():

	import argparse
	
	global LOG_LEVEL
	global DAEMONIZED

	parser = argparse.ArgumentParser(description='ZeroMQ forwarder device')
	parser.add_argument('--loglevel', action='store', default=LL_INFO, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('-b', action='store_true')	# background, ie. no output to console
	args = parser.parse_args()

	LOG_LEVEL = args.loglevel
	DAEMONIZED = args.b
		
def setup():

	#
	# Logging
	#
	global logger
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)

	# Start logging to console or syslog
	if DAEMONIZED:
		#init_logging_s( address='/dev/log' )	# output to syslog
		logger = log_create_syslog_loghandler(logger, LOG_LEVEL, LOG_TAG, address='/dev/log' )
		
	else:
		#init_logging_c()						# output to console
		logger = log_create_console_loghandler(logger, LOG_LEVEL, LOG_TAG)

def main():

	#
	# Load configuration
	#
	configuration = load_configuration()	
	port_client = configuration['zeromq']['port_client']
	port_server = configuration['zeromq']['port_server']
	backend = None

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
		printer("Zero MQ forwarding enabled")
	except Exception, e:
		printer(e)
		printer("Bringing down zmq device")
	finally:
		pass
		frontend.close()
		backend.close()
		context.term()

if __name__ == "__main__":
	parse_args()
	setup()
	main()
	
