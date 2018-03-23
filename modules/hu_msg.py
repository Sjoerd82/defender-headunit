#
# Messaging layer
# Venema, S.R.G.
# 2018-03-22
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

def parse_message(message):
	"""
	Format: <path> <command>[:arg1,argn] [response_path]
	Returns a tuple/dict (#tbd) + data?
	"""
	path = []
	params = []
	resp_path = []
	path_cmd_resp = message.split(" ")
	
	# extract path
	for pathpart in path_cmd_resp[0].split("/"):
		if pathpart:
			path.append(pathpart.lower())
		
	# extract command and params
	cmd_par = path_cmd_resp[1].split(":")
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
	
	# extract response path
	if len(path_cmd_resp) >= 3:
		for pathpart in path_cmd_resp[2].split("/"):
			if pathpart:
				resp_path.append(pathpart.lower())
	
	# debugging
	print("[MQ] Received Path: {0}; Command: {1}; Parameters: {2}; Response path: {3}".format(path,command,params,resp_path))
	
	# return as a tuple:
	#return path, command, params, resp_path
	
	# return as a dict:
	parsed_message = {}
	parsed_message['path'] = path
	parsed_message['cmd'] = command
	parsed_message['args'] = params
	parsed_message['resp_path'] = resp_path
	return parsed_message

#********************************************************************************
# ZeroMQ Wrapper for Pub-Sub Forwarder Device
#
class MqPubSubFwdController:

	def __init__(self, address, port_pub, port_sub):

		# Context
		self.context = zmq.Context()
		
		# Pub-Sub
		self.publisher = None
		self.subscriber = None

		# Poller
		self.poller = zmq.Poller()
		
		self.address = address
		self.port_pub = port_pub
		self.port_sub = port_sub
		
		self.VALID_COMMANDS = ['GET','PUT','POST','DEL','DATA']

	def __send(self, message):
		self.publisher.send(message)
		time.sleep(1)	# required??? don't think so.. TODO: Remove, once we seen everything works..
		return True

	def __recv(self):
		message = self.subscriber.recv()
		return message
		
	def create_publisher(self):
		"""
		Setup and connect a publisher. Does not bind (uses the forwarder).
		"""
		self.publisher = self.context.socket(zmq.PUB)
		self.publisher.connect("tcp://{0}:{1}".format(self.address, self.port_pub))

	def create_subscriber(self, topics=['/']):
		"""
		Setup and connect a subscriber for the given topic(s).
		This function also registers the subscription with the poller.
		"""
		self.subscriber = self.context.socket (zmq.SUB)
		self.subscriber.connect("tcp://{0}:{1}".format(self.address, self.port_sub))
		self.poller.register(self.subscriber, zmq.POLLIN)
		for topic in topics:
			self.subscriber.setsockopt (zmq.SUBSCRIBE, topic)
		
	def publish_command(self, path, command, arguments=None, wait_for_reply=False, timeout=5000, response_path=None):
		"""
		Publish a message. If wait_for_reply, then block until a reply is received.
		Parameters:
		 - path: (list) path
		 - command: (string) command
		 - arguments: list of words or anything, but a list
		Returns:
		 - None (invalid command, send unsuccesful)
		 ? Raw return message
		 ? Tuple/Dict (#tbd)
		
		"""
		if command not in self.VALID_COMMANDS:
			return False
			
		if wait_for_reply and not response_path:
			response_path = '/myuniquereplypath/'
		
		message = "{0} {1}".format(path,command)
		
		# append arguments
		if arguments:
			if type(arguments) == 'list':
				message = "{0}:{1}".format(message, ",".join(arguments))
			else:
				message = "{0}:{1}".format(message, arguments)
			
		# append response path
		if response_path:
			message = "{0} {1}".format(message,response_path)
		
		if wait_for_reply:
			print "DEBUG: SETUP WAIT_FOR_REPLY; TOPIC={0}".format(response_path)
			# create a subscription socket, listening to the response path
			reply_subscriber = self.context.socket (zmq.SUB)
			reply_subscriber.connect("tcp://{0}:{1}".format(self.address, self.port_sub))
			reply_subscriber.setsockopt(zmq.SUBSCRIBE,response_path)

			# setup a temporary poller for the new socket
			reply_poller = zmq.Poller()
			reply_poller.register(reply_subscriber, zmq.POLLIN)
		
		print "DEBUG: SENDING MESSAGE: {0}".format(message)
		retval = self.__send(message)
		if not retval:
			return False
		elif not wait_for_reply:
			return True
		else:
			# poll for a reply
			#try:
			print "DEBUG: POLLING !"
			response = None
			parsed_response = None
			events = reply_poller.poll(timeout)
			#except zmq.ZMQError:
				# No Message Available
			#	return None
			
			if events:
				print "DEBUG: YES!"
				# todo: have a look at what's returned?
				# read response from the server
				response = reply_subscriber.recv()
				parsed_response = parse_message(response)
			else:
				print "DEBUG: NOPE"
				
			#TODO: DO WE NEED TO DISCONNECT??
			#reply_subscriber.disconnect(self.address)
			return parsed_response
			
	def publish_data(self, path, payload, retval='200'):
		"""
		Publish a "payload" message
		"""
		data={}
		data['retval'] = retval
		data['payload'] = payload
		message = "{0} DATA {1}".format(path, data)
		self.publisher.send(message)
		time.sleep(1)	# required?
		
	def poll(self, timeout=None):
		"""
		Blocking call, if no timeout specified.
		Returns raw message, or None if no data.
		"""
		print "DEBUG: poll()"
		socks = dict(self.poller.poll())
		message = None
		if self.subscriber in socks:
			message = self.__recv()
		return message
