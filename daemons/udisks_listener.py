#!/usr/bin/python

#
# Udisks D-Bus event listener
# Venema, S.R.G.
# 2018-03-11
#
# Udisks D-Bus event listener forwards events on regarding Udisks-glue to ZeroMQ
#


import sys
import os
import time

# ZeroMQ
import zmq

# dbus
import dbus.service
import dbus.exceptions

# main loop
import gobject
from dbus.mainloop.glib import DBusGMainLoop

# Utils
sys.path.append('../modules')
from hu_utils import *

#********************************************************************************
# GLOBAL vars & CONSTANTS
#
CONTROL_NAME='udisks'

# zmq
subscriber = None
publisher = None

# ********************************************************************************
# todo
#
# TODO!!! the "headunit"-logger is no longer accessible once this script is started "on its own"..
def myprint( message, level, tag ):
	print("[{0}] {1}".format(tag,message))

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=CONTROL_NAME ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


# ********************************************************************************
# Zero MQ functions
#
def zmq_connect():

	global publisher
	
	printer("Connecting to ZeroMQ forwarder")

	zmq_ctx = zmq.Context()
	port_client = "5559"
	publisher = zmq_ctx.socket(zmq.PUB)
	publisher.connect("tcp://localhost:{0}".format(port_client))

def zmq_send(path_send,message):

	global publisher

	#TODO
	#data = json.dumps(message)
	data = message
	printer("Sending message: {0} {1}".format(path_send, data))
	publisher.send("{0} {1}".format(path_send, data))
	
def cb_udisk_dev_add( device ):
	printer('Device added: {0}'.format(str(device)),tag='UDISKS')
	item = {}
	item['command'] = 'DEVADD'
	item['device'] = device
	queue('blocking',item,'button_devadd')

def cb_udisk_dev_rem( device ):
	printer('Device removed: {0}'.format(str(device)),tag='UDISKS')
	item = {}
	item['command'] = 'DEVREM'
	item['device'] = device
	queue('blocking',item,'button_devrem')

def udisk_add( device ):

	global Sources

	device_obj = bus.get_object("org.freedesktop.UDisks", device)
	device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)
	#
	#  beware.... anything after this may or may not be defined depending on the event and state of the drive. 
	#  Attempts to get a prop that is no longer set will generate a dbus.connection:Exception
	#

	# HANDY DEBUGGING TIP, DISPLAY ALL AVAILABLE PROPERTIES:
	# WILL *NOT* WORK FOR DEVICE REMOVAL
	#data = device_props.GetAll('')
	#for i in data: print i+': '+str(data[i])
	
	# Variables
	DeviceFile = ""
	mountpoint = ""
	mytag = "UDISKS"
	
	try:
		DeviceFile = device_props.Get('org.freedesktop.UDisks.Device',"DeviceFile")
		printer(" > DeviceFile: {0}".format(DeviceFile),tag=mytag)
		
	except:
		printer(" > DeviceFile is unset... Aborting...",tag=mytag)
		return None
	
	# Check if DeviceIsMediaAvailable...
	try:
		is_media_available = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsMediaAvailable")
		if is_media_available:
			printer(" > Media available",tag=mytag)
		else:
			printer(" > Media not available... Aborting...",tag=mytag)
			return None
	except:
		printer(" > DeviceIsMediaAvailable is not set... Aborting...",tag=mytag)
		return None
	
	# Check if it is a Partition...
	try:
		is_partition = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsPartition")
		if is_partition:
			printer(" > Device is partition",tag=mytag)
	except:
		printer(" > DeviceIsPartition is not set... Aborting...",tag=mytag)
		return None

	if not is_partition:
		printer(" > DeviceIsPartition is not set... Aborting...",tag=mytag)
		return None

	# Please Note:
	# DeviceFile = dbus.String(u'/dev/sda1', variant_level=1)
		
	ix = Sources.getIndex('name','media')
	
	#return DeviceFile
	parameters = {}
	parameters['index'] = ix
	parameters['device'] = str(DeviceFile)
	isAdded = Sources.sourceAddSub(ix,parameters)
	
	if isAdded:
	
		#get ix, ix_ss
		ix_ss = Sources.getIndexSub(ix,'device',str(DeviceFile))
		
		# check, and if available play
		if Sources.sourceCheck( ix, ix_ss ):
			#Sources.setCurrent( ix, ix_ss )
			#TODO: move to queue
			#Sources.sourcePlay()
			hu_play(ix, ix_ss)

			
		printSummary(Sources)
		return True
	else:
		return False
	
	#queue('blocking','DEVREM','button_devrem')

	#IdLabel: SJOERD
	#DriveSerial: 0014857749DCFD20C7F95F31
	#DeviceMountPaths: dbus.Array([dbus.String(u'/media/SJOERD')], signature=dbus.Signature('s'), variant_level=1)
	#DeviceFileById: dbus.Array([dbus.String(u'/dev/disk/by-id/usb-Kingston_DataTraveler_SE9_0014857749DCFD20C7F95F31-0:0-part1'), dbus.String(u'/dev/disk/by-uuid/D2B6-F8B3')], signature=dbus.Signature('s'), variant_level=1)
	
	#
	# DeviceFile contains the device name of the added device..
	#


	# check source, if added successfully
	

		

