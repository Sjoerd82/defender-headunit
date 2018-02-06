#!/usr/bin/python

import time

#load json source configuration
import json

#dynamic module loading
import sys, inspect

#starting plugins in separate thread
import threading
import subprocess

# support modules
from hu_utils import *
from hu_settings import *
from hu_mpd import *

# DBUS STUUF,, ALL REQUIRED???
import dbus, dbus.service, dbus.exceptions
import sys
from dbus.mainloop.glib import DBusGMainLoop
import gobject

# qeueing
from Queue import Queue
from multiprocessing import Process

# GLOBAL vars
Sources = SourceController()	#TODO: rename "Sources" -- confusing name
mpdc = None

# CONSTANTS
CONFIG_FILE_DEFAULT = '/mnt/PIHU_APP/defender-headunit/config/configuration.json'
CONFIG_FILE = '/mnt/PIHU_CONFIG/configuration.json'
VERSION = "1.0.0"

hu_details = { 'track':None, 'random':'off', 'repeat':True }

def volume_att_toggle():
	return None

def volume_up():
	print('Vol Up')
	return None

def volume_down():
	print('Vol Down')
	return None
	
# ********************************************************************************
# Output wrapper
#
def printer( message, level=20, continuation=False, tag='SYSTEM' ):
	print( "{0} {1}".format(level, message))


def cb_remote_btn_press ( func ):

	global Sources
	global cSettings

	# Handle button press
	if func == 'SHUFFLE':
		print('\033[95m[BUTTON] Shuffle\033[00m')
		set_random( 'toggle' )
	elif func == 'SOURCE':
		print('\033[95m[BUTTON] Next source\033[00m')
		pa_sfx('button_feedback')
		printer('Blocking Queue Size before: {0}'.format(qBlock.qsize()))
		
		try:
			qBlock.put("SOURCE", False)
		except Queue.Full:
			printer('Queue is full.. ignoring button press.')

		printer('Blocking Queue Size after: {0}'.format(qBlock.qsize()))
		return 0
		
	elif func == 'ATT':
		print('\033[95m[BUTTON] ATT\033[00m')
		pa_sfx('button_feedback')
		volume_att_toggle()
	elif func == 'VOL_UP':
		print('\033[95m[BUTTON] VOL_UP\033[00m')		
		pa_sfx('button_feedback')
		qPrio.put("VOL_UP", False)
		qPrio.put('BLANK2', False)
		return 0
	elif func == 'VOL_DOWN':
		print('\033[95m[BUTTON] VOL_DOWN\033[00m')
		pa_sfx('button_feedback')
		qPrio.put("VOL_DOWN", False)
		return 0
	elif func == 'SEEK_NEXT':
		print('\033[95m[BUTTON] Seek/Next\033[00m')
		pa_sfx('button_feedback')
		qBlock.put("SEEK_NEXT", False)
	elif func == 'SEEK_PREV':
		print('\033[95m[BUTTON] Seek/Prev.\033[00m')
		pa_sfx('button_feedback')
		qBlock.put("SEEK_PREV", False)
	elif func == 'DIR_NEXT':
		print('\033[95m[BUTTON] Next directory\033[00m')
		dir_next()
	elif func == 'DIR_PREV':
		print('\033[95m[BUTTON] Prev directory\033[00m')
		#if dSettings['source'] == 1 or dSettings['source'] == 2 or dSettings['source'] == 6:
		#	pa_sfx('button_feedback')
		#	#mpc_prev_folder()
		#else:
		#	pa_sfx('error')
		#	print(' No function for this button! ')
	elif func == 'UPDATE_LOCAL':
		print('\033[95m[BUTTON] Updating local MPD database\033[00m')
		pa_sfx('button_feedback')
		#locmus_update()
	elif func == 'OFF':
		print('\033[95m[BUTTON] Shutting down\033[00m')
		pa_sfx('button_feedback')
		shutdown()
	else:
		print('Unknown button function')
		pa_sfx('error')

