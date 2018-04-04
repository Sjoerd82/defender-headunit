#
# SOURCE PLUGIN: Line-In
# Venema, S.R.G.
# 2018-04-03
#
# AUX / Line-In
#

#
# Extends SourcePlugin
#

from yapsy.IPlugin import IPlugin
from modules.hu_utils import *
from modules.source_plugin import SourcePlugin

class MySource(SourcePlugin,IPlugin):

	def __init__(self):
		super(MySource,self).__init__()

	def on_add(self, sourceconfig):
		"""Executed after a source is added by plugin manager.
		Executed by: hu_source.load_source_plugins().
		Return value is not used.
		
		LINE: Currently only ONE LINE-IN supported.
		"""
		index = self.sourceCtrl.index('name',self.name)	#name is unique
		if index is None:
			print "Plugin {0} does not exist".format(self.name)
			return False
		
		self.add_subsource(index,self,index)
		return True
		
	def add_subsource(self, index):
		subsource = {}
		subsource['displayname'] = 'AUX'
		self.sourceCtrl.add_sub( index, subsource )

	def get_details(self, **kwargs ):
		details = {}
		track = copy.deep_copy(self.empty_track)
		track['display'] = "AUX"
		details['state'] = self.state
		return details
