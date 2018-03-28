#
# Source Plugin base class
# Venema, S.R.G.
# 2018-03-28
#
# This BASE CLASS contains shared code and minimal implementation
# of a source plugin.
#

from modules.hu_utils import *

class SourcePlugin(object):

	def __init__(self, logger, name, displayname):
		super(SourcePlugin, self).__init__(logger, name, displayname)
		print('__INIT__ BASESOURCECLASS')
		self.logger = logger
		self.name = name
		self.displayname = displayname
		self.printer('C Base Source Class Init', level=LL_DEBUG)

	def printer(self, message, level=LL_INFO, tag=None):
		if tag is None:
			tag = self.name
		self.logger.log(level, message, extra={'tag': tag})
	
	def configuration():
		minimal_config = {}
		minimal_config['name'] = self.name
		minimal_config['displayname'] = self.displayname
		minimal_config['order'] = 0
		# return configuration (from json config file)
		plugindir = "sources"
		configFileName = os.path.join(plugindir,self.name+'.json')
		if not os.path.exists( configFileName):
			printer('Configuration not found: {0}'.format(configFileName))
			return minimal_config
		
		# load source configuration file
		jsConfigFile = open( configFileName )
		config=json.load(jsConfigFile)
		
		# test if name is unique?
		# #TODO

		# TODO: merge minimal_config ?
		return config
	
	def init(self, sourceCtrl):
		self.printer('Initializing...',level=LL_DEBUG)

	def check(self, sourceCtrl, subSourceIx=None):
		self.printer('Checking availability...',level=LL_DEBUG)
		
	def play(self, sourceCtrl, resume={}):
		self.printer('Not implemented',level=LL_DEBUG)
		
	def stop(self):
		self.printer('Not implemented',level=LL_DEBUG)
		
	def next(self):
		self.printer('Not implemented',level=LL_DEBUG)
		
	def prev(self):
		self.printer('Not implemented',level=LL_DEBUG)

	def pause(self, mode):
		self.printer('Not implemented',level=LL_DEBUG)

	def random(self, mode):
		self.printer('Not implemented',level=LL_DEBUG)

	def seekfwd(self):
		self.printer('Not implemented',level=LL_DEBUG)

	def seekrev(self):
		self.printer('Not implemented',level=LL_DEBUG)

	def update(self, location):
		self.printer('Not implemented'',level=LL_DEBUG)
		
	def get_details():
		return False

	def get_state():
		return False

	def get_playlist():
		return False

	def get_folders():
		return False

	def source_get_media_details():
		return False