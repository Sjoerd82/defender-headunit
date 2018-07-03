#
# Wrapper for python-mpd2
# Venema, S.R.G.
# 2018-03-27
#
# This is a WRAPPER for python-mpd2
# https://pypi.python.org/pypi/python-mpd2
#
# Provide a logger object to __init__ to get output from this class.
#
# TODO:
# - add wrapper decorator for connection test
#
# MpdController()
#
# CONTROL & PLAYBACK
# play					Play
# pause					Pause
# stop					Stop
# next					Next track
# prev					Prev track
# seek					Seek
# random				Set Random mode
# repeat				Set Repeat mode
#
# DATABASE
# is_dbdir				Checks if given directory is in database
# update_db				Updates database
#
# INFO, STATS & METADATA
# state					Returns {state}
# track					Returns {track}
# stats					Returns {stats} #TODO
#
# PLAYLIST
# pls_load				Load playlist
# pls_pop_dir			Populate playlist for given MPD directory, return count
# pls_pop_streams		Populate playlist with streaming URLs
# pls_is_populated		Check if the playlist is populated (deprecate?)
# pls_dirs				Generate a directory-playlist position mapping
# pls_clear				Clear playlist
#
# STREAMING
#
# strm_load_file?
#
# locmus.py [OK]
# media.py [OK]
# smb.py [OK]
#
# playlistClear		=> pls_clear
# playlistPop		=> pls_pop
# playlistIsPop		=> pls_is_populated
# dbCheckDirectory	=> is_dbdir
# update_call		-> } update_db
# update			=> }
# lastKnowPos	-> MOVE
# lastKnowPos2	-> MOVE
# playStart			=> play
# mpc_get_PlaylistDirs	=> pls_dirs
# mpc_get_currentsong	=> track
# mpc_get_status		=> state
# mpc_get_trackcount	deprecate?
# channelSubscribe		=> REMOVED
# nextTrack			=> next
# prevTrack			=> prev
# stop				=> stop
# random

"""
mpc_random_get
mpc_random_get
mpc_get_PlaylistDirs
mpc_current_folder
mpc_next_folder_pos
mpc_prev_folder_pos
mpc_next_folder
mpc_prev_folder
mpc_stop
mpc_lkp
mpc_populate_playlist
mpc_db_label_exist
"""
#

import os
import sys
from subprocess import call
from mpd import MPDClient, MPDError
from mpd import ConnectionError as MPDConnectionError
from mpd import CommandError as MPDCommandError

from hu_utils import *

LOG_TAG = 'MPD'

# 
# Check: https://github.com/Mic92/python-mpd2/pull/92
# This Wrapper might not be needed anymore when upgrading to the latest library version
#
class MPDClientWrapper(object):

	def __init__(self, *args, **kwargs):
		self.__dict__['_mpd'] = MPDClient(*args, **kwargs)

	def __getattr__(self, name):
		a = self._mpd.__getattribute__(name)
		if not callable(a): return a

		def b(*args, **kwargs):
			try:
				return a(*args, **kwargs)
			#except (MPDConnectionError, mpd.ConnectionError) as e:
			except:
				cargs, ckwargs = self.__dict__['_connect_args']
				self.connect(*cargs, **ckwargs)
				return a(*args, **kwargs)

		return b

	def __setattr__(self, name, value):
		self._mpd.__setattr__(name, value)

	def connect(self, *args, **kwargs):
		self.__dict__['_connect_args'] = args, kwargs
		self.disconnect()
		self._mpd.connect(*args, **kwargs)

	def disconnect(self):
		try:
			self._mpd.close()
			self._mpd.disconnect()
		#except (MPDConnectionError, mpd.ConnectionError) as e:
		#    pass
		finally:
			self._mpd._reset()

