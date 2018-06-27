#
# Collection of functions used everywhere.
# Has no dependencies*
#

import logging
from logging import Formatter
import logging.handlers
import copy
import re

import shutil	# load config

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
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560

DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_CONFIG_FILE = '/etc/configuration.json'


#********************************************************************************
# Markup
#

tagcolors = {
  'source'	: 'yellow'
 ,'plugin'	: 'blue'
 ,'button'	: 'light_magenta'
 ,'mq'		: 'yellow_2'
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


# ********************************************************************************
# Data Structures
#
def dict_track(	display=None
				,source=None
				,rds=None
				,artist=None
				,composer=None
				,performer=None
				,album=None
				,albumartist=None
				,title=None
				,length=None
				,elapsed=None
				,trackno=None
				,disc=None
				,folder=None
				,genre=None
				,date=None ):
	""" Details about what's playing. Only display is mandatory.
		Which fields are present strongly depends on the type of source and the availability of metadata.
		Sources are free to add their own tags. The ones mentioned below are the standardized.

	Field | Value
	--- | ---
	`display` | Formatted string
	`source` | Source name
	`rds` | RDS information (FM)
	`artist` | Artist name
	`composer` | The artist who composed the song
	`performer` | The artist who performed the song
	`album` | Album name
	`albumartist` | On multi-artist albums, this is the artist name which shall be used for the whole album
	`title` | Song title
	`length` | Track length (ms)
	`elapsed` | Elapsed time (ms) --?
	`track` | Decimal track number within the album
	`disc` | The decimal disc number in a multi-disc album.
	`genre` | Music genre, multiple genre's might be delimited by semicolon, though this is not really standardized
	`date` | The song's release date, may be only the year part (most often), but could be a full data (format?)
	"""
	track = {}
	track['display'] = display
	track['source'] = source
	track['rds'] = rds
	track['artist'] = artist
	track['composer'] = composer
	track['performer'] = performer
	track['album'] = album
	track['albumartist'] = albumartist
	track['title'] = title
	track['length'] = length
	track['elapsed'] = elapsed
	track['track'] = trackno
	track['disc'] = disc
	track['folder'] = folder
	track['genre'] = genre
	track['date'] = date
	return track

def dict_volume( system=None
				,device=None
				,simple_vol=None
				,channels=None
				,muted=None ):
	"""
	`system` | "alsa", "jack", "pulseaudio", "mpd"(?)
	`device` | Ex. "hw:0,0", "default-sink", etc.
	`channels` | `[{level}]` list of levels
	`muted` | Useful?
	"""
	volume = {}
	volume['system'] = system
	volume['device'] = device
	volume['simple_vol'] = simple_vol
	volume['channels'] = channels
	volume['muted'] = muted
	return volume


def struct_data(payload,code=None):
	"""
	Return a {data} structure: { 'retval':<return code>, 'payload':<payload> }
	Payload can be of any datatype*, but must be serializable (?).
	* If payload is None or False, a 500 code will be created, and no payload.
	  Payload can also be a Tuple consisting of a Payload and Return Value.
	"""
	data = {}
	if isinstance(payload, tuple) and len(payload) == 2 and isint(payload[1]):
		data['retval'] = int(payload[1])
		data['payload'] = payload[0]
	else:		
		if payload is False:
			data['retval'] = 500
			data['payload'] = None
		elif payload is True or payload is None:
			data['retval'] = 200
			data['payload'] = None
		else:
			data['retval'] = 200
			data['payload'] = payload
			
		if code is not None:
			data['retval'] = code
	
	return data
	
# ********************************************************************************
# MQ
#def validate_args(**args):

def validate_args(arg_defs,args,repeat=False):

	defs = arg_defs[:]	# cuz we might manipulate it, and python is stupid
	if not isinstance(args, list):
		print "second argument must be a list"
		return None

	# generate definitions
	if repeat:
		for i in range(len(args)/len(arg_defs)-1):
			defs.extend(arg_defs)
	
	for i, arg in enumerate(args):
		# datatype	
		if isinstance(arg, defs[i]['datatype']):
			#print "Datatype: PASS"
			pass
		else:
			if defs[i]['datatype'] == bool and strint_to_bool(arg) is not None:
				args[i] = strint_to_bool(arg)
			else:
				print "Datatype: FAIL"
				return None
				
	if len(defs)-len(args) > 0:
		for arg_def in defs[len(args):len(defs)]:
			args.append(arg_def['default'])

	# everything OK
	return args

# ********************************************************************************
"""	LOGGING
	
	printer
		use instead of print()
		
	log_get_logger
	
	log_create_console_loghandler
		Creates a log handler for Console output
		
	log_create_syslog_loghandler	
		Creates a log handler for Syslog output
		The address may be a tuple consisting of (host, port)
		or a string such as '/dev/log'
		
	tag
		Return an (ANSI) formatted tag
		
	ColoredFormatter
		log formatter with ANSI formatting
		
	RemAnsiFormatter
		log formatter which actively removes ANSI formatting
	
"""
def printer( message, level=LL_INFO, tag="",logger_name=""):
	logger = logging.getLogger(logger_name)
	logger.log(level, message, extra={'tag': tag})
	
def log_getlogger( name, level, tag, address=None):
	logger = logging.getLogger(name)
	logger.setLevel(logging.DEBUG)

	if address is not None:
		# output to syslog
		logger = log_create_syslog_loghandler(logger, level, tag, address='/dev/log')
	else:
		# output to console
		logger = log_create_console_loghandler(logger, level, tag)
		
	return logger
		
def log_create_console_loghandler(logger, log_level, log_tag=None):
	# Create log handler
	ch = logging.StreamHandler()						# create console handler
	ch.setLevel(log_level)								# set log level
	
	# Formatter
	fmtr_ch = ColoredFormatter("%(tag)s%(message)s")	# create formatters
	ch.setFormatter(fmtr_ch)							# add formatter to handlers

	# Add handler
	logger.addHandler(ch)								# add ch to logger
	
	# Feedback
	if log_tag is not None:
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

def tag ( tagname, format='ANSI', tagsize=6 ):
	""" Return an (ANSI) formatted tag """
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

# *******************************************************************************
# ArgParse
#
def default_parser(description,banner=None):

	import argparse
	global DEFAULT_LOG_LEVEL

	if banner is not None:
		print "************************************************************"
		print "* "+banner
		print "************************************************************"
	
	# use debug, if no overriding log level given, and debug flag is set
	debug_file = '/root/DEBUG_MODE'
	if os.path.exists(debug_file):
		DEFAULT_LOG_LEVEL = LL_DEBUG
		print "Debug output enabled"
	
	parser = argparse.ArgumentParser(description=description)
	parser.add_argument('--loglevel', action='store', default=DEFAULT_LOG_LEVEL, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('--config','-c', action='store', help='Configuration file', default=DEFAULT_CONFIG_FILE)
	parser.add_argument('-b', action='store_true', default=False)
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
	return parser


# *******************************************************************************
# Setup

# ********************************************************************************
# Handy DAEMON stuff
# Load Configurations
#
def load_cfg(config, configs, zmq_port_pub, zmq_port_sub, daemon_script=None, logger_name=None):


	cfg_main = None
	cfg_zmq = None
	cfg_daemon = None
	cfg_gpio = None
	printer("Hello from load_cfg",logger_name=logger_name)
	
	# main
	LOGGER_NAME = 'gpio'	# TODO
	cfg_main = configuration_load(logger_name,config)

	if cfg_main is None:
		return cfg_main, cfg_zmq, cfg_daemon, cfg_gpio
	
	# zeromq
	if not 'zeromq' in cfg_main:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(zmq_port_pub))
		printer('Subscriber port: {0}'.format(zmq_port_sub))
		cfg_zmq = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB }
	else:
		cfg_zmq = {}
		# Get portnumbers from either the main config, or default value
		if 'port_publisher' in cfg_main['zeromq']:
			cfg_zmq['port_publisher'] = cfg_main['zeromq']['port_publisher']
		else:
			cfg_zmq['port_publisher'] = DEFAULT_PORT_PUB
		
		if 'port_subscriber' in cfg_main['zeromq']:
			cfg_zmq['port_subscriber'] = cfg_main['zeromq']['port_subscriber']		
		else:
			cfg_zmq['port_subscriber'] = DEFAULT_PORT_SUB

	# TODO, integrate in above
	# Pub/Sub port override
	if zmq_port_pub:
		cfg_zmq['port_publisher'] = args.port_publisher
	if zmq_port_sub:
		cfg_zmq['port_subscriber'] = args.port_subscriber
			
	# daemon
	if 'daemons' in cfg_main and daemon_script is not None:
		for daemon in cfg_main['daemons']:
			if 'script' in daemon and daemon['script'] == daemon_script: #os.path.basename(__file__):
				cfg_daemon = daemon
				break #only one
		
	# gpio
	if cfg_daemon is not None:
		if 'directories' not in cfg_main or 'daemon-config' not in cfg_main['directories'] or 'config' not in cfg_daemon:
			cfg_gpio = None
		else:		
			config_dir = cfg_main['directories']['daemon-config']
			# TODO
			config_dir = "/mnt/PIHU_CONFIG/"	# fix!
			config_file = cfg_daemon['config']
			gpio_config_file = os.path.join(config_dir,config_file)
	
			# load gpio configuration
			if os.path.exists(gpio_config_file):
				cfg_gpio = configuration_load(logger_name,gpio_config_file)
			else:
				print "ERROR: not found: {0}".format(gpio_config_file)

	return cfg_main, cfg_zmq, cfg_daemon, cfg_gpio
		