def cb_mpd_event( event ):
	global Sources
	global settings
	global mpdc

	printer('DBUS event received: {0}'.format(event), tag='MPD')

	# anything related to the player	
	if event == "player":
	
		# first let's determine the state:	
		status = mpdc.mpc_get_status()
		#print "STATUS: {0}.".format(status)
		#print "STATE : {0}.".format(status['state'])
		
		if 'state' in status:
			if status['state'] == 'stop':
				print 'detected that mpd playback has stopped.. ignoring this'
			elif status['state'] == 'pause':
				print 'detected that mpd playback has paused.. ignoring this'
			elif status['state'] == 'play':
				print "do stuff for play"
	
	#	currSrc = Sources.get( None )
		
		
		
		
	# OLD, NEEDS UPDATE: #todo
	#	if not currSrc == None:
	#		if 'label' in currSrc:
	#			mpc_save_pos_for_label( currSrc['label'], "/mnt/PIHU_CONFIG" )
	#		else:
	#			mpc_save_pos_for_label( currSrc['name'], "/mnt/PIHU_CONFIG" )

		""" PROBLEMS AHEAD
		
		#hu_details
		mpcSong = mpdc.mpc_get_currentsong()
		#mpcStatus = mpdc.mpc_get_status()
		mpcTrackTotal = mpdc.mpc_get_trackcount()
			
		if 'artist' in mpcSong:
			artist = mpcSong['artist']
		else:
			artist = None

		if 'title' in mpcSong:
			title = mpcSong['title']
		else:
			title = None
			
		if 'track' in mpcSong:
			track = mpcSong['track']
		else:
			track = None
		
		file = os.path.basename(mpcSong['file'])
		
		#disp.lcd_play( artist, title, file, track, mpcTrackTotal )
		"""
				
	elif event == "update":
		printer(" ...  database update started or finished (no action)", tag='MPD')
		
	elif event == "database":
		printer(" ...  database updated with new music #TODO", tag='MPD')
		
	elif event == "playlist":
		priner(" ...  playlist changed (no action)", tag='MPD')
	#elif event == "media_removed":
	#elif event == "media_ready":
	
	elif event == "ifup":
		printer(" ...  WiFi interface up: checking network related sources", tag='MPD')
		stream_check()
		smb_check()
		
	elif event == "ifdown":
		printer(" ...  WiFi interface down: marking network related sources unavailable", tag='MPD')
		Sources.setAvailable('depNetwork',True,False)
		
	else:
		printer(' ...  unknown event (no action)', tag='MPD')
		
# Timer 1: executed every 30 seconds
def cb_timer1():

	global cSettings
	#global disp

	printer('Interval function [30 second]', level=LL_DEBUG, tag="TIMER1")

	# save settings (hu_settings)
	#cSettings.save()
	
	#hudispdata = {}
	#hudispdata['src'] = "USB"		#temp.
	#disp.dispdata(hudispdata)

	return True

#Timer 2: Test the queuing
def cb_timer2():
	qPrio.put('VOL_UP',False)
	return True
	

def worker_queue_prio():
	while True:
	#	while not qPrio.empty():
		item = qPrio.get()
		#item = qPrio.get_nowait()
		print "QUEUE WORKER PRIO: {0}".format(item)
		#if item == 'VOL_UP':
		#	print "volume_up()"
		#elif item == 'VOL_DOWN':
		#	print "volume_down()"
		qPrio.task_done()

def worker_queue_blocking():
	global Sources

	while True:
	#while not qBlock.empty():
		item = qBlock.get()
		print "QUEUE WORKER BLOCK: {0}".format(item)
		if item == 'SOURCE':
			do_source()
		elif item == 'SEEK_NEXT':
			Sources.sourceSeekNext()
		elif item == 'SEEK_PREV':
			Sources.sourceSeekPrev()
		else:
			print 'UNKNOWN TASK'
		qBlock.task_done()

def worker_queue_async():
	while True:
		item = qAsync.get()
		print "QUEUE WORKER ASYNC: {0}".format(item)
		qAsync.task_done()

		
#********************************************************************************
#
# DBus Dispay Signals
#

class dbusDisplay(dbus.service.Object):
	def __init__(self, conn, object_path='/com/arctura/display'):
		dbus.service.Object.__init__(self, conn, object_path)

	#decided to just send everything as string, should be easier to handle...:
	#dbus.service.signal("com.arctura.display", signature='a{sv}')
	@dbus.service.signal("com.arctura.display", signature='a{ss}')
	def dispdata(self, dispdata):
		pass

#********************************************************************************
#
# Initialization
#

threads = []
# loop through the control plugin dir
for filename in os.listdir( configuration['directories']['controls'] ):
		#if filename.startswith('') and
		if filename.endswith('.py'):
			pathfilename = os.path.join( configuration['directories']['controls'], filename )
			t = threading.Thread(target=plugin_execute, args=(pathfilename,))
			t.setDaemon(True)
			threads.append(t)
			#t.start()	WORKAROUND

