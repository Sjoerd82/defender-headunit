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
	""" Parses a MQ standardized message.
	Format: <path>[+response_path] <command>[:arg1, argn]
	Format: <path> DATA:<data>
	                                                 ^ags may contain spaces, double quotes, all kinds of messed up shit
	
	Arguments:
	 message		string, message
	 
	Returns:
	{
		'path'     : path
		'cmd'      : command (PUT, GET or DATA)
		'args'     : params
		'resp_path': resp_path
	}
	"""
	printer(colorize("{0}: {1}".format(__name__,'parse_message(message):'),'dark_gray'),level=LL_DEBUG)
	
	path = []
	params = []
	resp_path = []
	data = {}
	
	raw_path_resp_cmd = message.split(" ",1) #maxsplit=1, seperating at the first space [0]=paths, [1]=cmd+params
	raw_path_resp = raw_path_resp_cmd[0].split("+",1) # [0] = path, [1] = response path
	raw_cmd_par   = raw_path_resp_cmd[1].split(":",1)	#maxsplit=1,seperating at the first semicolon. [0]=cmd, [1]=param(s)
	
	# extract path
	for pathpart in raw_path_resp[0].split("/"):
		if pathpart:
			path.append(pathpart.lower())
	
	# extract response path (if any), as a whole..
	if len(raw_path_resp) > 1:
		resp_path = raw_path_resp[1]
	
	# extract command and arguments
	if len(raw_cmd_par) == 1:
		command = raw_cmd_par[0].lower()
	elif len(raw_cmd_par) == 2:
		command = raw_cmd_par[0].lower()
		#param = raw_cmd_par[1]
		
		if command == 'DATA':
			data = raw_cmd_par[1]
			print "DATA: {0}".format(data)
		else:
			print "LOADING: {0} ({1})".format(raw_cmd_par[1],type(raw_cmd_par[1]))
			
			param = json.loads(raw_cmd_par[1])

			if command == 'data':
				#expect a json/dict
				params.append(param)
			else:
				#,-delimited parameters
				for parpart in param.split(","):
					if parpart:
						params.append(parpart)
		
	else:
		printer("Malformed message!",level=LL_ERROR)
		return False
	
	# debugging
	#print("[MQ] Received Path: {0}; Command: {1}; Parameters: {2}; Response path: {3}".format(path,command,params,resp_path))
	
	# return as a tuple:
	#return path, command, params, resp_path
	
	# return as a dict:
	parsed_message = {}
	parsed_message['path'] = path
	parsed_message['cmd'] = command
	parsed_message['args'] = params
	parsed_message['resp_path'] = resp_path
	parsed_message['data'] = data
	return parsed_message

def create_data(payload, retval):
	""" Returns a standard data object.
	Returns:
	{
	 "retval": 200,
	 "data": { payload* }
	}
	"""
	data = {}	
	data['retval'] = retval
	data['payload'] = payload
	return data


#********************************************************************************
# ZeroMQ Wrapper for Pub-Sub Forwarder Device
#
class MqPubSubFwdController(object):

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
		#printer(colorize("Sending MQ message: {0}".format(message),'dark_gray'),level=LL_DEBUG)
		printer("Sending MQ message: {0}".format(message), level=LL_DEBUG, tag='MQ')
		printer("Sending MQ message: {0}".format(message))
		print("Sending MQ message: {0}".format(message))
		self.publisher.send(message)
		#time.sleep(1)	# required??? don't think so.. TODO: Remove, once we seen everything works..
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
		
		# TODO; FOR SOME REASON WE NEED TO DEFINE IT HERE..
		# .. DEFINING IT LATER, IN PUBLISH_COMMAND() DOESN'T WORK ?!
		self.reply_subscriber = self.context.socket (zmq.SUB)
		self.reply_subscriber.connect("tcp://{0}:{1}".format(self.address, self.port_sub))
		#self.poller.register(self.reply_subscriber, zmq.POLLIN)
		#self.reply_subscriber.setsockopt (zmq.SUBSCRIBE, '/bladiebla')
		
	def publish_command(self, path, command, arguments=None, wait_for_reply=False, timeout=5000, response_path=None):
		"""
		Publish a message. If wait_for_reply, then block until a reply is received.
		Parameters:
		 - path: (list) path or string
		 - command: (string) command
		 - arguments: list of words or anything, but a list
		Returns:
		 - None (invalid command, send unsuccesful)
		 ? Raw return message
		 ? Tuple/Dict (#tbd)
		
		"""		
		if command not in self.VALID_COMMANDS:
			print "invalid command"
			return False
			
		if wait_for_reply and not response_path:
			response_path = '/myuniquereplypath/'

		# path[+response_path] and command
		if response_path:
			message = "{0}+{1} {2}".format(path,response_path,command)
		else:
			message = "{0} {1}".format(path,command)
		
		# append arguments
		if arguments:
			if type(arguments) == 'list':
				print "DEBUG MSG: LIST"
				message = "{0}:{1}".format(message, ",".join(arguments))
			elif type(arguments) == 'dict':
				print "DEBUG MSG: DICT"
				jsonified_args = json.dumps(arguments)
				message = "{0}:{1}".format(message, jsonified_args)				
			else:
				print "DEBUG MSG: OTHER"
				jsonified_args = json.dumps(arguments)
				message = "{0}:{1}".format(message, jsonified_args)
		
		if wait_for_reply:
			print "DEBUG: SETUP WAIT_FOR_REPLY; TOPIC={0}".format(response_path)
			# create a subscription socket, listening to the response path
	#		reply_subscriber = self.context.socket (zmq.SUB)
	#		reply_subscriber.connect("tcp://{0}:{1}".format(self.address, self.port_sub))
	#		time.sleep(1)
			# setup a temporary poller for the new socket
	#		reply_poller = zmq.Poller()
	#		reply_poller.register(reply_subscriber, zmq.POLLIN)
			self.poller.register(self.reply_subscriber, zmq.POLLIN)
			self.reply_subscriber.setsockopt (zmq.SUBSCRIBE, response_path)
	#		reply_subscriber.setsockopt(zmq.SUBSCRIBE,response_path)

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
	#		events = dict(reply_poller.poll()) #timeout
			events = dict(self.poller.poll())
			self.poller.unregister(self.reply_subscriber)
			#except zmq.ZMQError:
				# No Message Available
			#	return None
	#		if self.subscriber in events:
			if self.reply_subscriber in events:
				print "OHYEAHBABY! AGAIN"
			
			if events:
				print "DEBUG: YES!"
				# todo: have a look at what's returned?
				# read response from the server
				msg_resp = self.reply_subscriber.recv()
				msg_prsd = parse_message(msg_resp)
				data = msg_prsd['data']
				#data = create_data(msg_prsd['data'],200)
				"""
				print "------------"
				print "RAW:"
				print response
				print "PARSED:"
				parsed_response = parse_message(response)
				print parsed_response
				"""
				
				#? this ok? clean-up?
				# check response?
				return data
				
			else:
				print "DEBUG: NOPE"
				
			#TODO: DO WE NEED TO DISCONNECT??
			#reply_subscriber.disconnect(self.address)
			#return parsed_response
			return response
			
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
		#print "DEBUG: poll()"
		socks = dict(self.poller.poll())
		message = None
		if self.subscriber in socks:
			message = self.__recv()
		return message
