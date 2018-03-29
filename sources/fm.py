#
# SOURCE PLUGIN: FM
# Venema, S.R.G.
# 2018-03-28
#
# Plays FM radio
#
# Extends SourcePlugin
#

from yapsy.IPlugin import IPlugin
from modules.hu_utils import *
from modules.source_plugin import SourcePlugin

# Station list
#  TODO: load/save. In configuration(?)
lFmStations = [ 96.40, 99.10, 101.20, 102.54 ]

#class PluginOne(IPlugin):
#	def print_name(self):
#		print "This is plugin 1"
		

class sourceClass(IPlugin,SourcePlugin):

	# __init__ is called by YAPSY, no room for additional parameters (?)
	#def __init__(self, logger, name, displayname):
	#def __init__(self):
	
		#self.displayname = 'FM'
		#self.logger=logging.getLogger('srcctrl')
		
		#super(LocalMusic, self).__init__(self.logger, self.name, self.displayname)
		#print('__INIT__ SOURCECLASS')
		#self.printer('A Source Class Init', level=LL_DEBUG)
		#SourcePlugin.__init__(self, logger, 'fm', 'FM')
	
	def init( self, plugin_name ):
		print("sourceClass (FM) init()")
		self.printer('Initializing...')
		self.name = plugin_name
		return True

	def uhm_subs(self, sourceCtrl):
		return True

	def check( self, sourceCtrl, subSourceIx=None  ):
		"""	Check source
		
			Checks to see if FM is available (SUBSOURCE INDEX will be ignored)
			Returns a list with dict containing changes in availability
			
			TODO: Will now simply return TRUE.
		"""
		self.printer('CHECK availability...')

		subsource_availability_changes = []
		new_availability = True
		
		ix = sourceCtrl.index('name','fm')	# source index
		fm_source = sourceCtrl.source(ix)		
		original_availability = fm_source['available']
		
		if new_availability is not None and new_availability != original_availability:
			sourceCtrl.set_available( ix, new_availability )
			subsource_availability_changes.append({"index":ix,"available":new_availability})
		
		return subsource_availability_changes
		
	def play( self, sourceCtrl, subSourceIx=None ):
		self.printer('Start playing FM radio...')
		return True	

	def stop( self ):
		self.printer('Stop CLASS!')
		return True
		
	def pause( self, mode ):
		self.printer('Pause. Mode: {0}'.format(mode))
		#TODO IMPLEMENT
		return True

	def random( self, mode ):
		self.printer('Random. Mode: {0}'.format(mode))
		#TODO IMPLEMENT
		return True

	def seekfwd( self ):
		self.printer('Seek FFWD')
		#TODO IMPLEMENT
		return True

	def seekrev( self ):
		self.printer('Seek FBWD')
		#TODO IMPLEMENT
		return True

	def update( self ):
		self.printer('Update not supported')
		return True

	def get_details():
		return False

	def get_state():
		return False

	def get_playlist():
		return False

	#def get_folders():

	def source_get_media_details():
		return False


	
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