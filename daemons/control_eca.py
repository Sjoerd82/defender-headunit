#!/usr/bin/python

#
# Ecasound Control
# Venema, S.R.G.
# 2018-04-20
#
# Ecasound controller controls Ecasound over ZeroMQ.
# Use for volume and eq control
# 
# Pyecasound on github:
# https://github.com/skakri/ecasound/tree/master/pyecasound
#
# Interactive Mode (IAM) commands:
# https://ecasound.seul.org/ecasound/Documentation/ecasound-iam_manpage.html
# 

# MQ: Pub & Sub

import sys
import os
import time

# ecasound
#from pyeca import *		# default implementation
from ecacontrol import *	# native Python implementation
from Queue import Queue		# queuing

# Utils
#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController
from hu_gpio import GpioController
from hu_commands import Commands
from hu_datastruct import Modeset

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "Ecasound Controller"
BANNER = "Ecasound Controller Daemon"
LOG_TAG = 'ECASND'
LOGGER_NAME = 'ecasnd'

SUBSCRIPTIONS = ['/volume/','/equalizer/','/events/source/','/ecasound/','/mode/']
#SUBSCRIPTIONS = ['/ecasound/']

PATH_VOLUME = '/volume'
PATH_VOLUME_EVENT = '/events/volume'

ECA_CHAIN_MASTER_AMP = 'pre'	# chain object that contains the master amp
ECA_CHAIN_MUTE = 'pre'			# chain object to mute
ECA_CHAIN_EQ = None				# chain object that contains the equalizer

eca_chain_op_master_amp = None
att_level = 20		# TODO, get from configuration
local_volume = 1	# TOOD, retrieve from resume!
local_volume_chg = False
eca_chain_selected = None
volume_increment = 0.15
volume_increment_fast = 0.5
chainsetup_filename = None
resilience_modes_received = False

logger = None
args = None
messaging = MqPubSubFwdController(origin=LOGGER_NAME)
gpio = None
command = Commands()
eca = None

cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ
cfg_ecasound = None
cfg_gpio = None		# GPIO setup

# global datastructures
modes = Modeset()
mode_controller = False		# ToDo remove

qVolume = None

app_commands =	[
	{	'name': 'mode-change',
		'params': [ {'name':'mode', 'required':True, 'datatype': (str,unicode), 'help':'Mode to set'},
					{'name':'state', 'required':True, 'datatype': bool, 'default': False, 'help':'True or False'}
		],
		'params_repeat': True,
		'description': 'Set a number of modes at once',
		'command': 'PUT',
		'path': '/mode/change'
	}
]

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})
		
def load_cfg_ecasound():
	""" Load ecasound configuration
		Returns:
			True: 	Success
			False:	Critical failure
	"""
	global eca_chainsetup
	global eca_chain_master_amp
	global eca_chain_mute
	global eca_chain_eq
	global eca_amplify_max
	global eca_volume_increment
	
	# load ecasound
	if 'ecasound' not in cfg_main:
		printer("Ecasound section not found in configuration.",level=LL_CRITICAL)
		return
	else:
		config = cfg_main['ecasound']
	
	# load mandatory variables
	try:
		eca_chainsetup = cfg_main['ecasound']['chainsetup']
		eca_chain_master_amp = cfg_main['ecasound']['chain_master_amp']
	except KeyError:
		printer("Mandatory configuration items missing in ecasound section",level=LL_CRITICAL)
		return
	
	# load other, less important, variables
	try:
		eca_chain_mute = cfg_main['ecasound']['chain_mute']
	except KeyError:
		eca_chain_mute = None
		printer("No muting chain specified, mute not available",level=LL_WARNING)

	try:
		eca_chain_eq = cfg_main['ecasound']['chain_eq']
	except KeyError:
		eca_chain_eq = None
		printer("No EQ chain specified, EQ not available",level=LL_WARNING)
		
	try:
		eca_amplify_max = cfg_main['ecasound']['amplify_max']
	except KeyError:
		eca_amplify_max = 100
		printer("No maximum amplification level specified, setting maximum amplification to 100%",level=LL_INFO)

	try:
		eca_amplify_max = cfg_main['ecasound']['volume_increment']
	except KeyError:
		eca_volume_increment = 5
		printer("No default volume increment specified, setting volume increment to 5%",level=LL_INFO)
		
	return config
		
