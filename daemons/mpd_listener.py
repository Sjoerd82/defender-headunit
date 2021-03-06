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

import errno								# so why exactly?
from socket import error as socket_error	#

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
BANNER = "MPD events listener"
LOG_TAG = 'MPDLST'
LOGGER_NAME = 'mpdlst'

DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559

# global variables
logger = None
args = None
messaging = MqPubSubFwdController()
oMpdClient = None

# configuration
cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ

MAX_RESILIENCE_WAIT = 20	# max wait 20sec. before retrying connection
connected_mpd = False

# todo get 'official' dict
state = { "state":None, "id":None, "random":None, "repeat":None, "time":None, "filename":None }
track = dict_track()

#mpd_player_state = { "state":None, "songid":None, "random":None, "repeat":None }
#mpd_player_track = { "state":None, "songid":None, "random":None, "repeat":None }

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})


# ********************************************************************************
# Load configuration
#
def load_cfg_main():
	""" load main configuration """
	config = configuration_load(LOGGER_NAME,args.config)
	return config

def load_cfg_zmq():
	""" load zeromq configuration """	
	if not 'zeromq' in cfg_main:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		#cfg_main["zeromq"] = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB } }
		config = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB }
		return config
	else:
		config = {}
		# Get portnumbers from either the config, or default value
		if 'port_publisher' in cfg_main['zeromq']:
			config['port_publisher'] = cfg_main['zeromq']['port_publisher']
		else:
			config['port_publisher'] = DEFAULT_PORT_PUB
		
		if 'port_subscriber' in cfg_main['zeromq']:
			config['port_subscriber'] = cfg_main['zeromq']['port_subscriber']		
		else:
			config['port_subscriber'] = DEFAULT_PORT_SUB
			
		return config

def load_cfg_daemon():
	""" load daemon configuration """
	if 'daemons' not in cfg_main:
		return
	else:
		for daemon in cfg_main['daemons']:
			if 'script' in daemon and daemon['script'] == os.path.basename(__file__):
				return daemon
	
# ********************************************************************************
# Load configuration
#
"""
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
"""

def mpd_connect():
	""" Blocking """

	global oMpdClient
	global connected_mpd

	connect_retry = 0
	oMpdClient.timeout = None              # network timeout in seconds (floats allowed), default: None
	oMpdClient.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
	
	while not connected_mpd:
	
		resillience_time = 5 * connect_retry
		if resillience_time > MAX_RESILIENCE_WAIT:
			resillience_time = MAX_RESILIENCE_WAIT

		if connect_retry == 0:
			printer("Connecting to MPD at {0}:{1}".format("localhost","6600"),level=LL_INFO)
		else:
			printer("Not connected [{0}]... Retrying in {1} sec.".format(connect_retry,resillience_time),level=LL_INFO)
			time.sleep(resillience_time)
		try:
			oMpdClient.connect("localhost", 6600)  # connect to localhost:6600
			connected_mpd = True
			connect_retry = 0
		except socket_error as serr:
			printer("Could not connect to server.",level=LL_ERROR)
			connected_mpd = False
			connect_retry += 1
			
	if connected_mpd:
		print(oMpdClient.mpd_version)          # print the MPD version
	
		#Now handled via udisks dbus:
		#print('[MPD-DBUS] Subscribing to channel: media_ready')
		#oMpdClient.subscribe("media_ready")

		#Now handled via udisks dbus:
		#print('[MPD-DBUS] Subscribing to channel: media_removed')
		#oMpdClient.subscribe("media_removed")

		#Workaround for not having NetworkManager:
		# post-up script defined in /etc/network/interface
		printer('Subscribing to channel: ifup')
		oMpdClient.subscribe("ifup")

		#Workaround for not having NetworkManager:
		# post-down script defined in /etc/network/interface
		printer('Subscribing to channel: ifdown')
		oMpdClient.subscribe("ifdown")
		
		printer('send_idle()')
		oMpdClient.send_idle()
		