# ********************************************************************************
# Load JSON configuration
#
def load_cfg_main(logger_name, configfile=None, defaultconfig=None):

	# ********************************************************************************
	# Restore default configuration
	#
	def configuration_restore( configfile, defaultconfig ):
		if os.path.exists(defaultconfig):
			shutil.copy(defaultconfig,configfile)
			return True

	if configfile is None:
		configfile = DEFAULT_CONFIG_FILE
	
	# keep track if we restored the config file
	restored = False
	
	# use the default from the config dir, in case the configfile is not found (first run)
	if not os.path.exists(configfile):
		if defaultconfig and os.path.exists(defaultconfig):
			printer('Configuration not present (first run?); loading default: {0}'.format( defaultconfig ), tag='CONFIG', logger_name=logger_name)
			restored = configuration_restore( configfile, defaultconfig )
			if not restored:
				printer('Restoring configuration {0}: [FAIL]'.format(defaultconfig), LL_CRITICAL, tag='CONFIG', logger_name=logger_name)
				return None
		else:
			printer('Configuration not present, and default missing')
			return None

	# open configuration file (restored or original) and Try to parse it
	jsConfigFile = open(configfile)
	try:
		config=json.load(jsConfigFile)
	except:
		printer('Loading/parsing {0}: [FAIL]'.format(configfile) ,LL_CRITICAL, tag='CONFIG', logger_name=logger_name)
		# if we had not previously restored it, try that and parse again
		if not restored and defaultconfig:
			printer('Restoring default configuration', tag='CONFIG', logger_name=logger_name)
			configuration_restore( configfile, defaultconfig )
			jsConfigFile = open(configfile)
			config=json.load(jsConfigFile)
			return config
		else:
			printer('Loading/parsing restored configuration failed!'.format(configfile) ,LL_CRITICAL, tag='CONFIG', logger_name=logger_name)
			return None

	# not sure if this is still possible, but let's check it..
	if config == None:
		printer('Loading configuration failed!'.format(configfile) ,LL_CRITICAL, tag='CONFIG', logger_name=logger_name)
	else:
		printer('Loading configuration [OK]'.format(configfile), tag='CONFIG', logger_name=logger_name)
		
	return config

