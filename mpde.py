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

			print(' ...  EVENT: {0}'.format(e))
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
				
				for m in messages:
					print m
					#print('Channel: {0}'.format(m["channel"]))
					#print('Message: {0}'.format(m["message"]))
				print(messages["channel"])
				
			elif e == "player" or 'mixer':
				#oMpdClient.command_list_ok_begin()
				#oMpdClient.status()
				#results = oMpdClient.command_list_end()		
				#
				#for r in results:
				#	print(r)
				self.mpd_control('save')
				
			#elif e == "subscription":
			#	oMpdClient.command_list_ok_begin()
			#	oMpdClient.channels()
			#	results = oMpdClient.command_list_end()		
			#
			#	for r in results:
			#		print(r)		

			else:
				print(' ...  unmanaged event')
	
	#oMpdClient will create a list variable with the change events
	#@dbus.service.signal("com.arctura.mpd", signature='as')
	#def mpd_control(self, event):
	#	print(event)
		
	@dbus.service.signal("com.arctura.mpd", signature='s')
	def mpd_control(self, ding):
		print
	