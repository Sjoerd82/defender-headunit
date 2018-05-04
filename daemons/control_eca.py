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

ECA_CHAIN_MASTER_AMP = 'PRE'	# chain object that contains the master amp
ECA_CHAIN_MUTE = 'PRE'			# chain object to mute
ECA_CHAIN_EQ = None				# chain object that contains the equalizer

cfg_ecasound = None
eca_chain_op_master_amp = None
att_level = 20		# TODO, get from configuration
local_volume = 50	
eca_chain_selected = None

logger = None
args = None
messaging = None
eca = None

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# ********************************************************************************
# Load configuration
#
def load_zeromq_configuration():
	
	configuration = configuration_load(LOGGER_NAME,args.config)
	
	if not configuration or not 'zeromq' in configuration:
		printer('Error: Configuration not loaded or missing ZeroMQ, using defaults:')
		printer('Publisher port: {0}'.format(args.port_publisher))
		printer('Subscriber port: {0}'.format(args.port_subscriber))
		configuration = { "zeromq": { "port_publisher": DEFAULT_PORT_PUB, "port_subscriber":DEFAULT_PORT_SUB } }
		return configuration
		
	else:
		# Get portnumbers from either the config, or default value
		if not 'port_publisher' in configuration['zeromq']:
			configuration['zeromq']['port_publisher'] = DEFAULT_PORT_PUB
			
		if not 'port_subscriber' in configuration['zeromq']:
			configuration['zeromq']['port_subscriber'] = DEFAULT_PORT_SUB
			
	return configuration

def load_ecasound_configuration():
	""" Load ecasound configuration
		Returns:
			True: 	Success
			False:	Critical failure
	"""
	global cfg_ecasound
	global eca_chainsetup
	global eca_chain_master_amp
	global eca_chain_mute
	global eca_chain_eq
	global eca_amplify_max
	global eca_volume_increment
	
	# load ecasound
	if 'ecasound' not in configuration:
		printer("Ecasound section not found in configuration.",level=LL_CRITICAL)
		return False
	else:
		cfg_ecasound = configuration['ecasound']
	
	# load mandatory variables
	try:
		eca_chainsetup = configuration['ecasound']['chainsetup']
		eca_chain_master_amp = configuration['ecasound']['chain_master_amp']
	except KeyError:
		printer("Mandatory configuration items missing in ecasound section",level=LL_CRITICAL)
		return False
	
	# load other, less important, variables
	try:
		eca_chain_mute = configuration['ecasound']['chain_mute']
	except KeyError:
		eca_chain_mute = None
		printer("No muting chain specified, mute not available",level=LL_WARNING)

	try:
		eca_chain_eq = configuration['ecasound']['chain_eq']
	except KeyError:
		eca_chain_eq = None
		printer("No EQ chain specified, EQ not available",level=LL_WARNING)
		
	try:
		eca_amplify_max = configuration['ecasound']['amplify_max']
	except KeyError:
		eca_amplify_max = 100
		printer("No maximum amplification level specified, setting maximum amplification to 100%",level=LL_INFO)

	try:
		eca_amplify_max = configuration['ecasound']['volume_increment']
	except KeyError:
		eca_volume_increment = 5
		printer("No default volume increment specified, setting volume increment to 5%",level=LL_INFO)
		
	return True

# ********************************************************************************
# Ecasound
#

def eca_load_chainsetup_file(ecs_file):
	""" Load, Test and Connect chainsetup file
		Returns:
			True:	All OK
			False:	Chainsetup not loaded
	"""
	# load chainsetup from file, it will be automatically selected
	eca.command("cs-load {0}".format(ecs_file))
	
	#
	# test the loaded chainsetup
	#
	eca_chain_selected = eca.command("cs-selected")
	if eca_chain_selected[:5] is not 'ERROR':
		printer("Loaded chainsetup: {0}".format(eca_chain_selected))
	else:
		printer("Could not select chainsetup!",level=LL_CRITICAL)
		#eca.command("stop")
		#eca.command("cs-disconnect")
		#exit(1)
		return False
	
	chains = eca.command("c-list")
	printer("Chainsetup contains chains and operators:")
	for chain in chains:
		printer("Chain: {0}".format(chain))
		eca.command("c-select {0}".format(chain))
		chain_ops = eca.command("cop-list")
		for chain_op in chain_ops:
			printer(" - {0}".format(chain_op))
	
	# TEST: Amp chain (Volume Control)
	if cfg_ecasound['chain_master_amp'] not in chains:
		printer("Master amp chain ({0}) not found!".format(cfg_ecasound['chain_master_amp']))
	else:
		eca.command("c-select {0}".format(cfg_ecasound['chain_master_amp']))
		eca_chain_selected = eca.command("c-selected")
		if cfg_ecasound['chain_master_amp'] in eca_chain_selected:

			chain_ops = eca.command("cop-list")
			if 'amp-%' not in chain_ops:		
				printer("Master amp chain: {0} [OK]".format(cfg_ecasound['chain_master_amp']))
			else:
				printer("Operator 'Amplify' not found!",level=LL_CRITICAL)
				#eca.command("stop")
				#eca.command("cs-disconnect")
				#exit(1)
				return False
				
		else:
			printer("Could not select master amp chain!",level=LL_CRITICAL)
			#eca.command("stop")
			#eca.command("cs-disconnect")
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
	eca.command("cs-connect")
	printer("Current amp level: {0}%".format(eca_get_effect_amplification()))
	return True
	
