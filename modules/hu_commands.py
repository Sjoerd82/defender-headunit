#!/usr/bin/python

#
# Commands
# Venema, S.R.G.
# 2018-06-11
#
# Commands, arguments and MQ-mapper.
#

class Commands(object):

	def __init__(self):
	
		self.command_list = []
				
		self.function_mq_map = [

			{	'name': 'SOURCE',
				'description': 'Retrieve details for given index',
				'command': 'GET',
				'params': [
					{'name':'index', 'datatype':(int,),'required':False, 'help':'Source index'},
					{'name':'subindex', 'datatype':(int,),'required':False, 'help':'Source subindex'}
				],
				'path': '/source/primary'
			},
		
			{	'name': 'SOURCE-SET',
				'description': 'Activate primary source',
				'command': 'PUT',
				'params': [
					{'name':'index', 'datatype':(int,),'required':True, 'help':'Source index'}
				],
				'path': '/source/primary'
			},
			
			{	'name': 'SOURCE-CHECK',
				'description': 'Check source availability',
				'command': 'PUT',
				'params': [
					{'name':'index', 'datatype':(int,),'required':False, 'help':'Source index'},
					{'name':'subindex', 'datatype':(int,),'required':False, 'help':'Source subindex'}
				],
				'path': '/source/check'
			},
			
			{	'name': 'SOURCE-SELECT',
				'description': 'Select a (sub)source',
				'command':'PUT',
				'params': [
					{'name':'index', 'datatype':(int,),'required':True, 'help':'Source index'},
					{'name':'subindex', 'datatype':(int,),'required':False, 'help':'Source subindex'}
				],
				'path': '/source/subsource'
			},
			
			{	'name': 'SOURCE-NEXT-PRIMARY',
				'description': 'Select next primary source',
				'command': 'PUT',
				'params': None,
				'path': '/source/next_primary'
			},
			
			{	'name': 'SOURCE-PREV-PRIMARY',
				'description': 'Select previous primary source',
				'command': 'PUT',
				'params': None,
				'path': '/source/prev_primary'
			},
			
			{	'name': 'SOURCE-NEXT',
				'description': 'Select next source',
				'command': 'PUT',
				'params': None,
				'path': '/source/next'
			},
			
			{	'name': 'SOURCE-PREV',
				'description': 'Select previous source',
				'command': 'PUT',
				'params': None,
				'path': '/source/prev'
			},
			
			{	'name': 'SOURCE-AVAILABLE',
				'description': 'Set source availability',
				'command': 'PUT',
				 'params': [
					{'name':'availability', 'datatype':(bool,), 'required':True, 'help':''},
					{'name':'index', 'datatype':(int,), 'required':True, 'help':'Source index'},
					{'name':'subindex', 'datatype':(int,),'required':True, 'help':'Source subindex'}
				],
				'path': '/source/available'
			},
			
			{	'name': 'SOURCE-DETAILS',
				'description': 'Get source details',
				'command': 'GET',
				'params': [
					{'name':'index', 'datatype':(int,), 'required':False, 'help':'Source index'},
					{'name':'subindex', 'datatype':(int,), 'required':False, 'help':'Source subindex'}
				],
				'path': '/source/subsource'
			},
			
			{	'name': 'SOURCE-UPDATE',
				'description': 'Update source (MPD: Source Database)',
				'command': 'PUT',
				'params': [
					{'name':'index', 'datatype':(int,), 'required':False, 'help':'Source index'},
					{'name':'subindex', 'datatype':(int,), 'required':False, 'help':'Source subindex'}
				],
				'path': '/source/update'
			},
			
			{	'name': 'SOURCE-UPDATE-LOCATION',
				'description': 'Update MPD database for given location',
				'command': 'PUT',
				'params': [
					{'name':'location', 'datatype':(str,unicode,), 'required':True, 'help':'Relative location, as seen from MPD'}
				],
				'path': '/source/update-location'
			},
			
			{	'name': 'SUBSOURCE',
				'description': 'Retrieve details for given subindex or current source',
				'command': 'GET',
				'params': [
					{'name':'index', 'datatype':(int,),'required':False, 'help':'Source index'},
					{'name':'subindex', 'datatype':(int,),'required':False, 'help':'Source subindex'}
				],
				'path': '/source/subsource'
			},
			
			{	'name': 'PLAYER-PLAY',
				'description': 'Start playback',
				'command': 'PUT',
				'params': None,
				'path': '/player/state',
				'params_override': '{"state":"play"}'
			},
			{	'name': 'PLAYER-PAUSE',
				'description': 'Pause playback',
				'command': 'PUT',
				'params': None,
				'path': '/player/state',
				'params_override': '{"state":"pause"}'
			},
			{	'name': 'PLAYER-STOP',
				'description': 'Stop playback',
				'command': 'PUT',
				'params': None,
				'path': '/player/state',
				'params_override': '{"state":"stop"}'
			},
			{	'name': 'PLAYER-STATE',
				'description': 'Get state',
				'command': 'GET',
				'params': None,
				'path': '/player/state'
			},
			{	'name': 'PLAYER-SET-STATE',
				'description': 'Set state',
				'command': 'PUT',
				'params': [ {'name':'state', 'datatype':(str,unicode,), 'choices':['play','pause','stop'], 'required':True} ],
				'path': '/player/state'
			},
			{	'name': 'PLAYER-NEXT',
				'description': 'Play next song',
				'command': 'PUT',
				'params': [ {'name':'count', 'datatype':(int,), 'required':False, 'help':'Number of tracks to go ahead'} ],
				'path': '/player/next'
			},
			{	'name': 'PLAYER-PREV',
				'description': 'Play previous song',
				'command': 'PUT',
				'params': [ {'name':'count', 'datatype':(int,), 'required':False, 'help':'Number of tracks to go back'} ],
				'path': '/player/prev'
			},
			{	'name': 'PLAYER-SEEK',
				'description': 'Seek',
				'command': 'PUT',
				'params': [ {'name':'seconds', 'datatype':(str,unicode,int,), 'choices':['INT_SIGNED'], 'required':True, 'help':'Use a + or - sign to seek forward or reverse'} ],
				'path': '/player/seek'
			},
			{	'name': 'PLAYER-FOLDERS',
				'description': 'List folders',
				'command': 'GET',
				'params': None,
				'path': '/player/folders'
			},
			{	'name': 'PLAYER-NEXTFOLDER',
				'description': 'Next folder',
				'command': 'PUT',
				'params': None,
				'path': '/player/nextfolder'
			},
			{	'name': 'PLAYER-PREVFOLDER',
				'description': 'Prev folder',
				'params': None,
				'command': 'PUT',
				'path': '/player/prevfolder'
			},
			{	'name': 'PLAYER-UPDATE',
				'description': 'Update MPD database',
				'params': [ {'name':'location', 'datatype':(str,unicode,), 'required':False, 'help':'Location to update'} ],
				'command': 'PUT',
				'path': '/player/update'
			},
			{	'name': 'PLAYER-RANDOM-MODES',
				'description': 'Get available random modes',
				'params': None,
				'command': 'GET',
				'path': '/player/randommode'
			},
			{	'name': 'PLAYER-RANDOM',
				'description': 'Set random',
				'params': [ {'name':'mode', 'datatype':(str,unicode,), 'choices':['ON','OFF','TOGGLE'], 'required':False, 'default':'TOGGLE'} ],
				'command': 'PUT',
				'path': '/player/random'
			},
			{	'name': 'PLAYER-DETAILS',
				'description': 'Get player details',
				'params': None,
				'command': 'GET',
				'path': '/player/track'
			},
			
			{	'name': 'VOLUME-GET',
				'description': 'Get volume level',
				'params': None,
				'command': 'GET',
				'path': '/volume/master'
			},
			
			{	'name': 'VOLUME-SET',
				'description': 'Set volume',
				'params': [ {'name':'volume', 'datatype': (str,unicode,int,float,), 'choices':['up','down','FLOAT_PERCENTAGE','FLOAT_SIGNED','att','mute'], 'required':True, 'help':'Volume in percentage'} ],
				'command': 'PUT',
				'path': '/volume/master'
			},
			
			{	'name': 'VOLUME-INCR',
				'description': 'Increase volume',
				'params': [ {'name':'volume', 'datatype': (str,unicode,int,float,), 'choices':['FLOAT_PERCENTAGE','FLOAT_SIGNED'], 'required':True,'help':'Volume in percentage'} ],
				'command': 'PUT',
				'path': '/volume/master/increase'
			},
			{	'name': 'VOLUME-DECR',
				'params': [ {'name':'volume', 'datatype': (str,unicode,int,float,), 'choices':['FLOAT_PERCENTAGE','FLOAT_SIGNED'], 'required':True,'help':'Volume in percentage'} ],
				'description': 'Decrease volume',
				'command': 'PUT',
				'path': '/volume/master/decrease'
			},
			
			{	'name': 'VOLUME-ATT',
				'description': 'Set volume to ATT level',
				'params': [ {'name':'mode', 'datatype':(str,unicode,), 'choices':['ON','OFF','TOGGLE'], 'required':False, 'default':'ON'} ],
				'command': 'PUT',
				'path': '/volume/att'
			},
			{	'name': 'VOLUME-MUTE',
				'description': 'Mute volume',
				'params': [ {'name':'mode', 'datatype':(str,unicode,), 'choices':['ON','OFF','TOGGLE'], 'required':False, 'default':'TOGGLE'} ],
				'command': 'PUT',
				'path': '/volume/mute'
			},
			
			{	'name': 'ECA-CHAINSETUP-GET',
				'description': 'Get current ecasound chainsetup',
				'params': None,
				'command': 'GET',
				'path': '/ecasound/chainsetup'
			},
			{	'name': 'ECA-CHAINSETUP-SET',
				'description': 'Select ecasound chainsetup',
				'params': [ {'name':'chainsetup', 'datatype':(str,unicode,), 'required':True, 'help':'Name of chain setup'} ],
				'command': 'PUT',
				'path': '/ecasound/chainsetup'
			},
			
			{	'name': 'MODE-CHANGE',
				'description': 'Set a number of modes at once',
				'params': [ {'name':'mode', 'required':True, 'datatype': (str,unicode,), 'help':'Mode to set'},
							{'name':'state', 'required':True, 'datatype': (bool,), 'default': False, 'help':'True to activate or False to deactivate'} ],
				'params_repeat': True,
				'command': 'PUT',
				'path': '/mode/change'
			},
			{	'name': 'MODE-SET',
				'description': 'Set a mode',
				'params': [ {'name':'mode', 'datatype':(str,unicode,), 'required':True, 'help':'Mode to set'},
							{'name':'state', 'datatype':(bool,), 'required':False, 'default': False, 'help':'True to activate or False to deactivate'}
				],
				'command': 'PUT',
				'path': '/mode/set'
			},
			{	'name': 'MODE-UNSET',
				'description': 'Unset a mode',
				'params': [ {'name':'mode', 'datatype':(str,unicode,), 'required':True, 'help':'Mode to unset'} ],
				'command': 'PUT',
				'path': '/mode/unset'
			},	
			{	'name': 'MODES-LIST',
				'description': 'Get list of registered modes',
				'params': None,
				'command': 'GET',
				'path': '/mode/list'
			},
			{	'name': 'MODES-ACTIVE',
				'description': 'Get list of currently active modes',
				'params': None,
				'command': 'GET',
				'path': '/mode/active'
			},
			{	'name': 'mode-test1',
				'description': 'TEST PUT',
				'params': None,
				'command': 'PUT',
				'path': '/mode/test',
				'wait_for_reply': False
			},
			{	'name': 'mode-test2',
				'description': 'TEST GET',
				'params': None,
				'command': 'GET',
				'path': '/mode/test',
				'wait_for_reply': False
			},

			{	'name': 'UDISKS-DEVICES',
				'description': 'List registered UDisks devices',
				'params': None,
				'command': 'GET',
				'path': '/udisks/devices'
			},
			
			{	'name': 'SYSTEM-REBOOT',
				'description': 'Reboot system',
				'params': [ {'name':'timer', 'datatype':(int,), 'required':False, 'help':'Time in seconds to shutdown'} ],
				'command': 'PUT',
				'path': '/system/reboot'
			},
			{	'name': 'SYSTEM-SHUTDOWN',
				'description': 'Shutdown system' ,
				'params': [ {'name':'timer', 'datatype':(int), 'required':False, 'help':'Time in seconds to shutdown'} ],
				'command': 'PUT',
				'path': '/system/shutdown'
			}
			
			]

		for command in self.function_mq_map:
			self.command_list.append(command['name'])
		
	def get_command(self, command):
		ix = self.command_list.index(command)
		if ix is not None:
			return self.function_mq_map[ix]
			
	def get_command_by_path(self, mq_path, mq_cmd):
		print "gcbp {0} {1}".format(mq_path, mq_cmd)
		# TODO, add postfix slash to search
		for cmd in self.function_mq_map:
			if cmd['path'].upper() == mq_path.upper() and cmd['command'].upper() == mq_cmd.upper():
				print "MATCH {0}".format(cmd)
				return cmd

	def validate(self, command=None):
		""" Decorator function.
			Validates arguments.
			Returns list of valid arguments, None (no arguments) or False (invalid)
			If command could not be found then ???
		"""
		def decorator(fn):
			def wrapper(*args,**kwargs):
				# add an empty args, if not present
				if 'args' not in kwargs:
					kwargs['args'] = None
					
				# derive from MQ-command mapping table
				if ( command is None and
					'path' in kwargs and
					'cmd' in kwargs ):
					command_to_validate = self.get_command_by_path(kwargs['path'],kwargs['cmd'])
					if command_to_validate is not None:
						#kwargs['args'] = self.validate_args(command_to_validate['name'],kwargs['args'])
						print command_to_validate['name']
						print kwargs['args']
						kwargs['args'] = self.validate_args('MODES-ACTIVE',None)
					else:
						return False #??????????????
				# use provided command
				#else:
				#	kwargs['args'] = self.validate_args(command,list_of_args)
				
				return fn(*args,**kwargs)
			return wrapper
		return decorator		
	
	def validate_args(self, command, args): #, repeat=False):
		"""
		args must be a list of arguments
		Returns list of args (including defaults) if valid (may return None if no params)
		Raises a ValueError if invalid.
		"""
		print "DEBUG.. hello from validate_args Command={0}".format(command)
		def strint_to_bool(value):
			if isinstance(value, (str,unicode)) and value.lower() in ['true','on','1','t']:
				return True
			elif  isinstance(value, (str,unicode)) and value.lower() in ['false','off','0','f']:
				return False
			elif  isinstance(value, int) and value in [1]:
				return True
			elif  isinstance(value, int) and value in [0]:
				return False
			else:
				return None

		def isint(value):
			"""
			Return true if value is an int
			"""
			if value[0] == '+' or value[0] == '-': value = value[1:]
			try:
				ret = float(value).is_integer()
				return ret
			except:
				return False
				
		def isfloatint(value):
			"""
			Return true if value is a float OR an int
			"""
			if value[0] == '+' or value[0] == '-': value = value[1:]
			try:
				ret = float(value)
				return True
			except:
				return False
			
		cmd_def = self.get_command(command)
		arg_defs = cmd_def['params']
				
		# no arguments
		if arg_defs is None and (args is None or args == []):
			return None
		# no arguments, but some given
		elif arg_defs is None and len(args) > 0:
			return None	 # ignoring extra arguments
		
		# check if arguments are provided as a list
		if not isinstance(args, list):
			print "second argument must be a list"
			return None

		# make a copy
		defs = arg_defs[:]	# cuz we might manipulate it, and python is stupid
		if defs is None:
			return None

		# generate repeat definitions
		if 'params_repeat' in cmd_def and cmd_def['params_repeat']:
			repeat = True
		else:
			repeat = False
			
		if repeat:
			for i in range(len(args)/len(arg_defs)-1):
				defs.extend(arg_defs)
		
		# error handling
		error_raise = False
		error_msg = ""
		error_msg_datatype = ""
		error_msg_choices = ""

		# LOOP THROUGH ALL PROVIDED ARGUMENTS
		for i, arg in enumerate(args):
			# datatype
			if isinstance(arg, defs[i]['datatype']):
				pass
			else:
				if bool in defs[i]['datatype'] and strint_to_bool(arg) is not None:
					args[i] = strint_to_bool(arg)
				elif int in defs[i]['datatype'] and isinstance(arg, str) and isint(arg):
					# an int hidden as a string...
					args[i] = int(arg)
				else:
					#print "hu_commands.py: Validate: Datatype: FAIL; {0}".format(type(args[i]))
					error_raise = True
					error_msg_datatype += "{0}".format(defs[i]['name'])
					
			# choices (case insensitive, valid for strings ONLY)
			if ( 'choices' in defs[i] and
				 isinstance(arg, str) and
				 not arg.lower() in [choice.lower() for choice in defs[i]['choices']] ):
					if 'FLOAT_PERCENTAGE' in defs[i]['choices'] and arg.endswith('%') and isfloatint(arg[:-1]):
						pass
					elif 'INT_PERCENTAGE' in defs[i]['choices'] and arg.endswith('%') and isint(arg[:-1]):
						pass
					elif 'FLOAT_SIGNED' in defs[i]['choices'] and (arg.startswith('+') or arg.startswith('-')) and isfloatint(arg[1:]):
						pass
					elif 'INT_SIGNED' in defs[i]['choices'] and (arg.startswith('+') or arg.startswith('-')) and isint(arg[1:]):
						pass
					else:
						error_raise = True
						error_msg_choices += "{0} must be in: {1}".format(defs[i]['name'],",".join(defs[i]['choices']))
						
		if error_raise:
			
			if error_msg_datatype != "" and error_msg_choices != "":
				error_msg_datatype = "Invalid datatype(s): " + error_msg_datatype
				error_msg_choices = "Invalid choice: " + error_msg_choices
				raise ValueError(error_msg_datatype,error_msg_choices)
			elif error_msg_datatype != "":
				error_msg_datatype = "Invalid datatype(s): " + error_msg_datatype
				raise ValueError(error_msg_datatype)
			elif error_msg_choices != "":
				error_msg_choices = "Invalid choice: " + error_msg_choices
				raise ValueError(error_msg_choices)
			
			'''
			errors = []
			if error_msg_datatype != "":
				#error_msg += "Invalid datatype(s):" + error_msg_datatype
				errors.append(error_msg_datatype)
				
			if error_msg_choices != "":
				#error_msg += "Invalid choice:" + error_msg_choices
				errors.append(error_msg_choices)
			
			print errors
			raise ValueError(errors)
			'''
		
		# add default values / check if enough arguments present
		args_missing = len(defs)-len(args)
		i=0
		for arg_def in defs[len(args):len(defs)]:
			if 'default' in arg_def:
				i += 1
		defaults_available = i
		
		if args_missing == 0 and args_missing == defaults_available:
			# all ok
			pass
		elif args_missing > 0 and args_missing == defaults_available:
			for arg_def in defs[len(args):len(defs)]:
				#print arg_def
				args.append(arg_def['default'])
		else:
			raise ValueError("Not enough arguments")
		
		# everything OK
		return args

