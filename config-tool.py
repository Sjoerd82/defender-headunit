#!/usr/bin/python

#
# Headunit system config tool for busybox
# Venema, S.R.G.
# 2018-03-23
#
# Uses the "SYSTEM_CONFIGURATION" section from configuration.json to 
# configure system configuration files.
#

import sys

#********************************************************************************
# Version
#
from version import __version__

#********************************************************************************
# Logging
from logging import getLogger

#********************************************************************************
# Headunit modules
from modules.hu_utils import *

# ********************************************************************************
# load json source configuration
import os
import json
from collections import OrderedDict		# load json in ordered dict to save to file in same order

DESCRIPTION = "Configure Linux environment"
LOG_TAG = 'CFIGTL'
DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_LOG_LEVEL = LL_INFO

logger = None			# logging
args = None				# command line arguments
configuration = None	# configuration

# ********************************************************************************
# Output wrapper
#
def printer(message, level=20, tag='CONFIG'):
	print(message)


# ********************************************************************************
# Configuration loader
#
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


def verbose_before(filename):
	printer("Creating: {0}".format(filename))
	if args.v:
		printer("--Current configuration:----------------")
		with open(filename, 'rb' ) as cfg_file:
			for line in cfg_file:
				sys.stdout.write(line)	# because print() adds a line ending

def verbose_after(filename):
	if args.v:
		printer("--New configuration:--------------------")
		with open(filename, 'rb' ) as cfg_file:
			for line in cfg_file:
				sys.stdout.write(line)	# because print() adds a line ending
	
# ********************************************************************************
# Config writers
#
def write_config_dbus( config ):

	verbose_before(config['location'])
	with open( config['location'], 'w' ) as outfile:
		outfile.write('<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"\n')
		outfile.write(' "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">\n')
		outfile.write('<busconfig>\n')
  		outfile.write('  <policy context="default">\n')
		for service in config['services']:
			outfile.write('    <allow own="{0}"/>\n'.format(service))
		outfile.write('  </policy>\n')
		outfile.write('</busconfig>\n')
	verbose_after(config['location'])

# the wpa_supplicant config is a tricky one as it requires quotes for text fields only.
def write_config_wpa( config ):
	group = "={"
	delim = "="
	quoted_fields=("ssid")
	
	verbose_before(config['location'])
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
	verbose_after(config['location'])
	
def write_config_smb( config ):
	verbose_before(config['location'])
	with open( config['location'], 'w' ) as outfile:

		outfile.write('[global]\n')
		for key,value in config['global'].items():
			outfile.write('  {0} = {1}\n'.format(key,value))
			
		for key,value in config['shares'].items():
			outfile.write('\n[{0}]\n'.format(key))
			for listkey,listval in config['shares'][key].items():
				outfile.write('  {0} = {1}\n'.format(listkey,listval))
	verbose_after(config['location'])

def write_config_resolv( config ):
	verbose_before(config['location'])
	with open( config['location'], 'w' ) as outfile:
		for nameserver in config['nameservers']:
			outfile.write('nameserver {0}'.format(nameserver))
	verbose_after(config['location'])

def write_config_ecs( config ):
	for chainsetup in config['chainsetups']:
		ecs_file = os.path.join(config['location'],chainsetup['n']+'.ecs')
		verbose_before(ecs_file)
		with open(ecs_file, 'w' ) as outfile:
			outfile.write('-n:{0}\n'.format(chainsetup['n']))
			for chain in chainsetup['chains']:
				for key,value in chain.iteritems():
					outfile.write('-{0}:{1}'.format(key,value))

		verbose_after(ecs_file)

def write_config_ecp( config ):
	for preset in config['effect_presets']:
		ecp_file = os.path.join(config['location'],preset['name']+'.ecp')
		verbose_before(ecp_file)
		with open(ecp_file, 'w' ) as outfile:
			outfile.write('{0}={1}\n'.format(preset['name'],preset['preset']))
		verbose_after(ecp_file)
			
def write_config_generic( config, delim="=", group="={", quotes="" ):
	verbose_before(config['location'])
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
	verbose_after(config['location'])

def touch_file(filename):
	printer("Creating: {0}".format(filename))
	with open( filename, 'w' ) as outfile:
		outfile.write('')


