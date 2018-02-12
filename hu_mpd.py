# ********************************************************************************
# Wrapper for python-mpd2
#
import os
import subprocess
from subprocess import Popen, PIPE
import pickle

import sys

from mpd import MPDClient

from hu_utils import *
# ********************************************************************************
# Output wrapper
#

def printer( message, level=20, continuation=False, tag='MPD' ):
	#TODO: test if headunit logger exist...
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )



#TODO
sDirSave = "/mnt/PIHU_CONFIG"

class mpdController():

	#self.mpdc = MPDClient()		# class attribute -- shared by all instances... gives irrelevant connect errors... not sure if this is good or bad

	def __init__( self ):
		# Connect to MPD
		try:
			printer('Initializing MPD client', level=LL_DEBUG)
			self.mpdc = MPDClient()				# per instance !
			self.mpdc.timeout = 10                # network timeout in seconds (floats allowed), default: None
			self.mpdc.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
			self.mpdc.connect("localhost", 6600)
			printer(' > Version: {0}'.format(self.mpdc.mpd_version), level=LL_DEBUG)          # print the MPD version
			self.mpdc.random(0)
			self.mpdc.repeat(1)	
			#self.mpdc.idle()		#keep the connection open... But this blocks :(
			self.mpdc.send_idle()	#keep the connection open... Non-blocking..
		except:
			printer('Failed to connect to MPD server: {0}'.format(sys.exc_info()[0]), level=LL_ERROR)
	
	def __del__( self ):
			print('Disconnecting')	#, level=LL_DEBUG
			#self.mpdc.disconnect()		#often fails __del__ seems quite unstable
		
	def playlistClear( self ):
		printer('Emptying MPD playlist')
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???
		#self.mpdc.command_list_ok_begin()

		try:
			self.mpdc.noidle()
		except:
			printer('WEIRD... no idle was set..')
		
		self.mpdc.stop()
		self.mpdc.clear()
		self.mpdc.send_idle()

		#print self.mpdc.command_list_end()
		#call(["mpc", "-q", "stop"])
		#call(["mpc", "-q", "clear"])
		#self.mpcd.close()

	def playlistPop( self, type, sMpdDir ):
		printer('Populating playlist, folder: {0}'.format(sMpdDir))

		self.mpdc.noidle()
	
		if type == 'locmus' or type == 'smb' or type == 'media':
			try:
				self.mpdc.findadd('base',sMpdDir)
			except:
				printer('ERROR: folder not in MPD database?')
		elif type == 'stream':
			# Using the command line:
			#  ..but this generates some problems with special characters
			streams_file = sDirSave + "/streams.txt"
			#p1 = subprocess.Popen(["cat", streams_file], stdout=subprocess.PIPE)
			#p2 = subprocess.Popen(["mpc", "add"], stdin=p1.stdout, stdout=subprocess.PIPE)
			#p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
			#output,err = p2.communicate()		
			streams=open(streams_file,'r')
			with open(streams_file,'r') as streams:
				for l in streams:
					uri = l.rstrip()
					if not uri[:1] == '#' and not uri == '':
						uri_OK = url_check(uri)
						if uri_OK:
							print(' ....  . Stream [OK]: {0}'.format(uri))
							call(["mpc", "-q", "add", uri])
						else:
							print(' ....  . Stream [FAIL]: {0}'.format(uri))
		else:
			self.mpdc.findadd('base',type)
		
		self.mpdc.send_idle()
		
	def playlistIsPop( self ):
		printer('Checking if playlist is populated')

		self.mpdc.noidle()
		self.mpdc.command_list_ok_begin()
		self.mpdc.status()
		results = self.mpdc.command_list_end()
		self.mpdc.send_idle()

		return results[0]['playlistlength']

	def dbCheckDirectory( self, directory ):
		printer("Checking existance of folder in MPD db..")
		taskcmd = "mpc listall "+directory+" | wc -l"
		# if directory is not in mpd db, "mpd error: No such directory" will be returned
		task = subprocess.Popen(taskcmd, shell=True, stdout=subprocess.PIPE)
		mpcOut = task.stdout.read()
		assert task.wait() == 0
		
		if mpcOut.rstrip('\n') == '0':
			printer(' > {0}: nothing in the database for this source.'.format(directory))
			return False
		else:
			printer(' > {0}: found {1:s} tracks'.format(directory,mpcOut.rstrip('\n')))
			return True

	# location must be a path relative to MPD
	def update_call( self, location, wait=True ):

		#Sound effect
		pa_sfx('mpd_update_db')
		#Debug info
		printer('Updating database for location: {0}'.format(location))
		#Update
		if wait:
			printer(' > Please wait, this may take some time...')
			call(["mpc", "--wait", "-q", "update", location])
			printer(' > Update finished')
		else:
			call(["mpc", "-q", "update", location])
			#bMpdUpdateSmb
	
	def update( self, location, wait=True ):

		#Sound effect
		pa_sfx('mpd_update_db')
		#Debug info
		printer('Updating database for location: {0}'.format(location))

		try:
			self.mpdc.noidle()
		except:
			printer('WEIRD... no idle was set..')

		#Update
		if wait:
			printer(' > Please wait, this may take some time...')
			self.mpdc.update(location)
			printer(' > Update finished')
		else:
			self.mpdc.update(location)

		self.mpdc.command_list_ok_begin()
		self.mpdc.status()
		results = self.mpdc.command_list_end()
		print results
		
		#self.mpdc.idle()
		self.mpdc.send_idle()
			
	def lastKnownPos( self, id ):
	
		#default
		pos = {'pos': 1, 'time': 0}

		#TODO!
		iThrElapsed = 20	 # Minimal time that must have elapsed into a track in order to resume position
		iThrTotal = 30		 # Minimal track length required in order to resume position
		
		# open pickle_file, if it exists
		pickle_file = sDirSave + "/mp_" + id + ".p"
		if os.path.isfile(pickle_file):
			printer('Retrieving last known position from lkp file: {0:s}'.format(pickle_file))
			try:
				dSavePosition = pickle.load( open( pickle_file, "rb" ) )
			except:
				printer('PICKLE: Loading {0:s} failed!'.format(pickle_file))
				return pos

			#otherwise continue:
#			self.mpdc.noidle()
#			psfind = self.mpdc.playlistfind('filename',dSavePosition['file'])
#			self.mpdc.idle()
#
# SEEMS TO HANG?
#
			psfind = []
			
			#in the unlikely case of multiple matches, we'll just take the first, psfind[0]
			if len(psfind) == 0:
				printer(' > File not found in loaded playlist')
			else:
				pos['pos'] = int(psfind[0]['pos'])+1
				timeElapsed,timeTotal = map(int, dSavePosition['time'].split(':'))
				printer('Match found: {0}. Continuing playback at #{1}'.format(dSavePosition['file'],pos['pos']))
				printer(' > Elapsed/Total time: {0}s/{1}s'.format(timeElapsed,timeTotal))
				if timeElapsed > iThrElapsed and timeTotal > iThrTotal:
					pos['time'] = str(timeElapsed)
					printer(' > Elapsed time over threshold: continuing at last position.')
				else:
					printer(' > Elapsed time below threshold or short track: restarting at beginning of track.')

		return pos
		
#	def playStart( str(playslist_pos['pos']), playslist_pos['time'] ):
	def playStart( self, pos, time ):
		print('todo')

	def mpc_get_PlaylistDirs( self ):

		printer('Building playlist directory structure...')

		# local variables
		dirname_current = ''
		dirname_prev = ''
		iPos = 1

		# clear arMpcPlaylistDirs
		arMpcPlaylistDirs = []

		# TODO! DETERMINE WHICH IS FASTER... Commandline seems faster
		
		# Via the API
		"""
		xMpdClient = MPDClient() 
		xMpdClient.connect("localhost", 6600)  # connect to localhost:6600
		playlistitem = xMpdClient.playlistinfo()
		xMpdClient.close()
		
		for line in playlistitem:
			dirname_current=os.path.dirname(line['filename'].strip())
			t = iPos, dirname_current
			if dirname_prev != dirname_current:
				arMpcPlaylistDirs.append(t)
			dirname_prev = dirname_current
			iPos += 1
		"""
		
		# Via the commandline