# loop through the output plugin dir
for filename in os.listdir( configuration['directories']['output'] ):
		#if filename.startswith('') and
		if filename.endswith('.py'):
			pathfilename = os.path.join( configuration['directories']['output'], filename )
			t = threading.Thread(target=plugin_execute, args=(pathfilename,))
			t.setDaemon(True)
			threads.append(t)
			#t.start()	WORKAROUND

# NOTE: Plugins are now loading in the background, in parallel to code below.
# NOTE: This can really interfere, in a way I don't understand.. executing the threads later helps... somehow..
# NOTE: For NOW, we'll just execute the threads after the loading of the "other" plugins...


#
# Load mpd dbus listener
#
#
t = threading.Thread(target=plugin_execute, args=('/mnt/PIHU_APP/defender-headunit/dbus_mpd.py',))
t.setDaemon(True)
threads.append(t)



# WORKAROUND...
for t in threads:
	t.start()

# LCD (TODO: move to plugins)
#from hu_lcd import *
#disp = lcd_mgr()
#disp.lcd_text('Welcome v0.1.4.8')

# MPD
mpdc = mpdController()

#
# end of initialization
#
#********************************************************************************
myprint('INITIALIZATION FINISHED', level=logging.INFO, tag="SYSTEM")


#********************************************************************************
#
# Mainloop
#
#def main():

#
# Setting up worker threads
#
printer('Setting up queues and worker threads')

# Short stuff that can run anytime:
qPrio = Queue(maxsize=0)	# 0 = infinite
qPrio.put('BLANK', False)

# Blocking stuff that needs to run in sequence
qBlock = Queue(maxsize=4)	# 0 = infinite

# Long stuff that can run anytime (but may occasionally do a reality check):
qAsync = Queue(maxsize=4)	# 0 = infinite

t1 = threading.Thread(target=worker_queue_prio)
#p1 = Process(target=worker_queue_prio)
t1.setDaemon(True)
#p1.daemon = True
t1.start()
#p.join()

t2 = threading.Thread(target=worker_queue_blocking)
#p2 = Process(target=worker_queue_blocking)
t2.setDaemon(True)
#p2.daemon = True
t2.start()

t3 = threading.Thread(target=worker_queue_async)
#p3 = Process(target=worker_queue_async)
t3.setDaemon(True)
#p3.daemon = True
t3.start()

"""
qBlock.put("SOURCE")
qPrio.put("VOL_UP")
qBlock.put("NEXT")
qPrio.put("VOL_UP")
qPrio.put("VOL_ATT")
qBlock.put("SHUFFLE")
qPrio.put("SHUTDOWN")

exit()
"""

#********************************************************************************
#
# Main loop
#

#
# Initialize the mainloop
#
DBusGMainLoop(set_as_default=True)


#
# main loop
#
mainloop = gobject.MainLoop()


#
# 30 second timer
#
gobject.timeout_add_seconds(30,cb_timer1)
gobject.timeout_add_seconds(5,cb_timer2)

#
# DBus: system bus
# On a root only embedded system there may not be a usable session bus
#
bus = dbus.SystemBus()

# Output
disp = dbusDisplay(bus)


"""
time.sleep(5)	#wait for the plugin to be ready

hudispdata = {}
hudispdata['rnd'] = "1"
hudispdata['artist'] = "The Midnight"
disp.dispdata(hudispdata)

time.sleep(5)
hudispdata = {}
hudispdata['rnd'] = "0"
disp.dispdata(hudispdata)

time.sleep(5)
hudispdata = {}
hudispdata['att'] = "1"
disp.dispdata(hudispdata)

exit()
"""
#
# Connect Callback functions to DBus Signals
#
bus.add_signal_receiver(cb_mpd_event, dbus_interface = "com.arctura.mpd")
bus.add_signal_receiver(cb_remote_btn_press, dbus_interface = "com.arctura.remote")

#
# Start the blocking main loop...
#
try:
	mainloop.run()
finally:
	mainloop.quit()


# TODO
# problem is that the setup() imports modules, yielding: SyntaxWarning: import * only allowed at module level
# another issue is that all global vars need to be defined (not really a problem i think..)
"""
if __name__ == '__main__':
	setup()
	main()
"""
	