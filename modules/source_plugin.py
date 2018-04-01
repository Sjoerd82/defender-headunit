#
# Source Plugin base class
# Venema, S.R.G.
# 2018-03-28
#
# This BASE CLASS contains shared code and minimal implementation
# of a source plugin.
#
DEFAULT_CONFIG_FILE = '/etc/configuration.json'

from modules.hu_utils import *

class SourcePlugin(object):

	def __init__(self):
		self.name = None
		self.logger = None
		
		self.state = {}
		self.state['state'] = None
		self.state['random'] = None
		self.state['repeat'] = None
		
	def init(self, plugin_name, logger):
		self.name = plugin_name
		self.logger = logger
		return True

	def post_add(self, sourceCtrl, sourceconfig):
		pass

	def check(self, **kwargs):
		"""	Check source
		Returns LIST marking all subsources as available
		"""
		
		if 'SrcCtrl' in kwargs:
			SrcCtrl = kwargs['SrcCtrl']
		else:
			return []
		
		
		if 'index' in kwargs:
			index = kwargs['index']
		else:
			index = SrcCtrl.index('name',self.name)
			
		subsources = SrcCtrl.subsource_all(index)
		if subsources is None:
			return []	
		
		avchg = []
		for i in range(len(subsources)):
			avchg_subsource = {}
			avchg_subsource['index'] = index
			avchg_subsource['subindex'] = i
			avchg_subsource['available'] = True
			avchg.append(avchg_subsource)
		
		return avchg

	def configuration(self, name):
		if name is None:
			return None
		
		config = {}
		
		# return configuration (from json config file)
		plugindir = "sources"	#TODO
		configFileName = os.path.join(plugindir,self.name+'.json')
		if not os.path.exists( configFileName):
			printer('Configuration not found: {0}'.format(configFileName))
		else:
			# load source configuration file
			jsConfigFile = open( configFileName )
			config=json.load(jsConfigFile)
		
		config['name'] = name		
		
		# load main configuration
		main_configuration = configuration_load('srctrl', DEFAULT_CONFIG_FILE)
		if 'source_config' in main_configuration and name in main_configuration['source_config']:
			config.update(main_configuration['source_config'][name])
			
		return config
			
	def play(self, **kwargs):
		# not implemented
		return False
		
	def stop(self, **kwargs):
		# not implemented
		return False
		
	def next(self, **kwargs):		
		# not implemented
		return False
		
	def prev(self, **kwargs):
		# not implemented
		return False

	def pause(self, **kwargs):
		# not implemented
		return False

	def random(self, **kwargs):
		# not implemented
		return False

	def seekfwd(self, **kwargs):
		# not implemented
		return False

	def seekrev(self, **kwargs):
		# not implemented
		return False

	def update(self, **kwargs):
		# not implemented
		return False

	def get_state(self, **kwargs ):
		return self.state

	def get_details(self, **kwargs):
		details = {}
		track = {'display':None,'rds':None,'artist':None,'composer':None,'performer':None,'album':None,'albumartist':None,'title':None,'length':None,'elapsed':None,'track':None,'disc':None,'genre':None,'date':None}
		details['track'] = track
		details['state'] = self.state
		return details
		
	# ------------------------
	# todo:


	def get_playlist():
		return False

	def get_folders():
		return False

	def source_get_media_details():
		return False
		
	def printer(self, message, level=LL_INFO, tag=None):
		if tag is None:
			tag = self.name
		
		if self.logger is None:
			print("[{0}] {1}".format(tag,message))
		else:
			self.logger.log(level, message, extra={'tag': tag})
