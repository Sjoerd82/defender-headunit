#
# SOURCE PLUGIN: Local Music
# Venema, S.R.G.
# 2018-03-27
#
# Plays local music folder(s), as defined in the main configuration.
#

#
# Extends MPDSOURCEPLUGIN
#

from yapsy.IPlugin import IPlugin
from modules.hu_utils import *
from modules.hu_settings import getSourceConfig
from modules.source_plugin_mpd import MpdSourcePlugin

class MySource(MpdSourcePlugin,IPlugin):
	# the name of the class doesn't matter (?)
	# functions are searched Left-to-Right

	def __init__(self):
		super(MySource,self).__init__()
		self.index = None

	# TODO: CAN WE LEAVE THIS OUT? WILL THEN EXECUTE THE on_init on the derived class, right?
	def on_init(self, plugin_name, sourceCtrl, logger=None):
		super(MySource, self).init(plugin_name,logger)	# Executes init() at MpdSourcePlugin
		return True

	def on_add(self, sourceCtrl, sourceconfig):
		"""Executed after a source is added by plugin manager.
		Executed by: hu_source.load_source_plugins().
		Return value is not used.
		
		LOCMUS: Add predefined subsources
		Subsources for this source are pre-defined in the main configuration ('local_media').
		"""
		self.index = sourceCtrl.index('name',self.name)	#name is unique
		if self.index is None:
			self.printer("Plugin {0} does not exist".format(self.name),level=LL_ERROR)
			return False
		
		if 'local_media' in sourceconfig:

			for local_media in sourceconfig['local_media']:
				mountpoint = local_media['mountpoint']
				mpd_dir = local_media['mpd_dir']
				self.add_subsource(mountpoint, mpd_dir, sourceCtrl)

		return True

	def add_subsource(self, mountpoint, mpd_dir, sourceCtrl):
		subsource = {}
		subsource['displayname'] = 'local: ' + mountpoint
		subsource['mountpoint'] = mountpoint
		subsource['mpd_dir'] = mpd_dir
		subsource['label'] = mpd_dir
		sourceCtrl.add_sub( self.index, subsource )

	def check_availability( self, subindex=None ):
		"""Executed after post_add, and may occasionally be called.
		If a subindex is given then only check that subsource.
		
		This method updates the availability.
		
		Returns: List of changes in availability.
		
		LOCMUS: Check if local directory exists and has music in the MPD database
		"""
		locations = []							# list of tuples; index: 0 = mountpoint, 1 = mpd dir, 2 = availability.
		subsource_availability_changes = []		# list of changes
		
		if subindex is None:
			subsources = sourceCtrl.subsource_all( self.index )
			i = 0
		else:
			subsources = list(sourceCtrl.subsource( self.index, subindex ))
			i = subindex
		
		for subsource in subsources:
			mountpoint = subsource['mountpoint']			
			cur_availability = subsource['available']
			self.printer('Checking local folder: {0}, current availability: {1}'.format(mountpoint,cur_availability))
			new_availability = check_mpddb_mountpoint(mountpoint, createdir=True, waitformpdupdate=True)
			self.printer('Checked local folder: {0}, new availability: {1}'.format(mountpoint,new_availability))
			
			if new_availability is not None and new_availability != cur_availability:
				subsource_availability_changes.append({"index":self.index,"subindex":i,"available":new_availability})			
			
			i += 1
		
		return subsource_availability_changes