class MpdController(object):

	def __printer( self, message, level=LL_INFO, tag=LOG_TAG):
		self.logger.log(level, message, extra={'tag': tag})

	def __init__( self, logger, repeat=1, random=0 ):
		self.logger = logger
		self.pls_dir_pos = []		# list of start positions of directories in the playlist
		
		# Connect to MPD
		try:
			self.__printer('Initializing MPD client', level=LL_DEBUG)
			#self.mpdc = MPDClientWrapper()		# per instance !
			self.mpdc = MPDClient()		# per instance !
			self.mpdc.timeout = None			# network timeout in seconds (floats allowed), default: None
			self.mpdc.idletimeout = None		# timeout for fetching the result of the idle command is handled seperately, default: None
			self.mpdc.connect("localhost", 6600)
			self.__printer(' > Version: {0}'.format(self.mpdc.mpd_version), level=LL_DEBUG)          # print the MPD version
			self.mpdc.random(random)
			self.mpdc.repeat(repeat)	
			#self.mpdc.idle()		#keep the connection open... But this blocks :(
			self.mpdc.send_idle()	#keep the connection open... Non-blocking..
		except:
			self.__printer('Failed to connect to MPD server: {0}'.format(sys.exc_info()[0]), level=LL_ERROR)
			
		# populate self.pls_dir_pos
		self.pls_gather_dir_pos()
	
	def __test_conn(self):

		"""
		test = self.mpdc.connect("localhost", 6600)
		print test
		
		self.mpdc.noidle()
		
		"""
		result = True
		try:
			self.mpdc.noidle()
		except MPDConnectionError as e:
			self.mpdc.connect("localhost", 6600)
			result = False
		except:
			self.__printer('WEIRD... no idle was set..')
			
		return result
	
	def __return_to_idle(self):
		self.mpdc.send_idle()

	def _mpdconnect(self):
		"""
		Decorator function.
		Test connection and attempts to reconnect if not connected.
		Reinstitutes idle state
		"""
		def decorator(self,fn):
		
			def wrapper(self,*args,**kwargs):
			
				# check if idle set
				result = True
				try:
					self.mpdc.noidle()
				except MPDConnectionError as e:
					self.mpdc.connect("localhost", 6600)
					result = False
				except:
					self.__printer('WEIRD... no idle was set..')
					
				ret = fn(self,*args,**kwargs)
				return ret
				
				self.mpdc.send_idle()
				
			return wrapper
		return decorator
		
	def play ( self, pos=None, time=0 ):
		#TODO: add id=None
		"""	Start playback
			Optionally provde:
				- position in playlist OR song id
				- time in track
		"""		
		self.__test_conn()
		if pos is not None: # and time is not None:
			self.seek(pos,time)
			self.mpdc.play(pos)	#TODO: pos param needed?
			#return True #?
		else:
			self.mpdc.play()
			
		self.__return_to_idle()
		return True

	@_mpdconnect
	def pause (self):
		self.mpdc.pause()
		
	@_mpdconnect
	def stop (self):
		self.mpdc.stop()
		
	@_mpdconnect
	def next(self, count=1):
		for i in range(count):
			try:
				self.mpdc.next()
			except MPDCommandError as e:
				self.__printer("ERROR: {0}".format(e),level=LL_ERROR)
				#TODO: what to do now?
		return True
			
	@_mpdconnect
	def prev(self, count=1):
		for i in range(count):
			self.mpdc.previous()

	@_mpdconnect
	def seek(self, seeksec='+1'):
		self.mpdc.seekcur(seeksec)

	@_mpdconnect
	def random(self, mode='next'):
		"""	Set random mode. Modes:
			- On / 1 / Playlist
			- Off / 0
			- Folder
			- Next, Prev
			Not supported:
			- Folder
			- Genre
			- Artist
		"""
		mode = str(mode).lower()
		if mode in ('on','1','playlist'):
			#subprocess.call(["mpc", "-q", "random", "on"])
			#subprocess.call(["mpc", "-q", "next"])
			self.mpdc.random(1)
		elif mode in ('off','0'):
			#subprocess.call(["mpc", "-q", "random", "off"])
			self.mpdc.random(0)
		elif mode in ('folder'):
			#todo
			pass
		elif mode in ('next','toggle'):
			#TODO: current_mode = self.mpdc.status()
			print('[MPC] Next random mode')
			subprocess.call(["mpc", "-q", "random"])
		
	@_mpdconnect
	def repeat(self, mode='toggle'):
		"""	Set random mode. Modes:
			- On (1)
			- Off (0)
			- Toggle
		"""
		if mode in ('on','1'):
			self.mpdc.repeat(1)
		elif mode in ('off','0'):
			self.mpdc.repeat(0)
		# toggle
		else:
			#todo
			pass
	
	@_mpdconnect
	def is_dbdir(self, directory):
		#if self.__test_conn() == False:
		#	return False
		
		self.__printer("Checking existance of folder in MPD db..")
		taskcmd = "mpc listall "+directory+" | wc -l"
		# if directory is not in mpd db, "mpd error: No such directory" will be returned
		task = subprocess.Popen(taskcmd, shell=True, stdout=subprocess.PIPE)
		mpcOut = task.stdout.read()
		assert task.wait() == 0
		
		if mpcOut.rstrip('\n') == '0':
			self.__printer(' > {0}: nothing in the database for this source.'.format(directory))
			#self.__return_to_idle()
			return False
		else:
			self.__printer(' > {0}: found {1:s} tracks'.format(directory,mpcOut.rstrip('\n')))
			#self.__return_to_idle()
			return True
	
	@_mpdconnect
	def update (self, directory, wait=True):
		
		self.__printer('Updating database for location: {0}'.format(directory))
		#self.__test_conn()

		#Sound effect
		#pa_sfx('mpd_update_db')

		#Update
		if wait:
			self.__printer(' > Please wait, this may take some time...')
			self.mpdc.update(directory)
			self.__printer(' > Update finished')
		else:
			self.mpdc.update(directory)

		self.mpdc.command_list_ok_begin()
		self.mpdc.status()
		results = self.mpdc.command_list_end()
		
		#self.__return_to_idle()
		print results
	
	@_mpdconnect	
	def state(self):
		"""
		Return State
		"""
		#self.__test_conn()
		#mpd_state = self.mpdc.status()
		state = {}
		#self.__return_to_idle()
		return state

	@_mpdconnect
	def track(self):
		"""
		Return track details
		"""
		#self.__test_conn()
		results = self.mpdc.currentsong()
		#self.__return_to_idle()
		#{'album': 'Exodus', 'composer': 'Andy Hunter/Tedd T.', 'title': 'Go', 'track': '1', 'duration': '411.480', 'artist': 'Andy Hunter', 'pos': '0', 'last-modified': '2013-10-12T15:53:13Z', 'albumartist': 'Andy Hunter', 'file': 'PIHU_SMB/music/electric/Andy Hunter/Andy Hunter - 2002 - Exodus/01 - Andy Hunter - Go.mp3', 'time': '411', 'date': '2002', 'genre': 'Electronic/Dance', 'id': '44365'}
		return results
	
	@_mpdconnect
	def next_folder():
		"""
		Plays first track of next folder and turns off random
		Replaces: mpc_next_folder
		"""	
		curr_pos = self.__pls_pos_curr()
		
		# update dir playlist positions
		if len(self.pls_dir_pos) == 0 and curr_pos >0:
			self.pls_gather_dir_pos()		
		
		next_pos = self.__pls_pos_next_dir(curr_pos)
		try:
			self.mpdc.play(next_pos)
		except MPDCommandError as e:
			self.__printer("ERROR: {0}".format(e),level=LL_ERROR)
				
	# --- PLAYLIST
	
	'''TODO
	def pls_load(self):
		"""	Load playlist
		"""
	`'''
	
	def pls_pop_dir(self, location):
		"""	Populate playlist for given MPD directory
			Returns: count
		"""
		self.__printer('Populating playlist, folder: {0}'.format(location))
		self.__test_conn()
	
		try:		
			#self.mpdc.command_list_ok_begin()
			self.mpdc.findadd('base',location)
			results = self.mpdc.status()	# get count
			#results = self.mpdc.command_list_end()
		except:
			self.__printer('ERROR: folder not in MPD database?')
		
		#self.mpdc.play()
		self.__return_to_idle()
				
		if 'playlistlength' in results:
			return results['playlistlength']
		#if results is None:
		#	return None
		# ?
		#elif 'playlistlength' in results[0]:
		#	return results[0]['playlistlength']
		else:
			return None

	def pls_pop_streams(self, streams):
		"""Populate playlist with given list of streams """
		self.__printer('Populating playlist')
		self.__test_conn()
		for stream in streams:
			self.mpdc.add(stream)
		self.__return_to_idle()
		
	def pls_is_populated(self):
		"""	Check if the playlist is populated (deprecate?)
		"""
		self.__printer('Checking if playlist is populated')
		self.__test_conn()
		
		self.mpdc.command_list_ok_begin()
		self.mpdc.status()
		results = self.mpdc.command_list_end()
		self.__return_to_idle()

		return results[0]['playlistlength']
		
	def pls_dirs(self):
		"""
		Return a directory-playlist position mapping
		"""
		return self.pls_dir_pos

	def __pls_pos_curr(self):
		"""
		Return current playlist position
		"""
		status = self.mpdc.status()
		if 'song' in status:
			return status['song']
		
	def __pls_pos_next_dir(self, current_pos=0):
		"""
		Return playlist position of next directory
		"""
		if current_pos == 0:
			return 1
		
		if len(self.pls_dir_pos) == 0:
			return
		
		for dir_pos in self.pls_dir_pos:
			if dir_pos > current_pos:
				return dir_pos
		
		# wrap around
		return 1
		
	def pls_clear(self):
		"""	Clear playlist
		"""
		self.__printer('Emptying MPD playlist')
		#todo: how about cropping, populating, and removing the first? item .. for faster continuity???
		#self.mpdc.command_list_ok_begin()

		"""
		try:
			self.mpdc.noidle()
		except MPDConnectionError:
			self.mpdc.connect("localhost", 6600)
		except:
			printer('WEIRD... no idle was set..')
		
		try:
			self.mpdc.stop()
			self.mpdc.clear()
		except:
			printer('Dont know why but this sometimes failes!!!! Investigate..',level=LL_CRITICAL)
		
		self.mpdc.send_idle()
		"""
		#print self.mpdc.command_list_end()
		subprocess.call(["mpc", "-q", "stop"])
		subprocess.call(["mpc", "-q", "clear"])
	# --
		
	#def mpc_get_PlaylistDirs( self ):
	def pls_gather_dir_pos(self):

		self.__printer('Building playlist directory structure...')

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
		
	def mpc_get_status( self ):
		self.__test_conn()

		self.mpdc.command_list_ok_begin()
		self.mpdc.status()

		results = self.mpdc.command_list_end()
		self.__return_to_idle()
		
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
		
	# --- OUTPUTS
	def outputs(self):
		self.mpdc.noidle()
		outputs = self.mpdc.outputs()
		print type(outputs)
		self.mpdc.send_idle()
		return outputs

	def output_enable(self, id):
		self.mpdc.noidle()
		self.mpdc.enableoutput(id)
		self.mpdc.send_idle()
		
	def output_disable(self, id):
		self.mpdc.noidle()
		self.mpdc.disableoutput(id)
		self.mpdc.send_idle()
			

# Migrate
'''
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
		subprocess.call(["mpc", "-q", "random", "on"])
		subprocess.call(["mpc", "-q", "next"])

	# off
	elif state == 'off':
		print('[MPC] Random OFF')
		subprocess.call(["mpc", "-q", "random", "off"])

	# toggle
	else: 
		print('[MPC] Toggling random')
		subprocess.call(["mpc", "-q", "random"])
	
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
	subprocess.call(["mpc", "-q", "play", str(mpc_next_folder_pos())])
	# Shuffle Off

def mpc_prev_folder():
	print('[MPC] Prev folder')
	subprocess.call(["mpc", "-q", "play", str(mpc_prev_folder_pos())])
	
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
						subprocess.call(["mpc", "-q", "add", uri])
					else:
						print(' ....  . Stream FAIL: {0}'.format(uri))
	else:
		xMpdClient.findadd('base',label)
	
	xMpdClient.close()
	
	#oMpdClient.send_idle()


		
		
'''
