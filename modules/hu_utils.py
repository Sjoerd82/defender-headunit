#
# Collection of functions used everywhere.
# Has no dependencies*
#

# myprint()
import logging

# call, check_output
import subprocess

# pathroot
import os

#json and pickle:
import json
import pickle

#to check for an internet connection
import socket

#to check an URL
#import httplib2	# Buildroot is not supporting SSL... somehow...
import urllib2

# Third party modules
from colored import fg, bg, attr
from pid import PidFile

#log levels
LL_CRITICAL = 50
LL_ERROR = 40
LL_WARNING = 30
LL_INFO = 20
LL_DEBUG = 10
LL_NOTSET = 0

# Defines how to handle output
def myprint( message, level=LL_INFO, tag=""):
	logger = logging.getLogger('headunit')
	logger.log(level, message, extra={'tag': tag})

def printer( message, level=LL_INFO, tag=""):
	logger = logging.getLogger('headunit')
	logger.log(level, message, extra={'tag': tag})

	
# ********************************************************************************
# Load JSON configuration
#
def configuration_load( configfile, defaultconfig=None ):

	# keep track if we restored the config file
	restored = False
	
	# use the default from the config dir, in case the configfile is not found (first run)
	if not os.path.exists(configfile) and os.path.exists(defaultconfig):
		printer('Configuration not present (first run?); loading default: {0}'.format( defaultconfig ), tag='CONFIG')
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
		printer('Loading configuration [OK]'.format(configfile), tag='CONFIG')
		
	return config

# Add ANSI markup to a string
def colorize ( string, foreground, background='black' ):
	colorized = fg(foreground) + bg(background) + string + attr('reset')
	return colorized

# Return true if script for given pid is already running
def check_running( pid_file ):
	if not os.path.exists('/var/run/'+pid_file+'.pid'):
		return False
	else:
		print('pid file found: /var/run/{0}.pid'.format(pid_file))
		
		# try a lock, if succesful, it's a stale pid file, and we'll delete it
		try:
			with PidFile(pid_file) as p:
				print('Checking if we\'re already runnning')
				return False
		except:
			print('Already runnning! Stopping.')
			return True

# ********************************************************************************
# PulseAudio
#
def pa_sfx_load( sfxdir ):
	printer('Loading sound effects')
	call(["pactl","upload-sample",sfxdir+"/startup.wav", "startup"])
	call(["pactl","upload-sample",sfxdir+"/beep_60.wav", "beep_60"])
	call(["pactl","upload-sample",sfxdir+"/beep_70.wav", "beep_70"])
	call(["pactl","upload-sample",sfxdir+"/beep_60_70.wav", "beep_60_70"])
	call(["pactl","upload-sample",sfxdir+"/beep_60_x2.wav", "beep_60_x2"])
	call(["pactl","upload-sample",sfxdir+"/error.wav", "error"])
	call(["pactl","upload-sample",sfxdir+"/bt.wav", "bt"])

#
def pa_sfx( sfx ):

	#global sPaSfxSink
	#global bBeep
	sPaSfxSink = "alsa_output.platform-soc_sound.analog-stereo"
	bBeep = False
	
	if bBeep:
		beep()
	else:
		if sfx == 'startup':
			subprocess.call(["pactl", "play-sample", "startup", sPaSfxSink])
		elif sfx == 'button_feedback':
			subprocess.call(["pactl", "play-sample", "beep_60", sPaSfxSink])
		elif sfx == 'error':
			subprocess.call(["pactl", "play-sample", "error", sPaSfxSink])
		elif sfx == 'mpd_update_db':
			subprocess.call(["pactl", "play-sample", "beep_60_70", sPaSfxSink])
		elif sfx == 'bt':
			subprocess.call(["pactl", "play-sample", "bt", sPaSfxSink])
		elif sfx == 'reset_shuffle':
			subprocess.call(["pactl", "play-sample", "beep_60_x2", sPaSfxSink])

# Return dictionary with mounts
# optionally apply a filter on device and/or fs and/or a list of mountpoints to exclude
def get_mounts( spec=None, fs=None, mp_exclude=[] ):

	mounts = []
	with open('/proc/mounts','r') as f:
		for line in f.readlines():
			mount = {}
			mount['spec'] = line.split()[0]
			mount['mountpoint'] = line.split()[1]
			mount['fs'] = line.split()[2]

			# excluded mountpoints
			if not mount['mountpoint'] in mp_exclude:
				
				# filters:
				if not spec is None and mount['spec'] == spec:
					mounts.append(mount)
				elif not fs is None and mount['fs'] == fs:
					mounts.append(mount)
				elif spec is None and fs is None and not mount['fs'] in ('devtmpfs','proc','devpts','tmpfs','sysfs'):
					mounts.append(mount)

	return mounts

def internet():
	#TODO
	sInternet="www.google.com"
	try:
		# connect to the host -- tells us if the host is actually reachable
		socket.create_connection((sInternet, 80))
		return True
	except OSError:
		pass
	except:
		pass
	return False

def url_check( url ):
	# Using httplib2, supporting https (?):
	#h = httplib2.Http()
	#resp = h.request(url, 'HEAD')
	#assert int(resp[0]['status']) < 400
	
	# Using urllib2:
	try:
		urllib2.urlopen(url)
		return True
	except:
		return False
		
def get_part_uuid( device ):
	# TODO: check "device"
	# retrieve the partition uuid from the "blkid" command
	partuuid = subprocess.check_output("blkid "+device+" -s PARTUUID -o value", shell=True).rstrip('\n')
	return partuuid

#def get_label_from_