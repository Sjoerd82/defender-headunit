#!/usr/bin/python

#
# Udisks D-Bus event listener
# Venema, S.R.G.
# 2018-03-23
#
# Udisks D-Bus event listener forwards events on regarding Udisks-glue to ZeroMQ
#

import sys
import os
from time import sleep

# dbus
import dbus.service
import dbus.exceptions

# main loop
import gobject
from dbus.mainloop.glib import DBusGMainLoop

# Utils
#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController
from hu_commands import Commands

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "UDisks listener"
BANNER = "Udisks D-BUS listener"
LOG_TAG = 'UDISKS'
LOGGER_NAME = 'udisks'

SUBSCRIPTIONS = ['/udisks/']

PATH_EVENT_ADD = '/events/udisks/added'
PATH_EVENT_REM = '/events/udisks/removed'

# global variables
logger = None
args = None
messaging = MqPubSubFwdController()
bus = None
command = Commands()

# configuration
cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ

# keep track of anything attached
attached_drives = []

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# -------------------------------------------------------------------------
# Sub Functions must return None (invalid params) or a {data} object.
# TODO: event path
@messaging.register('/udisks/devices', cmd='GET')
@command.validate()
def get_devices(path=None, cmd=None, args=None, data=None):
	"""	Retrieve List of Registered Devices """						
	data = struct_data(attached_drives)
	return data	# this will be returned using the response path


#********************************************************************************
# Parse command line arguments
#
def parse_args():

	global args
	import argparse
	parser = default_parser(DESCRIPTION,BANNER)
	# additional command line arguments mat be added here
	args = parser.parse_args()

#********************************************************************************
# CALLBACK functions:
#  cb_udisk_dev_add
#  cb_udisk_dev_rem
#
def cb_udisk_dev_add( device ):
	printer('Device added: {0}'.format(str(device)))
	#item = {}
	#item['command'] = 'DEVADD'
	#item['device'] = device
	#queue('blocking',item,'button_devadd')
	udisk_add(device)

def cb_udisk_dev_rem( device ):
	printer('Device removed: {0}'.format(str(device)))
	#item = {}
	#item['command'] = 'DEVREM'
	#item['device'] = device
	#queue('blocking',item,'button_devrem')
	udisk_rem(device)

#********************************************************************************
# Device added
#
def udisk_add( device ):

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
	
	try:
		DeviceFile = device_props.Get('org.freedesktop.UDisks.Device',"DeviceFile")
		printer(" > DeviceFile: {0}".format(DeviceFile))
	except:
		printer(" > DeviceFile is unset... Aborting...")
		return None
	
	# Check if DeviceIsMediaAvailable...
	try:
		is_media_available = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsMediaAvailable")
		if is_media_available:
			printer(" > Media available")
		else:
			printer(" > Media not available... Aborting...")
			return None
	except:
		printer(" > DeviceIsMediaAvailable is not set... Aborting...")
		return None
	
	# Check if it is a Partition...
	try:
		is_partition = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsPartition")
		if is_partition:
			printer(" > Device is partition")
	except:
		printer(" > DeviceIsPartition is not set... Aborting...")
		return None

	if not is_partition:
		printer(" > DeviceIsPartition is not set... Aborting...")
		return None

	# Please Note:
	# DeviceFile = dbus.String(u'/dev/sda1', variant_level=1)

	printer("Registering")
	media_info = {}	
	media_info['device'] = str(DeviceFile)
	media_info['uuid'] = get_part_uuid(str(DeviceFile))
	media_info['mountpoint'] = get_mountpoint(media_info['device'])
	
	if media_info['mountpoint'] is None:
		printer(" > Device was inserted, but there is no mountpoint. Waiting 30 seconds...")
		for i in range(6):
			sleep(5)
			printer(" > Retrying...")
			media_info['mountpoint'] = get_mountpoint(media_info['device'])
			if media_info['mountpoint'] is not None:
				printer(" > Mountpoint found [OK]")
				break
	
	if media_info['mountpoint'] is not None:		
		media_info['label'] = os.path.basename(media_info['mountpoint']).rstrip('\n')
		attached_drives.append(media_info)
		printer(" > Registering [OK]")

		# if we can't send a dict, then for the time being do this:
		#param = '{{"device":"{0}", "mountpoint":"{1}","uuid":"{2}","label":"{3}"}}'.format(str(DeviceFile),media_info['mountpoint'],media_info['uuid'],media_info['label'])
		
		mq_args = json.dumps(media_info)
		
		#messaging.publish(PATH_EVENT_ADD,'DATA',param)
		ret = messaging.publish(PATH_EVENT_ADD,'DATA',mq_args)
		if ret == True:
			printer(" > Sending MQ notification [OK]")
		else:
			printer(" > Sending MQ notification [FAIL] {0}".format(ret))
	else:
		printer(" > Device was inserted, but there was no mountpoint. [FAIL]")
	
	#IdLabel: SJOERD
	#DriveSerial: 0014857749DCFD20C7F95F31
	#DeviceMountPaths: dbus.Array([dbus.String(u'/media/SJOERD')], signature=dbus.Signature('s'), variant_level=1)
	#DeviceFileById: dbus.Array([dbus.String(u'/dev/disk/by-id/usb-Kingston_DataTraveler_SE9_0014857749DCFD20C7F95F31-0:0-part1'), dbus.String(u'/dev/disk/by-uuid/D2B6-F8B3')], signature=dbus.Signature('s'), variant_level=1)
	
		
