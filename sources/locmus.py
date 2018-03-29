#
# SOURCE PLUGIN: Local Music
# Venema, S.R.G.
# 2018-03-27
#
# Plays local music folder(s), as defined in the main configuration.
# Extends SOURCEPLUGIN and MPDSOURCEPLUGIN
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

	def init(self, plugin_name, logger=None):
		super(MySource, self).init(plugin_name,logger)
		"""	At this point, the source has *not* been added yet, and thus no index is available!		
		"""
		print("LocalMusic (locmus) init()")
		print self.name
		print self.logger
		
		#self.name = name
		#MpdSourcePlugin.__init__(self,self.logger)

	def post_add(self, sourceCtrl, sourceconfig):

		def locmus_add( self, label, dir, mpd_dir, sourceCtrl ):

			#TODO:
			mpd_musicdir = '/media'		

			# get index (name is unique)
			ix = sourceCtrl.index('name','locmus')
			if ix is None:
				print "Plugin {0} does not exist".format('locmus')
				return False
			# construct the subsource
			subsource = {}
			subsource['name'] = 'locmus'
			subsource['displayname'] = 'local: ' + dir
			subsource['order'] = 0			# no ordering
			subsource['mountpoint'] = dir
			subsource['mpd_dir'] = mpd_dir
			subsource['label'] = label
			#subsource['uuid'] = None		# not relevant for local sources

			sourceCtrl.add_sub( ix, subsource )
		
		# get source configuration from main configuration
		#locmusConfig = getSourceConfig('locmus')
		
		# add all locations as configured
		#for location in locmusConfig:
		
		for subsource in sourceconfig['subsources']:
			locmus_add( subsource['label']
					   ,subsource['musicdir']
					   ,subsource['musicdir_mpd']
					   ,sourceCtrl )

				
	# Source Check: Return True/False (available/not available)
	# Optionally, provide list of mountpoint(s) to check
	#def locmus_check( sourceCtrl, mountpoint=None ):
	def check( self, sourceCtrl, subSourceIx=None ):
		super(MySource, self).check(sourceCtrl, subSourceIx)
		"""	Check source
		
			Checks all configured mountpoints
			if SUBSOURCE INDEX given, will only check mountpoint of that subsource index.
			Returns a list with dict containing changed subsources
		
			TODO: check if new mountpoints were added in the configuration.
		"""
		print "CHECK @ LocalMusic"
		ix = sourceCtrl.index('name','locmus')	# source index
		locations = []							# list of tuples; index: 0 = mountpoint, 1 = mpd dir, 2 = availability.
		subsource_availability_changes = []		# list of changes
		
		if subSourceIx is None:
			subsources = sourceCtrl.subsource_all( ix )
			for subsource in subsources:
				locations.append( (subsource['mountpoint'], subsource['mpd_dir'], subsource['available']) )
			ssIx = 0
		else:
			subsource = sourceCtrl.subsource( ix, subSourceIx )
			locations.append( (subsource['mountpoint'], subsource['mpd_dir'], subsource['available']) )
			ssIx = subSourceIx

		# check mountpoints
		subsource_availability_changes = self.check_mpd(locations, ix, ssIx)
		
		return subsource_availability_changes


		
	