#
# Messaging layer
# Venema, S.R.G.
# 2018-03-17
#
# Abstracted communication layer.
#
# Currently a wrapper for ZeroMQ Pub/Sub, but can be adapted to accommodate
# any other MQ software
#

import zmq
import time
import sys
from logging import getLogger	# logger

sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *


def printer( message, level=LL_INFO, tag="", logger_name=__name__):
	logger = logging.getLogger(logger_name)
	logger.log(level, message, extra={'tag': tag})


#********************************************************************************
# ZeroMQ
#

def zmq_send(publisher, message):

	#global publisher

	#data = { "cmd:" cmd }
	#data = json.dumps(message)
	#data = cmd
	#printer("Sending message: {0} {1}".format(path_send, data))
	publisher.send(message)
	time.sleep(1)
	
def zmq_recv(subscriber):
	message = subscriber.recv()
	return message

def zmq_recv_async(subscriber):

	try:
		message = subscriber.recv(zmq.NOBLOCK)
	except zmq.ZMQError:
		message = None
		
	return message
	
#********************************************************************************
# ZeroMQ Wrapper
#

class MessageController():

	def __init__(self):

		# Context
		self.context = zmq.Context()
		
		# Pub-Sub
		self.publisher = None
		self.subscriber = None
		self.topics = []
		
		# Req-Rep
		self.server = None
		self.client = None

		# Poller
		self.poller = zmq.Poller()
		
	def start_server(self, address):
		self.server = self.context.socket(zmq.REP)
		#self.client = context.socket(zmq.REQ)
		self.server.bind(address)
		time.sleep(1)
		
	# todo: args: which sockets to poll?
	def poll_register(self):
		self.poller.register(self.server, zmq.POLLIN)
		self.poller.register(self.subscriber, zmq.POLLIN)
	
	def poll(self):
		socks = dict(self.poller.poll())
		return socks
	
	#todo: port numbers ?
	#todo: rename to connect_pub_sub or something..
	#def connect(self):
	def connect(self):

		self.subscriber = self.context.socket (zmq.SUB)
		port_server = "5560" #TODO: get port from config
		self.subscriber.connect ("tcp://localhost:{0}".format(port_server)) # connect to server

		port_client = "5559"
		self.publisher = self.context.socket(zmq.PUB)
		self.publisher.connect("tcp://localhost:{0}".format(port_client))
	
		#self.publisher, self.subscriber = zmq_connect(self.publisher, self.subscriber)		
		# todo: check if connected
		# return True/False
		return True

	
	def subscribe(self, topic):
		self.subscriber.setsockopt (zmq.SUBSCRIBE, topic)
		return True
		
	def send_command(self, path, command, **kwargs):
		message = "{0} {1}".format(path, command)
		print("sending: {0}".format(message))
		retval = zmq_send(self.publisher, message)
		return retval

	"""
	def send_command_return(self, path, return_path, command, **kwargs=None):
		message =
		retval = zmq_send(publisher, message)
		return retval
	"""

	def send_data(self, path, payload, retval='200'):
		# todo: check if already prefixed with "/data"-topic
		data={}
		data['retval'] = retval
		data['payload'] = payload
		message = '{0} {1}'.format(path,data)
		print("sending: {0}".format(message))
		retval = zmq_send(self.publisher, message)
		return retval	
	
	# Blocking function
	def receive(self, ):
		received = zmq_recv(self.subscriber)
		return received

	# Asynch version
	def receive_async(self):
		received = zmq_recv_async(self.subscriber)
		return received
	
	def receive_poll(self,path,timeout):
		self.subscriber.setsockopt(zmq.SUBSCRIBE, path)
		print("Waiting for {0}ms for a message on {1}".format(timeout,path))
		retval = self.subscriber.poll(timeout,zmq.POLLIN)
		if retval == 0:
			print "NOTHING RECEIVED WITHIN TIMEOUT"
			return None
		else:
			received = zmq_recv(self.subscriber)
			return received
	
	def recv_data(self):
		zmq_recv(self.subscriber)
	
	#def recv_message(self):
	
	def parse_message(self, message):
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
		
		parsed_message = {}
		parsed_message['path'] = path
		parsed_message['cmd'] = command
		parsed_message['args'] = params
		return parsed_message
		