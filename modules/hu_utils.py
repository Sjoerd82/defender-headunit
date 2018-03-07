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