def eca_get_effect_amplification():
	eca.command("c-select '{0}'".format(ECA_CHAIN_MASTER_AMP))
	eca.command("cop-select '{0}'".format(eca_chain_op_master_amp))
	eca.command("copp-select '0'")
	eca.command("cop-get")
	ea_value = 50
	return ea_value
	
def eca_set_effect_amplification(level):
	#eca_chain_selected
	eca.command("c-select '{0}'".format(ECA_CHAIN_MASTER_AMP))
	eca.command("cop-select '{0}'".format(eca_chain_op_master_amp))
	eca.command("copp-select '0'")
	eca.command("cop-set '{0}'".format(level))
	return level
	
def eca_mute(state):
	""" state can be: 'on', 'off' or 'toggle' """
	eca.command("c-select '{0}'".format(ECA_CHAIN_MUTE))
	eca.command("c-mute '{0}'".format(state))
	
def handle_path_volume(path,cmd,params):

	base_path = 'volume'
	# remove base path
	del path[0]

	def get_master(params):
		level = eca_get_effect_amplification()
		print level

	def put_master(params):
	
		# arg can be: <str:up|down|+n|-n|att>
	
		level = 20
		eca_set_effect_amplification(level)

	def put_increase(params):
		"""	Increase Volume
			Arguments:		<str:up|down|+n|-n|att>
			Return data:	Nothing
		"""
		local_volume += 5
		eca.command('copp-set {0}'.format(local_volume))
		if not args.b:
			printer("Amp level: {0}%".format(local_volume))
		
	def put_decrease(params):
		local_volume -= 5
		eca.command('copp-set {0}'.format(local_volume))
		if not args.b:
			printer("Amp level: {0}%".format(local_volume))
		
	def put_att(params):
		# arg can be: <str:on|off|toggle>,[int:Volume, in %]

		eca_set_effect_amplification(att_level)

	def put_mute(params):
		#arg can be <str:on|off|toggle>
		eca_mute(params)
	
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

# ********************************************************************************
# On Idle
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
	# Load configuration
	#
	global configuration
	if not args.port_publisher and not args.port_subscriber:
		configuration = load_zeromq_configuration()
	else:
		if args.port_publisher and args.port_subscriber:
			pass
		else:
			configuration = load_zeromq_configuration()
	
		# Pub/Sub port override
		if args.port_publisher:
			configuration['zeromq']['port_publisher'] = args.port_publisher
		if args.port_subscriber:
			configuration['zeromq']['port_subscriber'] = args.port_subscriber
	
	retval = load_ecasound_configuration()
	if not retval:
		exit(1)

	#
	# ECA
	#	
	global eca
	os.environ['ECASOUND'] = '/usr/bin/ecasound --server'
	eca = ECA_CONTROL_INTERFACE(2)	# # debug level (0, 1, 2, ...)
	
	cs_location = configuration['system_configuration']['ecasound_ecs']['location']
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
		
	printer('Initialized [OK]')

def main():

	global bus
	
	# Initialize the mainloop
	DBusGMainLoop(set_as_default=True)
	mainloop = gobject.MainLoop()
	
	# Initialize MQ message receiver
	gobject.idle_add(handle_mq_message)

	try:
		eca.command("start")
		mainloop.run()
	finally:
		mainloop.quit()
		print "Stopping Ecasound"
		eca.command("stop")
		eca.command("cs-disconnect")

if __name__ == "__main__":
	parse_args()
	setup()
	main()
	
