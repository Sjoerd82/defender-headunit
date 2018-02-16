#!/usr/bin/python

# ********************************************************************************
#
# Dbus monitor
#
#

from hu_utils import *

dbus_addr = "com.arctura.volume"
#outputName='d1606a'
#outputName_long = 'LCD 1606a'

# ********************************************************************************
# Output wrapper
#

# TODO!!! the "headunit"-logger is no longer accessible once this script is started "on its own"..
def myprint( message, level, tag ):
	print("[{0}] {1}".format(tag,message))

def printer( message, level=20, continuation=False, tag="d1606a" ):
	#TODO: test if headunit logger exist...
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


printer('Starting Volume')

		
# ********************************************************************************
#
# Dbus libraries
#
# #TODO, check if these are actually all required..
#
import dbus, dbus.service, dbus.exceptions
import sys

from dbus.mainloop.glib import DBusGMainLoop
import gobject

import os

# ********************************************************************************

import subprocess
from subprocess import call
from subprocess import Popen, PIPE


# ********************************************************************************
#
#
#
		


class dbusService( dbus.service.Object ):

	def __init__( self, bus_name ):
		#ehm?
		super(dbusService,self).__init__(bus_name, "/com/arctura/volume")

		
class pa_volume_handler():

	VOL_INCR = "5%"

	def __init__(self, sink):
		self.pa_sink = sink

	def vol_set_pct(self, volume):
		#vol_pct = str(volume) + "%"
		vol_pct = volume
		call(["pactl", "set-sink-volume", self.pa_sink, vol_pct])
		
	def vol_up(self):
		vol_chg = "+" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.pa_sink, vol_chg])
		
	def vol_down(self):
		vol_chg = "-" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.pa_sink, vol_chg])

	def vol_get(self):
		#pipe = Popen("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'")
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		vol = subprocess.check_output("/root/pa_volume.sh")
		return int(vol.splitlines()[0])

		
# callback, keep it short! (blocks new input)
def cb_volume( volume ):

	printer('DBUS event received: {0}'.format(data), tag='volume')
	pavh.vol_set_pct(volume)
		
	return True
			

# ********************************************************************************
#
# Main loop
#

#
# Initialize the mainloop
#
DBusGMainLoop(set_as_default=True)

#
# main loop
#
mainloop = gobject.MainLoop()

#
# DBus: system bus
# On a root only embedded system there may not be a usable session bus
#
bus = dbus.SystemBus()


pavh = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')

# Declare a name where our service can be reached
#try:
#	bus_name = dbus.service.BusName(dbus_addr,
#                                    bus=dbus.SystemBus(),
#                                    do_not_queue=True)
#	printer('DBus OK: {0}'.format(dbus_addr))
#except dbus.exceptions.NameExistsException:
#	printer("DBus: Service is already running")
#	sys.exit(1)

#
# Connect Callback functions to DBus Signals
#
bus.add_signal_receiver(cb_volume, dbus_interface = "com.arctura.volume")
	
# Run the loop
try:
    #dbusService(bus_name)
    mainloop.run()
except KeyboardInterrupt:
    printer("keyboard interrupt received")
except Exception as e:
    printer("Unexpected exception occurred: '{}'".format(str(e)))
finally:
    printer("quitting...")
    mainloop.quit()

