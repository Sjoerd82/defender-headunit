
pluginName='lastfm'

from hu_utils import *

# TODO!!! the "headunit"-logger is no longer accessible once this script is started "on its own"..
def myprint( message, level, tag ):
	print("[{0}] {1}".format(tag,message))

# Wrapper for "myprint"
def printer( message, level=LL_INFO, continuation=False, tag=controlName ):
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

printer('Starting Plugin {0}'.format(pluginName))


# headunit stuff
from hu_settings import *

# required here
import pylast
import datetime
import time
import os

"""
import json
def configuration_load( configfile ):
	try:
		jsConfigFile = open(configfile)
		config=json.load(jsConfigFile)
		return config
	except:
		print('Loading/parsing {0}: [FAIL]'.format(configfile))
		
def getPluginConfig( pluginName ):
	CONFIG_FILE = 'D://Python/configuration.json'
	configuration = configuration_load( CONFIG_FILE )
	return configuration['plugins_other'][pluginName]

"""
# Key for "Headunit"
# In order to perform a write operation you need to authenticate yourself
pluginConfig = getPluginConfig('scrobbler')
API_KEY = pluginConfig['lastfm_api_key']
API_SECRET = pluginConfig['lastfm_api_secret']
username = pluginConfig['lastfm_username']
password_hash = pluginConfig['lastfm_password_hash']
scrobble_dir = 'D://Python/'
tracks_file = 'scrobble.csv'

print('!debug!')

def plugin_init():
	print('[PLUGIN] Scrobbler_lastfm loading...')

	# Login
	try:
		network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET, username=username, password_hash=password_hash)
	except:
		print('Login failed!')

def cb_onInternetChanged():
	print('Internet changed')
	#TODO
	#IF internet available:
	#IF file exists:
	if False:
		scrobbleFromFile()

def cb_onTrackChanged():
	print('Track changed')
	#playing = hash("-".join(artist,track)
	# (Re)start timer, 60 seconds

def cb_onTrackChangedTimer():
	print('Track changed timer expired -- checking')
	#playing_prev = playing
	#get current track (how??????????)
	#playing = hash("-".join(artist,track)
	#if playing == playing_prev:
		#scrobbleTrack

def scrobbleTrack( artist, track, unixtime=None ):
	# IF INTERNET
	if False:
		scrobbleTrackOffline( artist, track )
	else:
		scrobbleTrackOnline( artist, track, unixtime )

def scrobbleTrackOnline( artist, track, unixtime=None ):
	#print('[LASTFM] Scrobbling')
	if unixtime == None:
		unix_timestamp = int(time.mktime(datetime.datetime.now().timetuple()))
	else:
		#todo check validity of unixtime
		#valid int
		unix_timestamp = int(unixtime)
		#real time? ####### UNTESTED!
		if unix_timestamp < 1000000:
			# Scrobbled tracks were saved when no real date/time was available.
			# Base the date on yesterday 00:00
			d = datetime.datetime.now().date() - datetime.timedelta(days=1)
			t = datetime.time(0, 0)
			ydaymidnight = datetime.datetime.combine(d,t)
			base = int(time.mktime(ydaymidnight.timetuple()))
			unix_timestamp += base
	
	# IF INTERNET:
	#network.scrobble(artist=artist, title=track, timestamp=int(unix_timestamp))
	print('[LASTFM] Scrobbling {0}: {1} - {2}'.format(unix_timestamp,artist,track))

def scrobbleTrackOffline( artist, track ):
	print('[LASTFM] Offline Scrobbling')
	tracksfile = os.path.join(scrobble_dir, tracks_file)
	unix_timestamp = int(time.mktime(datetime.datetime.now().timetuple()))
	with open( tracksfile, 'a' ) as f:
		f.write(','.join([str(unix_timestamp),artist,track])+'\n')

def scrobbleFromFile():
	print('[LASTFM] Scrobbling earlier played tracks')
	tracksfile = os.path.join(scrobble_dir, tracks_file)
	#rename/move to a copy, in case new tracks get scrobbled
	tracksfilecp = tracksfile + '.process'
	os.rename(tracksfile,tracksfilecp)
	with open( tracksfilecp, 'r' ) as f:
		for line in f:
			scrobbleData = line.strip().split(',')
			scrobbleTrackOnline(scrobbleData[1],scrobbleData[2],scrobbleData[0])
			print('[LASTFM] Scrobbling: {0}, {1}, {2}'.format(scrobbleData[1],scrobbleData[2],scrobbleData[0]))
	os.remove(tracksfilecp)
		
	#load tracks from file

plugin_init()
#register dbus functions
print('[LASTFM] listening for MPD DBus messages...')

## JUST SOME TESTS ##
#scrobbleTrackOffline('HIM','Pretending')
#scrobbleTrackOffline('HIM','Join Me')
#scrobbleFromFile()
