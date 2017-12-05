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
				self.oMpdClient.send_idle() # continue idling
				self.mpd_handle_change(changes)
			
			time.sleep(0.1)

	def mpd_handle_change(self, changes):
		print('[MPD] Change event received:')
		print(changes)
		for k in changes:
			print(k)
		
		#for k, v in changes.items():
		#	print(k,v)
	
		mpd_control('test!')
	
	#handling variably nested dicts is hard/impossible?
	@dbus.service.signal("com.arctura.mpd", signature='s')
	def mpd_control(self, event):
		print(event)

			