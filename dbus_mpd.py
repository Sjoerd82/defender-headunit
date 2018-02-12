#!/usr/bin/python

# DBus service for handling MPD events

import dbus, dbus.service, dbus.exceptions
import sys

from dbus.mainloop.glib import DBusGMainLoop
import gobject

import random
import time

import threading

from select import select

# python-mpd2 0.5.1 (not sure if this is the forked mpd2)
# used mainly for getting the current song for lookup on reload
from mpd import MPDClient

class mpdControl(dbus.service.Object):

	oMpdClient = None

	def __init__(self, bus_name):
		super(mpdControl,self).__init__(bus_name, "/com/arctura/mpd")

		print('[MPD-DBUS] Initializing MPD client')
		self.oMpdClient = MPDClient() 

		self.oMpdClient.timeout = 10                # network timeout in seconds (floats allowed), default: None
		self.oMpdClient.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
		self.oMpdClient.connect("localhost", 6600)  # connect to localhost:6600
		print(self.oMpdClient.mpd_version)          # print the MPD version
	
		#Now handled via udisks dbus:
		#print('[MPD-DBUS] Subscribing to channel: media_ready')
		#self.oMpdClient.subscribe("media_ready")

		#Now handled via udisks dbus:
		#print('[MPD-DBUS] Subscribing to channel: media_removed')
		#self.oMpdClient.subscribe("media_removed")

		#Workaround for not having NetworkManager:
		# post-up script defined in /etc/network/interface
		print('[MPD-DBUS] Subscribing to channel: ifup')
		self.oMpdClient.subscribe("ifup")

		#Workaround for not having NetworkManager:
		# post-down script defined in /etc/network/interface
		print('[MPD-DBUS] Subscribing to channel: ifdown')
		self.oMpdClient.subscribe("ifdown")
		
		print('[MPD-DBUS] send_idle()')
		self.oMpdClient.send_idle()
		
		while True:			

			canRead = select([self.oMpdClient], [], [], 0)[0]
			if canRead:
			
				# fetch change(s)
				changes = self.oMpdClient.fetch_idle()
				
				# handle/parse the change(s)
				self.mpd_handle_change(changes)
				
				# don't pass on the changes (datatype seems too complicated for dbus)
				#self.mpd_control(changes)
				
				# continue idling
				self.oMpdClient.send_idle()
			
			# required?????
			time.sleep(0.1)

	def mpd_handle_change(self, events):
	
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
				
				self.oMpdClient.command_list_ok_begin()
				self.oMpdClient.readmessages()
				messages = self.oMpdClient.command_list_end()
				#print messages
				
				# messages = list of dicts
				for msg in messages:
					for m in msg:
						print('Channel: {0}'.format(m['channel']))
						print('Message: {0}'.format(m['message']))
						if m['channel'] == 'media_removed':
							self.mpd_control('media_removed')
						elif m['channel'] == 'media_ready':
							self.mpd_control('media_ready')
						elif m['channel'] == 'ifup':
							self.mpd_control('ifup')
						elif m['channel'] == 'ifdown':
							self.mpd_control('ifdown')
						else:
							print('ERROR: Channel not supported')
				
			elif e == "player":
				#
				# This works, but instead, it's more effective to handle this at the headunit.py side
				#
				#self.oMpdClient.command_list_ok_begin()
				#self.oMpdClient.status()
				#results = self.oMpdClient.command_list_end()		
				#				
				#for r in results:
				#	print(r)
				#
				# Output:
				# {'songid': '180', 'playlistlength': '36', 'playlist': '18', 'repeat': '1', 'consume': '0', 'mixrampdb': '0.000000', 'random': '0', 'state': 'play', 'elapsed': '0.000', 'volume': '100', 'single': '0', 'nextsong': '31', 'time': '0:193', 'duration': '193.328', 'song': '30', 'audio': '44100:24:2', 'bitrate': '0', 'nextsongid': '181'}
				
				self.mpd_control('player')
				# do not add code after here... (will not be executed)
			
			#elif e == "subscription":
			#	oMpdClient.command_list_ok_begin()
			#	oMpdClient.channels()
			#	results = oMpdClient.command_list_end()		
			#
			#	for r in results:
			#		print(r)		
			elif e == "database"
				self.mpd_control('database')
			else:
				print(' ...  unmanaged event')
	
	#oMpdClient will create a list variable with the change events
	#@dbus.service.signal("com.arctura.mpd", signature='as')
	#def mpd_control(self, event):
	#	print(event)
		
	@dbus.service.signal("com.arctura.mpd", signature='s')
	def mpd_control(self, ding):
		pass


# Initialize a main loop
DBusGMainLoop(set_as_default=True)
loop = gobject.MainLoop()

# Declare a name where our service can be reached
try:
    bus_name = dbus.service.BusName("com.arctura.mpd",
                                    bus=dbus.SystemBus(),
                                    do_not_queue=True)
except dbus.exceptions.NameExistsException:
    print("service is already running")
    sys.exit(1)

# Run the loop
try:
    # Create our initial objects
    mpdControl(bus_name)
    loop.run()
except KeyboardInterrupt:
    print("keyboard interrupt received")
except Exception as e:
    print("Unexpected exception occurred: '{}'".format(str(e)))
finally:
    print("quitting...")
    loop.quit()