def udisk_rem( device ):

	global Sources

	device_obj = bus.get_object("org.freedesktop.UDisks", device)
	device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)
	#
	#  beware.... anything after this may or may not be defined depending on the event and state of the drive. 
	#  Attempts to get a prop that is no longer set will generate a dbus.connection:Exception
	#

	# HANDY DEBUGGING TIP, DISPLAY ALL AVAILABLE PROPERTIES:
	# WILL *NOT* WORK FOR DEVICE REMOVAL
	#data = device_props.GetAll('')
	#for i in data: print i+': '+str(data[i])
	
	# Variables
	DeviceFile = ""
	mountpoint = ""
	mytag = "UDISKS"
	ix = Sources.getIndex('name','media')
	
	# The removed mountpoint can be derived from str(device)

	# WHAT IF IT'S PLAYING??
	# TODO CHECK IF PLAYING!!

	# TODO ignore /dev/sda
	
	# form the partition device name
	partition = "/dev/"+os.path.basename(str(device))

	# search for the subsource index
	ix_ss = Sources.getIndexSub(ix, 'device', partition)
	if not ix_ss is None:
	
		# check current index, to check if we're playing this to-be removed sub-source
		arIxCurr = Sources.getIndexCurrent()
	
		# remove sub-source
		printer(' > Removing {0}...'.format(partition))
		Sources.remSub(ix, ix_ss)
		
		# stop playing, if removed source is current source
		print "DEBUG 1: {0}".format(arIxCurr)
		if ix == arIxCurr[0] and ix_ss == arIxCurr[1]:
			print "DEBUG 2"
			Sources.sourceStop()
			print "DEBUG 3"
			x = Sources.next(reverse=True)
			#x = Sources.next()
			print "DEBUG 4: {0}".format(x)
			hu_play()
			print "DEBUG 5"

	
		# display overview
		printSummary(Sources)
	else:
		printer(' > Not a subsource: {0}'.format(partition))	
		

	
def setup():

	# ZMQ
	zmq_connect()
	printer('Initialized [OK]')

def main():

	# Initialize the mainloop
	DBusGMainLoop(set_as_default=True)
	mainloop = gobject.MainLoop()

	try:
		bus = dbus.SystemBus()
	except dbus.DBusException:
		raise RuntimeError("No D-Bus connection")

	# Declare a name where our service can be reached
	try:
		bus_name = dbus.service.BusName("com.arctura.mpd", bus, do_not_queue=True)
	except dbus.exceptions.NameExistsException:
		print("service is already running")
		sys.exit(1)

	bus.add_signal_receiver(cb_udisk_dev_add, signal_name='DeviceAdded', dbus_interface="org.freedesktop.UDisks")
	bus.add_signal_receiver(cb_udisk_dev_rem, signal_name='DeviceRemoved', dbus_interface="org.freedesktop.UDisks")

	try:
		mainloop.run()
	finally:
		mainloop.quit()


if __name__ == "__main__":
	setup()
	main()