# ********************************************************************************
# Ecasound
#
def eca_execute(command,tries=3):
	""" executes an IAM command and examines the output, retries if neccessary """
	for i in range(tries):
		reteca = eca.command(command)
		#if type(reteca) is StringType:
		if isinstance(reteca, str):
			if reteca[0:21] == "Response length error":
				time.sleep(1)
				printer("Executed: {0:30}; [FAIL] {1}".format(command,reteca),level=LL_ERROR)
			elif reteca == "":
				printer(colorize("Executed: {0:30}; [OK]".format(command,type(reteca)),'light_magenta'),level=LL_DEBUG)
				return reteca		
			else:
				printer(colorize("Executed: {0:30}; [OK] Response: {1}".format(command,reteca),'light_magenta'),level=LL_DEBUG)
				return reteca
		#elif reteca is None:
		else:
			printer(colorize("Executed: {0:30}; [OK] Response type: {1}".format(command,type(reteca)),'light_magenta'),level=LL_INFO)	#change to LL_DEBUG
			return reteca

def eca_load_chainsetup_file(ecs_file):
	""" Load, Test and Connect chainsetup file
		Returns:
			True:	All OK
			False:	Chainsetup not loaded
	"""
	# load chainsetup from file, it will be automatically selected
	eca_execute("cs-load {0}".format(ecs_file))
	
	#
	# test the loaded chainsetup
	#
	eca_chain_selected = eca_execute("cs-selected")
	if eca_chain_selected[:5] is not 'ERROR':
		printer("Loaded chainsetup: {0}".format(eca_chain_selected))
	else:
		printer("Could not select chainsetup!",level=LL_CRITICAL)
		#eca_execute("stop")
		#eca_execute("cs-disconnect")
		#exit(1)
		return False
	
	chains = eca_execute("c-list")
	printer("Chainsetup contains chains and operators:")
	for chain in chains:
		printer("Chain: {0}".format(chain))
		eca_execute("c-select {0}".format(chain))
		chain_ops = eca_execute("cop-list")
		for chain_op in chain_ops:
			printer(" - {0}".format(chain_op))
	
	# TEST: Amp chain (Volume Control)
	if cfg_ecasound['chain_master_amp'] not in chains:
		printer("Master amp chain ({0}) not found!".format(cfg_ecasound['chain_master_amp']))
	else:
		eca_execute("c-select {0}".format(cfg_ecasound['chain_master_amp']))
		eca_chain_selected = eca_execute("c-selected")
		if cfg_ecasound['chain_master_amp'] in eca_chain_selected:

			chain_ops = eca_execute("cop-list")
			#if 'amp-%' not in chain_ops:		
			if 'Amplify' in chain_ops:
				printer("Master amp chain: {0} [OK]".format(cfg_ecasound['chain_master_amp']))
				
			else:
				printer("Operator 'Amplify' not found!",level=LL_CRITICAL)
				#eca_execute("stop")
				#eca_execute("cs-disconnect")
				#exit(1)
				return False
				
		else:
			printer("Could not select master amp chain!",level=LL_CRITICAL)
			#eca_execute("stop")
			#eca_execute("cs-disconnect")
			#exit(1)
			return False

	# TEST: Mute chain (#TODO!)
	'''
	if eca_chain_mute and cfg_ecasound['chain_mute'] not in chains:
		printer("Mute chain ({0}) not found!".format(cfg_ecasound['chain_mute']))
	else:
		printer("Mute chain: {0}".format(cfg_ecasound['chain_mute']))
		
	# TEST: EQ chain (#TODO!)
	if eca_chain_eq and cfg_ecasound['chain_eq'] not in chains:
		printer("EQ chain ({0}) not found!".format(cfg_ecasound['chain_eq']))
	else:
		printer("EQ chain: {0}".format(cfg_ecasound['chain_eq']))
	'''
	# all good!
	global chainsetup_filename
	chainsetup_filename = ecs_file
	
	# TODO TODO TODO -- GET FROM RESUME -- !!! !!!
	eca_set_effect_amplification(local_volume)

	eca_execute("cs-connect")
