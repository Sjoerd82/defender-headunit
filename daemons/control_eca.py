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

import sys
import os
import time

# main loop
import gobject
from dbus.mainloop.glib import DBusGMainLoop

# ecasound
from pyeca import *				# default implementation
#from ecacontrol import *		# native Python implementation

# Utils
#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_gpio import GpioController
from hu_msg import MqPubSubFwdController
from hu_msg import parse_message


# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "Ecasound Controller"
WELCOME = "Ecasound Controller Daemon"
LOG_TAG = 'ECASND'
LOGGER_NAME = 'ecasnd'

#DEFAULT_CONFIG_FILE = '/etc/configuration.json'
#DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560
SUBSCRIPTIONS = ['/volume/','/equalizer/']

PATH_VOLUME = '/volume'
PATH_VOLUME_EVENT = '/events/volume'

ECA_CHAIN_MASTER_AMP = 'pre'	# chain object that contains the master amp
ECA_CHAIN_MUTE = 'pre'			# chain object to mute
ECA_CHAIN_EQ = None				# chain object that contains the equalizer

eca_chain_op_master_amp = None
att_level = 20		# TODO, get from configuration
local_volume = 30	# TOOD, retrieve from resume!
eca_chain_selected = None
volume_increment = 5

logger = None
args = None
messaging = None
gpio = None
eca = None

cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ
cfg_ecasound = None
cfg_gpio = None		# GPIO setup


# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# ********************************************************************************
# Load configuration
#
def load_cfg_main():
	""" load main configuration """
	config = configuration_load(LOGGER_NAME,args.config)
	return config

def load_cfg_zmq():
	""" load zeromq configuration """	
	if not 'zeromq' in cfg_main:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		#cfg_main["zeromq"] = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB } }
		config = { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB }
		return config
	else:
		config = {}
		# Get portnumbers from either the config, or default value
		if 'port_publisher' in cfg_main['zeromq']:
			config['port_publisher'] = cfg_main['zeromq']['port_publisher']
		else:
			config['port_publisher'] = DEFAULT_PORT_PUB
		
		if 'port_subscriber' in cfg_main['zeromq']:
			config['port_subscriber'] = cfg_main['zeromq']['port_subscriber']		
		else:
			config['port_subscriber'] = DEFAULT_PORT_SUB
			
		return config

def load_cfg_daemon():
	""" load daemon configuration """
	if 'daemons' not in cfg_main:
		return
	else:
		for daemon in cfg_main['daemons']:
			if 'script' in daemon and daemon['script'] == os.path.basename(__file__):
				return daemon

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

def load_cfg_gpio():		
	""" load specified GPIO configuration """	
	if 'directories' not in cfg_main or 'daemon-config' not in cfg_main['directories'] or 'config' not in cfg_daemon:
		return
	else:		
		config_dir = cfg_main['directories']['daemon-config']
		# TODO
		config_dir = "/mnt/PIHU_CONFIG/"	# fix!
		config_file = cfg_daemon['config']
		
		gpio_config_file = os.path.join(config_dir,config_file)
	
	# load gpio configuration
	if os.path.exists(gpio_config_file):
		config = configuration_load(LOGGER_NAME,gpio_config_file)
		return config
	else:
		print "ERROR: not found: {0}".format(gpio_config_file)
		return
# ********************************************************************************
# Ecasound
#
def eca_execute(command,tries=3):
	""" executes an IAM command and examines the output, retries if neccessary """
	for i in range(tries):
		reteca = eca.command(command)
		#if type(reteca) is StringType:
		if isinstance(reteca, str):
			if reteca[0:20] == "Response length error":
				time.sleep(1)
				printer("Executed: {0:30}; [FAIL] {1}".format(command,reteca),level=LL_ERROR)
			elif reteca == "":
				printer(colorize("Executed: {0:30}; [OK]".format(command,type(reteca)),'light_magenta'),level=LL_INFO)	#change to LL_DEBUG
				return reteca		
			else:
				printer(colorize("Executed: {0:30}; [OK] Response: {1}".format(command,reteca),'light_magenta'),level=LL_INFO)	#change to LL_DEBUG
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
	eca_chain_op_master_amp = 'Amplify'
	#eca_chain_selected
	
	# todo, keep local track of selected cs, c, etc.
	
	eca_execute("c-select {0}".format(ECA_CHAIN_MASTER_AMP))
	eca_execute("cop-select {0}".format(eca_chain_op_master_amp))
	eca_execute("copp-index-select 1")
	print eca_execute("copp-set {0}".format(level),tries=1)
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
def cb_gpio_function(code):
	global local_volume
	print "EXECUTE: {0}".format(code)
	if code in ('VOLUME_INC','VOLUME_DEC'):#function_map:
		if code == 'VOLUME_INC':
			local_volume += 5
			eca_set_effect_amplification(local_volume)
		elif code == 'VOLUME_DEC':
			local_volume -= 5
			eca_set_effect_amplification(local_volume)
	else:
		print "function {0} not in function_map".format(code)	