#********************************************************************************
# Parse command line arguments
#
def parse_args():

	import argparse
	global args

	parser = argparse.ArgumentParser(description=DESCRIPTION)
	parser.add_argument('--loglevel', action='store', default=DEFAULT_LOG_LEVEL, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('--config','-c', action='store', help='Configuration file', default=DEFAULT_CONFIG_FILE)
	parser.add_argument('-v',  required=False, action='store_true', help='Verbose')
	parser.add_argument('--all',  required=False, action='store_true', help='Generate all files')
	parser.add_argument('--dbus', required=False, action='store_true', help='Generate dbus configuration')
	parser.add_argument('--wpa',  required=False, action='store_true', help='Generate wpa_supplicant.conf file')
	parser.add_argument('--hapd', required=False, action='store_true', help='Generate hostapd.conf file')
	parser.add_argument('--dnsm', required=False, action='store_true', help='Generate dnsmasq.conf file')
	parser.add_argument('--mpd',  required=False, action='store_true', help='Generate mpd.conf file')
	parser.add_argument('--smb',  required=False, action='store_true', help='Generate samba.conf file')
	parser.add_argument('--ecs',  required=False, action='store_true', help='Generate ecasound chainsetup files')
	parser.add_argument('--ecp',  required=False, action='store_true', help='Generate ecasound effects preset file')
	parser.add_argument('--wifi', required=False, action='store_true', help='Set WiFi mode')

	args = parser.parse_args()

#********************************************************************************
# Setup
#
def setup():
	global configuration
	
	printer('Loading: {0}'.format( args.config ))
	configuration = configuration_load( args.config )

	if 'system_configuration' not in configuration:
		printer('Configuration file does not contain a SYSTEM_CONFIGURATION section')
		exit()	

# ********************************************************************************
# Main Program
#
def main():


	def validate_config( ci, required_fields ):
		""" """
		if ci in configuration['system_configuration']:
			if not all (k in configuration['system_configuration'][ci] for k in required_fields):
				return False
				printer('Configuration for {0} is missing required fields'.format(ci))
		else:
			printer('No configuration for {0}'.format(ci))
			return False
			
		return True
	
	if args.all or args.dbus:
		if validate_config( 'dbus', ['location','services'] ):				
			write_config_dbus( configuration['system_configuration']['dbus'] )
		else:
			printer('DBus: Invalid Config')
							
	if  args.all or args.wpa:
		if validate_config( 'wpa_supplicant', ['location','network'] ):
			write_config_wpa( configuration['system_configuration']['wpa_supplicant'])
		else:
			printer('WPA: Invalid Config')

	if  args.all or args.hapd:
		if validate_config( 'hostapd', ['location','interface','driver','ssid','channel'] ):
			write_config_generic( configuration['system_configuration']['hostapd'], '=', '={' )
		else:
			printer('hostapd: Invalid Config')

	if  args.all or args.dnsm:
		if validate_config( 'dnsmasq', ['location','interface'] ):
			write_config_generic( configuration['system_configuration']['dnsmasq'], '=', '={' )
		else:
			printer('dnsmasq: Invalid Config')

	if  args.all or args.mpd:
		if validate_config( 'mpd', ['location','music_directory','audio_output'] ):
			write_config_generic( configuration['system_configuration']['mpd'], '\t', ' {', '"' )
		else:
			printer('mpd: Invalid Config')

	if  args.all or args.smb:
		if validate_config( 'smb', ['location','global','shares'] ):
			write_config_smb( configuration['system_configuration']['smb'] )
		else:
			printer('smb: Invalid Config')
		
	if  args.all or args.ecs:
		if validate_config( 'ecasound_ecs', ['location','chainsetups'] ):
			write_config_ecs( configuration['system_configuration']['ecasound_ecs'] )
		else:
			printer('ecs: Invalid Config')

	if  args.all or args.ecp:
		if validate_config( 'ecasound_ecp', ['location'] ):
			write_config_ecp( configuration['system_configuration']['ecasound_ecp'] )
		else:
			printer('ecs: Invalid Config')

	if  args.all or args.wifi:
		if 'wifi' not in configuration:
			printer('Cannot set WiFi mode, not configured (section: wifi, attribute: mode)')
		else:
			mode = configuration['wifi']['mode']
			if mode in ['network','wpa']:
				if os.path.exists('/root/WLAN-AP'):
					os.remove('/root/WLAN-AP')
				touch_file('/root/WLAN-WPA')
			elif mode == 'ap':
				if os.path.exists('/root/WLAN-WPA'):
					os.remove('/root/WLAN-WPA')
				touch_file('/root/WLAN-AP')
			else:
				printer('Unkown mode: {0}'.format(mode))
		
if __name__ == '__main__':
	parse_args()
	setup()
	main()
