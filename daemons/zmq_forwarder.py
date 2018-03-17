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
#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *

DEFAULT_PORT_CLIENT = 5559
DEFAULT_PORT_SERVER = 5560

CONFIG_FILE = '/etc/configuration.json'


#logging
import logging
import logging.config
#from logging import Formatter
import datetime
import os
logger = None

from hu_logger import ColoredFormatter
from hu_logger import RemAnsiFormatter

# for logging to syslog
import socket
SYSLOG_UDP_PORT=514
LOGLEVEL_C = LL_INFO
DAEMONIZED = None

# Initiate logger.
def init_logging():

	global logger

	# logging is global
	logger = logging.getLogger('zmqfwd')
	logger.setLevel(logging.DEBUG)
	
def init_logging_c():

	global logger
	global LOGLEVEL_C

	# create console handler
	ch = logging.StreamHandler()
	ch.setLevel(LOGLEVEL_C)

	# create formatters
	fmtr_ch = ColoredFormatter("%(tag)s%(message)s")

	# add formatter to handlers
	ch.setFormatter(fmtr_ch)

	# add ch to logger
	logger.addHandler(ch)
	
	logger.info('Logging started: Console',extra={'tag':'log'})
	
# address may be a tuple consisting of (host, port) or a string such as '/dev/log'
def init_logging_s( address=('localhost', SYSLOG_UDP_PORT), facility="zmqfwd", socktype=socket.SOCK_DGRAM ):

	global logger
	
	# create syslog handler
	#sh = logging.handlers.SysLogHandler(address=address, facility=facility, socktype=socktype)
	sh = logging.handlers.SysLogHandler(address=address, socktype=socktype)
	sh.setLevel(logging.DEBUG)

	# create formatters
	fmtr_sh = RemAnsiFormatter("%(asctime)-9s [%(levelname)-8s] %(tag)s %(message)s")
		
	# add formatter to handlers
	sh.setFormatter(fmtr_sh)

	# add sh to logger
	logger.addHandler(sh)
	
	logger.info('Logging started',extra={'tag':'log'})

# Defines how to handle output
def myprint1( message, level=LL_INFO, tag=""):
	logger = logging.getLogger('zmqfwd')
	logger.log(level, message, extra={'tag': tag})
	
def printer( message, level=20, continuation=False, tag='SYSTEM' ):
	#TODO: test if headunit logger exist...
	print(message)
	if continuation:
		myprint1( message, level, '.'+tag )
	else:
		myprint1( message, level, tag )


def load_configuration():

	configuration = {}
	#configuration = configuration_load(CONFIG_FILE)
	
	if not 'zeromq' in configuration:
		printer('Error: ZeroMQ not in configuration, using defaults:')
		printer('Client port: {0}'.format(DEFAULT_PORT_CLIENT))
		printer('Server port: {0}'.format(DEFAULT_PORT_SERVER))
		configuration = { "zeromq": { "port_client": DEFAULT_PORT_CLIENT, "port_server":DEFAULT_PORT_SERVER } }
	
	return configuration

#********************************************************************************
#
# Parse command line arguments and environment variables
# Command line takes precedence over environment variables and settings.json
#
def parse_args():
	import argparse

	global LOGLEVEL_C
	global DAEMONIZED
	
	parser = argparse.ArgumentParser(description='ZeroMQ forwarder device')
	parser.add_argument('--loglevel', action='store', default=LL_INFO, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('-b', action='store_true')	# background, ie. no output to console
	args = parser.parse_args()

	LOGLEVEL_C = args.loglevel
	DAEMONIZED = args.b

	init_logging()	
	if DAEMONIZED:
		print('Daemonizing. All output will be written to the syslog.')
		init_logging_s( address='/dev/log' )	# output to syslog
	else:
		init_logging_c()						# output to console

def main():

	#
	# Load main configuration
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
	main()
	
