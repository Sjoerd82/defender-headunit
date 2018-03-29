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

	logger = None

	#def __init__(self, logger, name, displayname):
	def __init__(self):
		
		self.name = None
		#self.logger = None
		
		# recreate a logger #TODO, get it from upstream!
		"""
		self.logger=logging.getLogger('srctrl')
		self.logger.setLevel(logging.DEBUG)
		ch = logging.StreamHandler()						# create console handler
		ch.setLevel(logging.DEBUG)								# set log level
		self.logger.addHandler(ch)
		"""

	#def add_logger(self, logger):
	#	self.logger = logger
		
	def new_init( self, name ):
		self.name = name
		return True

	def printer(self, message, level=LL_INFO, tag=None):
		#print "PRINTER {0}: {1}".format(self.logger,message)
		if tag is None:
			tag = self.name
		self.logger.log(level, message, extra={'tag': tag})
	
	def configuration(self, name):
		print("LOADING SOURCE CONFIGURATION")
		minimal_config = {}
		minimal_config['name'] = name
		minimal_config['displayname'] = name
		minimal_config['order'] = 0
		minimal_config['enabled'] = True
		minimal_config['available'] = False
		# return configuration (from json config file)
		plugindir = "sources"	#TODO
		configFileName = os.path.join(plugindir,self.name+'.json')
		if not os.path.exists( configFileName):
			printer('Configuration not found: {0}'.format(configFileName))
			return minimal_config
		
		# load source configuration file
		jsConfigFile = open( configFileName )
		config=json.load(jsConfigFile)
		
		config['name'] = name		
		# TODO: merge minimal_config ?
		return config
	
	def init(self, **kwargs):
		self.printer('Initializing...!')

	def check(self, sourceCtrl, subSourceIx=None):
		#self.printer('Checking availability...',level=LL_DEBUG)
		print "INIT @ SourcePlugin"
		
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