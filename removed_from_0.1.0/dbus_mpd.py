#!/usr/bin/python

# DBus service for handling MPD events

import dbus, dbus.service, dbus.exceptions
import sys

from dbus.mainloop.glib import DBusGMainLoop
import gobject

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
	# load mpde.py
    from mpde import mpdControl
    mpdControl(bus_name)
    loop.run()
except KeyboardInterrupt:
    print("keyboard interrupt received")
except Exception as e:
    print("Unexpected exception occurred: '{}'".format(str(e)))
finally:
    print("quitting...")
    loop.quit()
