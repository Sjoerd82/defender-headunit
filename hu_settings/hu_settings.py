
from hu_utils import *
import os
import json
import pickle

# ********************************************************************************
# Output wrapper
#

def printer( message, level=20, continuation=False, tag='STTNGS' ):
	#TODO: test if headunit logger exist...
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

# ********************************************************************************
# Load JSON configuration
#
def configuration_load( configfile, defaultconfig=None ):

	# use the default from the config dir, if not found
	#not defaultconfig==None and
	if not os.path.exists(configfile) and os.path.exists(defaultconfig):
		printer('Configuration not present (first run?); copying default')
		os.copy(defaultconfig,configfile)

	try:
		jsConfigFile = open(configfile)
		config=json.load(jsConfigFile)
		return config
	except:
		printer('Loading/parsing {0}: [FAIL]'.format(configfile),LL_CRITICAL)

def configuration_save( configfile, configuration ):
	printer('Saving Configuration')
	try:
		json.dump( configuration, open( configfile, "wb" ) )
	except:
		printer(' > ERROR saving configuration',LL_CRITICAL,True)
		pa_sfx(LL_ERROR)
			
def settings_save( sJsonFile, dSettings ):
	printer('Saving settings')
	try:
		json.dump( dSettings, open( sJsonFile, "wb" ) )
	except:
		printer(' > ERROR saving settings',LL_CRITICAL,True)
		pa_sfx(LL_ERROR)
	
def settings_load( sJsonFile, dDefaultSettings ):
	printer('Loading previous settings')
	try:
		jsConfigFile = open(sJsonFile)
		jSettings = json.load(jsConfigFile)
		dSettings = jSettings
	except:
		printer(' ......  Loading headunit.p failed. First run? - Creating headunit.p with default values.')
		#assume: fails because it's the first time and no settings saved yet? Setting default:
		json.dump( dDefaultSettings, open( sJsonFile, "wb" ) )
		return dDefaultSettings

	#VOLUME
	#check if the value is valid
	if dSettings['volume'] < 0 or dSettings['volume'] > 100:
		dSettings['volume'] = 40
		pickle.dump( dSettings, open( sPickleFile, "wb" ) )
		printer(' ......  No setting found, defaulting to 40%')
	elif dSettings['volume'] < 30:
		printer(' ......  Volume too low, defaulting to 30%')
		dSettings['volume'] = 30
	else:
		printer(' ......  Volume: {0:d}%'.format(dSettings['volume']))
	
	#SOURCE
	printer(' ......  Source: {0}'.format(dSettings['source']))
	#MEDIASOURCE
	printer(' ......  Media source: {0}'.format(dSettings['mediasource']))
	#MEDIALABEL
	printer(' ......  Media label: {0}'.format(dSettings['medialabel']))
	
	printer('\033[96m ......  DONE\033[00m')
	return dSettings

def getSourceConfig( sourceName ):
	CONFIG_FILE = '/mnt/PIHU_CONFIG/configuration.json'
	configuration = configuration_load( CONFIG_FILE )
	return configuration['source_config'][sourceName]

def getPluginConfig( pluginName ):
	CONFIG_FILE = '/mnt/PIHU_CONFIG/configuration.json'
	configuration = configuration_load( CONFIG_FILE )
	return configuration['plugins_other'][pluginName]

# ********************************************************************************
# DEPRECATED --- NOW USING JSON
# Save & Load settings, using pickle
#

def p_settings_save( sPickleFile, dSettings ):
	printer('Saving settings')
	try:
		pickle.dump( dSettings, open( sPickleFile, "wb" ) )
	except:
		printer(' > ERROR saving settings',LL_CRITICAL,True)
		pa_sfx(LL_ERROR)

def p_settings_load( sPickleFile, dSettings ):
	printer('Loading previous settings')
	try:
		dSettings = pickle.load( open( sPickleFile, "rb" ) )
	except:
		printer(' ......  Loading headunit.p failed. First run? - Creating headunit.p with default values.')
		#assume: fails because it's the first time and no settings saved yet? Setting default:
		pickle.dump( dSettings, open( sPickleFile, "wb" ) )

	#VOLUME
	#check if the value is valid
	if dSettings['volume'] < 0 or dSettings['volume'] > 100:
		dSettings['volume'] = 40
		pickle.dump( dSettings, open( sPickleFile, "wb" ) )
		printer(' ......  No setting found, defaulting to 40%')
	elif dSettings['volume'] < 30:
		printer(' ......  Volume too low, defaulting to 30%')
		dSettings['volume'] = 30
	else:
		printer(' ......  Volume: {0:d}%'.format(dSettings['volume']))
	
	#SOURCE
	printer(' ......  Source: {0}'.format(dSettings['source']))
	#MEDIASOURCE
	printer(' ......  Media source: {0}'.format(dSettings['mediasource']))
	#MEDIALABEL
	printer(' ......  Media label: {0}'.format(dSettings['medialabel']))
	
	printer('\033[96m ......  DONE\033[00m')