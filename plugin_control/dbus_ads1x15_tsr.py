#!/usr/bin/python

# Remote control DBus service
# Based on https://github.com/larryprice/python-dbus-blog-series/blob/part3/service

import dbus, dbus.service, dbus.exceptions
import sys

from dbus.mainloop.glib import DBusGMainLoop
import gobject

from hu_utils import *

controlName='ad1x15'

#############################
# Loaded by: remote_dbus.py
# Button presses are NOT asynchronous!! i.e. wait until a button press is handled before the next button can be handled.
# TODO: Consider making them asynchronous, or at least the update lib (long) / volume (short) buttons

import random
import time

import threading

# Import the ADS1x15 module.
import Adafruit_ADS1x15

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=controlName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


printer('Starting Remote Control: Resistor Network')

"""
try:
    bus_name = dbus.service.BusName("com.arctura.remote",
                                    bus=dbus.SystemBus(),
                                    do_not_queue=True)
except dbus.exceptions.NameExistsException:
    printer("service is already running")
    sys.exit(1)
	
RemoteControl(bus_name)
"""


# Initialize a main loop
DBusGMainLoop(set_as_default=True)
loop = gobject.MainLoop()

# Declare a name where our service can be reached
try:
    bus_name = dbus.service.BusName("com.arctura.remote",
                                    bus=dbus.SystemBus(),
                                    do_not_queue=True)
except dbus.exceptions.NameExistsException:
    printer("service is already running")
    sys.exit(1)

# Run the loop
try:
    # Create our initial objects
	# load remote.py
    #from remote import RemoteControl
    RemoteControl(bus_name)
    loop.run()
except KeyboardInterrupt:
    printer("keyboard interrupt received")
except Exception as e:
    printer("Unexpected exception occurred: '{}'".format(str(e)))
finally:
    printer("quitting...")
    loop.quit()