#	eca_execute("start")
	
	printer("Current amp level: {0}%".format(eca_get_effect_amplification()))
	return True
	
def eca_get_effect_amplification():
	eca_chain_op_master_amp = 'Amplify'
	eca_execute("c-select {0}".format(ECA_CHAIN_MASTER_AMP))
	eca_execute("cop-select {0}".format(eca_chain_op_master_amp))
	eca_execute("copp-index-select 1")
	ea_value = eca_execute("copp-get")
	return ea_value
	
def eca_set_effect_amplification(level):

	global local_volume
	
	if level < 0:
		local_volume = 0
		level = 0
		
	#eca_chain_op_master_amp = 'Amplify'
	#eca_chain_selected
	# todo, keep local track of selected cs, c, etc.
	#eca_execute("c-select {0}".format(ECA_CHAIN_MASTER_AMP))	# redundant, for now... #todo
	#eca_execute("cop-select {0}".format(eca_chain_op_master_amp))
	#eca_execute("copp-index-select 1")
	#print
	eca_execute("copp-set {0}".format(level),tries=1)
	return level
	
def eca_mute(state):
	""" state can be: 'on', 'off' or 'toggle' """
	if state in ['on','off','mute']:
		eca_execute("c-select {0}".format(ECA_CHAIN_MUTE))
		eca_execute("c-mute {0}".format(state))
		return True
	else:
		printer("Invalid mute parameter: {0}. Valid parameters are 'on','off' or 'toggle'".format(state),level=LL_ERROR)
		return False

# ********************************************************************************
# GPIO Callback
#
def cb_gpio_function(code, params):
	global local_volume
	global local_volume_chg
	#print "Added to queue: EXECUTE: {0}".format(code)
	#qVolume.put(code)
	if code in ('VOLUME_INC','VOLUME_DEC','VOLUME_INC_FAST','VOLUME_DEC_FAST'):
		printer("Executing: {0}".format(code))
		if code == 'VOLUME_INC':
			local_volume += volume_increment
			local_volume_chg = True
		elif code == 'VOLUME_DEC':
			local_volume -= volume_increment
			local_volume_chg = True
		elif code == 'VOLUME_INC_FAST':
			local_volume += volume_increment_fast
			local_volume_chg = True
		elif code == 'VOLUME_DEC_FAST':
			local_volume -= volume_increment_fast
			local_volume_chg = True
			
	elif code == 'PLAYER_NEXT':
		mq_path = '/player/next'
		mq_cmd = 'PUT'
		ret = messaging.publish_command(mq_path,mq_cmd)
		if ret == True:
			print "Response: [OK]"
		elif ret == False or ret is None:
			print "Response: [FAIL]"
		
	elif code == 'PLAYER_PREV':
		mq_path = '/player/prev'
		mq_cmd = 'PUT'
		ret = messaging.publish_command(mq_path,mq_cmd)
		if ret == True:
			print "Response: [OK]"
		elif ret == False or ret is None:
			print "Response: [FAIL]"

	elif code == 'SOURCE_NEXT':
		mq_path = '/source/next'
		mq_cmd = 'PUT'
		ret = messaging.publish_command(mq_path,mq_cmd)
		if ret == True:
			print "Response: [OK]"
		elif ret == False or ret is None:
			print "Response: [FAIL]"
	else:
		printer("Function {0} not in function_map".format(code),level=LL_ERROR)


def cb_mode_change(mode_changes):
	print "Hello from cb_mode_change(): {0}".format(mode_changes)
	
