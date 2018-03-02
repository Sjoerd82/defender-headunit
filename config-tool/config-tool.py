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

env_config_file = os.environ["HU_CONFIG_FILE"]

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
parser.add_argument('--resv', required=False, action='store_true', help='Generate resolv.conf file')
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
arg_resv = args.resv
arg_mpd  = args.mpd
arg_smb  = args.smb

# ********************************************************************************
#
# load json source configuration
import os
import json
import hu_settings


# ********************************************************************************
# Output wrapper
#
def printer( message, level=20, continuation=False, tag='SYSTEM' ):
	#TODO: test if headunit logger exist...
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

# ********************************************************************************
# Config writers
#

def write_config_dbus( dbus_config ):
	#open file for replacement
	#print header
	for service in dbus_config['services']
	#print footer

def write_config_wpa( wpa_config ):
	with open( wpa_config['location'], 'w' ) as outfile:
		for key, value in wpa_config:
			if not key in ('location','networks'):
				outfile.write('{0}={1}'.format(key,value))
				
		for network in wpa_config['networks']:
			outfile.write('network={')
			outfile.write('ssid={0}'.format(network['ssid']))
			outfile.write('psk={0}'.format(network['psk']))
			outfile.write('}')

def write_config_mpd( mpd_config ):
	#open file for replacement
	#print header
	for outputs in dbus_config['outputs']

def write_config_smb( smb_config ):
	#open file for replacement
	#print header
	for outputs in dbus_config['shares']

def write_config_resolv( config ):
	with open( config['location'], 'w' ) as outfile:
		for nameserver in config['nameservers']:
			outfile.write('nameserver {0}'.format(nameserver))

def write_config_generic( config, delim="=", group="={" ):
"""
Format:
 key1=value1
 key2=value2
 list-key {
   key1=value1
   key2=value2
 }
"""
	with open( config['location'], 'w' ) as outfile:
		for key, value in config:
			if type(key) == 'list':
				if group == "={":
					outfile.write('{0}{1}{2}'.format(key,delim,group))
				for listkey, listvar in config[key]:
					outfile.write('  {1}{0}{2}'.format(delim,listkey,listvar))
				if group == "={":
					outfile.write('}')
			elif not key in ('location'):
				outfile.write('{1}{0}{2}'.format(delim,key,value))


# ********************************************************************************
# Main Program
#

def main():

	def validate_config( ci, required_fields ):
		if ci in configuration['system_configuration']:
			if not all (k in configuration['system_configuration'][ci] for k in required_fields):
				return False
				printer('Configuration for {0} is missing required fields'.format(ci))
		else:
			printer('No configuration for {0}'.format(ci))
			return False
			
		return True

	configuration = hu_settings.configuration_load( arg_config )
	
	if 'system_configuration' not in configuration:
		printer('Configuration file does not contain a system configuration.')
		exit()
	
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
							
	elif arg_wpa:
		if validate_config( 'wpa_supplicant', ['location','networks'] ):
			write_config_generic( configuration['system_configuration']['wpa_supplicant'], '=', '={' )

	elif arg_hapd:
		if validate_config( 'hostapd', ['location','interface','driver','ssid','channel'] ):
			write_config_generic( configuration['system_configuration']['hostapd'], '=', '={' )

	elif arg_dnsm:
		if validate_config( 'dnsmasq', ['location'] ):
			write_config_generic( configuration['system_configuration']['dhcpd'] )

	elif arg_resv:
		if validate_config( 'resolv', ['location','nameservers'] ):
			write_config_resolv( configuration['system_configuration']['resolv'] )
			
	elif arg_mpd:
		if validate_config( 'mpd', ['location','outputs'] ):
			write_config_mpd( configuration['system_configuration']['mpd'] )

	elif arg_smb:
		if validate_config( 'smb', ['location','shares'] ):
			write_config_smb( configuration['system_configuration']['smb'] )

		
if __name__ == '__main__':
	main()
