
from hu_utils import *

#file operations:
import os
import shutil

#json and pickle:
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
# Restore default configuration
#
def configuration_restore( configfile, defaultconfig ):
	if os.path.exists(defaultconfig):
		shutil.copy(defaultconfig,configfile)
		return True

# ********************************************************************************
# Load JSON configuration
#
def configuration_load( configfile, defaultconfig=None ):

	# keep track if we restored the config file
	restored = False
	
	# use the default from the config dir, in case the configfile is not found (first run)
	if not os.path.exists(configfile) and os.path.exists(defaultconfig):
		printer('Configuration not present (first run?); copying default', tag='CONFIG')
		restored = configuration_restore( configfile, defaultconfig )
		if not restored:
			printer('Restoring configuration {0}: [FAIL]'.format(defaultconfig), LL_CRITICAL, tag='CONFIG')
			return None

	# open configuration file (restored or original) and Try to parse it
	jsConfigFile = open(configfile)
	try:
		config=json.load(jsConfigFile)
	except:
		printer('Loading/parsing {0}: [FAIL]'.format(configfile) ,LL_CRITICAL, tag='CONFIG')
		# if we had not previously restored it, try that and parse again
		if not restored:
			printer('Restoring default configuration', tag='CONFIG')
			configuration_restore( configfile, defaultconfig )
			jsConfigFile = open(configfile)
			config=json.load(jsConfigFile)
			return config
		else:
			printer('Loading/parsing restored configuration failed!'.format(configfile) ,LL_CRITICAL, tag='CONFIG')
			return None

	# not sure if this is still possible, but let's check it..
	if config == None:
		printer('Loading configuration failed!'.format(configfile) ,LL_CRITICAL, tag='CONFIG')
	else:
		printer('Loading configuration OK'.format(configfile), tag='CONFIG')
	
	return config

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