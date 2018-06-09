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
from hu_msg import parse_message

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "UDisks listener"
BANNER = "Udisks D-BUS listener"
LOG_TAG = 'UDISKS'
LOGGER_NAME = 'udisks'

SUBSCRIPTIONS = ['/udisks/']
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559

PATH_EVENT_ADD = '/events/udisks/added'
PATH_EVENT_REM = '/events/udisks/removed'

# global variables
logger = None
args = None
messaging = MqPubSubFwdController()
bus = None

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

# ********************************************************************************
# Load configuration
#
# ********************************************************************************
# Load configuration
#
def load_cfg_main():
	""" load main configuration """
	config = configuration_load(LOGGER_NAME,args.config)
	return config

def load_cfg_zmq():
	""" load zeromq configuration """	
	if not 'zeromq' in cfg_main:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		#cfg_main["zeromq"] = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB } }
		config = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB }
		return config
	else:
		config = {}
		# Get portnumbers from either the config, or default value
		if 'port_publisher' in cfg_main['zeromq']:
			config['port_publisher'] = cfg_main['zeromq']['port_publisher']
		else:
			config['port_publisher'] = DEFAULT_PORT_PUB
		
		if 'port_subscriber' in cfg_main['zeromq']:
			config['port_subscriber'] = cfg_main['zeromq']['port_subscriber']		
		else:
			config['port_subscriber'] = DEFAULT_PORT_SUB
			
		return config

def load_cfg_daemon():
	""" load daemon configuration """
	if 'daemons' not in cfg_main:
		return
	else:
		for daemon in cfg_main['daemons']:
			if 'script' in daemon and daemon['script'] == os.path.basename(__file__):
				return daemon

def load_cfg_gpio():
	""" load specified GPIO configuration """	
	if 'directories' not in cfg_main or 'daemon-config' not in cfg_main['directories'] or 'config' not in cfg_daemon:
		return
	else:		
		config_dir = cfg_main['directories']['daemon-config']
		# TODO
		config_dir = "/mnt/PIHU_CONFIG/"	# fix!
		config_file = cfg_daemon['config']
		
		gpio_config_file = os.path.join(config_dir,config_file)
	
	# load gpio configuration
	if os.path.exists(gpio_config_file):
		config = configuration_load(LOGGER_NAME,gpio_config_file)
		return config
	else:
		print "ERROR: not found: {0}".format(gpio_config_file)
		return


	configuration = configuration_load(LOGGER_NAME,args.config)
	
	if not configuration or not 'zeromq' in configuration:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		configuration = { "zeromq": { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB } }
		return configuration
		
	else:
		# Get portnumbers from either the config, or default value
		if not 'port_publisher' in configuration['zeromq']:
			configuration['zeromq']['port_publisher'] = DEFAULT_PORT_PUB
			
		if not 'port_subscriber' in configuration['zeromq']:
			configuration['zeromq']['port_subscriber'] = DEFAULT_PORT_SUB
			
	return configuration	

# ********************************************************************************
# On Idle
#
# -------------------------------------------------------------------------
# Sub Functions must return None (invalid params) or a {data} object.
@messaging.handle_mq('/udisks/devices', cmd='GET')
def get_devices(path=None, cmd=None, args=None, data=None):
	"""	Retrieve List of Registered Devices """						
	data = struct_data(attached_drives)
	return data	# this will be returned using the response path
	
"""
def idle_message_receiver():
	parsed_msg = messaging.poll(timeout=1000, parse=True)	#Timeout: None=Blocking
	if parsed_msg:
		ret = messaging.execute_mq(parsed_msg['path'], parsed_msg['cmd'], args=parsed_msg['args'], data=parsed_msg['data'] )
			
		if parsed_msg['resp_path'] and ret is not False:
			messaging.publish_command(parsed_msg['resp_path'],'DATA',ret)
		
	return True # Important! Returning true re-enables idle routine.
"""

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
		
		#messaging.publish_command(PATH_EVENT_ADD,'DATA',param)
		ret = messaging.publish_command(PATH_EVENT_ADD,'DATA',mq_args)
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
			messaging.publish_command(PATH_EVENT_REM,'DATA',param)
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
	global cfg_gpio

	# main
	cfg_main = load_cfg_main()
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	# zeromq
	if not args.port_publisher and not args.port_subscriber:
		cfg_zmq = load_cfg_zmq()
	else:
		if args.port_publisher and args.port_subscriber:
			pass
		else:
			load_cfg_zmq()
	
		# Pub/Sub port override
		if args.port_publisher:
			configuration['zeromq']['port_publisher'] = args.port_publisher
		if args.port_subscriber:
			configuration['zeromq']['port_subscriber'] = args.port_subscriber

	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
			
	# daemon
	cfg_daemon = load_cfg_daemon()
	if cfg_daemon is None:
		printer("Daemon configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	# gpio
	cfg_gpio = load_cfg_gpio()
	if cfg_gpio is None:
		printer("GPIO configuration could not be loaded.", level=LL_CRITICAL)
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
	gobject.idle_add(messaging.poll_and_execute(1000))

	try:
		mainloop.run()
	finally:
		mainloop.quit()


if __name__ == "__main__":
	parse_args()
	setup()
	main()
	
	
