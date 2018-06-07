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

# MQ paths
mq_path_list = []
mq_disp_keys = []
mq_path_func = {}	# "CMD/path/path/": function


def printer( message, level=LL_INFO, tag="", logger_name=__name__):
	#logger = logging.getLogger(logger_name)
	#logger.log(level, message, extra={'tag': tag})
	print message

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

def handle_mq(mq_path, cmd=None):
	""" Decorator function.
		Registers the MQ path (nothing more at the moment..)
	"""
	def decorator(fn):
		global mq_path_list
		global mq_path_func
		global mq_disp_keys
		global mq_path_disp

		key = dispatcher_key(mq_path,cmd)		
		mq_path_list.append(prepostfix(mq_path).lower())
		mq_disp_keys.append(key)		# used by idle-thingy
		mq_path_func[key] = fn
		
		def decorated(*args,**kwargs):
			return fn(*args,**kwargs)
		return decorated
	return decorator
	
"""
def special_disp(path_dispatch, command_dispatch):

	# TODO: handle commands
	print "SPECIAL DISP"
	
	owww... handle the command too... two-dim lookup with regexp horrror

	k in d
{ "/all/X/": "function", "method": ["GET"] }
{ "/all/X/": "function", "method": ["GET,PUT"] }
{ "/all/X/": "function", "method": [] }

    path_dispatch = prepostfix(path_dispatch)
    # if there's an exact match, always handle that
    if path_dispatch in mq_path_list:
        return mq_path_func[path_dispatch]
    else:
        for path,function in mq_path_func.iteritems():
           wildpath = re.sub(r'\*',r'.*',path)
           if wildpath != path:
               res = re.search(wildpath,path_dispatch)
               if res is not None:
                   return mq_path_func[path]
    return None
"""

def dispatcher_key(path_dispatch,cmd):

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

def special_disp(path_dispatch, cmd=None): #, args=None):
	"""	Return function for given path and command.
	
		Will try an exact match first, if that fails a wildcard match will be
		attempted.
	"""
	key = dispatcher_key(path_dispatch,cmd)

	# if there's an exact match, always handle that
	# else, try wildcards
	if key in mq_path_func:
		return mq_path_func[key]

	else:	
		if cmd is None:
			key = dispatcher_key(path_dispatch,'#')
			
		for full_path,function in mq_path_func.iteritems():
			wildpath = re.sub(r'\*',r'.*',full_path)
			wildpath = re.sub(r'\#',r'.*',wildpath)
			print "C {0}".format(wildpath)
			if wildpath != full_path:
				res = re.search(wildpath,key)
				if res is not None:
					key =  res.group()
					# we could execute the function, but let's just return it...
					return mq_path_func[full_path]#(path=path_dispatch, cmd=cmd, args=args)

def super_disp(path_dispatch, cmd=None, args=None, data=None):
	"""	Execute function for given path and command.
	
		Will try an exact match first, if that fails a wildcard match will be
		attempted.
		
		Returns a payload struct.
	"""
	key = dispatcher_key(path_dispatch,cmd)

	# if there's an exact match, always handle that
	# else, try wildcards
	if key in mq_path_func:
		ret = mq_path_func[key](path=path_dispatch, cmd=cmd, args=args, data=data)
		test = struct_data(ret)
		print type(test)
		return struct_data(ret)

	else:	
		if cmd is None:
			key = dispatcher_key(path_dispatch,'#')
			
		for full_path,function in mq_path_func.iteritems():
			wildpath = re.sub(r'\*',r'.*',full_path)
			wildpath = re.sub(r'\#',r'.*',wildpath)
			print "C {0}".format(wildpath)
			if wildpath != full_path:
				res = re.search(wildpath,key)
				if res is not None:
					key =  res.group()
					# we could execute the function, but let's just return it...
					ret = mq_path_func[full_path](path=path_dispatch, cmd=cmd, args=args, data=data)
					test = struct_data(ret)
					print type(test)
					return struct_data(ret)
	
	return struct_data(None,500)

	
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
		
		self.VALID_COMMANDS = ['GET','PUT','POST','DEL','DATA', 'INFO']
		
		self.mq_path_list = []
		self.mq_path_func = {}

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

	'''
	def handle_mq(self, path):
		""" tbd.
			can we move this to hu_msg ?
		"""
		def decorator(fn):
			self.mq_path_list.append(path)
			self.mq_path_func[path] = fn
			def decorated(*args,**kwargs):
				print "Hello from handl_mq decorator, your path is: {0}".format(path)
				return fn(*args,**kwargs)
			return decorated
		return decorator
	'''
		
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
			#printer("Invalid command: {0}".format(command),level=LL_ERROR)
			print("Invalid command: {0}".format(command))
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
			if isinstance(arguments, list):
				#message = "{0}:{1}".format(message, ",".join(arguments))
				args_lijstje_als_tekst = ",".join(arguments)
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
				msg_prsd = parse_message(msg_resp)
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
		return message
