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
sys.path.append('../modules')
from hu_utils import *

#********************************************************************************
# GLOBAL vars & CONSTANTS
#

# mpd
oMpdClient = None
	
# zmq
subscriber = None
publisher = None

# ********************************************************************************
# Zero MQ functions
#
def zmq_connect():

	global publisher
	
	printer("Connecting to ZeroMQ forwarder")

	zmq_ctx = zmq.Context()
	port_client = "5559"
	publisher = zmq_ctx.socket(zmq.PUB)
	publisher.connect("tcp://localhost:{0}".format(port_client))

def mpd_handle_change(events):

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
			zmq_send('/event/mpd/player','SET')
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
			zmq_send('/event/mpd/update','SET')
		elif e == "options":
			print "OPTIONS! RANDOM??"
		else:
			print(' ...  unmanaged event')
	
def setup():

	# ZMQ
	zmq_connect()
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
	setup()
	main()