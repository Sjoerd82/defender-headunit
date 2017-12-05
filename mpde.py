# Loaded by: dbus_mpd.py

import dbus.service
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

		print('[---] Initializing MPD client')
		self.oMpdClient = MPDClient() 

		self.oMpdClient.timeout = 10                # network timeout in seconds (floats allowed), default: None
		self.oMpdClient.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
		self.oMpdClient.connect("localhost", 6600)  # connect to localhost:6600
		print(self.oMpdClient.mpd_version)          # print the MPD version
	
		print('[---] Subscribing to channel: media_ready')
		self.oMpdClient.subscribe("media_ready")

		print('[---] Subscribing to channel: media_removed')
		self.oMpdClient.subscribe("media_removed")
	
		print('[---] send_idle()')
		self.oMpdClient.send_idle()
		
		while True:			
			canRead = select([self.oMpdClient], [], [], 0)[0]
			if canRead:
				changes = self.oMpdClient.fetch_idle()
				#self.mpd_handle_change(changes)
				self.mpd_control(changes)
				
				self.oMpdClient.command_list_ok_begin()
				self.oMpdClient.readmessages()
				messages = self.oMpdClient.command_list_end()
				print messages

				self.oMpdClient.send_idle() # continue idling
			
			time.sleep(0.1)

	#oMpdClient will create a list variable with the change events
	@dbus.service.signal("com.arctura.mpd", signature='as')
	def mpd_control(self, event):
		print(event)
	