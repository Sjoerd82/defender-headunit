#
# SOURCE PLUGIN: Streaming URL's
# Venema, S.R.G.
# 2018-04-03
#
# Plays Streaming URL's
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
		
		STREAM: Subsources for this source can be retrieved from the main configuration ('stream_groups')
		  *OR* (FUTURE), from a separate file (in case there many streams that would
		  otherwise make the configuration file too bloated.
		"""
		# subsource strategy: "subsources": "stream_groups" # NOT USED AT THE MOMENT #TODO
		if 'stream_groups' in sourceconfig:
			index = self.sourceCtrl.index('name',self.name)	#name is unique
			if index is None:
				print "Plugin {0} does not exist".format(self.name)
				return False
				
			order = 0
			for stream_group in sourceconfig['stream_groups']:
				streams = []
				for stream in stream_group['streams']:
					streams.append(stream['uri'])
				self.add_subsource( stream_group['group_name']
								   ,streams
								   ,order
								   ,index)
				order += 1
		return True

	def add_subsource(self, group_name, streams, order, index):
		subsource = {}
		subsource['displayname'] = stream_group['group_name']
		subsource['order'] = order
		subsource['mpd_streams'] = streams
		self.sourceCtrl.add_sub(index, subsource)

	def check_availability(self, subindex=None):
		"""Executed after post_add, and may occasionally be called.
		If a subindex is given then only check that subsource.
		
		This method updates the availability.
		
		Returns: List of changes in availability.
		
		SMB: Check if subsource exists and has music in the MPD database
		"""
		index = self.sourceCtrl.index('name',self.name)	#name is unique
		subsource_availability_changes = []
		stream_source = self.sourceCtrl.source(index)		
		original_availability = stream_source['available']
		
		#TODO!!
		sDirSave = "/mnt/PIHU_CONFIG"
		
		# Test internet connection
		connected = internet()
		if not connected:
			self.printer(' > Internet: [FAIL]')
			self.printer(' > Marking source not available')
			new_availability = False
		else:
			self.printer(' > Internet: [OK]')

		# See if we have streaming URL's
		streams_file = sDirSave + "/streams.txt"
		if os.path.isfile(streams_file):
			self.printer(' > Stream URL\'s: File found [OK]')
		else:
			self.printer(' > Stream URL\'s: File not found [FAIL]')
			self.printer(' > Marking source not available')
			new_availability = False

		# Check if at least one stream is good
		self.printer('Checking to see we have at least one valid stream')
		with open(streams_file,'r') as streams:
			for l in streams:
				uri = l.rstrip()
				if not uri[:1] == '#' and not uri == '':
					uri_OK = url_check(uri)					
					if uri_OK:
						self.printer(' > Stream [OK]: {0}'.format(uri))
						new_availability = True
					else:
						self.printer(' > Stream [FAIL]: {0}'.format(uri))
						new_availability = False

		if new_availability is not None and new_availability != original_availability:
			self.sourceCtrl.set_available( index, new_availability )
			subsource_availability_changes.append({"index":index,"available":new_availability})

		return subsource_availability_changes
	
	def play( self, subindex=None ):
		super(MySource,self).play()
				
		#
		# load playlist
		#
		
		# NOT ANYMORE - OR TODO: MPD playlist for local music *should* be updated by inotifywait.. but, it's a bit tricky, so test for it..

		# populate playlist
		self.mpc.playlistClear()
		self.mpc.playlistPop('stream',None)
		
		# check if succesful...
		playlistCount = self.mpc.playlistIsPop()
		if playlistCount == "0":
			self.printer(' > Nothing in the playlist, aborting...')
			pa_sfx(LL_ERROR)
			return False	
		else:
			self.printer(' .... . Found {0:s} items'.format(playlistCount))
			
		#
		# continue where left
		#
		
		#TODO!
		#playslist_pos = mpc.lastKnownPos( sLabel )
		
		self.printer(' > Starting playback')
		#call(["mpc", "-q" , "play", str(playslist_pos['pos'])])
		call(["mpc", "-q" , "play"])

		# double check if source is up-to-date
		# todo
		
		return True

	def stop( self ):
		super(MySource,self).stop()
		# save position and current file name for this drive
		self.mpc.mpc_save_pos_for_label( 'stream' )
		return True
		