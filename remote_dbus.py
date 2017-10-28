#!/usr/bin/python

# Remote control DBus service
# Based on https://github.com/larryprice/python-dbus-blog-series/blob/part3/service

import dbus, dbus.service, dbus.exceptions
import sys

class RemoteControl(dbus.service.Object):
	def __init__(self):
		#self.session_bus = dbus.SessionBus()
		#name = dbus.service.BusName("com.example.SampleService", bus=self.session_bus)
		#dbus.service.Object.__init__(self, name, '/SomeObject')
		# Declare a name where our service can be reached
		try:
			bus_name = dbus.service.BusName("com.arctura.remote",
											bus=dbus.SystemBus(),
											do_not_queue=True)
		except dbus.exceptions.NameExistsException:
			print("service is already running")
			sys.exit(1)
    @dbus.service.method("com.example.SampleInterface", in_signature='s', out_signature='as')
    def HelloWorld(self, hello_message):
        return ["Hello", "from example-service.py", "with unique name", self.session_bus.get_unique_name()]
    @dbus.service.method("com.example.SampleInterface", in_signature='', out_signature='')
    def Exit(self):
        mainloop.quit()
		
if __name__ == '__main__':
	# using gobject
	#from dbus.mainloop.glib import DBusGMainLoop
	import dbus.mainloop.glib
	import gobject
	
	# Initialize a main loop
	DBusGMainLoop(set_as_default=True)
	loop = gobject.MainLoop()
	
	object = RemoteControl()
	#loop.run()

	# Run the loop
	try:
		# Create our initial objects
		#from dbustest.random_data import RandomData
		#RandomData(bus_name)
		#from random_data import RemoteControl
		#RemoteControl(bus_name)
		
		loop.run()
	except KeyboardInterrupt:
		print("keyboard interrupt received")
	except Exception as e:
		print("Unexpected exception occurred: '{}'".format(str(e)))
	finally:
		#loop.quit()

	