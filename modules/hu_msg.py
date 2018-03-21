#
# Messaging layer
# Venema, S.R.G.
# 2018-03-20
#
# A wrapper for ZeroMQ Pub/Sub
# 
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
"""
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
"""
	
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
		
		# Srv-Cli
		self.server = None
		self.server_topic = None
		self.client = None

		# Servers, access by address
		#self.servers = {}
		self.sockets = []
		self.addresses = {}
		
		# Client-Server
		self.is_server = None
		
		# Poller
		self.poller = zmq.Poller()
	
	# Setup a publisher to the given (forwarder) address
	# This function does not do a bind on the address, so it can be used in combination with a forwarder.
	def create_publisher(self, address):
		self.publisher = self.context.socket(zmq.PUB)
		self.publisher.connect(address)

	# Setup a subscription for the given address and topic(s)
	# The publisher does not need to be created first, necessarily.
	# This function also registers the subscription with the poller
	def create_subscriber(self, address, topics=['/']):
		self.subscriber = self.context.socket (zmq.SUB)
		self.subscriber.connect(address)
		for topic in topics:
			self.subscriber.setsockopt (zmq.SUBSCRIBE, topic)
		self.poller.register(self.subscriber, zmq.POLLIN)
		
	# Setup a server on the given address
	# This function does a bind, but it uses the PUB-SUB socket type to prevent deadlocks.
	# It should always return a message immediately after receiving one.
	# A unique topic must be given so the server can prefix it's output to be directed to the client.
	# This function also registers the server with a poller
	def create_server(self, server_address, topic):
		#self.server = self.context.socket(zmq.REP)
		# for supporting multiple servers, use this:
		"""
		self.servers[server_address] = self.context.socket(zmq.PUB)
		self.servers[server_address].bind(server_address)
		"""
		self.server = self.context.socket(zmq.PUB)
		self.server.bind(server_address)
		time.sleep(1)	# still needed when polling?

		self.is_server = True
		# also create a client for listening
		self.client = self.context.socket (zmq.SUB)
		self.client.setsockopt (zmq.SUBSCRIBE, topic)
		self.poller.register(self.client, zmq.POLLIN)
		

	# Setup a client on the given address. Use the same (unique) topic as used by the server
	# This function also registers the client with a poller
	def create_client(self, server_address, topic):
		#self.client = self.context.socket (zmq.REQ)
		self.client = self.context.socket (zmq.SUB)
		self.client.setsockopt (zmq.SUBSCRIBE, topic)
		self.client.connect(server_address)
		self.poller.register(self.client, zmq.POLLIN)
		
		# also create a publisher, but don't bind
		self.server = self.context.socket(zmq.PUB)
		
		# WE MUST NOT CALL CREATE_SERVER ANYMORE!
		self.is_server = False
		
		

	def publish_request(self, path, request, arguments):
		if request not in ('GET','PUT','POST','DEL'):
			return None
		message = "{0} {1}:{2}".format(path,request,arguments)	#TODO: add return path
		self.publisher.send(message)
		time.sleep(1)	# required?
	
	def publish_response(self, path, payload, retval='200'):
		data={}
		data['retval'] = retval
		data['payload'] = payload
		message = "{0} RESP {1}".format(path, data)
		self.publisher.send(message)
		time.sleep(1)	# required?

	def publish_event(self, path, payload):
		data={}
		data['retval'] = None
		data['payload'] = payload
		message = "{0} INFO {1}".format(path, data)
		self.publisher.send(message)
		time.sleep(1)	# required?
	
	# Request from CLIENT to SERVER; timeout in ms
	def client_request(self, path, request, arguments, timeout=5000):
		print "DEBUG: client_request()"
		message = "/srcctrl{0} {1}:{2}".format(path,request,arguments)
		# setup a temporary poller for the server socket
		reply_poller = zmq.Poller()
		reply_poller.register(self.client, zmq.POLLIN)
		# send client message to the server

		print "DEBUG: @SERVER (PUB) Sending message: {0}".format(message)
		self.server.send(message)
		# poll for a reply
		try:
			events = reply_poller.poll(timeout)
		except zmq.ZMQError:
			# No Message Available
			return None
		
		if events:
			# todo: have a look at what's returned?
			# read response from the server
			response = self.client.recv()
			return response
		else:
			return None
	#	return "bla!"
	
	# Response from SERVER to CLIENT
	def server_response(self, path, payload, retval='200'):
		data={}
		data['retval'] = retval
		data['payload'] = payload
		message = "{0} RESP {1}".format(path, data)
		self.server.send(message)
		time.sleep(1)	# required?
		
	#def send_event(self):
	#def send_data(self):
	
	# Return a tuple with the socket type and message, or None if no data
	# Possible socket types: server, subscriber (client doesn't poll here, it polls in the client_request function)
	def poll(self):
		print "DEBUG: poll()"
		socks = dict(self.poller.poll())
		print "DEBUG: poll returns: {0}".format(socks)
		msgtype = None
		message = None
		if self.server in socks:
			message = self.server.recv()
			msgtype = "server"
		if self.client in socks:
			message = self.client.recv()
			msgtype = "server"
		if self.subscriber in socks:
			message = self.subscriber.recv()
			msgtype = "subscriber"
		return msgtype, message

	def send_to_server(self, message):
		print "sending message: {0}".format(message)
		self.client.send(message)
		print "send_to_server() is waiting for a message...."
		retmsg = self.client.recv()
		print "....send_to_server() received a message"
		return retmsg
	
	def send_to_client(self, message):
		msg_json = json.dumps(message)
		self.server.send(msg_json)
	
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
		