#
# SOURCE PLUGIN: SMB Network Shares
# Venema, S.R.G.
# 2018-04-03
#
# Plays everything mounted on /media/PIHU_SMB
#

#
# Extends MPDSOURCEPLUGIN
#

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
		
		SMB: This function adds all SMB shares, but does not check if they have music.
		"""
		
		# Subsources for this source can be gathered from the directory on
		# which the SMB shares are mounted. default:/media/PIHU_SMB.
		
		index = self.sourceCtrl.index('name',self.name)	#name is unique
		if index is None:
			print "Plugin {0} does not exist".format(self.name)
			return False

		mountpoints = get_mounts( fs='cifs' )
		if not mountpoints:
			self.printer(' > No SMB network shares found')
		else:
			self.printer(' > Found {0} network shares'.format(len(mountpoints)))
		
		for mount in mountpoints:
			mountpoint = mount['mountpoint']
			label = os.path.basename(mount['mountpoint']).rstrip('\n')
			path = '' #?
			self.add_subsource( mountpoint
					           ,label
							   ,path
							   ,index)
		return True

	def add_subsource(self, mountpoint, label, path, index):
		subsource = {}
		subsource['displayname'] = 'smb: ' + mountpoint
		subsource['mountpoint'] = mountpoint
		subsource['mpd_dir'] = mountpoint[7:]		# TODO -- ASSUMING /media
		subsource['label'] = label
		subsource['path'] = path
		self.sourceCtrl.add_sub(index, subsource)

	def check_availability(self, subindex=None):
		"""Executed after post_add, and may occasionally be called.
		If a subindex is given then only check that subsource.
		
		This method updates the availability.
		
		Returns: List of changes in availability.
		
		SMB: Check if subsource exists and has music in the MPD database
		"""
		subsource_availability_changes = super(MySource,self).check_availability(subindex=subindex)
		return subsource_availability_changes

		
	# Returns a list of everything mounted on /media, but does not check if it has music.
	# Returned is 2-dimension list
	'''
	def __smb_getAll( self ):

		lst_mountpoints = get_mounts( fs='cifs' )

		if not lst_mountpoints:
			self.__printer(' > No SMB network shares found')
		else:
			# filter out everything that's not mounted on /media/PIHU_SMB
			# TODO: remove hardcoded path
			for i, mp in enumerate(lst_mountpoints):
				if not mp['mountpoint'].startswith('/media/PIHU_SMB'):
					del lst_mountpoints[i]
			
			# check if anything left
			if not lst_mountpoints:
				self.__printer(' > No SMB network shares found on /media/PIHU_SMB')
			else:				
				self.__printer(' > Found {0} share(s)'.format(len(lst_mountpoints)))
		
		return lst_mountpoints
	'''
	
	def Xinit( self, sourceCtrl ):
		self.__printer('Initializing...', level=15)
		# do a general media_check to find any mounted drives
		#media_check( label=None )
			
		# add all locations as configured
		arSmb = self.__smb_getAll()
		for mount in arSmb:
			if mount['spec'].startswith('//'):
				smbAddr = mount['spec']
				mountpoint = mount['mountpoint']
				self.__smb_add( mountpoint
						       ,smbAddr
						       ,sourceCtrl)

		return True

	def Xcheck( self, sourceCtrl, subSourceIx=None  ):
		self.__printer('Checking availability...')
		
		ix = sourceCtrl.index('name','smb')
		smb_source = sourceCtrl.source(ix)		
		original_availability_pri = smb_source['available']

		
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

		# stop, if nothing to check
		if not locations:
			self.__printer('No network shares available',LL_WARNING)
			if original_availability_pri != False:
				subsource_availability_changes.append({"index":ix,"available":False})
			return subsource_availability_changes
		
		# check mountpoint(s)
		for location in locations:
		
			# get mountpoint and mpd dir
			mountpoint = location[0]
			mpd_dir = location[1]
			original_availability = location[2]
			new_availability = None

			self.__printer('SMB folder: {0}'.format(mountpoint))
			if not os.listdir(mountpoint):
				self.__printer(" > SMB directory is empty.",LL_WARNING)
				new_availability = False
			else:
				self.__printer(" > SMB directory present and has files.",LL_INFO)
				
				if not self.mpdc.is_dbdir( mpd_dir ):
					self.__printer(" > Running MPD update for this directory.. ALERT! LONG BLOCKING OPERATION AHEAD...")
					self.mpdc.update_db( mpd_dir )
					if not self.mpdc.is_dbdir( mpd_dir ):
						self.__printer(" > Nothing to play marking unavailable...")
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
		
	
		#Check if wlan is up
		#TODO
		
		# ASSUME FOR NOW, THAT THE CONNECTIONS ARE CREATED BY THE SYSTEM, ON /media/PIHU_SMB,
		# SO WE ONLY NEED TO CHECK /media/PIHU_SMB...
		
		
		
		#See if we have smb location(s)
		#TODO

		#Check if any of those locations could be on our current network
		#TODO
		
		#Check if at least one stream is good
		#TODO

		#OVERRIDE
		#printer(' > Not implemented yet, presenting source as available ',level=LL_CRITICAL)
		#arSourceAvailable[6]=1
		#Sources.setAvailable('name','smb', True)

		return subsource_availability_changes

		
	def Xplay( self, sourceCtrl, position=None, resume={} ):
		self.__printer('Start playing (MPD)')
		
		#
		# variables
		#
		arIx = sourceCtrl.index_current()
		subsource = sourceCtrl.subsource( arIx[0], arIx[1] )
		sLocalMusicMPD = subsource['mpd_dir']

		#
		# load playlist
		#

		# populate playlist
		self.mpdc.pls_clear()
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
				sourceCtrl.set_available( ix, False, subSourceIx )
				pa_sfx(LL_ERROR)
				return False
			else:
				self.__printer(' > Found {0:s} tracks'.format(playlistCount))
		else:
			self.__printer(' > Found {0:s} tracks'.format(playlistCount))
		
		#
		# continue where left
		#
		
		# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
		
		if resume:
			playslist_pos = self.mpdc.lastKnownPos2( resume['file'], resume['time'] )	
		else:
			playslist_pos = {'pos': 1, 'time': 0}
		
		self.__printer(' > Starting playback')
		#mpc.playStart( str(playslist_pos['pos']), playslist_pos['time'] )
		subprocess.call(["mpc", "-q" , "stop"])
		subprocess.call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
		if playslist_pos['time'] > 0:
			self.__printer(' ...  Seeking to {0} sec.'.format(playslist_pos['time']))
			subprocess.call(["mpc", "-q" , "seek", str(playslist_pos['time'])])


		# double check if source is up-to-date
		
		# Load playlist directories, to enable folder up/down browsing.
		#mpc_get_PlaylistDirs()
		# Run in the background... it seems the thread stays active relatively long, even after the playlistdir array has already been filled.
	#	mpc_get_PlaylistDirs_thread = threading.Thread(target=mpc_get_PlaylistDirs)
	#	mpc_get_PlaylistDirs_thread.start()

		return True