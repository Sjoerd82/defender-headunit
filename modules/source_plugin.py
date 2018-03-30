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
		
	def init(self, plugin_name, logger):
		self.name = plugin_name
		self.logger = logger
		return True

	def post_add(self, sourceCtrl, sourceconfig):
		pass

	def check(self, sourceCtrl, subSourceIx=None):
		"""	Check source
		
			Returns all subsources as available
			
		"""
		print "DEBUG"
		print self.name

		ix = sourceCtrl.index('name',self.name)
		subsources = sourceCtrl.subsource_all(ix)
		
		print ix
		print subsources
		
		
		if subsources is None:
			return []
		
		avchg = []
		for i in range(len(subsources)):
			print i
			avchg_subsource = {}
			avchg_subsource['index'] = ix
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
		self.printer('Not implemented',level=LL_DEBUG)
		
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
		
	def printer(self, message, level=LL_INFO, tag=None):
		if tag is None:
			tag = self.name
		
		if self.logger is None:
			print("[{0}] {1}".format(tag,message))
		else:
			self.logger.log(level, message, extra={'tag': tag})
