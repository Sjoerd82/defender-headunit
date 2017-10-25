#!/usr/bin/python

# Remote control DBus service
# Based on https://github.com/larryprice/python-dbus-blog-series/blob/part3/service

import dbus, dbus.service, dbus.exceptions
import sys

from dbus.mainloop.glib import DBusGMainLoop
#from gi.repository import GLib
import gobject

# Initialize a main loop
DBusGMainLoop(set_as_default=True)
loop = GLib.MainLoop()

# Declare a name where our service can be reached
try:
    bus_name = dbus.service.BusName("com.arctura.remote",
                                    bus=dbus.SystemBus(),
                                    do_not_queue=True)
except dbus.exceptions.NameExistsException:
    print("service is already running")
    sys.exit(1)

# Run the loop
try:
    # Create our initial objects
    #from dbustest.random_data import RandomData
    #RandomData(bus_name)
	from random_data import RemoteControl
    RemoteControl(bus_name)
	
    loop.run()
except KeyboardInterrupt:
    print("keyboard interrupt received")
except Exception as e:
    print("Unexpected exception occurred: '{}'".format(str(e)))
finally:
    #loop.quit()

	