# SEEMS TO HANG?
		"""
		pipe = Popen('mpc -f %file% playlist', shell=True, stdout=PIPE)

		for line in pipe.stdout:
			dirname_current=os.path.dirname(line.strip())
			t = iPos, dirname_current
			if dirname_prev != dirname_current:
				arMpcPlaylistDirs.append(t)
			dirname_prev = dirname_current
			iPos += 1
		"""
			
		return arMpcPlaylistDirs
		
	def mpc_get_currentsong( self ):
	
		self.mpdc.noidle()
		self.mpdc.command_list_ok_begin()
		self.mpdc.currentsong()
		results = self.mpdc.command_list_end()
		self.mpdc.send_idle()
		
		# print results[0]
		#{'album': 'Exodus', 'composer': 'Andy Hunter/Tedd T.', 'title': 'Go', 'track': '1', 'duration': '411.480', 'artist': 'Andy Hunter', 'pos': '0', 'last-modified': '2013-10-12T15:53:13Z', 'albumartist': 'Andy Hunter', 'file': 'PIHU_SMB/music/electric/Andy Hunter/Andy Hunter - 2002 - Exodus/01 - Andy Hunter - Go.mp3', 'time': '411', 'date': '2002', 'genre': 'Electronic/Dance', 'id': '44365'}
		
		#return self.mpdc.currentsong()
		return results[0]

	def mpc_get_status( self ):

		try:
			self.mpdc.noidle()
		except:
			printer('WEIRD... no idle was set..')

		self.mpdc.command_list_ok_begin()
		self.mpdc.status()

		results = self.mpdc.command_list_end()
		self.mpdc.send_idle()
		
		#print results

		#print results[0]:
		#{'songid': '14000', 'playlistlength': '7382', 'playlist': '8', 'repeat': '1', 'consume': '0', 'mixrampdb': '0.000000', 'random': '1', 'state': 'play', 'elapsed': '0.000', 'volume': '100', 'single': '0', 'nextsong': '806', 'time': '0:239', 'duration': '239.020', 'song': '6545', 'audio': '44100:24:2', 'bitrate': '0', 'nextsongid': '8261'}

		#return self.mpdc.currentsong()
		return results[0]

	def mpc_get_trackcount( self ):
		#TODO
		return 12

	def channelSubscribe( self, channel ):
	
		self.mpdc.noidle()
		self.mpdc.subscribe(channel)
		self.mpdc.send_idle()
		
	def nextTrack( self ):
		print('Next track')
		call(["mpc", "-q", "next"])
		
	def prevTrack( self ):
		print('Prev. track')
		call(["mpc", "-q", "prev"])

	def stop( self ):
		print('Stop')

	def random( self, state ):
		global dSettings
				
		# on
		if state == 'on':
			print('[MPC] Random ON + Next track')
			call(["mpc", "-q", "random", "on"])
			call(["mpc", "-q", "next"])

		# off
		elif state == 'off':
			print('[MPC] Random OFF')
			call(["mpc", "-q", "random", "off"])

		# toggle
		else: 
			print('[MPC] Toggling random')
			call(["mpc", "-q", "random"])

def mpc_random_get():

	xMpdClient = MPDClient() 
	xMpdClient.connect("localhost", 6600)  # connect to localhost:6600
	xMpdClient.command_list_ok_begin()
	xMpdClient.status()
	results = xMpdClient.command_list_end()

	# Dictionary in List
	try:
		for r in results:
			random = r['random']
	except:
		print(' ...  Error, key not found!')
		return "unknown"
	
	if random == '1':
		return "on"
	elif random == '0':
		return "off"
	else:
		return "unknown"
	
	xMpdClient.close()

def mpc_random( state ):
	global dSettings
	
	# check sound
	if not (dSettings['source'] == 1 or dSettings['source'] == 2 or dSettings['source'] == 5 or dSettings['source'] == 6):
		print('[MPC] Random: invalid source... aborting...')
		pa_sfx('error')
		return 1
	
	# on
	if state == 'on':
		print('[MPC] Random ON + Next track')
		call(["mpc", "-q", "random", "on"])
		call(["mpc", "-q", "next"])

	# off
	elif state == 'off':
		print('[MPC] Random OFF')
		call(["mpc", "-q", "random", "off"])

	# toggle
	else: 
		print('[MPC] Toggling random')
		call(["mpc", "-q", "random"])
	