# ********************************************************************************
# MQ handler
#	
def handle_mq_message():
	#print "DEBUG: idle_msg_receiver()"
	
	def dispatcher(path, command, arguments):
		handler_function = 'handle_path_' + path[0]
		if handler_function in globals():
			ret = globals()[handler_function](path, command, arguments)
			return ret
		else:
			print("No handler for: {0}".format(handler_function))
			return None
		
	rawmsg = messaging.poll(timeout=None)				#None=Blocking
	if rawmsg:
		printer("Received message: {0}".format(rawmsg),level=LL_DEBUG)
		parsed_msg = parse_message(rawmsg)

		# send message to dispatcher for handling	
		retval = dispatcher(parsed_msg['path'],parsed_msg['cmd'],parsed_msg['args'])
		
		if parsed_msg['resp_path']:
			#print "DEBUG: Resp Path present.. returing message.."
			messaging.publish_command(parsed_msg['resp_path'],'DATA',retval)
		
	return True # Important! Returning true re-enables idle routine.

def validate_args(args, min_args, max_args):

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

def handle_path_volume(path,cmd,params):
	""" This function implements /volume/-functions:
		get /volume/master
		put /volume/master
		put /volume/master/increase
		put /volume/master/decrease
		put /volume/att
		put /volume/mute
	"""	
	base_path = 'volume'
	# remove base path
	del path[0]

	def get_master(params):
		""" get master volume """
		validate_args(params,0,0)	# no args
		level = eca_get_effect_amplification()
		data = get_data(dict_volume(system='ecasound', simple_vol=level),returndata=True)
		print "DEBUG data:"
		print data
		return data

	def put_master(params):
		""" set master volume """
		global local_volume
		validate_args(params,1,1)	# arg can be: <str:up|down|+n|-n|att>
		old_volume = local_volume
		if params[0] == 'up':
			local_volume += volume_increment
			
		elif params[0] == 'down':
			local_volume -= volume_increment
			
		elif params[0][0] == '+':
			try:
				change = int(params[0][1:])
				local_volume += change
				print "DEBUG: LEVEL = + {0}".format(change)
			except:
				print "ERROR converting volume level to integer"
			
		elif params[0][0] == '-':
			try:
				change = int(params[0][1:])
				local_volume += change
				print "DEBUG: LEVEL = - {0}".format(change)
			except:
				print "ERROR converting volume level to integer"

		elif params[0] == 'att':
			local_volume = att_level
			
		eca_set_effect_amplification(local_volume)
		get_data(None,eventpath='/events/volume/changed')

	def put_master_increase(params):
		"""	Increase Volume
			Arguments:		[percentage]
			Return data:	Nothing
		"""
		global local_volume
		validate_args(params,0,1)	# [percentage]
		
		if not params:
			local_volume += volume_increment
		else:
			change = int(params[0][1])
			local_volume += change

		eca_set_effect_amplification(local_volume)	
		if not args.b:
			printer("Amp level: {0}%".format(local_volume))

		get_data(None,eventpath='/events/volume/changed')
		
	def put_master_decrease(params):
		global local_volume
		validate_args(params,0,1)	# [percentage]
		
		if not params:
			local_volume -= volume_increment
		else:
			change = int(params[0][1])
			local_volume -= change

		eca_set_effect_amplification(local_volume)	
		if not args.b:
			printer("Amp level: {0}%".format(local_volume))
			
		get_data(None,eventpath='/events/volume/changed')
			
	def put_att(params):
		global local_volume
		validate_args(params,0,2)	# [str:on|off|toggle],[int:Volume, in %]

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

	def put_mute(params):
		validate_args(params,0,1)	# arg can be [str:on|off|toggle]
		if not params:
			eca_mute('toggle')
		else:
			eca_mute(params[0])
			
		get_data(None,eventpath='/events/volume/mute')
	
	if path:
		function_to_call = cmd + '_' + '_'.join(path)
	else:
		# called without sub-paths
		function_to_call = cmd + '_' + base_path

	ret = None
	if function_to_call in locals():
		ret = locals()[function_to_call](params)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret),level=LL_DEBUG)
	else:
		printer('Function {0} does not exist'.format(function_to_call))

	return ret
	
def handle_path_equalizer(path,cmd,args):

	base_path = 'equalizer'
	# remove base path
	del path[0]

	def get_eq(args):
		pass
		
	def put_eq(args):
		pass
		
	def put_band(args):
		pass

	if path:
		function_to_call = cmd + '_' + '_'.join(path)
	else:
		# called without sub-paths
		function_to_call = cmd + '_' + base_path

	ret = None
	if function_to_call in locals():
		ret = locals()[function_to_call](args)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret),level=LL_DEBUG)
	else:
		printer('Function {0} does not exist'.format(function_to_call))

	return ret

#********************************************************************************
# Parse command line arguments
#
def parse_args():

	global args
	import argparse
	parser = default_parser(DESCRIPTION,WELCOME)
	# additional command line arguments mat be added here
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

	global messaging

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
	global cfg_daemon
	#global cfg_zmq	#only used here(?)
	global cfg_ecasound
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
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Subscriber: {0}".format(DEFAULT_PORT_SUB))
	messaging.create_subscriber(SUBSCRIPTIONS)

	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()

	#
	# GPIO
	#
	gpio = GpioController(cfg_gpio,cb_gpio_function)

	printer('Initialized [OK]')

def main():

	global bus
	
	# Initialize the mainloop
	DBusGMainLoop(set_as_default=True)
	mainloop = gobject.MainLoop()
	
	# Initialize MQ message receiver
	gobject.idle_add(handle_mq_message)

	try:
		eca_execute("start")
		mainloop.run()
	finally:
		mainloop.quit()
		print "Stopping Ecasound"
		eca_execute("stop")
		eca_execute("cs-disconnect")

if __name__ == "__main__":
	parse_args()
	setup()
	main()
	