"""
def handle_queue(code,count):
	global local_volume
	print "EXECUTE: {0} ({1} times)".format(code,count)
	if code in ('VOLUME_INC','VOLUME_DEC','VOLUME_INC_FAST','VOLUME_DEC_FAST'):#function_map:
		if code == 'VOLUME_INC':
			local_volume += volume_increment * count
			eca_set_effect_amplification(local_volume)
		elif code == 'VOLUME_DEC':
			local_volume -= volume_increment * count
			eca_set_effect_amplification(local_volume)
	else:
		print "function {0} not in function_map".format(code)
"""


# ********************************************************************************
# MQ handler
#

def validate_args2(args, min_args, max_args):

	if len(args) < min_args:
		printer('Function arguments missing', level=LL_ERROR)
		return False
		
	if len(args) > max_args:
		printer('More than {0} argument(s) given, ignoring extra arguments'.format(max_args), level=LL_WARNING)
		#args = args[:max_args]
		
	return True

def get_data(ret,returndata=False,eventpath=None):

	print "DEBUG: ret = {0}".format(ret)

	data = {}
	
	if ret is None:
		data['retval'] = 500
		data['payload'] = None
		
	elif ret is False:
		data['retval'] = 500
		data['payload'] = None
		
	elif ret is True:
		data['retval'] = 200
		data['payload'] = None

	else:
		data['retval'] = 200
		data['payload'] = ret

	if ( eventpath == '/events/volume/changed' or 
	     eventpath == '/events/volume/att' or
	     eventpath == '/events/volume/mute' ):
		data['payload'] = ret
		messaging.publish_command(eventpath,'DATA',data)
			
	if not returndata:
		data['payload'] = None
		
	return data

# ********************************************************************************
# MQ: /ecasound
#	
@messaging.handle_mq('/ecasound/chainsetup', cmd='GET')
def mq_eca_cs_get(path=None, cmd=None, args=None, data=None):
	"""	Retrieve currently active chainsetup """
	data = struct_data(chainsetup_filename)
	return data	# this will be returned using the response path
	
@messaging.handle_mq('/ecasound/chainsetup', cmd='PUT')
def mq_eca_cs_put(path=None, cmd=None, args=None, data=None):
	"""	Set the active chainsetup """
	# TODO: validate input
	print args[0]
	if os.path.exists(args[0]):
		ret = eca_load_chainsetup_file(args[0])
	data = struct_data(ret) # True=OK, False=Not OK
	return data
	
@messaging.handle_mq('/ecasound/mode/active', cmd='DATA')
def mq_eca_mode_active(path=None, cmd=None, args=None, data=None):
	global resilience_modes_received
	print "RECEIVED LIST OF ACTIVE MODES..."
	print data
	resilience_modes_received = True
	if 'payload' in data:
		active_modes = data['payload']
		for mode in active_modes:
			print "SETTING MODE ACTIVE: {0}".format(mode)
			gpio.set_mode(mode)

# ********************************************************************************
# MQ: /volume
#

@messaging.handle_mq('/volume/master', cmd='GET')
def mq_master_get(path=None, cmd=None, args=None, data=None):
	""" get master volume """
	validate_args2(params,0,0)	# no args
	level = eca_get_effect_amplification()
	data = get_data(dict_volume(system='ecasound', simple_vol=level),returndata=True)
	print "DEBUG data:"
	print data
	return data
	
@messaging.handle_mq('/volume/master', cmd='PUT')
@command.validate('VOLUME-SET')
def mq_master_put(path=None, cmd=None, args=None, data=None):
	""" set master volume """
	global local_volume
	#validate_args2(params,1,1)	# arg can be: <str:up|down|+n|-n|att>
	old_volume = local_volume
	if args[0] == 'up':
		local_volume += volume_increment
		
	elif args[0] == 'down':
		local_volume -= volume_increment
		
	elif args[0][0] == '+':
		try:
			change = int(args[0][1:])
			local_volume += change
			print "DEBUG: LEVEL = + {0}".format(change)
		except:
			print "ERROR converting volume level to integer"
		
	elif args[0][0] == '-':
		try:
			change = int(args[0][1:])
			local_volume += change
			print "DEBUG: LEVEL = - {0}".format(change)
		except:
			print "ERROR converting volume level to integer"

	elif args[0] == 'att':
		local_volume = att_level
		
	eca_set_effect_amplification(local_volume)
	get_data(None,eventpath='/events/volume/changed')

