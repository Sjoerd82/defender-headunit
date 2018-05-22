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
# USAGE
# MQ Subscribers should connect to the forwarders Publishers port,
# publishers should connect to the forwarders Subscribers port.
#
# ARGUMENTS
# -l, --loglevel     log level
# -c, --config       configuration file
# -b                 background/daemon mode: all output goes to the syslog instead of console
# --port_publisher   publisher port number
# --port_subscriber  subscriber port number 


import zmq						# ZeroMQ
import sys						# path
from logging import getLogger	# logger

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "ZeroMQ forwarder device"
BANNER = "ZeroMQ forwarder device"
LOG_TAG = 'ZMQFWD'
LOGGER_NAME = 'zmqfwd'

DEFAULT_PORT_SUB = 5560		# FWD: used by Pub
DEFAULT_PORT_PUB = 5559		# FWD: used by Sub

# global variables
logger = None
args = None
configuration = None


# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# ********************************************************************************
# Load configuration
#
def load_zeromq_configuration():
	# This is a Forwarder, thus the Pub/Sub ports must be reversed!!
	# ... this could be done with less code ;-)	
	
	configuration = configuration_load(LOGGER_NAME,args.config)
	
	if not configuration or not 'zeromq' in configuration:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		configuration = { "zeromq": { "port_publisher": DEFAULT_PORT_SUB, "port_subscriber":DEFAULT_PORT_PUB } }
		return configuration
		
	else:
		# Get portnumbers from either the config, or default value
		if 'port_publisher' in configuration['zeromq']:
			config_pub = configuration['zeromq']['port_publisher']
		else:
			printer('port_publisher not in configuration, using default')
			config_pub = DEFAULT_PORT_PUB
			
		if 'port_subscriber' in configuration['zeromq']:
			config_sub = configuration['zeromq']['port_subscriber']
		else:
			printer('port_subscriber not in configuration, using default')
			config_sub = DEFAULT_PORT_SUB
		
		# Reverse ports
		configuration['zeromq']['port_publisher'] =  config_sub
		configuration['zeromq']['port_subscriber'] = config_pub
	
	return configuration

#********************************************************************************
# Parse command line arguments and environment variables
#
def parse_args():

	global args
	import argparse
	parser = default_parser(DESCRIPTION,BANNER)
	# additional command line arguments mat be added here
	args = parser.parse_args()
		
def setup():

	#
	# Logging
	# -> Output will be logged to the syslog, if -b specified, otherwise output will be printed to console
	#
	global logger
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)

	if args.b:
		logger = log_create_syslog_loghandler(logger, args.loglevel, LOG_TAG, address='/dev/log') 	# output to syslog
	else:
		logger = log_create_console_loghandler(logger, args.loglevel, LOG_TAG) 						# output to console

	debug_file = '/root/DEBUG_MODE'
	if os.path.exists(debug_file):
		printer('DEBUG MODE!!!!')

	#
	# Load configuration
	#
	global configuration
	if not args.port_publisher and not args.port_subscriber:
		configuration = load_zeromq_configuration()
	else:
		if args.port_publisher and args.port_subscriber:
			pass
		else:
			configuration = load_zeromq_configuration()
	
		# Pub/Sub port override
		if args.port_publisher:
			configuration['zeromq']['port_subscriber'] = args.port_publisher
		if args.port_subscriber:
			configuration['zeromq']['port_publisher'] = args.port_subscriber

def main():	
	
	port_subscriber = configuration['zeromq']['port_subscriber']
	port_publisher = configuration['zeromq']['port_publisher']
	backend = None

	try:
		context = zmq.Context(1)
		# Socket facing clients
		frontend = context.socket(zmq.SUB)
		frontend.bind("tcp://*:{0}".format(port_subscriber))

		# Don't filter!
		frontend.setsockopt(zmq.SUBSCRIBE, "")

		# Socket facing services
		backend = context.socket(zmq.PUB)
		backend.bind("tcp://*:{0}".format(port_publisher))

		printer("Zero MQ forwarding ready")
		printer('Connect Publishers to port: {0}'.format(port_subscriber))
		printer('Connect Subscribers to port: {0}'.format(port_publisher))
		zmq.device(zmq.FORWARDER, frontend, backend)

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
	
