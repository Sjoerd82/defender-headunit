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
import json
from logging import getLogger	# logger

sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *

#def printer( message, level=LL_INFO, tag="", logger_name=__name__):
	#logger = logging.getLogger(logger_name)
	#logger.log(level, message, extra={'tag': tag})
#	print message


# DEPRECATED
# only still used by:
#  eca_vol_test.py
#  hu.py
#  hu_src_ctrl.py
# replace with parsed_msg = messaging.poll(timeout=None, parse=True)
#def parse_message(message):

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

	def __init__(self, address=None, port_pub=None, port_sub=None, origin=None):

		# Context
		self.context = zmq.Context()
		
		# Pub-Sub
		self.publisher = None
		self.subscriber = None

		# Origin ## ? Isn't there a build-in variable to know the creating script name?
		self.origin = origin
		#print(__name__)		#nope
		#print(__file__)		#nope
		#print(__package__)		#nope
		
		# Poller
		self.poller = zmq.Poller()
		
		self.address = address
		self.port_pub = port_pub
		self.port_sub = port_sub
		
		self.VALID_COMMANDS = ['GET','PUT','POST','DEL','DATA', 'INFO']
		
		self.mq_path_list = []	# /path/path/*/ list of paths, from decorators, may contain wildcards
		self.topics = []		# list of MQ subscriptions, generated from above, or configured
		self.mq_path_func = {}	# "CMD/path/path/": function
		# V2:					  "CMD/path/path/": { "function":fn, "event":"path" }

		
	def __send(self, message):
		#printer(colorize("Sending MQ message: {0}".format(message),'dark_gray'),level=LL_DEBUG)
	#	printer("Sending MQ message: {0}".format(message), level=LL_DEBUG, tag='MQ')
	#	printer("Sending MQ message: {0}".format(message))
		#print("Sending MQ message: {0}".format(message))
		self.publisher.send(message)
		#time.sleep(1)	# required??? don't think so.. TODO: Remove, once we seen everything works..
		return True

	def __recv(self):
		message = self.subscriber.recv()
		return message

	def __dispatcher_key(self, path_dispatch, cmd):		
		#lower case
		path_dispatch = path_dispatch.lower()
		
		#prefix
		if not path_dispatch.startswith("/"):
			path_dispatch = "/"+path_dispatch

		#postfix
		if not path_dispatch.endswith("/"):
			path_dispatch += "/"

		#cmd
		xstr = lambda s: s or "#"

		#build key
		key_cmd_path = xstr(cmd).lower()+path_dispatch
		return key_cmd_path
	
	def set_address(self, address=None, port_pub=None, port_sub=None):
		if address is not None: self.address = address
		if port_pub is not None: self.port_pub = port_pub
		if port_sub is not None: self.port_sub = port_sub		
	
	def create_publisher(self):
		"""
		Setup and connect a publisher. Does not bind (uses the forwarder).
		"""
		self.publisher = self.context.socket(zmq.PUB)
		self.publisher.connect("tcp://{0}:{1}".format(self.address, self.port_pub))

	def create_subscriber(self, subscriptions=[]):
		"""	Setup and connect a subscriber for the given topic(s).
			This function also registers the subscription with the poller.
		"""
		if not self.topics:
			self.topics.extend(subscriptions)
		else:
			for subscription in subscriptions:
				if subscription not in self.topics:
					self.topics.append(subscription)
		
		self.subscriber = self.context.socket (zmq.SUB)
		self.subscriber.connect("tcp://{0}:{1}".format(self.address, self.port_sub))
		self.poller.register(self.subscriber, zmq.POLLIN)
		for topic in self.topics:
			self.subscriber.setsockopt (zmq.SUBSCRIBE, topic)
		
		# TODO; FOR SOME REASON WE NEED TO DEFINE IT HERE..
		# .. DEFINING IT LATER, IN PUBLISH_COMMAND() DOESN'T WORK ?!
		self.reply_subscriber = self.context.socket (zmq.SUB)
		self.reply_subscriber.connect("tcp://{0}:{1}".format(self.address, self.port_sub))
		#self.poller.register(self.reply_subscriber, zmq.POLLIN)
		#self.reply_subscriber.setsockopt (zmq.SUBSCRIBE, '/bladiebla')

	def add_subscription(subscription):
		if subscription not in self.topics:
			self.topics.append(subscription)
		
	def subscriptions(self):
		return self.topics		
	
	def create_message(self, path, command, arguments=None, response_path=None):
			
		# path[+response_path] and command
		if response_path:
			message = "{0}+{1}|{2}|{3}".format(path,response_path,self.origin,command)
		else:
			message = "{0}|{1}|{2}".format(path,self.origin,command)
		
		# append arguments
		if arguments:
			if isinstance(arguments, list):
				#message = "{0}:{1}".format(message, ",".join(arguments))
				args_lijstje_als_tekst = ",".join(str(arg) for arg in arguments)
				jsonified_args = json.dumps(args_lijstje_als_tekst)
				message = "{0}:{1}".format(message, jsonified_args)
			elif type(arguments) == 'dict':
				#print "DEBUG MSG: DICT"
				jsonified_args = json.dumps(arguments)
				message = "{0}:{1}".format(message, jsonified_args)
			elif isinstance(arguments, dict):
				#print "DEBUG MSG: DICT"
				jsonified_args = json.dumps(arguments)
				message = "{0}:{1}".format(message, jsonified_args)
			else:
				#print "DEBUG MSG: OTHER"
				jsonified_args = json.dumps(arguments)
				message = "{0}:{1}".format(message, jsonified_args)
				
		return message
	
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
		
		# check command is valid
		if command not in self.VALID_COMMANDS:
			#printer("Invalid command: {0}".format(command),level=LL_ERROR)
			print("Invalid command: {0}".format(command))
			return False
		
		# generate response_path, if missing
		if wait_for_reply and not response_path:
			response_path = '/myuniquereplypath/'

		# create message
		message = self.create_message(path, command, arguments, response_path)
		
		if wait_for_reply:
			#print "DEBUG: SETUP WAIT_FOR_REPLY; TOPIC={0}".format(response_path)
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

		#print "message = {0}".format(message)
		#print type(arguments)	# <class 'hu_datastruct.Modes'>
		retval = self.__send(message)
		if not retval:
			return False
		elif not wait_for_reply:
			return True
		else:
			response = None
			parsed_response = None
	#		events = dict(reply_poller.poll()) #timeout
	
			events = dict(self.poller.poll())
			if timeout is not None:
				events = dict(self.poller.poll(timeout))
			else:
				events = dict(self.poller.poll())

			self.poller.unregister(self.reply_subscriber)
			#except zmq.ZMQError:
				# No Message Available
			#	return None
	#		if self.subscriber in events:
			if self.reply_subscriber in events:
				#print "OHYEAHBABY! AGAIN"
				pass
			
			if events:
				#print "DEBUG: YES!"
				# todo: have a look at what's returned?
				# read response from the server
				msg_resp = self.reply_subscriber.recv()
				msg_prsd = self.parse_message(msg_resp)
				data = msg_prsd['data']
				
				#? this ok? clean-up?
				# check response?
				return data
				
			else:
				print "DEBUG: NOPE"
				
			#TODO: DO WE NEED TO DISCONNECT??
			#reply_subscriber.disconnect(self.address)
			#return parsed_response
			return response
				
	def poll(self, timeout=None, parse=False):
		"""
		Blocking call, if no timeout (ms) specified.
		Returns raw message, or None if no data.
		"""
		#print "DEBUG: poll()"
		if timeout is not None:
			socks = dict(self.poller.poll(timeout))
		else:
			socks = dict(self.poller.poll())
		message = None
		if self.subscriber in socks:
			message = self.__recv()
			if parse:
				return self.parse_message(message)
			
		return message
		
	def parse_message(self, message):
		""" Parses a MQ standardized message.
		Formats:
			<path>[+response_path]|[origin]|<command>[:arg1, argn]
			<path>|[origin]DATA:<data>
														 ^args may contain spaces, double quotes, all kinds of messed up shit
		
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
		#printer(colorize("{0}: {1}".format(__name__,'parse_message(message):'),'dark_gray'),level=LL_DEBUG)
		
		path = []
		params = []
		resp_path = []
		data = {}
		
		raw_path_resp_cmd = message.split("|",2) #maxsplit=2, seperating by two pipes [0]=paths, [1]=origin, [2]=cmd+params
		raw_path_resp = raw_path_resp_cmd[0].split("+",1) # [0] = path, [1] = response path
		origin        = raw_path_resp_cmd[1]
		raw_cmd_par   = raw_path_resp_cmd[2].split(":",1)	#maxsplit=1,seperating at the first semicolon. [0]=cmd, [1]=param(s)
		
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
			# extract data or arguments
			if command == 'data':
				data = json.loads(raw_cmd_par[1])
				#print "DATA: {0}".format(data)
			else:
				#print "LOADING: {0} ({1})".format(raw_cmd_par[1],type(raw_cmd_par[1]))		
				param = json.loads(raw_cmd_par[1])

				# TODO perhaps better to do a check type() instead..
				if command == 'data':
					#expect a json/dict
					params.append(param)
				elif command == 'info':
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
		parsed_message['origin'] = origin
		return parsed_message
	
	#********************************************************************************

	# EXPERIMENTAL
	def poll_and_execute(self,timeout,ignore_own_message=True):
		parsed_msg = self.poll(timeout=500, parse=True)	#Timeout: None=Blocking
		if parsed_msg:
			if parsed_msg['origin'] == self.origin and ignore_own_message:
				pass
			else:
				ret = self.execute_mq(parsed_msg['path'], parsed_msg['cmd'], args=parsed_msg['args'], data=parsed_msg['data'])
				if parsed_msg['resp_path'] and ret is not None:
					self.publish_command(parsed_msg['resp_path'],'DATA',ret)
				
		return True
	
	# EXPERIMENTAL
	def test_path(self,full_path):
	
		if not full_path.startswith("/"):
			full_path = "/"+full_path
		#postfix
		if not full_path.endswith("*"):
			full_path += "*"

		wildpath = re.sub(r'\*',r'.*',full_path)
	
		path_start = full_path.find('/')
		if path_start == -1:
			return -1 # invalid path
			
		path_end = full_path.find('*')
		if path_end == -1:
			path_end = len(topic)
		
		path_stripped = prepostfix(full_path[path_start:path_end].lower())
		#print "Stripped: {0} -> {1}".format(full_path,path_stripped)

		if path_stripped not in self.topics: #self.mq_path_list:
			#print "Not Found :)"
			return path_stripped
		else:
			return None
	
		
	def handle_mq(self, mq_path, cmd=None, event=None):
		""" Decorator function.
			Registers the MQ path (nothing more at the moment..)
		"""
		def decorator(fn):
			def decorated(*args,**kwargs):
				key = self.__dispatcher_key(mq_path,cmd)
				self.mq_path_list.append(prepostfix(mq_path).lower())
				self.mq_path_func[key] = { 'function':fn, 'event':event }
				
				# add topic to subscriptions, if not already there
				stripped = self.test_path(mq_path)
				if stripped is not None:
					self.topics.append(stripped)
				
				print "!DEBUG.. right now the list is: ".format(len(self.mq_path_list))
			
				#def decorated(*args,**kwargs):
				return fn(*args,**kwargs)
			return decorated
		return decorator
	
	def execute_mq(self, path_dispatch, cmd=None, args=None, data=None):
		"""	Execute function for given path and command.
		
			Will try an exact match first, if that fails a wildcard match will be
			attempted.
			
			Returns a payload struct.
			
			If return value is 2xx (?) and event present, will send out an event message.
			Hmm, is this good practice? the decorated function can do a publish_command just as easily..
			 .... let's see how this works out..
		"""
		
		# path_dispatch may be a string or a list
		if isinstance(path_dispatch, list):
			# convert to string
			path_dispatch = "/" + "/".join(path_dispatch)
		
		key = self.__dispatcher_key(path_dispatch,cmd)

		# if there's an exact match, always handle that
		# else, try wildcards
		if key in self.mq_path_func:
			ret = self.mq_path_func[key]['function'](path=path_dispatch, cmd=cmd, args=args, data=data)
			if ret is not None:
				ret_data = struct_data(ret)
				if ret_data['retval'] == 200 and self.mq_path_func[key]['event'] is not None:
					# todo... send out data ??? same data ???
					self.publish_command(self.mq_path_func[key]['event'], 'INFO', arguments=None, wait_for_reply=False, response_path=None)
				return ret_data

		else:	
			if cmd is None:
				key = self.__dispatcher_key(path_dispatch,'#')
				
			for full_path,attributes in self.mq_path_func.iteritems():
				wildpath = re.sub(r'\*',r'.*',full_path)
				wildpath = re.sub(r'\#',r'.*',wildpath)
				if wildpath != full_path:
					res = re.search(wildpath,key)
					if res is not None:
						key =  res.group()
						# we could execute the function, but let's just return it...
						ret = self.mq_path_func[full_path]['function'](path=path_dispatch, cmd=cmd, args=args, data=data)
						ret_data = struct_data(ret)
						if ret_data['retval'] == 200 and self.mq_path_func[full_path]['event'] is not None:
							# todo... send out data ??? same data ???
							self.publish_command(self.mq_path_func[full_path]['event'], 'INFO', arguments=None, wait_for_reply=False, response_path=None)
						return ret_data
		
		return None
		