@messaging.handle_mq('/volume/master/increase', cmd='PUT')
def mq_master_increase_put(path=None, cmd=None, args=None, data=None):
	"""	Increase Volume
		Arguments:		[percentage]
		Return data:	Nothing
	"""
	global local_volume
	validate_args2(params,0,1)	# [percentage]
	
	if not params:
		local_volume += volume_increment
	else:
		change = int(params[0][1])
		local_volume += change

	eca_set_effect_amplification(local_volume)	
	if not args.b:
		printer("Amp level: {0}%".format(local_volume))

	get_data(None,eventpath='/events/volume/changed')
	
@messaging.handle_mq('/volume/master/decrease', cmd='PUT')
def mq_master_decrease_put(path=None, cmd=None, args=None, data=None):
	global local_volume
	validate_args2(params,0,1)	# [percentage]
	
	if not params:
		local_volume -= volume_increment
	else:
		change = int(params[0][1])
		local_volume -= change

	eca_set_effect_amplification(local_volume)	
	if not args.b:
		printer("Amp level: {0}%".format(local_volume))
		
	get_data(None,eventpath='/events/volume/changed')
	
@messaging.handle_mq('/volume/master/att', cmd='PUT')
def mq_att_put(path=None, cmd=None, args=None, data=None):
	global local_volume
	validate_args2(params,0,2)	# [str:on|off|toggle],[int:Volume, in %]

	if not params:
		local_volume = att_level
		
	if len(params) == 2:
		tmp_att_level = params[1]
	else:
		tmp_att_level = att_level
		
	if len(params) == 1:
		if params[0] == "on":
			local_volume = tmp_att_level
		#elif params[0] == "off":
		#	local_volume = ?
		#elif params[0] == "toggle":
		#	pass
	eca_set_effect_amplification(local_volume)
	get_data(None,eventpath='/events/volume/att')
	
@messaging.handle_mq('/volume/master/mute', cmd='PUT')
def mq_mute_put(path=None, cmd=None, args=None, data=None):
	validate_args2(params,0,1)	# arg can be [str:on|off|toggle]
	if not params:
		eca_mute('toggle')
	else:
		eca_mute(params[0])
		
	get_data(None,eventpath='/events/volume/mute')
	
# ********************************************************************************
# MQ: /equalizer
#
@messaging.handle_mq('/equalizer/eq')
def get_eq(path=None, cmd=None, args=None, data=None):
	pass	

@messaging.handle_mq('/equalizer/band', cmd='PUT')
def put_band(path=None, cmd=None, args=None, data=None):
	pass

# ********************************************************************************
# MQ: /events
#
@messaging.handle_mq('/events/source/active', cmd='DATA')
def mq_source_active_data(path=None, cmd=None, args=None, data=None):
	if len(params) >= 1:
		payload = json.loads(params[0])
		print payload
	else:
		print "HUH??"
		
@messaging.handle_mq('/events/mode/set', cmd='DATA')
def mq_mode_set_data(path=None, cmd=None, args=None, data=None):
	print "A MODE WAS SET"


# ********************************************************************************
# MQ: /mode
#
# args = list of arguments
# return False to return a 500 error thingy
# return None to not return anything

