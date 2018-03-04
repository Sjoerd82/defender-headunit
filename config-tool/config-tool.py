#!/usr/bin/python

# Headunit system config tool for busybox
#
# Author: Sjoerd Venema
# License: tbd
#

#********************************************************************************
#
# Version
#
#from version import __version__
#

#********************************************************************************
#
# Logging
#
import logging
import logging.config
import datetime
import os
logger = None
from hu_logger import *

#********************************************************************************
#
# Parse command line arguments
#
#

import os
import argparse



# ********************************************************************************
#
# load json source configuration
import os
import json
# load json in ordered dict to save to file in same order
from collections import OrderedDict
#import hu_settings

def configuration_load( configfile, defaultconfig=None ):

	# keep track if we restored the config file
	
	# use the default from the config dir, in case the configfile is not found (first run)

	# open configuration file (restored or original) and Try to parse it
	jsConfigFile = open(configfile)
	try:
		#config=json.load(jsConfigFile)
		config=json.load(jsConfigFile, object_pairs_hook=OrderedDict)
	except:
		config = None
		printer('Loading/parsing {0}: [FAIL]'.format(configfile) ,LL_CRITICAL, tag='CONFIG')
		# if we had not previously restored it, try that and parse again

	return config


# ********************************************************************************
# Output wrapper
#
def printer( message, level=20, continuation=False, tag='SYSTEM' ):

	print(message)

	#TODO: test if headunit logger exist...
	#if continuation:
	#	myprint( message, level, '.'+tag )
	#else:
	#	myprint( message, level, tag )

# ********************************************************************************
# Config writers
#

def write_config_dbus( config ):
	printer("Creating: {0}".format(config['location']))
	with open( config['location'], 'w' ) as outfile:
		outfile.write('<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"\n')
		outfile.write(' "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">\n')
		outfile.write('<busconfig>\n')
  		outfile.write('  <policy context="default">\n')
		for service in config['services']:
			outfile.write('    <allow own="{0}"/>\n'.format(service))
		outfile.write('  </policy>\n')
		outfile.write('</busconfig>')

# the wpa_supplicant config is a tricky one as it requires quotes for text fields only.
def write_config_wpa( config ):
	printer("Creating: {0}".format(config['location']))
	
	group = "={"
	delim = "="
	quoted_fields=("ssid")
	
	with open( config['location'], 'w' ) as outfile:
		for key,value in config.items():
			if isinstance(value, list):				
				for lon in value:
					outfile.write('{0}{2}\n'.format(key,delim,group))
					for listkey, listval in lon.items():
						if listkey in quoted_fields:
							quotes = '"'
						else:
							quotes = ''
						outfile.write('  {1}{0}{3}{2}{3}\n'.format(delim,listkey,listval,quotes))
					outfile.write('}\n')
			elif not key == 'location':
				if value:
					if key in quoted_fields:
						quotes = '"'
					else:
						quotes = ''
					outfile.write('{1}{0}{3}{2}{3}\n'.format(delim,key,value,quotes))
				else:
					outfile.write('{0}\n'.format(key))

def write_config_smb( config ):
	printer("Creating: {0}".format(config['location']))
	with open( config['location'], 'w' ) as outfile:

		outfile.write('[global]\n')
		for key,value in config['global'].items():
			outfile.write('  {0} = {1}\n'.format(key,value))
			
		for key,value in config['shares'].items():
			outfile.write('\n[{0}]\n'.format(key))
			for listkey,listval in config['shares'][key].items():
				outfile.write('  {0} = {1}\n'.format(listkey,listval))

def write_config_resolv( config ):
	with open( config['location'], 'w' ) as outfile:
		for nameserver in config['nameservers']:
			outfile.write('nameserver {0}'.format(nameserver))

def write_config_generic( config, delim="=", group="={", quotes="" ):
	printer("Creating: {0}".format(config['location']))
	with open( config['location'], 'w' ) as outfile:
		for key,value in config.items():
			if isinstance(value, list):				
				for lon in value:
					if (group == "={" or group == " {") :
						outfile.write('{0}{2}\n'.format(key,delim,group))
					for listkey, listval in lon.items():
						outfile.write('  {1}{0}{3}{2}{3}\n'.format(delim,listkey,listval,quotes))
					if (group == "={" or group == " {") :
						outfile.write('}\n')
			elif not key == 'location':
				if value:
					outfile.write('{1}{0}{3}{2}{3}\n'.format(delim,key,value,quotes))
				else:
					outfile.write('{0}\n'.format(key))