#********************************************************************************
# Device removed
#
def udisk_rem( device ):

	device_obj = bus.get_object("org.freedesktop.UDisks", device)
	device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)
	#
	#  beware.... anything after this may or may not be defined depending on the event and state of the drive. 
	#  Attempts to get a prop that is no longer set will generate a dbus.connection:Exception
	#
	
	# Variables
	DeviceFile = ""
	mountpoint = ""
	media_info = {}

	# HANDY DEBUGGING TIP, DISPLAY ALL AVAILABLE PROPERTIES:
	# WILL *NOT* WORK FOR DEVICE REMOVAL
	#data = device_props.GetAll('')
	#for i in data: print i+': '+str(data[i])
	
	partition = "/dev/"+os.path.basename(str(device))
	print partition
	
	# find our missing drive
	ix_del = None
	i=0
	for devpart in attached_drives:
		if devpart['device'] == partition:
	
			#media_info['partition'] = partition
			media_info['device'] = devpart['device']
			media_info['uuid'] = devpart['uuid']
			media_info['mountpoint'] = devpart['mountpoint']
			media_info['label'] = devpart['label']

			param = '{{"device":"{0}", "mountpoint":"{1}","uuid":"{2}","label":"{3}"}}'.format(media_info['device'],media_info['mountpoint'],media_info['uuid'],media_info['label'])
			messaging.publish(PATH_EVENT_REM,'DATA',param)
			ix_del = i
			break
		i+=1
	
	if ix_del is not None:
		del attached_drives[ix_del]
	else:
		printer("An unregistered device was removed.")
	
	"""
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
	"""

#********************************************************************************	
def setup():

	global messaging

	#
	# Logging
	# -> Output will be logged to the syslog, if -b specified, otherwise output will be printed to console
	#
	global logger
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)

	if args.b:
		logger = log_create_syslog_loghandler(logger, args.loglevel, LOG_TAG, address='/dev/log') 	# output to syslog
	else:
		logger = log_create_console_loghandler(logger, args.loglevel, LOG_TAG) 						# output to console
	
	#
	# Configuration
	#
	global cfg_main
	global cfg_zmq
	global cfg_daemon
	global cfg_dummy

	cfg_main, cfg_zmq, cfg_daemon, cfg_dummy = load_cfg(
		args.config,
		['main','zmq','daemon'],
		args.port_publisher, args.port_subscriber,
		daemon_script=os.path.basename(__file__),
		logger_name=LOGGER_NAME	)
	
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
			
	if cfg_daemon is None:
		printer("Daemon configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
					
	#
	# ZMQ
	#
	printer("ZeroMQ: Initializing")
	messaging.set_address('localhost',cfg_zmq['port_publisher'],cfg_zmq['port_subscriber'])
	
	printer("ZeroMQ: Creating Publisher: {0}".format(cfg_zmq['port_publisher']))
	messaging.create_publisher()
	
	printer("ZeroMQ: Creating Subscriber: {0}".format(cfg_zmq['port_subscriber']))
	messaging.create_subscriber(SUBSCRIPTIONS)

	printer('ZeroMQ subscriptions:')
	for topic in messaging.subscriptions():
		printer("> {0}".format(topic))

	#
	# See if anything already attached
	#
	mountpoints = get_mounts(mp_exclude=['/','/dev','/media/PIHU_DATA','/media/PIHU_DATA2','/mnt/PIHU_CONFIG','/mnt/PIHU_APP'], fs_exclude=['cifs','tmpfs'])
	for mountpoint in mountpoints:
		media_info = {}
		media_info['device'] = mountpoint['spec']
		media_info['mountpoint'] = mountpoint['mountpoint']
		media_info['uuid'] = get_part_uuid(media_info['device'])
		media_info['label'] = os.path.basename(media_info['mountpoint']).rstrip('\n')
		attached_drives.append(media_info)
	
	printer('Found drives: {0}'.format(attached_drives))
	
	printer('Initialized [OK]')

def main():

	global bus
	
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
	gobject.idle_add(messaging.poll_and_execute,1000)

	try:
		mainloop.run()
	finally:
		mainloop.quit()


if __name__ == "__main__":
	parse_args()
	setup()
	main()
	
	