def mpd_handle_change(events):

	global state

	# loop over the available event(s)
	for e in events:

		#print(' ...  EVENT: {0}'.format(e))
		if e == "message":	
			printer("Event: Message")
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
			printer("Event: Player")
			#
			# This works, but instead, it's more effective to handle this at the headunit.py side
			#
			oMpdClient.command_list_ok_begin()
			oMpdClient.status()
			results = oMpdClient.command_list_end()
			
			#print results
			# Output:
			# {'songid': '180', 'playlistlength': '36', 'playlist': '18', 'repeat': '1', 'consume': '0', 'mixrampdb': '0.000000', 'random': '0', 'state': 'play', 'elapsed': '0.000', 'volume': '100',
			# 'single': '0', 'nextsong': '31', 'time': '0:193', 'duration': '193.328', 'song': '30', 'audio': '44100:24:2', 'bitrate': '0', 'nextsongid': '181'}
					
			if state['state'] != results[0]['state']:
				printer(" > State changed from {0} to {1}".format(state['state'],results[0]['state']))
				state['state'] = results[0]['state']
				ret = messaging.publish('/events/state','INFO', state)
				if ret == True:
					printer(" > Sending MQ notification [OK]")
				else:
					printer(" > Sending MQ notification [FAIL] {0}".format(ret))
			
			if 'songid' in results[0] and state['id'] != results[0]['songid']:
				printer(" > SongId changed")
				state['id'] = results[0]['songid']

				oMpdClient.command_list_ok_begin()
				oMpdClient.currentsong()
				results1 = oMpdClient.command_list_end()
				
				if 'file' in results1[0]: track['file'] = results1[0]['file']
				if 'artist' in results1[0]: track['artist'] = results1[0]['artist']
				if 'composer' in results1[0]: track['composer'] = results1[0]['composer']
				if 'performer' in results1[0]: track['performer'] = results1[0]['performer']
				if 'album' in results1[0]: track['album'] = results1[0]['album']
				if 'albumartist' in results1[0]: track['albumartist'] = results1[0]['albumartist']
				if 'title' in results1[0]: track['title'] = results1[0]['title']
				if 'length' in results1[0]: track['length'] = results1[0]['length']
				if 'elapsed' in results1[0]: track['elapsed'] = results1[0]['elapsed']
				if 'track' in results1[0]: track['track'] = results1[0]['track']
				if 'disc' in results1[0]: track['disc'] = results1[0]['disc']
				if 'folder' in results1[0]: track['folder'] = results1[0]['folder']
				if 'genre' in results1[0]: track['genre'] = results1[0]['genre']
				if 'date' in results1[0]: track['date'] = results1[0]['date']
				ret = messaging.publish('/events/track','INFO', track)
				if ret == True:
					printer(" > Sending MQ notification [OK]")
				else:
					printer(" > Sending MQ notification [FAIL] {0}".format(ret))
					
		#elif e == "subscription":
		#	oMpdClient.command_list_ok_begin()
		#	oMpdClient.channels()
		#	results = oMpdClient.command_list_end()		
		#
		#	for r in results:
		#		print(r)		
		elif e == "database":
			printer("Event: Database")
			#mpd_control('database')
			#zmq_send('/event/mpd/update','SET')
			#messaging.publish_event('/events/update', 'INFO', None)
			messaging.publish('/events/update','INFO', None)
		elif e == "options":
			print "OPTIONS! RANDOM??"
		else:
			printer('Unmanaged event: {0}'.format(e))
	

#********************************************************************************
# Parse command line arguments
#
def parse_args():

	global args
	import argparse
	parser = default_parser(DESCRIPTION,BANNER)
	# additional command line arguments mat be added here
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
	# Configuration
	#
	global cfg_main
	global cfg_zmq
	global cfg_daemon

	# main
	cfg_main = load_cfg_main()
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	# zeromq
	if not args.port_publisher and not args.port_subscriber:
		cfg_zmq = load_cfg_zmq()
	else:
		if args.port_publisher and args.port_subscriber:
			pass
		else:
			load_cfg_zmq()
	
		# Pub/Sub port override
		if args.port_publisher:
			configuration['zeromq']['port_publisher'] = args.port_publisher
		if args.port_subscriber:
			configuration['zeromq']['port_subscriber'] = args.port_subscriber

	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
			
	# daemon
	cfg_daemon = load_cfg_daemon()
	if cfg_daemon is None:
		printer("Daemon configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
			
	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")	
	messaging.set_address('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()

	#
	# MPD
	#
	global oMpdClient
	printer('MPD: Initializing')
	oMpdClient = MPDClient() 
	mpd_connect()
	

	printer('Initialized [OK]')
	
def main():

	global oMpdClient
	global connected_mpd
		
	while True:
		if connected_mpd:
			canRead = select([oMpdClient], [], [], 0)[0]
			if canRead:
			
				# fetch change(s)
				try:
					changes = oMpdClient.fetch_idle()
					# handle/parse the change(s)
					mpd_handle_change(changes)
					
					# don't pass on the changes (datatype seems too complicated for dbus)
					#mpd_control(changes)
					
					# continue idling
					oMpdClient.send_idle()
				except:
					connected_mpd = False
					
		else:
			mpd_connect()
		
		# required?????
		time.sleep(0.1)


if __name__ == "__main__":
	parse_args()
	setup()
	main()
	