'''
def load_cfg_zmq(cfg_main,override_pub,override_sub):
	""" load zeromq configuration """
	config = {}
	
	# in case both pub and sub supplied, uses these values
	if override_pub and override_sub:
		config['port_publisher'] = override_pub
		config['port_subscriber'] = override_sub
		return config

	# set defaults
	config['port_publisher'] = DEFAULT_PORT_PUB			
	config['port_subscriber'] = DEFAULT_PORT_SUB
		
	if not 'zeromq' in cfg_main:
		# use defaults if zeromq not in config and no values supplied
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
	else:
		# Get portnumbers from either the config, or default value
		if 'port_publisher' in cfg_main['zeromq']:
			config['port_publisher'] = cfg_main['zeromq']['port_publisher']
		
		if 'port_subscriber' in cfg_main['zeromq']:
			config['port_subscriber'] = cfg_main['zeromq']['port_subscriber']		
		
	# override, if available
	if override_pub: config['port_publisher'] = override_pub
	if override_sub: config['port_subscriber'] = override_sub
	return config

def load_cfg_daemon(cfg_main,script):
	""" load daemon configuration """
	if 'daemons' not in cfg_main:
		return None
	else:
		for daemon in cfg_main['daemons']:
			if 'script' in daemon and daemon['script'] == script:
				return daemon
	return None
'''
def configuration_load( logger_name, configfile, defaultconfig=None ):

	# ********************************************************************************
	# Restore default configuration
	#
	def configuration_restore( configfile, defaultconfig ):
		if os.path.exists(defaultconfig):
			shutil.copy(defaultconfig,configfile)
			return True

	# keep track if we restored the config file
	restored = False
	
	# use the default from the config dir, in case the configfile is not found (first run)
	if not os.path.exists(configfile):
		if defaultconfig and os.path.exists(defaultconfig):
			printer('Configuration not present (first run?); loading default: {0}'.format( defaultconfig ), tag='CONFIG', logger_name=logger_name)
			restored = configuration_restore( configfile, defaultconfig )
			if not restored:
				printer('Restoring configuration {0}: [FAIL]'.format(defaultconfig), LL_CRITICAL, tag='CONFIG', logger_name=logger_name)
				return None
		else:
			printer('Configuration not present, and default missing')
			return None

	# open configuration file (restored or original) and Try to parse it
	jsConfigFile = open(configfile)
	try:
		config=json.load(jsConfigFile)
	except:
		printer('Loading/parsing {0}: [FAIL]'.format(configfile) ,LL_CRITICAL, tag='CONFIG', logger_name=logger_name)
		# if we had not previously restored it, try that and parse again
		if not restored and defaultconfig:
			printer('Restoring default configuration', tag='CONFIG', logger_name=logger_name)
			configuration_restore( configfile, defaultconfig )
			jsConfigFile = open(configfile)
			config=json.load(jsConfigFile)
			return config
		else:
			printer('Loading/parsing restored configuration failed!'.format(configfile) ,LL_CRITICAL, tag='CONFIG', logger_name=logger_name)
			return None

	# not sure if this is still possible, but let's check it..
	if config == None:
		printer('Loading configuration failed!'.format(configfile) ,LL_CRITICAL, tag='CONFIG', logger_name=logger_name)
	else:
		printer('Loading configuration [OK]'.format(configfile), tag='CONFIG', logger_name=logger_name)
		
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

