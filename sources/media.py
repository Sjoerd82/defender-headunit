#
# SOURCE PLUGIN: Removable media
# Venema, S.R.G.
# 2018-03-27
#
# Plays everything mounted on /media, except in PIHU_*-folders
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

	def init(self, plugin_name, logger=None):
		super(MySource, self).init(plugin_name,logger)	# Executes init() at MpdSourcePlugin		
		return True

	def post_add(self, sourceCtrl, sourceconfig):
		"""Executed after a source is added by plugin manager.
		Executed by: hu_source.load_source_plugins().
		Return value is not used.
		
		This Post-Add add all mountpoints under /media, but does not check anything.
		"""
		
		lst_mountpoints = get_mounts( mp_exclude=['/','/mnt/PIHU_APP','/mnt/PIHU_CONFIG','/media/PIHU_DATA','/media/PIHU_DATA_'], fs_exclude=['cifs'] )
		
		if not lst_mountpoints:
			self.printer(' > No removable media found')
		else:
			self.printer(' > Found {0} removable media'.format(len(lst_mountpoints)))
		
		for mount in lst_mountpoints:
			
			# get mountpoint and label
			mountpoint = mount['mountpoint']
			sUsbLabel = os.path.basename(mount['mountpoint']).rstrip('\n')
			
			# get uuid
			try:
				uuid = subprocess.check_output("blkid "+mount['spec']+" -s PARTUUID -o value", shell=True).rstrip('\n')
			except:
				self.printer('Could not get a partition UUID for {0}'.format(mount['spec']),level=LL_ERROR)
				uuid = ''
				
			# add subsource
			self.__media_add_subsource( mountpoint
							           ,sUsbLabel
							           ,uuid
									   ,mount['mountpoint']
							           ,sourceCtrl)

		self.printer('Initializing... DONE')		
		return True


	# def check()
	
	# -------------------------------------------------------------------------
	
	def __media_add_subsource( self, dir, label, uuid, device, sourceCtrl ):
		# get index (name is unique)
		ix = sourceCtrl.index('name','media')
		
		# construct the subsource
		subsource = {}
		subsource['name'] = 'media'
		subsource['displayname'] = 'media: ' + dir
		subsource['order'] = 0		# no ordering
		subsource['mountpoint'] = dir
		subsource['mpd_dir'] = dir[7:]		# TODO -- ASSUMING /media
		subsource['label'] = label
		subsource['uuid'] = uuid
		subsource['device'] = device

		sourceCtrl.add_sub(ix, subsource)
	
	
	def zz__media_get_media_mountpoints():
		"""Returns a list of everything mounted on /media, but does not check if it has music.
		Returned is a 2-dimension list
		"""

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
		# TODO: remove hardcoded paths
		lst_mountpoints = get_mounts( mp_exclude=['/','/mnt/PIHU_APP','/mnt/PIHU_CONFIG','/media/PIHU_DATA','/media/PIHU_DATA_'], fs_exclude=['cifs'] )
		
		if not lst_mountpoints:
			self.__printer(' > No removable media found')
		else:
			#lst_mountpoints[:] = (x for x in somelist if determine(x))
			#yourList[:] = itertools.ifilter(do_the_magic, yourList)
			# filter out everything that's not mounted on /media or is smb:
			"""
			i=0
			#for i, mp in enumerate(lst_mountpoints):
			for mp in lst_mountpoints:
				print mp['mountpoint']
				print mp['fs']
				if not mp['mountpoint'].startswith('/media/') or mp['fs'] == 'cifs':
					print "DELETE: {0}".format(mp['mountpoint'])
					#del lst_mountpoints[i]
					#lst_mountpoints.remove( mp )
					
				i+=1
			"""
			# check if anything left
			if not lst_mountpoints:
				self.__printer(' > No removable media found')
			else:
				self.__printer(' > Found {0} removable media'.format(len(lst_mountpoints)))
		
		print lst_mountpoints
		return lst_mountpoints
		
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
	
	def zz_init( self, sourceCtrl ):
		self.__printer('Initializing...')
		
		# do a general media_check to find any mounted drives
		#media_check( label=None )
		
		# add all locations as configured
		arMedia = media_getAll()
		for mount in arMedia:
			
			# get mountpoint and label
			mountpoint = mount['mountpoint']
			sUsbLabel = os.path.basename(mount['mountpoint']).rstrip('\n')
			
			# get uuid
			try:
				uuid = subprocess.check_output("blkid "+mount['spec']+" -s PARTUUID -o value", shell=True).rstrip('\n')
			except:
				self.__printer('Could not get a partition UUID for {0}'.format(mount['spec']),level=LL_ERROR)
				uuid = ''
				
			# add subsource
			self.__media_add_subsource( mountpoint
							           ,sUsbLabel
							           ,uuid
									   ,mount['mountpoint']
							           ,sourceCtrl)

		self.__printer('Initializing... DONE')
		return True

	#  media_check with a "label" parameter checks specific label on /media
	def Xcheck( self, sourceCtrl, subSourceIx=None  ):
		"""	Check source
		
			Checks all mountpoints of /media
			if SUBSOURCE INDEX given, will only check mountpoint of that subsource index
			Returns a list with dict containing changed subsources
		
			Q: Look for new mountpoints?	Should be handled by udisks...
		"""
		
		self.printer('Checking availability...')
		# QUESTION.... SHOULD THIS MEDIA_CHECK GO LOOKING FOR POSSIBLE NEW MOUNTS?????
		"""
		try:
			print(' .....  Check if anything is mounted on /media...')
			# do a -f1 for devices, -f3 for mountpoints
			grepOut = subprocess.check_output(
				"mount | grep /media | cut -d' ' -f3",
				shell=True,
				stderr=subprocess.STDOUT,
			)
		except subprocess.CalledProcessError as err:
			print('ERROR:', err)
			pa_sfx('error')
			return False
		
		arMedia = grepOut.split()
		"""

		ix = sourceCtrl.index('name','media')	# index
		locations = []							# list of tuples; index: 0 = mountpoint, 1 = mpd dir, 2 = availability.
		subsource_availability_changes = []		# list of changes
						
		if subSourceIx == None:
			subsources = sourceCtrl.subsource_all( ix )
			for subsource in subsources:
				locations.append( (subsource['mountpoint'], subsource['mpd_dir'], subsource['available']) )
			ssIx = 0
		else:
			subsource = sourceCtrl.subsource( ix, subSourceIx )
			locations.append( (subsource['mountpoint'], subsource['mpd_dir'], subsource['available']) )
			ssIx = subSourceIx
			
		# check mountpoint(s)
		for location in locations:
			mountpoint = location[0]
			mpd_dir = location[1]
			original_availability = location[2]
			new_availability = None

			self.printer('Media folder: {0}'.format(mountpoint))
			if not os.listdir(mountpoint):
				self.printer(" > Removable music directory is empty.",LL_WARNING)
				new_availability = False
			else:
				self.printer(" > Removable music directory present and has files.",LL_INFO)
				if not self.mpdc.is_dbdir( mpd_dir ):
					self.printer(" > Running MPD update for this directory.. ALERT! LONG BLOCKING OPERATION AHEAD...")
					self.mpdc.update_db( mpd_dir, True )	#TODO: don't wait! set available on return of update..
					if not self.mpdc.is_dbdir( mpd_dir ):
						self.printer(" > Nothing to play marking unavailable...")
						new_availability = False
					else:
						self.__printer(" > Music found after updating")
						new_availability = True
				else:
					new_availability = True

			if new_availability is not None and new_availability != original_availability:
				sourceCtrl.set_available( ix, new_availability, ssIx )
				subsource_availability_changes.append({"index":ix,"subindex":ssIx,"available":new_availability})

			ssIx+=1

		return subsource_availability_changes
			
		"""
		
		# Return True/False for general check (when label is None)
		if label == None:
			if len(arMedia) > 0:
				print(' .....  /media has mounted filesystems.')
				return True
			else:
				print(' ..... nothing mounted on /media.')
				return False

		# Check if requested label is mounted
		label_found = False
		for mountpoint in arMedia:
			sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
			if sUsbLabel == label:
				label_found = True
				break

		# Requested label is not mounted
		if not label_found:
			print(' .....  label {0} is not mounted.'.format(label))
			return False
		
		print(' .....  Continuing to crosscheck with mpd database for music...')
		
		taskcmd = "mpc listall "+sUsbLabel+" | wc -l"
		task = subprocess.Popen(taskcmd, shell=True, stdout=subprocess.PIPE)
		mpcOut = task.stdout.read()
		assert task.wait() == 0
		
		if mpcOut.rstrip('\n') == '0':
			print(' ..... . {0}: nothing in the database for this source.'.format(sUsbLabel))
			return False
		else:
			print(' ..... . {0}: found {1:s} tracks'.format(sUsbLabel,mpcOut.rstrip('\n')))
			return True

		"""
			
		"""
		# playlist loading is handled by scripts that trigger on mount/removing of media
		# mpd database is updated on mount by same script.
		# So, let's check if there's anything in the database for this source:
		
		if len(arMedia) > 0:
			print(' .....  /media has mounted filesystems: ')
			for mountpoint in arMedia:
				print(' ... . {0}'.format(mountpoint))
			
			print(' .....  Continuing to crosscheck with mpd database for music...')
			for mountpoint in arMedia:
				sUsbLabel = os.path.basename(mountpoint).rstrip('\n')
				
				if sUsbLabel == sLocalMusicMPD:
					print(' ..... . {0}: ignoring local music directory'.format(sLocalMusicMPD))
				if sUsbLabel == sSambaMusic:
					print(' ..... . {0}: ignoring samba music directory'.format(sSambaMusicMPD))
				else:		
					taskcmd = "mpc listall "+sUsbLabel+" | wc -l"
					task = subprocess.Popen(taskcmd, shell=True, stdout=subprocess.PIPE)
					mpcOut = task.stdout.read()
					assert task.wait() == 0
					
					if mpcOut.rstrip('\n') == '0':
						print(' ..... . {0}: nothing in the database for this source.'.format(sUsbLabel))
					else:
						print(' ..... . {0}: found {1:s} tracks'.format(sUsbLabel,mpcOut.rstrip('\n')))
						
						# Adding source
						Sources.addSource({'name': 'media',
										   'displayname': 'Removable Media',
										   'order': 1,
										   'available': True,
										   'type': 'mpd',
										   'depNetwork': False,
										   'controls': ctrlsMedia,
										   'mountpoint': mountpoint,
										   'label': sUsbLabel,
										   'uuid': None }
						)
						#REMOVE:
						arMediaWithMusic.append(mountpoint)
						#default to found media, if not set yet
						
						# Determine the active mediasource
						if prefered_label == sUsbLabel:
							#pleister
							dSettings['mediasource'] = len(arMediaWithMusic)-1
						elif dSettings['mediasource'] == -1:
							dSettings['mediasource'] = 0



			# if nothing useful found, then mark source as unavailable
			#if len(arMediaWithMusic) == 0:
			#	arSourceAvailable[1]=0

		else:
			print(' ..... nothing mounted on /media.')

		return False
		"""
		
	def play( self, sourceCtrl, position=None, resume={} ):
		self.__printer('Start playing (MPD)')
		
		#
		# variables
		#
		arIx = sourceCtrl.index_current()
		subsource = sourceCtrl.subsource( arIx[0], arIx[1] )
		sLocalMusicMPD = subsource['mpd_dir']
		sUsbLabel = subsource['label']

		#
		# load playlist
		#

		# populate playlist
		self.mpdc.pls_clear()
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???
	#	sUsbLabel = os.path.basename(arMediaWithMusic[dSettings['mediasource']])
		playlistCount = self.mpdc.pls_pop(sLocalMusicMPD)

		# check if succesful...
		if playlistCount == "0":
			self.__printer(' > Nothing in the playlist, trying to update database...')
			
			# update and try again...
			self.mpdc.update_db( sLocalMusicMPD, True )
			playlistCount = self.mpdc.pls_pop(sLocalMusicMPD)
			
			# check if succesful...
			if playlistCount == "0":
				# Failed. Returning false will cause caller to try next source
				self.__printer(' > Nothing in the playlist, giving up. Marking source unavailable.')
				sourceCtrl.set_available( arIx[0], False, arIx[1] )
				pa_sfx(LL_ERROR)
				return False
			else:
				self.__printer(' > Found {0:s} tracks'.format(playlistCount))
		else:
			self.__printer(' > Found {0:s} tracks'.format(playlistCount))

		#
		# continue where left
		#
		
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

		return True
