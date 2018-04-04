#
# SOURCE PLUGIN: Removable media
# Venema, S.R.G.
# 2018-03-27
#
# Plays everything mounted on /media, except in PIHU_*-folders
# Will create a subsource when a USB drive is inserted using the UDisks service.
# Will not remove subsources of drives that are removed, will simply mark them unavailable.
#

#
# Extends MPDSOURCEPLUGIN
#

import os
import subprocess

from yapsy.IPlugin import IPlugin
from modules.hu_utils import *
from modules.hu_settings import getSourceConfig
from modules.source_plugin_mpd import MpdSourcePlugin

class MySource(MpdSourcePlugin,IPlugin):

	def __init__(self):
		super(MySource,self).__init__()

	def on_init(self, plugin_name, sourceCtrl, logger=None):
		super(MySource, self).on_init(plugin_name,sourceCtrl,logger)	# Executes init() at MpdSourcePlugin
		return True

	def on_add(self, sourceconfig):
		"""Executed after a source is added by plugin manager.
		Executed by: hu_source.load_source_plugins().
		Return value is not used.
		
		MEDIA: This adds all mountpoints under /media, but does not check anything.
		"""

		index = self.sourceCtrl.index('name',self.name)	#name is unique
		if index is None:
			print "Plugin {0} does not exist".format(self.name)
			return False
		
		# Discover + Add
		mountpoints = self.discover(add_subsource=True)
		
		return True

	def on_activate(self, subindex):
		return False

	def add_subsource(self, mountpoint, label, uuid, device, index):
		subsource = {}
		subsource['displayname'] = 'media: ' + mountpoint
		subsource['order'] = 0		# no ordering
		subsource['mountpoint'] = mountpoint
		subsource['mpd_dir'] = mountpoint[7:]		# TODO -- ASSUMING /media
		subsource['label'] = label
		subsource['uuid'] = uuid
		subsource['device'] = device
		self.sourceCtrl.add_sub(index, subsource)

	def check_availability(self, subindex=None):
		"""Executed after post_add, and may occasionally be called.
		If a subindex is given then only check that subsource.
		
		This method updates the availability.
		
		Returns: List of changes in availability.
		
		MEDIA: Check if subsource exists and has music in the MPD database
		"""
		locations = []							# list of tuples; index: 0 = mountpoint, 1 = mpd dir, 2 = availability.
		subsource_availability_changes = []		# list of changes
		index = self.sourceCtrl.index('name',self.name)	#name is unique

		if subindex is None:
			subsources = self.sourceCtrl.subsource_all( index )
			i = 0
		else:
			subsources = list(self.sourceCtrl.subsource( index, subindex ))
			i = subindex
		
		for subsource in subsources:
			mountpoint = subsource['mountpoint']			
			cur_availability = subsource['available']
			self.printer('Checking local folder: {0}, current availability: {1}'.format(mountpoint,cur_availability))
			new_availability = self.check_mpddb_mountpoint(mountpoint, createdir=True, waitformpdupdate=True)
			self.printer('Checked local folder: {0}, new availability: {1}'.format(mountpoint,new_availability))
			
			if new_availability is not None and new_availability != cur_availability:
				subsource_availability_changes.append({"index":index,"subindex":i,"available":new_availability})			
			
			i += 1
		
		return subsource_availability_changes
	
	# -------------------------------------------------------------------------

	def discover(self, add_subsource=True):
		"""Returns a list of everything mounted on /media, but does not check if it has music.
		Returned is a 2-dimension list
		Mountpoints already present will be omitted.
		"""

		mountpoints = get_mounts( mp_exclude=['/','/mnt/PIHU_APP','/mnt/PIHU_CONFIG','/media/PIHU_DATA','/media/PIHU_DATA_'], fs_exclude=['cifs'] )
		if not mountpoints:
			self.printer(' > No removable media found')
		else:
			self.printer(' > Found {0} removable media'.format(len(mountpoints)))

		i=0
		for mount in mountpoints:
			mountpoint = mount['mountpoint']
			device = mount['mountpoint']
			label = os.path.basename(mount['mountpoint']).rstrip('\n')
			
			# only add if not already present
			subindex = self.sourceCtrl.subindex('mountpoint',mountpoint)
			if subindex is None:
				# get uuid
				try:
					uuid = subprocess.check_output("blkid "+mount['spec']+" -s PARTUUID -o value", shell=True).rstrip('\n')
				except:
					self.printer('Could not get a partition UUID for {0}'.format(mount['spec']),level=LL_ERROR)
					uuid = ''
								
				self.add_subsource( mountpoint
								   ,label
								   ,uuid
								   ,device
								   ,index)
			else:
				del mountpoints[i]
			
			i+=1
			
		return mountpoints
		
		"""
		try:
			self.__printer('Check if anything is mounted on /media...')
			# do a -f1 for devices, -f3 for mountpoints
			grepOut = subprocess.check_output(
				"mount | grep /media | cut -d' ' -f1,3",
				shell=True,
				stderr=subprocess.STDOUT,
			)
		except subprocess.CalledProcessError as err:
			print('ERROR:', err)
			pa_sfx('error')
			return None
		
		grepOut = grepOut.rstrip('\n')
		lst_mountpoints = [[x for x in ss.split(' ')] for ss in grepOut.split('\n')]

		# remove local data (locmus) and smb mounts:
		# TODO: this shouldn't be hardcoded:
		lst_mountpoints[:] = [tup for tup in lst_mountpoints if (not tup[1] == '/media/PIHU_DATA' and not tup[0].startswith('//'))]
		"""
		return True	

	def zz_add_subsource( self, sourceCtrl, parameters ):
		
		has_mountpoint = False
		has_device = False
		device = ""
		mountpoint = ""
		uuid = ""
		label = ""
		mpd_dir = ""
		index = None
		
		# MOUNTPOINT and DEVICE
		if 'mountpoint' in parameters:
			print "MOUNTP"
			has_mountpoint = True
		
		if 'device' in parameters:
			device = parameters['device']
			print "DEVICE {0}".format(device)
			has_device = True
		
		# retrieve mountpoint or device
		if not has_mountpoint and not has_device:
			self.__printer('No mountpoint or device given, aborting')
			return False
			
		elif has_mountpoint and not has_device:
			print "DETERMINE DEVICE #TODO > aborting"
			#TODO
			return False
			
		elif has_device and not has_mountpoint:
			self.__printer("Determining mountpoint", level=LL_DEBUG)
			
			## get mountpoint from "mount" command
			#mountpoint = subprocess.check_output("mount | egrep "+device+" | cut -d ' ' -f 3", shell=True).rstrip('\n')
			## check if we have a mountpoint...
			#if mountpoint == "":
			#	self.__printer(" > No mountpoint found. Stopping.")
			#	return False
			
			# get mountpoint
			mountpoints = get_mounts( spec=device )	
			#if len(mountpoints) == 0:
			if not mountpoints:
				self.__printer(" > No mountpoint found. Stopping.")
				return False
			else:
				mountpoint = mountpoints[0]['mountpoint']

		# UUID
		if 'uuid' not in parameters:
			# retrieve the partition uuid (hu_utils)
			uuid = get_part_uuid(device)
		else:
			uuid = parameters['uuid']		
			
		# check if we have a UUID...
		if uuid == "":
			self.__printer(" > No UUID found. Stopping.")
			return False
		
		# LABEL
		if 'label' not in parameters:
			label = os.path.basename(mountpoint).rstrip('\n')
		else:
			label = parameters['label']
		
		# check if we have a label...
		if label == "":
			self.__printer(" > No label found. Stopping.")
			return False
		
		# MPD dir
		if 'mpd_dir' not in parameters:
			# TODO -- ASSUMING /media
			mpd_dir = mountpoint[7:]
		else:
			mpd_dir = parameters['mpd_dir']
		
		# Source index
		if 'index' not in parameters:
			index = sourceCtrl.index('name','media')
		else:
			index = parameters['index']

		# logging
		self.__printer(" > Mounted on: {0} (label: {1})".format(mountpoint,label))
			
		# construct the subsource
		subsource = {}
		subsource['name'] = 'media'
		subsource['displayname'] = 'media: ' + mountpoint
		subsource['order'] = 0		# no ordering
		subsource['mountpoint'] = mountpoint
		subsource['mpd_dir'] = mpd_dir
		subsource['label'] = label
		subsource['uuid'] = uuid
		subsource['device'] = device

		ret = sourceCtrl.add_sub(index, subsource)
		return ret
	
	def play( self, sourceCtrl, position=None, resume={} ):
		super(MySource,self).play()

		#
		# continue where left
		#
		
		'''
		# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1
		if resume:
			playslist_pos = self.mpdc.lastKnownPos2( resume['file'], resume['time'] )
			#playslist_pos = self.mpdc.lastKnownPos( sUsbLabel )
		else:
			playslist_pos = {'pos': 1, 'time': 0}
		
		self.__printer(' > Starting playback')
		#mpc.playStart( str(playslist_pos['pos']), playslist_pos['time'] )
		subprocess.call(["mpc", "-q" , "stop"])
		subprocess.call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
		if playslist_pos['time'] > 0:
			self.__printer(' > Seeking to {0} sec.'.format(playslist_pos['time']))
			subprocess.call(["mpc", "-q" , "seek", str(playslist_pos['time'])])

		# Load playlist directories, to enable folder up/down browsing.
		#mpc_get_PlaylistDirs()
		# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
	#		mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc_get_PlaylistDirs)
	#		mpc_get_PlaylistDirs_thread.start()

		'''
		return True
