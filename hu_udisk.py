# MISC (self.__printer, colorize)
from hu_utils import *

def udisk_details( device, action ):
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
	
	DeviceFile = ""
	mountpoint = ""
	
	try:
		DeviceFile = device_props.Get('org.freedesktop.UDisks.Device',"DeviceFile")
		print(" .....  DeviceFile: {0}".format(DeviceFile))
		
	except:
		print(" .....  DeviceFile is unset... Aborting...")
		return 1
	
	# Check if DeviceIsMediaAvailable...
	try:    
		is_media_available = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsMediaAvailable")
		if is_media_available:
			print(" .....  Media available")
		else:
			print(" .....  Media not available... Aborting...")
			return 1
	except:
		print(" .....  DeviceIsMediaAvailable is not set... Aborting...")
		return 1
	
	# Check if it is a Partition...
	try:
		is_partition = device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsPartition")
		if is_partition:
			print(" .....  Device is partition")
	except:
		print(" .....  DeviceIsPartition is not set... Aborting...")
		return 1

	if not is_partition:
		print(" .....  DeviceIsPartition is not set... Aborting...")
		return 1

	if action == 'A':
		# Find out its mountpoint...
		#IdLabel: SJOERD
		#DriveSerial: 0014857749DCFD20C7F95F31
		#DeviceMountPaths: dbus.Array([dbus.String(u'/media/SJOERD')], signature=dbus.Signature('s'), variant_level=1)
		#DeviceFileById: dbus.Array([dbus.String(u'/dev/disk/by-id/usb-Kingston_DataTraveler_SE9_0014857749DCFD20C7F95F31-0:0-part1'), dbus.String(u'/dev/disk/by-uuid/D2B6-F8B3')], signature=dbus.Signature('s'), variant_level=1)
		
		mountpoint = subprocess.check_output("mount | egrep "+DeviceFile+" | cut -d ' ' -f 3", shell=True).rstrip('\n')
		if mountpoint != "":
			sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
			print(" .....  Mounted on: {0} (label: {1})".format(mountpoint,sUsbLabel))
			mpc_update(sUsbLabel, True)
			media_check(sUsbLabel)
			media_play()
		else:
			print(" .....  No mountpoint found. Stopping.")
		
	elif action == 'R':
		# Find out its mountpoint...
		#We cannot retrieve many details from dbus about a removed drive, other than the DeviceFile (which at this point is no longer available).
		media_check( None )
		# Determine if we were playing this media (source: usb=1)
		#if dSettings['source'] == 1 and
		
		#TODO!
		
	else:
		print(" .....  ERROR: Invalid action.")
		pa_sfx('error')