def isint(value):
	"""
	Return true if value is an int
	Float without any digits after the decimal point is considered an integer.
	Warning: int('530.0') does not yield a 530 int, but returns a ValueError.
	"""
	if isinstance(value, int):
		return True	
	elif isinstance(value, (str,unicode)):
		if value[0] == '+' or value[0] == '-': value = value[1:]
		
	try:
		ret = float(value).is_integer()
		return ret
	except:
		return False
	
def strint_to_bool(value):
	if isinstance(value, (str,unicode)) and value.lower() in ['true','on','1','t']:
		return True
	elif  isinstance(value, (str,unicode)) and value.lower() in ['false','off','0','f']:
		return False
	elif  isinstance(value, int) and value in [1]:
		return True
	elif  isinstance(value, int) and value in [0]:
		return False
	else:
		return None
	
def str2bool( string ):
	if string.lower() in ("true","1"):
		return True
	elif string.lower() in ("false","0"):
		return False
	else:
		return None


def prepostfix(path):
    #prefix
    if not path.startswith("/"):
        path = "/"+path
    #postfix
    if not path.endswith("/"):
        path += "/"
    return path

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

def url_check(url, timeout=None):
	# Using httplib2, supporting https (?):
	#h = httplib2.Http()
	#resp = h.request(url, 'HEAD')
	#assert int(resp[0]['status']) < 400
	
	# Using urllib2:
	try:
		urllib2.urlopen(url,timeout)
		return True
	except:
		return False
		
def get_part_uuid( device ):
	# TODO: check "device"
	# retrieve the partition uuid from the "blkid" command
	partuuid = subprocess.check_output("blkid "+device+" -s PARTUUID -o value", shell=True).rstrip('\n')
	return partuuid

def get_mountpoint(device):
	with open('/proc/mounts','r') as f:
		for line in f.readlines():
			spec = line.split()[0]
			if spec == device:
				return line.split()[1]
	return None

		
#def get_label(mountpoint):
#	label = os.path.basename(mount['mountpoint']).rstrip('\n')
	


