#!/usr/bin/python

#
# PulseAudio Volume Control
# Venema, S.R.G.
# 2018-03-11
#
# PulseAudio volume control is controls PulseAudio sinks over ZeroMQ.
#

import sys
import os
import time

# ZeroMQ
import zmq

# PulseAudio
from subprocess import call
from subprocess import Popen, PIPE

# Utils
sys.path.append('../modules')
from hu_utils import *


#********************************************************************************
# GLOBAL vars & CONSTANTS
#
CONTROL_NAME='pactrl'

# zmq
subscriber = None
publisher = None

# ********************************************************************************
# Output wrapper
#

# TODO!!! the "headunit"-logger is no longer accessible once this script is started "on its own"..
def myprint( message, level, tag ):
	print("[{0}] {1}".format(tag,message))

def printer( message, level=20, continuation=False, tag="d1606a" ):
	#TODO: test if headunit logger exist...
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )

# ********************************************************************************
# Zero MQ functions
#
def zmq_connect():

	global publisher
	
	printer("Connecting to ZeroMQ forwarder")

	zmq_ctx = zmq.Context()

	subscriber = zmq_ctx.socket (zmq.SUB)
	port_server = "5560" #TODO: get port from config
	subscriber.connect ("tcp://localhost:{0}".format(port_server)) # connect to server

	port_client = "5559"
	publisher = zmq_ctx.socket(zmq.PUB)
	publisher.connect("tcp://localhost:{0}".format(port_client))
	
	#
	# Subscribe to topics
	#
	topics = ['/volume']
	for topic in topics:
		subscriber.setsockopt (zmq.SUBSCRIBE, topic)

	
def zmq_send(path_send,message):

	global publisher

	#TODO
	#data = json.dumps(message)
	data = message
	printer("Sending message: {0} {1}".format(path_send, data))
	publisher.send("{0} {1}".format(path_send, data))

def parse_message(message):
		path = []
		params = []
		path_cmd = message.split(" ")
		for pathpart in path_cmd[0].split("/"):
			if pathpart:
				path.append(pathpart.lower())
			
		base_topic = path[0]
		cmd_par = path_cmd[1].split(":")

		if len(cmd_par) == 1:
			command = cmd_par[0].lower()
		elif len(cmd_par) == 2:
			command = cmd_par[0].lower()
			param = cmd_par[1]

			for parpart in param.split(","):
				if parpart:
					params.append(parpart)
		else:
			print("Malformed message!")
			return False

		print("[MQ] Received Path: {0}; Command: {1}; Parameters: {2}".format(path,command,params))
		
		# TODO: handle message
		"""
		item = []	# or set?
		# check if base_topic ('player','event', etc.) function exists
		if base_topic in globals():
			# remove first item (base topic)
			del path[0]
			# if queue is empty, execute right away, else add to queue
			if queue_actions.empty():
				# execute:
				globals()[base_topic](path, command, params)
			else:
				# put in queue:
				item.append(base_topic)
				item.append(path)
				item.append(command)
				item.append(params)
				queue_actions.put(item, False) # False=Non-Blocking
		"""

"""
# ********************************************************************************
class dbusService( dbus.service.Object ):

	def __init__( self, bus_name ):
		#ehm?
		super(dbusService,self).__init__(bus_name, "/com/arctura/volume")

		
class pa_volume_handler():

	VOL_INCR = "5%"

	def __init__(self, sink):
		self.pa_sink = sink

	def vol_set_pct(self, volume):
		#vol_pct = str(volume) + "%"
		vol_pct = volume
		call(["pactl", "set-sink-volume", self.pa_sink, vol_pct])
		
	def vol_up(self):
		vol_chg = "+" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.pa_sink, vol_chg])
		
	def vol_down(self):
		vol_chg = "-" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.pa_sink, vol_chg])

	def vol_get(self):
		#pipe = Popen("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'")
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		vol = subprocess.check_output("/root/pa_volume.sh")
		return int(vol.splitlines()[0])

		
# callback, keep it short! (blocks new input)
def cb_volume( volume ):

	printer('DBUS event received: {0}'.format(volume), tag='volume')
	pavh.vol_set_pct(volume)
		
	return True
			
pavh = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')
"""

def setup():

	# ZMQ
	zmq_connect()
	printer('Initialized [OK]')

	
def main():

	while True:
		message = subscriber.recv()
		parse_message(message)
	

if __name__ == "__main__":
	setup()
	main()
	
