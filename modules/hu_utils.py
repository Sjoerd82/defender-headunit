#
# Collection of functions used everywhere.
# Has no dependencies*
#

# myprint()
import logging
from logging import Formatter
import copy
import re

# call, check_output
import subprocess

# pathroot
import os

# pactl
from subprocess import call

# json and pickle:
import json
import pickle

#to check for an internet connection
import socket
from socket import SOCK_DGRAM	# syslog

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

SYSLOG_UDP_PORT=514


#********************************************************************************
#
# Markup
#

tagcolors = {
  'source'	: 'yellow'
 ,'plugin'	: 'blue'
 ,'button'	: 'light_magenta'
 #SOURCES:
 ,'mpd'		: 'cyan'
 ,'fm'		: 'turquoise_4'
 ,'locmus'	: 'cyan'
 ,'media'	: 'cyan'
 ,'bt'		: 'light_blue'
 ,'line'	: 'green'
 ,'stream'	: 'deep_pink_1b'
 ,'smb'		: 'dark_orange'
 }


# Defines how to handle output
def myprint( message, level=LL_INFO, tag=""):
	logger = logging.getLogger('headunit')
	logger.log(level, message, extra={'tag': tag})

def printer( message, level=LL_INFO, tag=""):
	logger = logging.getLogger('headunit')
	logger.log(level, message, extra={'tag': tag})


# ********************************************************************************
# Logging
#
# init_logging_c		Creates a log handler for Console output
# init_logging_s		Creates a log handler for Syslog output
#						The address may be a tuple consisting of (host, port)
#						 or a string such as '/dev/log'
#

# *******************************************************************************
#
# Logging formatters
#

class ColoredFormatter(Formatter):
 
	def __init__(self, patern):
		Formatter.__init__(self, patern)
 
	def colorer(self, text, color=None):
		#if color not in COLORS:
		#    color = 'white'
		#clr = COLORS[color]
		#return (PREFIX + '%dm%s' + SUFFIX) % (clr, text)
		return None
 
	def format(self, record):
		colored_record = copy.copy(record)
		#levelname = colored_record.levelname
		#color = MAPPING.get(levelname, 'white')
		#colored_levelname = self.colorer(levelname, color)
		#colored_record.levelname = 'MyLevel' #colored_levelname

		#print colored_record.levelname
		
		# Markup specialstrings
		colored_record.msg = colored_record.msg.replace('[OK]',colorize('[OK]','light_green'))
		colored_record.msg = colored_record.msg.replace('[FAIL]',colorize('[FAIL]','light_red'))

		#Colorize according to error level
		if colored_record.levelno == LL_WARNING:
			fmessage = colorize(colored_record.msg,'orange_red_1')
		elif colored_record.levelno == LL_ERROR:
			fmessage = colorize(colored_record.msg,'light_red')
		elif colored_record.levelno == LL_CRITICAL:
			fmessage = colorize(colored_record.msg,'white','red')
		else:
			fmessage = colored_record.msg

		colored_record.msg = fmessage
		
		# Markup tag
		if not colored_record.tag == '':
			colored_record.tag = tag(colored_record.tag)+' '

		return Formatter.format(self, colored_record)

class RemAnsiFormatter(Formatter):
 
	def __init__(self, patern):
		Formatter.__init__(self, patern)

	def format(self, record):
		record_copy = copy.copy(record)
		
		# Remove any ANSI formatting
		record_copy.msg = re.sub('\033[[](?:(?:[0-9]*;)*)(?:[0-9]*m)', '', record_copy.msg)
	
		# Remove any ANSI formatting from the tag, if any..
		#if 'tag' in colored_record:
		#if colored_record.has_key('tag'):
		#if colored_record.extra  is not None:
		record_copy.tag = re.sub('\033[[](?:(?:[0-9]*;)*)(?:[0-9]*m)', '', record_copy.tag)
		if not record_copy.tag == '':
			record_copy.tag = tag(record_copy.tag,format='None')+' '
			#record_copy.tag = '['+record_copy.tag.upper()+']'

		#levelname = colored_record.levelname
		#color = MAPPING.get(levelname, 'white')
		#colored_levelname = self.colorer(levelname, color)
		#colored_record.levelname = 'MyLevel' #colored_levelname
		#colored_record.message = self.remansi(colored_record.message) #.upper()
		#colored_record.levelname = "blaa" #colored_record.levelname.lower()
		return Formatter.format(self, record_copy)
		
