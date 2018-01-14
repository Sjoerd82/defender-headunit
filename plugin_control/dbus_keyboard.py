#!/usr/bin/python

# Remote control DBus service
# Based on https://github.com/larryprice/python-dbus-blog-series/blob/part3/service

import dbus, dbus.service, dbus.exceptions
import sys

from dbus.mainloop.glib import DBusGMainLoop
import gobject

from hu_utils import *

controlName='keybrd'

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=controlName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


printer('Starting Keyboard Remote Control')

