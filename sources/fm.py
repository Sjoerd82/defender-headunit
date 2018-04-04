#
# SOURCE PLUGIN: FM
# Venema, S.R.G.
# 2018-04-01
#
# Plays FM radio
#

#
# Extends SourcePlugin
#

from yapsy.IPlugin import IPlugin
from modules.hu_utils import *
from modules.source_plugin import SourcePlugin

class MySource(SourcePlugin,IPlugin):
	"""
	__init__ is called by YAPSY, no room for additional parameters: logger, name, displayname
	Place SourcePlugin before IPlugin, so that super() call __init_ from SourcePlugin, not from IPlugin.
	"""
	
	def __init__(self):
		super(MySource,self).__init__()
	
	#def on_init
	#	super(MySource, self).init(plugin_name,sourceCtrl,logger)
	#	return True
	
	def on_add(self, sourceCtrl, sourceconfig):
		"""Executed after a source is added by plugin manager.
		Executed by: hu_source.load_source_plugins().
		Return value is not used.
		
		FM: No subsources.
		"""
		index = sourceCtrl.index('name',self.name)	#name is unique
		if index is None:
			print "Plugin {0} does not exist".format(self.name)
			return False
		
		self.add_subsource(index,self,index)
		return True

	def add_subsource(self, sourceCtrl, index):
		subsource = {}
		subsource['displayname'] = 'FM'
		sourceCtrl.add_sub( index, subsource )
		
	def play (self, **kwargs):
		super(MySource,self).play()
		self.printer('Start playing FM radio...')
		return True	

	def stop( self, **kwargs ):
		super(MySource,self).stop()
		return True
		
	def pause( self, mode, **kwargs ):
		self.printer('Pause. Mode: {0}'.format(mode))
		#TODO IMPLEMENT
		return True

	def random( self, mode, **kwargs ):
		self.printer('Random. Mode: {0}'.format(mode))
		#TODO IMPLEMENT
		return True

	def seekfwd( self, **kwargs ):
		self.printer('Seek FFWD')
		#TODO IMPLEMENT
		return True

	def seekrev( self, **kwargs ):
		self.printer('Seek FBWD')
		#TODO IMPLEMENT
		return True

	def get_details(self, **kwargs ):
		self.printer('Details ?')
		details = {}
		track = copy.deep_copy(self.empty_track)
		track['display'] = "Playing FM"
		details['track'] = track
		details['state'] = self.state
		return details
	
def fm_popMenu():
	newMenu = []
	if lFmStations == []:
		newMenu.append( { "entry":"No saved stations" } )
		newMenu.append( { "entry":"Scan for stations", "run":"fm_scan" } )
	else:
		for station in lFmStations:
			newStation = { "entry":str(station)+'FM', "sub":None, "run":"fm_play", "params":str(station) }
			newMenu.append(newStation)
	return newMenu