def mpc_get_PlaylistDirs():
	global arMpcPlaylistDirs
	print('[MPC] Building playlist directory structure...')

	# local variables
	dirname_current = ''
	dirname_prev = ''
	iPos = 1

	# clear arMpcPlaylistDirs
	arMpcPlaylistDirs = []

	# TODO! DETERMINE WHICH IS FASTER... Commandline seems faster
	
	# Via the API
	"""
	xMpdClient = MPDClient() 
	xMpdClient.connect("localhost", 6600)  # connect to localhost:6600
	playlistitem = xMpdClient.playlistinfo()
	xMpdClient.close()
	
	for line in playlistitem:
		dirname_current=os.path.dirname(line['filename'].strip())
		t = iPos, dirname_current
		if dirname_prev != dirname_current:
			arMpcPlaylistDirs.append(t)
		dirname_prev = dirname_current
		iPos += 1
	"""
	
	# Via the commandline
	pipe = Popen('mpc -f %file% playlist', shell=True, stdout=PIPE)

	for line in pipe.stdout:
		dirname_current=os.path.dirname(line.strip())
		t = iPos, dirname_current
		if dirname_prev != dirname_current:
			arMpcPlaylistDirs.append(t)
		dirname_prev = dirname_current
		iPos += 1

def mpc_current_folder():
	# Get current folder
	pipe = subprocess.check_output("mpc -f %file%", shell=True)
	return os.path.dirname(pipe.splitlines()[0])

def mpc_next_folder_pos():
	global arMpcPlaylistDirs
	dirname_current = mpc_current_folder()
	print(' ...  Current folder: {0:s}'.format(dirname_current))
	
	print(' >>> DEBUG info:')
	print mpc_get_PlaylistDirs_thread.isAlive()
	
	try:
		iNextPos = arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)+1)][0]
		print(' ...  New folder = {0:s}'.format(arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)+1)][1]))
	except IndexError:
		# I assume the end of the list has been reached...
		print(' ...  ERROR: IndexError - restart at 1')
		iNextPos = 1

	return iNextPos

def mpc_prev_folder_pos():
	global arMpcPlaylistDirs
	dirname_current = mpc_current_folder()
	print(' ...  Current folder: {0:s}'.format(dirname_current))

	print(' >>> DEBUG info:')
	print mpc_get_PlaylistDirs_thread.isAlive()

	try:
		iNextPos = arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)-1)][0]
		print(' ...  New folder = {0:s}'.format(arMpcPlaylistDirs[([y[1] for y in arMpcPlaylistDirs].index(dirname_current)-1)][1]))
	except IndexError:
		# I assume we past the beginning of the list...
		print(' ...  ERROR. Debug info = {0}'.format(len(arMpcPlaylistDirs)))
		iNextPos = arMpcPlaylistDirs[len(arMpcPlaylistDirs)][0]
		pa_sfx('error')

	return iNextPos


def mpc_next_folder():
	print('[MPC] Next folder')
	call(["mpc", "-q", "play", str(mpc_next_folder_pos())])
	# Shuffle Off

def mpc_prev_folder():
	print('[MPC] Prev folder')
	call(["mpc", "-q", "play", str(mpc_prev_folder_pos())])
	
def mpc_stop():
	print('[MPC] Stopping MPC [pause]')
	call(["mpc", "-q", "pause"])

	
"""
def mpc_save_pos( source ):
	global dSettings
	if source == 1:
		mpc_save_pos_for_label ( dSettings['medialabel'] )	
	elif source == 2:
		mpc_save_pos_for_label ('locmus')
	elif source == 5:
		mpc_save_pos_for_label ('stream')
	elif source == 6:
		mpc_save_pos_for_label ('smb')
"""