def log_create_console_loghandler(logger, log_level, log_tag):
	# Create log handler
	ch = logging.StreamHandler()						# create console handler
	ch.setLevel(log_level)								# set log level
	
	# Formatter
	fmtr_ch = ColoredFormatter("%(tag)s%(message)s")	# create formatters
	ch.setFormatter(fmtr_ch)							# add formatter to handlers

	# Add handler
	logger.addHandler(ch)								# add ch to logger
	logger.info('Logging started: Console',extra={'tag':log_tag})
	return logger
	
def log_create_syslog_loghandler(logger, log_level, log_tag, address=('localhost', SYSLOG_UDP_PORT), socktype=socket.SOCK_DGRAM ):
	# Create log handler
	sh = logging.handlers.SysLogHandler(address=address, socktype=socktype)
	sh.setLevel(log_level)

	# Formatter
	fmtr_sh = RemAnsiFormatter("%(asctime)-9s [%(levelname)-8s] %(tag)s %(message)s")
	sh.setFormatter(fmtr_sh)

	# Add handler
	logger.addHandler(sh)
	logger.info('Logging started: Syslog',extra={'tag':log_tag})
	return logger

# return an (ANSI) formatted tag
def tag ( tagname, format='ANSI', tagsize=6 ):
	if tagname == '' or tagname == None:
		return ''
		
	#If first character of the tag is a dot, it is a 'continuation'
	if tagname[0] == '.':
		bCont = True
	else:
		bCont = False

	if bCont:
		tagname = tagname[1:].upper()
		ftag = str('.').rjust(len(tagname),'.')
	else:
		ftag = tagname.upper()

	if format == 'ANSI':
		# Get/Set Color
		if tagname.lower() in tagcolors:
			color = tagcolors[tagname.lower()]
		else:
			color = 'white'
	
		if bCont:
			ctag = ' {0} '.format(colorize(ftag.center(tagsize),color))
		else:
			ctag = '[{0}]'.format(colorize(ftag.center(tagsize),color))
	else:
		if bCont:
			ctag = ' {0} '.format(ftag.center(tagsize))
		else:
			ctag = '[{0}]'.format(ftag.center(tagsize))
			
	return ctag
	#return self.colorize(ftag.center(self.tag_size),color)
	
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

	# TODO: PYTHON3: USE SHUTIL
	pactl = "/bin/patcl"

	if not os.path.isfile( pactl ):
		printer("PulseAudio pactl not found, cannot load sound effects")
		return False
	
	printer('Loading sound effects')
	call(["pactl","upload-sample",sfxdir+"/startup.wav", "startup"])
	call(["pactl","upload-sample",sfxdir+"/beep_60.wav", "beep_60"])
	call(["pactl","upload-sample",sfxdir+"/beep_70.wav", "beep_70"])
	call(["pactl","upload-sample",sfxdir+"/beep_60_70.wav", "beep_60_70"])
	call(["pactl","upload-sample",sfxdir+"/beep_60_x2.wav", "beep_60_x2"])
	call(["pactl","upload-sample",sfxdir+"/error.wav", "error"])
	call(["pactl","upload-sample",sfxdir+"/bt.wav", "bt"])
	return True

#
def pa_sfx( sfx ):

	print("PA SFX: {0}".format(sfx)) # TODO LL_DEBUG

	# TODO: PYTHON3: USE SHUTIL
	pactl = "/bin/patcl"

	if not os.path.isfile( pactl ):
		printer("PulseAudio pactl not found, cannot load sound effects")
		return False
	
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
	
	return True

# Return dictionary with mounts
# optionally apply a filter on device and/or fs and/or a list of mountpoints to exclude
def get_mounts( dev=None, fs=None, mp_exclude=[], fs_exclude=[] ):

	mounts = []
	with open('/proc/mounts','r') as f:
		for line in f.readlines():
			mount = {}
			mount['spec'] = line.split()[0]
			mount['mountpoint'] = line.split()[1]
			mount['fs'] = line.split()[2]

			# excluded mountpoints
			if not mount['mountpoint'] in mp_exclude and not mount['fs'] in fs_exclude:
				# filters:
				if not dev is None and mount['spec'] == dev:
					mounts.append(mount)
				elif not fs is None and mount['fs'] == fs:
					mounts.append(mount)
				elif dev is None and fs is None and not mount['fs'] in ('devtmpfs','proc','devpts','tmpfs','sysfs'):
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