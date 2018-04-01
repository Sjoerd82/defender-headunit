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
	
	def play (self, **kwargs):
		self.printer('Start playing FM radio...')
		self.state['state'] = 'playing'
		return True	

	def stop( self, **kwargs ):
		self.printer('Stop CLASS!')
		self.state['state'] = 'stopped'
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

	def get_state(self, **kwargs ):
		self.printer('State ?')
		return self.state
	
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