def mpc_lkp( label ):

	#default
	pos = {'pos': 1, 'time': 0}

	#TODO!
	iThrElapsed = 20							 # Minimal time that must have elapsed into a track in order to resume position
	iThrTotal = 30								 # Minimal track length required in order to resume position
	
	# open pickle_file, if it exists
	pickle_file = sDirSave + "/mp_" + label + ".p"
	if os.path.isfile(pickle_file):
		print('[MPC] Retrieving last known position from lkp file: {0:s}'.format(pickle_file))
		try:
			dSavePosition = pickle.load( open( pickle_file, "rb" ) )
		except:
			print(' ... PICKLE: Loading {0:s} failed!'.format(pickle_file))
			return pos

		#otherwise continue:
		oMpdClient = MPDClient() 
		oMpdClient.timeout = 10                # network timeout in seconds (floats allowed), default: None
		oMpdClient.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
		oMpdClient.connect("localhost", 6600)  # connect to localhost:6600
		#playlist = oMpdClient.playlistid()
		psfind = oMpdClient.playlistfind('filename',dSavePosition['file'])
		oMpdClient.close()
		oMpdClient.disconnect()
		
		#in the unlikely case of multiple matches, we'll just take the first, psfind[0]
		if len(psfind) == 0:
			print(' ...  File not found in loaded playlist')
		else:
			pos['pos'] = int(psfind[0]['pos'])+1
			timeElapsed,timeTotal = map(int, dSavePosition['time'].split(':'))
			print('[MPC] Match found: {0}. Continuing playback at #{1}'.format(dSavePosition['file'],pos['pos']))
			print(' ...  Elapsed/Total time: {0}s/{1}s'.format(timeElapsed,timeTotal))
			if timeElapsed > iThrElapsed and timeTotal > iThrTotal:
				pos['time'] = str(timeElapsed)
				print(' ...  Elapsed time over threshold: continuing at last position.')
			else:
				print(' ...  Elapsed time below threshold or short track: restarting at beginning of track.')
		"""
		for x in playlist:
			print x['file']
			if x['file'] == dSavePosition['file']:
				pos['pos'] = int(x['pos'])+1
				timeElapsed,timeTotal = map(int, dSavePosition['time'].split(':'))
				print('[MPC] Match found: {0}. Continuing playback at #{1}'.format(x['file'],pos['pos']))
				print(' ...  Elapsed/Total time: {0}s/{1}s'.format(timeElapsed,timeTotal))
				if timeElapsed > iThrElapsed and timeTotal > iThrTotal:
					pos['time'] = str(timeElapsed)
					print(' ...  Elapsed time over threshold: continuing at last position.')
				else:
					print(' ...  Elapsed time below threshold or short track: restarting at beginning of track.')
				break
		"""
# TODO --- NOT REQUIRED? IT WILL BE CREATED THE NEXT TIME THERE'S A PLAYER EVENT ANYWAY...
#	else:
#		print('[MPC] No position file available for this medium (first run?)')
#		mpc_save_pos_for_label (label)

	return pos

def mpc_populate_playlist ( label ):
	#global oMpdClient

	# Stop idle, in order to send a command
	#oMpdClient.noidle()
	
	xMpdClient = MPDClient() 
	xMpdClient.connect("localhost", 6600)  # connect to localhost:6600
		
	if label == 'locmus':
		xMpdClient.findadd('base',sLocalMusicMPD)
	if label == 'smb':
		xMpdClient.findadd('base',sSambaMusicMPD)
	elif label == 'stream':
		# Using the command line:
		#  ..but this generates some problems with special characters
		streams_file = sDirSave + "/streams.txt"
		#p1 = subprocess.Popen(["cat", streams_file], stdout=subprocess.PIPE)
		#p2 = subprocess.Popen(["mpc", "add"], stdin=p1.stdout, stdout=subprocess.PIPE)
		#p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
		#output,err = p2.communicate()		
		streams=open(streams_file,'r')
		with open(streams_file,'r') as streams:
			for l in streams:
				uri = l.rstrip()
				if not uri[:1] == '#' and not uri == '':
					uri_OK = url_check(uri)
					if uri_OK:
						print(' ....  . Stream OK: {0}'.format(uri))
						call(["mpc", "-q", "add", uri])
					else:
						print(' ....  . Stream FAIL: {0}'.format(uri))
	else:
		xMpdClient.findadd('base',label)
	
	xMpdClient.close()
	
	#oMpdClient.send_idle()


def mpc_playlist_is_populated():
	# Old method using mpc on the commandline:
	"""
	task = subprocess.Popen("mpc playlist | wc -l", shell=True, stdout=subprocess.PIPE)
	mpcOut = task.stdout.read()
	assert task.wait() == 0
	return mpcOut.rstrip('\n')
	"""
	# New method, using mpd status
	xMpdClient = MPDClient() 
	xMpdClient.connect("localhost", 6600)  # connect to localhost:6600
	xMpdClient.command_list_ok_begin()
	xMpdClient.status()
	results = xMpdClient.command_list_end()
	xMpdClient.close()
	return results[0]['playlistlength']
	

def mpc_db_label_exist( label ):
	print('[MPC] Checking if {0} occurs in the MPD database'.format(label))
	taskcmd = "mpc ls "+label+" | wc -l"
	task = subprocess.Popen(taskcmd, shell=True, stdout=subprocess.PIPE)
	mpcOut = task.stdout.read()
	assert task.wait() == 0
	
	if mpcOut.rstrip('\n') == '0':
		print(' ...  directory not found in mpd database')
		return False
	else:
		print(' ...  directory found in mpd database')
		return True
	