# ********************************************************************************
# Main Program
#

def main():

	#if environ.get('HU_CONFIG_FILE') is not None:
	env_config_file = os.getenv('HU_CONFIG_FILE')

	parser = argparse.ArgumentParser(description='Configure Linux environment')
	parser.add_argument('--system','-s', required=False, action='store', help='BusyBox,...', choices=['BusyBox'], metavar='BusyBox')
	if env_config_file:
		parser.add_argument('--config','-c', required=False, action='store', help='Configuration file', default=env_config_file)
	else:
		parser.add_argument('--config','-c', required=True, action='store', help='Configuration file')
	parser.add_argument('--all',  required=False, action='store_true', help='Generate all files')
	parser.add_argument('--dbus', required=False, action='store_true', help='Generate dbus configuration')
	parser.add_argument('--wpa',  required=False, action='store_true', help='Generate wpa_supplicant.conf file')
	parser.add_argument('--hapd', required=False, action='store_true', help='Generate hostapd.conf file')
	parser.add_argument('--dnsm', required=False, action='store_true', help='Generate dnsmasq.conf file')
	parser.add_argument('--mpd',  required=False, action='store_true', help='Generate mpd.conf file')
	parser.add_argument('--smb',  required=False, action='store_true', help='Generate samba.conf file')


	args = parser.parse_args()

	arg_system = args.system
	arg_config = args.config
	arg_all  = args.all
	arg_dbus = args.dbus
	arg_wpa  = args.wpa
	arg_hapd = args.hapd
	arg_dnsm = args.dnsm
	arg_mpd  = args.mpd
	arg_smb  = args.smb

	def validate_config( ci, required_fields ):
		if ci in configuration['system_configuration']:
			if not all (k in configuration['system_configuration'][ci] for k in required_fields):
				return False
				printer('Configuration for {0} is missing required fields'.format(ci))
		else:
			printer('No configuration for {0}'.format(ci))
			return False
			
		return True
	
	printer('Loading: {0}'.format( arg_config ))
	configuration = configuration_load( arg_config )
	
	if 'system_configuration' not in configuration:
		printer('Configuration file does not contain a system configuration.')
		exit()
	else:
		printer('System configuration found...')
	
	if arg_all:
		arg_dbus = True
		arg_wpa  = True
		arg_hapd = True
		arg_dnsm = True
		arg_resv = True
		arg_mpd  = True
		arg_smb  = True

	if arg_dbus:
		if validate_config( 'dbus', ['location','services'] ):
			write_config_dbus( configuration['system_configuration']['dbus'] )
		else:
			printer('DBus: Invalid Config')
							
	if arg_wpa:
		if validate_config( 'wpa_supplicant', ['location','network'] ):
			write_config_wpa( configuration['system_configuration']['wpa_supplicant'])
		else:
			printer('WPA: Invalid Config')

	if arg_hapd:
		if validate_config( 'hostapd', ['location','interface','driver','ssid','channel'] ):
			write_config_generic( configuration['system_configuration']['hostapd'], '=', '={' )
		else:
			printer('hostapd: Invalid Config')

	if arg_dnsm:
		if validate_config( 'dnsmasq', ['location','interface'] ):
			write_config_generic( configuration['system_configuration']['dnsmasq'], '=', '={' )
		else:
			printer('dnsmasq: Invalid Config')

	if arg_mpd:
		if validate_config( 'mpd', ['location','music_directory','audio_output'] ):
			write_config_generic( configuration['system_configuration']['mpd'], '\t', ' {', '"' )
		else:
			printer('mpd: Invalid Config')

	if arg_smb:
		if validate_config( 'smb', ['location','global','shares'] ):
			write_config_smb( configuration['system_configuration']['smb'] )
		else:
			printer('smb: Invalid Config')

		
if __name__ == '__main__':
	main()
