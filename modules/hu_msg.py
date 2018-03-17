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



#********************************************************************************
# ZeroMQ
#

import zmq
import time

def zmq_connect(publisher, subscriber):

	#global subscriber
	#global publisher

	print("Connecting to ZeroMQ forwarder")
	
	zmq_ctx = zmq.Context()
	subscriber = zmq_ctx.socket (zmq.SUB)
	port_server = "5560" #TODO: get port from config
	subscriber.connect ("tcp://localhost:{0}".format(port_server)) # connect to server

	port_client = "5559"
	publisher = zmq_ctx.socket(zmq.PUB)
	publisher.connect("tcp://localhost:{0}".format(port_client))

	#context = zmq.Context()
	#subscriber = context.socket (zmq.SUB)
	#subscriber.connect ("tcp://localhost:5556")	# TODO: get port from config
	#subscriber.setsockopt (zmq.SUBSCRIBE, '')

	return publisher, subscriber
	

def zmq_send(publisher, message):

	#global publisher

	#data = { "cmd:" cmd }
	#data = json.dumps(message)
	#data = cmd
	#printer("Sending message: {0} {1}".format(path_send, data))
	publisher.send(message)
	time.sleep(1)
	
def zmq_recv(subscriber):

	#global subscriber

	message_encoded = subscriber.recv()
	#message = json.loads(message_encoded)
	message = message_encoded
	print("Received message: {0}".format(message))
	#parse_message(message)
	return True

def zmq_recv_async(subscriber):

	try:
		message = subscriber.recv(flags=0)
	except zmq.ZMQError:
		message = None
		
	return message
	
#********************************************************************************
# Abstract functions
#

class MessageController():

	def __init__(self):
		self.subscriber = None
		self.publisher = None

	#todo: port numbers ?
	def connect(self):

		self.publisher, self.subscriber = zmq_connect(self.publisher, self.subscriber)		
		# todo: check if connected
		# return True/False
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

	# Blocking function
	def receive(self, ):
		received = zmq_recv(self.subscriber)
		return received

	# Asynch version
	def receive_async(self):
		received = zmq_recv_async(self.subscriber)
		return received
	
	def recv_data(self):
		zmq_recv(self.subscriber)
	
	#def recv_message(self):
	