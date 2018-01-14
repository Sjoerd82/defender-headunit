#!/usr/bin/python

# Remote control DBus service
# Based on https://github.com/larryprice/python-dbus-blog-series/blob/part3/service

import dbus, dbus.service, dbus.exceptions
import sys

from dbus.mainloop.glib import DBusGMainLoop
import gobject

from hu_utils import *

#keypress (unix only)
import tty, termios

controlName='keybrd'

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=controlName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

def getch():
	"""getch() -> key character

	Read a single keypress from stdin and return the resulting character. 
	Nothing is echoed to the console. This call will block if a keypress 
	is not already available, but will not wait for Enter to be pressed. 

	If the pressed key was a modifier key, nothing will be detected; if
	it were a special function key, it may return the first character of
	of an escape sequence, leaving additional characters in the buffer.
	"""
	fd = sys.stdin.fileno()
	old_settings = termios.tcgetattr(fd)
	try:
		tty.setraw(fd)
		ch = sys.stdin.read(1)
	finally:
		termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
	return ch
		
class rc_Keyboard(dbus.service.Object):

	def __init__(self, bus_name):
		super(rc_Keyboard,self).__init__(bus_name, "/com/arctura/keyboard")

		while True:
			keypress = getch()	#blocking function
			print keypress
			#time.sleep(0.1)

	@dbus.service.signal("com.arctura.keyboard", signature='s')
	def button_press(self, button):
		print("Button was pressed: {0}".format(button))

		
printer('Starting Remote Control: Keyboard')