@messaging.handle_mq('/mode/change', cmd='PUT')
def mq_mode_change_put(path=None, cmd=None, args=None, data=None):
	"""
	Change modes; MODE-CHANGE
	Args:    Pairs of Mode-State
	Returns: None
	"""
	valid_args = command.validate_args('MODE-CHANGE',args)
	if valid_args is not None and valid_args is not False:
		print "DEBUG, before: {0}".format(gpio.activemodes())
		gpio.change_modes(valid_args)
		printer("Active Modes: {0}".format(gpio.activemodes()))
	else:
		printer("put_change: Arguments: [FAIL]",level=LL_ERROR)
	
	return None
	
@messaging.handle_mq('/mode/set', cmd='PUT')
def mq_mode_set(path=None, cmd=None, args=None, data=None):
	print "A MODE WAS SET"
	if mode_controller:
		return True
	else:
		return None

@messaging.handle_mq('/mode/unset', cmd='PUT')
def mq_unset_put(path=None, cmd=None, args=None, data=None):
	print "A MODE WAS UNSET"
	
	if mode_controller:
		return True
	else:
		return None

	
#********************************************************************************
# Parse command line arguments
#
def parse_args():

	global args
	import argparse
	parser = default_parser(DESCRIPTION,BANNER)
	# additional command line arguments mat be added here
	parser.add_argument('--server',  required=False, action='store_true', help='Enable ECA server')		# todo, implement
	args = parser.parse_args()

"""
class pa_volume_handler():

	VOL_INCR = "5%"

	def __init__(self, sink):
		self.pa_sink = sink

	def vol_set_pct(self, volume):
		#vol_pct = str(volume) + "%"
		vol_pct = volume
		call(["pactl", "set-sink-volume", self.pa_sink, vol_pct])
		
	def vol_up(self):
		vol_chg = "+" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.pa_sink, vol_chg])
		
	def vol_down(self):
		vol_chg = "-" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.pa_sink, vol_chg])

	def vol_get(self):
		#pipe = Popen("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'")
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		vol = subprocess.check_output("/root/pa_volume.sh")
		return int(vol.splitlines()[0])

		
# callback, keep it short! (blocks new input)
def cb_volume( volume ):

	printer('DBUS event received: {0}'.format(volume), tag='volume')
	pavh.vol_set_pct(volume)
		
	return True
			
pavh = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')
"""

