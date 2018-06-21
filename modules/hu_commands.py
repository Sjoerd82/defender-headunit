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

			{	'name': 'SOURCE-LIST',
				'params': None,
				'description': 'List primary sources',
				'command': 'GET',
				'path': '/source/primary'
			},
			
			{	'name': 'SOURCE-CHECK',
				'params': [
					{'name':'index','required':False, 'help':''},
					{'name':'subindex','required':False, 'help':''}
				],
				'description': 'Check source availability',
				'command': 'PUT',
				'path': '/source/check'
			},
			
			{	'name': 'SOURCE-SELECT',
				 'params': [
					{'name':'index', 'required':True, 'help':''},
					{'name':'subindex','required':False, 'help':''}
				],
				 'description': 'Select a source',
				 'command':'PUT',
				 'path': '/source/subsource'
			},
			
			{	'name': 'SOURCE-NEXT-PRIMARY',
				'params': None,
				'description': 'Select next primary source',
				'command': 'PUT',
				'path': '/source/next_primary'
			},
			
			{	'name': 'SOURCE-PREV-PRIMARY',
				'params': None,
				'description': 'Select previous primary source',
				'command': 'PUT',
				'path': '/source/prev_primary'
			},
			
			{	'name': 'SOURCE-NEXT',
				'params': None,
				'description': 'Select next source',
				'command': 'PUT',
				'path': '/source/next'
			},
			
			{	'name': 'SOURCE-PREV',
				'params': None,
				'description': 'Select previous source',
				'command': 'PUT',
				'path': '/source/prev'
			},
			
			{	'name': 'SOURCE-AVAILABLE',
				 'params': [
					{'name':'availability', 'required':True, 'help':''},
					{'name':'index', 'required':True, 'help':''},
					{'name':'subindex','required':True, 'help':''}
				],
				'description': 'Set source availability',
				'command': 'PUT',
				'path': '/source/available'
			},
			
			{	'name': 'SOURCE-DETAILS',
				'params': [
					{'name':'index','required':False, 'help':'Source index'},
					{'name':'subindex','required':False, 'help':'Source subindex'}
				],
				'description': 'Get source details',
				'command': 'GET',
				'path': '/source/subsource'
			},
			
			{	'name': 'SOURCE-UPDATE',
				'params': [
					{'name':'index','required':False, 'help':'Source index'},
					{'name':'subindex','required':False, 'help':'Source subindex'}
				],
				'description': 'Update source (MPD: Source Database)',
				'command': 'PUT',
				'path': '/source/update'
			},
			
			{	'name': 'SOURCE-UPDATE-LOCATION',
				'params': [
					{'name':'location','required':True, 'help':'Relative location, as seen from MPD'}
				],
				'description': 'Update MPD database for given location',
				'command': 'PUT',
				'path': '/source/update-location'
			},
			
			{	'name': 'PLAYER-PLAY',
				'params': None,
				'description': 'Start playback',
				'command': 'PUT',
				'path': '/player/state',
				'params_override': '{"state":"play"}'
			},
			{	'name': 'PLAYER-PAUSE',
				'params': None,
				'description': 'Pause playback',
				'command': 'PUT',
				'path': '/player/state',
				'params_override': '{"state":"pause"}'
			},
			{	'name': 'PLAYER-STOP',
				'params': None,
				'description': 'Stop playback',
				'command': 'PUT',
				'path': '/player/state',
				'params_override': '{"state":"stop"}'
			},
			{	'name': 'PLAYER-STATE',
				'params': None,
				'description': 'Get state',
				'command': 'GET',
				'path': '/player/state'
			},
			{	'name': 'PLAYER-NEXT',
				'params': None,
				'description': 'Play next song',
				'command': 'PUT',
				'path': '/player/next'
			},
			{	'name': 'PLAYER-PREV',
				'params': None,
				'description': 'Play previous song',
				'command': 'PUT',
				'path': '/player/prev'
			},
			{	'name': 'PLAYER-SEEK',
				'params': [ {'name':'seconds', 'required':True, 'help':'Use a + or - sign to seek forward or reverse'} ],
				'description': 'Seek',
				'command': 'PUT',
				'path': '/player/seek'
			},
			{	'name': 'PLAYER-FOLDERS',
				'params': None,
				'description': 'List folders',
				'command': 'GET',
				'path': '/player/folders'
			},
			{	'name': 'PLAYER-NEXTFOLDER',
				'params': None,
				'description': 'Next folder',
				'command': 'PUT',
				'path': '/player/nextfolder'
			},
			{	'name': 'PLAYER-PREVFOLDER',
				'params': None,
				'description': 'Prev folder',
				'command': 'PUT',
				'path': '/player/prevfolder'
			},
			{	'name': 'PLAYER-UPDATE',
				'params': [ {'name':'location', 'required':False, 'help':'Location to update'} ],
				'description': 'Update MPD database',
				'command': 'PUT',
				'path': '/player/update'
			},
			{	'name': 'PLAYER-RANDOM-MODES',
				'params': None,
				'description': 'Get available random modes',
				'command': 'GET',
				'path': '/player/randommode'
			},
			{	'name': 'PLAYER-RANDOM',
				'params': [ {'name':'mode', 'required':False, 'help':'ON | OFF | TOGGLE (default)'} ],
				'description': 'Set random',
				'command': 'PUT',
				'path': '/player/random'
			},
			{	'name': 'PLAYER-DETAILS',
				'params': None,
				'description': 'Get player details',
				'command': 'GET',
				'path': '/player/track'
			},
			
			{	'name': 'VOLUME',
				'params': [ {'name':'volume', 'required':True,'help':'Volume in percentage'} ],
				'description': 'Set volume',
				'command': 'PUT',
				'path': '/volume'
			},
			
			{	'name': 'VOLUME-INCR',
				'params': [ {'name':'volume', 'required':True,'help':'Volume in percentage'} ],
				'description': 'Increase volume',
				'command': 'PUT',
				'path': '/volume'
			},
			{	'name': 'VOLUME-DECR',
				'params': [ {'name':'volume', 'required':True,'help':'Volume in percentage'} ],
				'description': 'Decrease volume',
				'command': 'PUT',
				'path': '/volume'
			},
			
			{	'name': 'VOLUME-ATT',
				'params': [ {'name':'mode', 'required':False, 'help':'ON (default) | OFF | TOGGLE'} ],
				'description': 'Set volume to ATT level',
				'command': 'PUT',
				'path': '/volume/att'
			},
			{	'name': 'VOLUME-MUTE',
				'params': [ {'name':'mode', 'required':False, 'help':'ON | OFF | TOGGLE (default)'} ],
				'description': 'Mute volume',
				'command': 'PUT',
				'path': '/volume/mute'
			},
			
			{	'name': 'ECA-CHAINSETUP-GET',
				'params': None,
				'description': 'Get current ecasound chainsetup',
				'command': 'GET',
				'path': '/ecasound/chainsetup'
			},
			{	'name': 'ECA-CHAINSETUP-SET',
				'params': [ {'name':'chainsetup', 'required':True, 'help':'Name of chain setup'} ],
				'description': 'Select ecasound chainsetup',
				'command': 'PUT',
				'path': '/ecasound/chainsetup'
			},
			
			{	'name': 'MODE-CHANGE',
				'params': [ {'name':'mode', 'required':True, 'datatype': (str,unicode), 'help':'Mode to set'},
							{'name':'state', 'required':True, 'datatype': bool, 'default': False, 'help':'True or False'} ],
				'params_repeat': True,
				'description': 'Set a number of modes at once',
				'command': 'PUT',
				'path': '/mode/change'
			},
			{	'name': 'MODE-SET',
				'params': [ {'name':'mode', 'required':True, 'help':'Mode to set'},
							{'name':'state', 'required':False, 'help':'True or False'}
				],
				'description': 'Set a mode',
				'command': 'PUT',
				'path': '/mode/set'
			},
			{	'name': 'MODE-UNSET',
				'params': [ {'name':'mode', 'required':True, 'help':'Mode to unset'} ],
				'description': 'Unset a mode',
				'command': 'PUT',
				'path': '/mode/unset'
			},	
			{	'name': 'MODES-LIST',
				'params': None,
				'description': 'Get list of registered modes',
				'command': 'GET',
				'path': '/mode/list'
			},
			{	'name': 'MODES-ACTIVE',
				'params': None,
				'description': 'Get list of currently active modes',
				'command': 'GET',
				'path': '/mode/active'
			},
			{	'name': 'mode-test1',
				'params': None,
				'description': 'TEST PUT',
				'command': 'PUT',
				'path': '/mode/test',
				'wait_for_reply': False
			},
			{	'name': 'mode-test2',
				'params': None,
				'description': 'TEST GET',
				'command': 'GET',
				'path': '/mode/test',
				'wait_for_reply': False
			},
			
			{	'name': 'SYSTEM-REBOOT',
				'params': [ {'name':'timer', 'required':False, 'help':'Time in seconds to shutdown. Default: 0'} ],
				'description': 'Reboot system',
				'command': 'PUT',
				'path': '/system/reboot'
			},
			{	'name': 'SYSTEM-SHUTDOWN',
				'params': [ {'name':'timer', 'required':False, 'help':'Time in seconds to shutdown. Default: 0'} ],
				'description': 'Shutdown system' ,
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

	#def validate_args(**args):
	def validate_args(self, command, args, repeat=False):
		"""
		args must be a list of arguments
		Returns args if valid
		"""

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
				
		arg_defs = self.get_command(command)['params']
		defs = arg_defs[:]	# cuz we might manipulate it, and python is stupid
		if defs is None:
			return None
		
		if not isinstance(args, list):
			print "second argument must be a list"
			return None

		# generate definitions
		if repeat:
			for i in range(len(args)/len(arg_defs)-1):
				defs.extend(arg_defs)
		
		for i, arg in enumerate(args):
			# datatype	
			if isinstance(arg, defs[i]['datatype']):
				#print "Datatype: PASS"
				pass
			else:
				if defs[i]['datatype'] == bool and strint_to_bool(arg) is not None:
					args[i] = strint_to_bool(arg)
				else:
					print "hu_commands.py: Validate: Datatype: FAIL"
					return None
					
		if len(defs)-len(args) > 0:
			for arg_def in defs[len(args):len(defs)]:
				print arg_def
				args.append(arg_def['default'])

		# everything OK
		return args

