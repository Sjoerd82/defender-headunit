#!/usr/bin/python

#
# MPD event listener
# Venema, S.R.G.
# 2018-03-11
#
# MPD event listener forwards events on the MPD daemon to ZeroMQ
#
# https://www.musicpd.org/doc/protocol/command_reference.html#status_commands
#

# DBus service for handling MPD events

import sys
import os
import time

# ZeroMQ
import zmq

# MPD
from select import select
from mpd import MPDClient

# Utils
#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "MPD Listener"
LOG_TAG = 'MPDLST'
LOGGER_NAME = 'mpdlst'

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559

logger = None
args = None
messaging = None
oMpdClient = None


# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# ********************************************************************************
# Load configuration
#
def load_zeromq_configuration():
	
	configuration = configuration_load(LOGGER_NAME,args.config)
	
	if not configuration or not 'zeromq' in configuration:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		configuration = { "zeromq": { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB } }
		return configuration
		
	else:
		# Get portnumbers from either the config, or default value
		if not 'port_publisher' in configuration['zeromq']:
			configuration['zeromq']['port_publisher'] = DEFAULT_PORT_PUB
			
		if not 'port_subscriber' in configuration['zeromq']:
			configuration['zeromq']['port_subscriber'] = DEFAULT_PORT_SUB
			
	return configuration
	
def mpd_handle_change(events):

	print "DEBUG: 3"
	print events

	# loop over the available event(s)
	for e in events:

		#print(' ...  EVENT: {0}'.format(e))
		if e == "message":	
			#oMpdClient.subscribe("media_ready")
			#oMpdClient.command_list_ok_begin()
			#oMpdClient.readmessages()
			#messages = oMpdClient.command_list_end()
			#for m in messages:
			#	print(' ...  MESSAGE: {0}'.format(m))
			
			oMpdClient.command_list_ok_begin()
			oMpdClient.readmessages()
			messages = oMpdClient.command_list_end()
			#print messages
			
			# messages = list of dicts
			for msg in messages:
				for m in msg:
					print('Channel: {0}'.format(m['channel']))
					print('Message: {0}'.format(m['message']))
					if m['channel'] == 'media_removed':
						mpd_control('media_removed')
					elif m['channel'] == 'media_ready':
						mpd_control('media_ready')
					elif m['channel'] == 'ifup':
						mpd_control('ifup')
					elif m['channel'] == 'ifdown':
						mpd_control('ifdown')
					else:
						print('ERROR: Channel not supported')
			
		elif e == "player":
			#
			# This works, but instead, it's more effective to handle this at the headunit.py side
			#
			#oMpdClient.command_list_ok_begin()
			#oMpdClient.status()
			#results = oMpdClient.command_list_end()		
			#				
			#for r in results:
			#	print(r)
			#
			# Output:
			# {'songid': '180', 'playlistlength': '36', 'playlist': '18', 'repeat': '1', 'consume': '0', 'mixrampdb': '0.000000', 'random': '0', 'state': 'play', 'elapsed': '0.000', 'volume': '100', 'single': '0', 'nextsong': '31', 'time': '0:193', 'duration': '193.328', 'song': '30', 'audio': '44100:24:2', 'bitrate': '0', 'nextsongid': '181'}
			
			#mpd_control('player')
			#zmq_send('/event/mpd/player','SET')
			state={}
			state['state'] = "Bla1"
			state['random'] = "off"
			state['repeat'] = "off"
			messaging.publish_command('/events/player','INFO', state)
			messaging.publish_command('/events/player','INF0', state)
			# do not add code after here... (will not be executed)
		
		#elif e == "subscription":
		#	oMpdClient.command_list_ok_begin()
		#	oMpdClient.channels()
		#	results = oMpdClient.command_list_end()		
		#
		#	for r in results:
		#		print(r)		
		elif e == "database":
			#mpd_control('database')
			#zmq_send('/event/mpd/update','SET')
			#messaging.publish_event('/events/update', 'INFO', None)
			messaging.publish_command('/events/update','INFO', None)
		elif e == "options":
			print "OPTIONS! RANDOM??"
		else:
			print(' ...  unmanaged event')
	

#********************************************************************************
# Parse command line arguments
#
def parse_args():

	import argparse
	global args

	parser = argparse.ArgumentParser(description=DESCRIPTION)
	parser.add_argument('--loglevel', action='store', default=DEFAULT_LOG_LEVEL, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('--config','-c', action='store', help='Configuration file', default=DEFAULT_CONFIG_FILE)
	parser.add_argument('-b', action='store_true', default=False)
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
	args = parser.parse_args()


def setup():

	global messaging

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
			configuration['zeromq']['port_publisher'] = args.port_publisher
		if args.port_subscriber:
			configuration['zeromq']['port_subscriber'] = args.port_subscriber
			
	#
	# ZMQ
	#
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()

	printer('Initialized [OK]')

def main():

	global oMpdClient

	print('[MPD] Initializing MPD client')
	oMpdClient = MPDClient() 

	oMpdClient.timeout = None              # network timeout in seconds (floats allowed), default: None
	oMpdClient.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
	oMpdClient.connect("localhost", 6600)  # connect to localhost:6600
	print(oMpdClient.mpd_version)          # print the MPD version

	#Now handled via udisks dbus:
	#print('[MPD-DBUS] Subscribing to channel: media_ready')
	#oMpdClient.subscribe("media_ready")

	#Now handled via udisks dbus:
	#print('[MPD-DBUS] Subscribing to channel: media_removed')
	#oMpdClient.subscribe("media_removed")

	#Workaround for not having NetworkManager:
	# post-up script defined in /etc/network/interface
	print('[MPD] Subscribing to channel: ifup')
	oMpdClient.subscribe("ifup")

	#Workaround for not having NetworkManager:
	# post-down script defined in /etc/network/interface
	print('[MPD] Subscribing to channel: ifdown')
	oMpdClient.subscribe("ifdown")
	
	print('[MPD] send_idle()')
	oMpdClient.send_idle()
		
	while True:			
		canRead = select([oMpdClient], [], [], 0)[0]
		if canRead:
			print "DEBUG: 2"
		
			# fetch change(s)
			changes = oMpdClient.fetch_idle()
			
			# handle/parse the change(s)
			mpd_handle_change(changes)
			
			# don't pass on the changes (datatype seems too complicated for dbus)
			#mpd_control(changes)
			
			# continue idling
			oMpdClient.send_idle()
		
		# required?????
		time.sleep(0.1)


if __name__ == "__main__":
	parse_args()
	setup()
	main()
	