#********************************************************************************	
def setup():

	#
	# Logging
	# -> Output will be logged to the syslog, if -b specified, otherwise output will be printed to console
	#
	global logger
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)

	if args.b:
		logger = log_create_syslog_loghandler(logger, args.loglevel, LOG_TAG, address='/dev/log') 	# output to syslog
	else:
		logger = log_create_console_loghandler(logger, args.loglevel, LOG_TAG) 						# output to console
	
	#
	# Configuration
	#
	global cfg_main
	global cfg_zmq
	global cfg_daemon
	global cfg_gpio
	global cfg_ecasound
	
	cfg_main, cfg_zmq, cfg_daemon, cfg_gpio = load_cfg(
		args.config,
		['main','zmq','daemon','gpio'],
		args.port_subscriber, args.port_subscriber,
		daemon_script=os.path.basename(__file__),
		logger_name=LOGGER_NAME	)
	
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
			
	if cfg_daemon is None:
		printer("Daemon configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	if cfg_gpio is None:
		printer("GPIO configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
		
	# eca
	cfg_ecasound = load_cfg_ecasound()
	if cfg_ecasound is None:
		printer("Ecasound configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)

	'''
	cfg_main = load_cfg_main()
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)

	# zeromq
	if not args.port_publisher and not args.port_subscriber:
		cfg_zmq = load_cfg_zmq()
	else:
		if args.port_publisher and args.port_subscriber:
			pass
		else:
			load_cfg_zmq()
	
		# Pub/Sub port override
		if args.port_publisher:
			configuration['zeromq']['port_publisher'] = args.port_publisher
		if args.port_subscriber:
			configuration['zeromq']['port_subscriber'] = args.port_subscriber

	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
			
	# daemon
	cfg_daemon = load_cfg_daemon()
	if cfg_daemon is None:
		printer("Daemon configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	# eca
	cfg_ecasound = load_cfg_ecasound()
	if cfg_ecasound is None:
		printer("Ecasound configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)

	# gpio
	cfg_gpio = load_cfg_gpio()
	if cfg_gpio is None:
		printer("GPIO configuration could not be loaded. GPIO input will not be available", level=LL_WARNING)
	'''

	#
	# ECA
	#	
	global eca
	os.environ['ECASOUND'] = '/usr/bin/ecasound --server'
	eca = ECA_CONTROL_INTERFACE(2)	# # debug level (0, 1, 2, ...)
	
	cs_location = cfg_main['system_configuration']['ecasound_ecs']['location']
	ecs_file = os.path.join(cs_location,eca_chainsetup+'.ecs')
	if os.path.exists(ecs_file):
		printer("Using chainsetup: {0} [OK]".format(ecs_file))
	else:
		printer("Not found: {0}".format(ecs_file),level=LL_CRITICAL)
		exit(1)

	retval = eca_load_chainsetup_file(ecs_file)
	if not retval:
		exit(1)

	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging.set_address('localhost',cfg_zmq['port_publisher'],cfg_zmq['port_subscriber'])
	
	printer("ZeroMQ: Creating Publisher: {0}".format(cfg_zmq['port_publisher']))
	messaging.create_publisher()

	printer("ZeroMQ: Creating Subscriber: {0}".format(cfg_zmq['port_subscriber']))
	messaging.create_subscriber(SUBSCRIPTIONS)

	printer('ZeroMQ subscriptions:')
	for topic in messaging.subscriptions():
		printer("> {0}".format(topic))

	#
	# GPIO
	#
	global gpio
	global modes
	printer("GPIO: Initializing")
	gpio = GpioController(cfg_gpio,cb_gpio_function,cb_mode_change,logger=logger)
	
	#modes = gpio.modeset('volume')
	#print modes
	#active_modes = modes.active_modes()	# None
	
	#print "Active modes: {0}".format(active_modes)
	#todo: GPIO cleanup
	
	print "EXPERIMENTAL, requesting active modes.."
	messaging.publish_command('/mode/active','GET', wait_for_reply=False, response_path='/ecasound/mode/active')
	
	printer('Initialized [OK]')

def main():

	global bus
	global qVolume
	global local_volume_chg
	global resilience_modes_received
		
	# Initialize the mainloop
	#DBusGMainLoop(set_as_default=True)
	#mainloop = gobject.MainLoop()
	
	# Initialize MQ message receiver
	#gobject.idle_add(handle_mq_message)
	
	#qVolume = Queue(maxsize=4)	# Short stuff that can run anytime:
	#qVolume = deque()	import ???


	eca_execute("start")
	counter = 0
	while True:
		
		if local_volume_chg == True:
			local_volume_chg = False
			eca_set_effect_amplification(local_volume)
		'''
		while not qVolume.empty():
			queue_size = qVolume.qsize()
			item = qVolume.get_nowait()
			if item is not None:
				# assuming that all items in queue are identical (perhaps it won't have to much impact on latency to actually test this)
				handle_queue(item,queue_size)
				# sign off task
				qVolume.task_done()
				qVolume.clear()
			time.sleep(0.1)
		'''
		if counter % 9 == 0:
			# only every 10th iteration
			messaging.poll_and_execute(500) # do this less often TODO! not critical, but takes up precious response time
			#counter = 0
			
		if counter % 150 == 0:
			if not resilience_modes_received:
				messaging.publish_command('/mode/active','GET',wait_for_reply=False, response_path='/ecasound/mode/active')
			counter = 0
		
		counter += 1
		
	print "Stopping Ecasound"
	eca_execute("stop")
	eca_execute("cs-disconnect")
	# gpio disconnect #TODO!
	
	"""
	try:
		eca_execute("start")
		mainloop.run()
	finally:
		mainloop.quit()
		print "Stopping Ecasound"
		eca_execute("stop")
		eca_execute("cs-disconnect")
	"""

if __name__ == "__main__":
	parse_args()
	setup()
	main()
	
