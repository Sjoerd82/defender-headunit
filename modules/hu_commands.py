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
			{
				'name': 'SOURCE',
				'description':'''Retrieve source details for current or given (sub)index.''',
				'command': 'GET',
				'params': [
					{ 'name':'index', 'datatype':(int,), 'required':False, 'help':'''Source index; '-1' returns all.''' },
					{ 'name':'subindex', 'datatype':(int,), 'required':False, 'help':'''Sub source index; '-1' returns all.''' }
				],
				'path':'/source'
			},

			{
				'name': 'SOURCE-SELECT',
				'description':'''Switch to given (sub)source and start playback.''',
				'command': 'PUT',
				'params': [
					{ 'name':'index', 'datatype':(int,), 'required':True, 'help':'''Source index''' },
					{ 'name':'subindex', 'datatype':(int,), 'required':False, 'help':'''Sub source index''' }
				],
				'path':'/source'
			},

			{
				'name': 'SOURCE-DELETE',
				'description':'''Remove specified (sub)source.''',
				'command': 'DEL',
				'params': [
					{ 'name':'index', 'datatype':(int,), 'required':True, 'help':'''Source index''' },
					{ 'name':'subindex', 'datatype':(int,), 'required':False, 'help':'''Sub source index''' }
				],
				'path':'/source'
			},

			{
				'name': 'SOURCE-NEXT',
				'description':'''Switch to next available (sub)source and start playback.''',
				'command': 'PUT',
				'params': [
					{ 'name':'primary', 'datatype':(bool,), 'required':False, 'help':'''Skip to to next primary source''' }
				],
				'path':'/source/next'
			},
			{
				'name': 'SOURCE-PREV',
				'description':'''Switch to previous available (sub)source and start playback.''',
				'command': 'PUT',
				'params': [
					{ 'name':'primary', 'datatype':(bool,), 'required':False, 'help':'''Skip to to previous primary source''' }
				],
				'path':'/source/prev'
			},
			{
				'name': 'SOURCE-ENABLE',
				'description':'''Mark (sub)source as (un)available.''',
				'command': 'PUT',
				'params': [
					{ 'name':'index', 'datatype':(int,), 'required':True, 'help':'''Source index''' },
					{ 'name':'subindex', 'datatype':(int,), 'required':True, 'help':'''Sub source index; '-1' marks all.''', 'default':-1 },
					{ 'name':'available', 'datatype':(bool,), 'required':True, 'help':'''Set Available''', 'choices':[True, False] }
				],
				'path':'/source/available'
			},


			{
				'name': 'SOURCE-UPDATE',
				'description':'''Update current or given (sub)source.''',
				'command': 'PUT',
				'params': [
					{ 'name':'index', 'datatype':(int,), 'required':False, 'help':'''Source index''' },
					{ 'name':'subindex', 'datatype':(int,), 'required':False, 'help':'''Sub source index''' }
				],
				'path':'/source/update'
			},

			{
				'name': 'SOURCE-CHECK',
				'description':'''Check current or given (sub)source for availability.''',
				'command': 'PUT',
				'params': [
					{ 'name':'index', 'datatype':(int,), 'required':False, 'help':'''Source index; '-1' checks all.''' },
					{ 'name':'subindex', 'datatype':(int,), 'required':False, 'help':'''Sub source index; '-1' checks all.''' }
				],
				'path':'/source/check'
			},

			{
				'name': 'PLAYER-METADATA',
				'description':'''Retrieve all available data, incl ID3 tag, of currently playing media.''',
				'command': 'GET',
				'params': None,
				'path':'/player/metadata'
			},
			{
				'name': 'PLAYER-PLS',
				'description':'''Retrieve current playlist.''',
				'command': 'GET',
				'params': None,
				'path':'/player/playlists'
			},
			{
				'name': 'PLAYER-PLS-LOAD',
				'description':'''Load playlist.''',
				'command': 'PUT',
				'params': [
					{ 'name':'playlist', 'datatype':(str,), 'required':True, 'help':'''Playlist to load''' }
				],
				'path':'/player/playlists/load'
			},
			{
				'name': 'PLAYER-NEXT',
				'description':'''Next track/station.''',
				'command': 'PUT',
				'params': [
					{ 'name':'advance_count', 'datatype':(int,), 'required':False, 'help':'''Number of tracks to advance.''' }
				],
				'path':'/player/next'
			},
			{
				'name': 'PLAYER-PREV',
				'description':'''Prev track/station.''',
				'command': 'PUT',
				'params': [
					{ 'name':'jump_to_start', 'datatype':(bool,), 'required':False, 'help':'''Jump to beginning of track (counts as 1 reverse), if supported.''', 'default':True },
					{ 'name':'reverse_count', 'datatype':(int,), 'required':False, 'help':'''Number of tracks to reverse.''' }
				],
				'path':'/player/prev'
			},

			{
				'name': 'PLAYER-PLAY-POS',
				'description':'''Play track at specified position in playlist.''',
				'command': 'PUT',
				'params': [
					{ 'name':'position', 'datatype':(int,), 'required':True, 'help':'''Position in playlist''' }
				],
				'path':'/player/play_positition'
			},
			{
				'name': 'PLAYER-FOLDERS',
				'description':'''Retrieve list of playlist position to folder mapping.''',
				'command': 'GET',
				'params': None,
				'path':'/player/folders'
			},
			{
				'name': 'PLAYER-FOLDER-NEXT',
				'description':'''Advance to next folder.''',
				'command': 'PUT',
				'params': [
					{ 'name':'advance_count', 'datatype':(int,), 'required':False, 'help':'''Number of folders to advance.''', 'default':1 }
				],
				'path':'/player/folder/next'
			},
			{
				'name': 'PLAYER-FOLDER-PREV',
				'description':'''Return to previous folder.''',
				'command': 'PUT',
				'params': [
					{ 'name':'jump_to_start', 'datatype':(bool,), 'required':False, 'help':'''Jump to first track in folder (counts as 1 reverse).''', 'default':True },
					{ 'name':'reverse_count', 'datatype':(int,), 'required':False, 'help':'''Number of folders to reverse.''', 'default':1 }
				],
				'path':'/player/folder/prev'
			},

			{
				'name': 'PLAYER-PLAY',
				'description':'''Play.''',
				'command': 'PUT',
				'params': [
					{ 'name':'state', 'datatype':(str,), 'required':False, 'help':'''Play state''', 'choices':['on','off','toggle'], 'default':'toggle' }
				],
				'path':'/player/play'
			},
			{
				'name': 'PLAYER-PAUSE',
				'description':'''Pause.''',
				'command': 'PUT',
				'params': [
					{ 'name':'state', 'datatype':(str,), 'required':False, 'help':'''Play state''', 'choices':['on','off','toggle'], 'default':'toggle' }
				],
				'path':'/player/pause'
			},
			{
				'name': 'PLAYER-STOP',
				'description':'''Stop.''',
				'command': 'PUT',
				'params': [
					{ 'name':'state', 'datatype':(str,), 'required':False, 'help':'''Play state''', 'choices':['on','off','toggle'], 'default':'toggle' }
				],
				'path':'/player/stop'
			},
			{
				'name': 'PLAYER-STATE',
				'description':'''Retrieve player state (play/pause/stop).''',
				'command': 'GET',
				'params': None,
				'path':'/player/state'
			},

			{
				'name': 'PLAYER-RANDOM-SET',
				'description':'''Set random mode.''',
				'command': 'PUT',
				'params': [
					{ 'name':'mode', 'datatype':(str,unicode,), 'required':False, 'help':'''Random mode''', 'choices':['off','next','prev','folder','artist','genre','playlist'], 'default':'next' }
				],
				'path':'/player/random'
			},
			{
				'name': 'PLAYER-RANDOM',
				'description':'''Retrieves current random mode.''',
				'command': 'GET',
				'params': None,
				'path':'/player/random'
			},
			{
				'name': 'PLAYER-RANDOM-LIST',
				'description':'''Retrieves list of supported random modes for currently playing source.''',
				'command': 'GET',
				'params': None,
				'path':'/player/random/supported'
			},
			{
				'name': 'PLAYER-RANDOM-NEXT',
				'description':'''Selects next random mode.''',
				'command': 'PUT',
				'params': None,
				'path':'/player/random/next'
			},
			{
				'name': 'PLAYER-RANDOM-PREV',
				'description':'''Selects previous random mode.''',
				'command': 'PUT',
				'params': None,
				'path':'/player/random/prev'
			},
			{
				'name': 'PLAYER-SEEK',
				'description':'''Seek forward or reverse. Use a negative value to reverse.''',
				'command': 'PUT',
				'params': [
					{ 'name':'seek_seconds', 'datatype':(int,), 'required':False, 'help':'''Seconds to seek forward/reverse''' }
				],
				'path':'/player/seek'
			},
			{
				'name': 'PLAYER-UPDATE',
				'description':'''Update MPD database, preferablly specify a location to update.''',
				'command': 'PUT',
				'params': [
					{ 'name':'location', 'datatype':(str,), 'required':False, 'help':'''Location, as seen from MPD''' }
				],
				'path':'/player/update'
			},
			{
				'name': 'SYSTEM-SHUTDOWN',
				'description':'''Shutdown.''',
				'command': 'PUT',
				'params': [
					{ 'name':'timer_seconds', 'datatype':(int,), 'required':False, 'help':'''Seconds to wait''', 'default':0 }
				],
				'path':'/system/shutdown'
			},
			{
				'name': 'SYSTEM-REBOOT',
				'description':'''Reboot.''',
				'command': 'PUT',
				'params': [
					{ 'name':'timer_seconds', 'datatype':(int,), 'required':False, 'help':'''Seconds to wait''', 'default':0 }
				],
				'path':'/system/reboot'
			},

			{
				'name': 'VOLUME',
				'description':'''Retrieve current volume''',
				'command': 'GET',
				'params': None,
				'path':'/volume/master'
			},
			{
				'name': 'VOLUME-SET',
				'description':'''Set volume, when using n+, n-, n=percentage)''',
				'command': 'PUT',
				'params': [
					{ 'name':'volume', 'datatype':(str,unicode,int,float,), 'required':True, 'help':'''Volume''', 'choices':['up','down','FLOAT_PERCENTAGE','FLOAT_SIGNED','att','mute'] }
				],
				'path':'/volume/master'
			},
			{
				'name': 'VOLUME-INCR',
				'description':'''Increase volume by percentage''',
				'command': 'PUT',
				'params': [
					{ 'name':'percentage', 'datatype':(str,unicode,int,float,), 'required':True, 'help':'''Percentage to increase''', 'choices':['FLOAT_PERCENTAGE'] }
				],
				'path':'/volume/master/increase'
			},
			{
				'name': 'VOLUME-DECR',
				'description':'''Decrease volume by percentage''',
				'command': 'PUT',
				'params': [
					{ 'name':'percentage', 'datatype':(str,unicode,int,float,), 'required':True, 'help':'''Percentage to decrease''', 'choices':['FLOAT_PERCENTAGE'] }
				],
				'path':'/volume/master/decrease'
			},
			{
				'name': 'VOLUME-ATT',
				'description':'''Set volume to ATT level. Optionally, set (override) level in %.''',
				'command': 'PUT',
				'params': [
					{ 'name':'state', 'datatype':(str,unicode,), 'required':False, 'help':'''Att state''', 'choices':['on','off','toggle'], 'default':'toggle' },
					{ 'name':'percentage', 'datatype':(str,unicode,int,float,), 'required':False, 'help':'''Volume percentage''', 'choices':['FLOAT_PERCENTAGE'] }
				],
				'path':'/volume/att'
			},

			{
				'name': 'VOLUME-MUTE',
				'description':'''Mute volume (default: toggle)''',
				'command': 'PUT',
				'params': [
					{ 'name':'state', 'datatype':(str,), 'required':False, 'help':'''Mute state''', 'choices':['on','off','toggle'], 'default':'toggle' }
				],
				'path':'/volume/mute'
			},

			{
				'name': 'ECA-CS',
				'description':'''Retrieve (file)name of current chainsetup.''',
				'command': 'GET',
				'params': None,
				'path':'/eca/chainsetup'
			},
			{
				'name': 'ECA-CS-SET',
				'description':'''Load chainsetup by name or from file.''',
				'command': 'PUT',
				'params': [
					{ 'name':'chainsetup', 'datatype':(str,unicode,), 'required':True, 'help':'''Filename or Name''' }
				],
				'path':'/eca/chainsetup'
			},

			{
				'name': 'MODE',
				'description':'''Retrieve list of all modes and their states.''',
				'command': 'GET',
				'params': None,
				'path':'/mode/all'
			},
			{
				'name': 'MODE-ACTIVE',
				'description':'''Retrieve list of all active modes.''',
				'command': 'GET',
				'params': None,
				'path':'/mode/active'
			},
			{
				'name': 'MODE-CHANGE',
				'description':'''(De)activate multiple modes in one go. Example: volume,off,bass,on.''',
				'command': 'PUT',
				'params': [
					{ 'name':'mode', 'datatype':(str,unicode,), 'required':True, 'help':'''Mode name.''' },
					{ 'name':'state', 'datatype':(bool,), 'required':True, 'help':'''Activate/Deactivate.''', 'choices':[True,False] }
				],
				'params_repeat':True,
				'path':'/mode/change'
			},

			{
				'name': 'MODE-ACTIVATE',
				'description':'''Activate mode.''',
				'command': 'PUT',
				'params': [
					{ 'name':'mode', 'datatype':(str,unicode,), 'required':True, 'help':'''Mode name.''' }
				],
				'path':'/mode/set'
			},
			{
				'name': 'MODE-DEACTIVATE',
				'description':'''Deactivate mode.''',
				'command': 'PUT',
				'params': [
					{ 'name':'mode', 'datatype':(str,unicode,), 'required':True, 'help':'''Mode name.''' }
				],
				'path':'/mode/unset'
			}
			
		]

		for command in self.function_mq_map:
			self.command_list.append(command['name'])
		
	def get_command(self, command):
		ix = self.command_list.index(command)
		if ix is not None:
			return self.function_mq_map[ix]
			
	def get_command_by_path(self, mq_path, mq_cmd):
		# TODO, add postfix slash to search
		for cmd in self.function_mq_map:
			if cmd['path'].upper() == mq_path.upper() and cmd['command'].upper() == mq_cmd.upper():
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
						try:
							kwargs['args'] = self.validate_args(command_to_validate['name'],kwargs['args'])
						except ValueError as err:
							print("ERROR: {0}".format(err))
							return False #??????????????
					else:
						return False #??????????????
				# use provided command
				#else:
				#	kwargs['args'] = self.validate_args(command,list_of_args)
				
				return fn(*args,**kwargs)
			return wrapper
		return decorator
	
	def validate_args(self, command, *args): #, repeat=False):
		"""
		args must be a list of arguments
		Returns list of args (including defaults) if valid (may return None if no params)
		Raises a ValueError if invalid.
		"""
		#print "DEBUG.. hello from validate_args Command={0}".format(command)
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
		
		# START CONVERSION TO *args FORMAT
		if isinstance(args,  tuple):
			arg_list = []
			for arg in args:
				arg_list.append(arg)
			
			args = arg_list
			print "CONVERTED BACK TO LIST: {0}".format(args)
			for arg in args:
				print "Arg: {0} {1}".format(arg, type(arg))
			if args = [[]]:
				print "PLEISTER [[]] -> None. fix dit"
				args = None
		
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
					error_msg_datatype += " param:{0}, datatype:{1}, must be:{2}".format(defs[i]['name'],type(arg),defs[i]['datatype'])
					
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
		i=0
		for arg_def in defs[len(args):len(defs)]:
			if 'required' in arg_def and arg_def['required']:
				i += 1
		args_req = i
		
		args_missing = args_req-len(args)
		i=0
		for arg_def in defs[len(args):len(defs)]:
			if 'default' in arg_def:
				i += 1
		defaults_available = i
		
		if args_missing < 0:
			pass
		elif args_missing == 0 and args_missing == defaults_available:
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

