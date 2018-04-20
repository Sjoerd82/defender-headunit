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
LOG_TAG = 'ECASND'
LOGGER_NAME = 'ecasnd'

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560
SUBSCRIPTIONS = ['/volume/','/equalizer/']

PATH_VOLUME = '/volume'
PATH_VOLUME_EVENT = '/events/volume'

ECA_CHAIN_MASTER_AMP = 'PRE'	# chain object that contains the master amp
ECA_CHAIN_MUTE = 'PRE'			# chain object to mute
ECA_CHAIN_EQ = None				# chain object that contains the equalizer


eca_chain_op_master_amp = None
att_level = 20		# TODO, get from configuration
test_volume = 50

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

# ********************************************************************************
# Ecasound
def eca_get_indexes():
	""" Get indexes of chain operators
	"""
	global eca_chain_op_master_amp
	eca.command("c-select {0}".format(ECA_CHAIN_MASTER_AMP))		# select chain
	# list of chain operators
	eca.command("cop-list")
	# match ea/amplifier
	# todo
	#ix_ea = ?
	#eca_chain_op_master_amp = ?
	
def eca_get_effect_amplification():
	eca.command("c-select '{0}'".format(ECA_CHAIN_MASTER_AMP))
	eca.command("cop-select '{0}'".format(eca_chain_op_master_amp))
	eca.command("copp-select '0'")
	eca.command("cop-get")
	ea_value = 50
	return ea_value
	
def eca_set_effect_amplification(level):
	eca.command("c-select '{0}'".format(ECA_CHAIN_MASTER_AMP))
	eca.command("cop-select '{0}'".format(eca_chain_op_master_amp))
	eca.command("copp-select '0'")
	eca.command("cop-set '{0}'".format(level))

def eca_mute(state):
	""" state can be: 'on', 'off' or 'toggle' """
	eca.command("c-select '{0}'".format(ECA_CHAIN_MUTE))
	eca.command("c-mute '{0}'".format(state))
	
def handle_path_volume(path,cmd,args):

	base_path = 'volume'
	# remove base path
	del path[0]

	def get_master(args):
		level = eca_get_effect_amplification()
		print level

	def put_master(args):
	
		# arg can be: <str:up|down|+n|-n|att>
	
		level = 20
		eca_set_effect_amplification(level)

	def put_increase(args):
		test_volume += 5
		eca.command('copp-set {0}'.format(test_volume))
		print "increased"
		
	def put_decrease(args):
		test_volume -= 5
		eca.command('copp-set {0}'.format(test_volume))
		print "decreased"
		
	def put_att(args):
		# arg can be: <str:on|off|toggle>,[int:Volume, in %]

		eca_set_effect_amplification(att_level)

	def put_mute(args):
		#arg can be <str:on|off|toggle>
		eca_mute(arg)
	
	if path:
		function_to_call = cmd + '_' + '_'.join(path)
	else:
		# called without sub-paths
		function_to_call = cmd + '_' + base_path

	ret = None
	if function_to_call in locals():
		ret = locals()[function_to_call](args)
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret))
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
		printer('Executed {0} function {1} with result status: {2}'.format(base_path,function_to_call,ret))
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
		printer("Received message: {0}".format(rawmsg))	#TODO: debug
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

	import argparse
	global args

	parser = argparse.ArgumentParser(description=DESCRIPTION)
	parser.add_argument('--loglevel', action='store', default=DEFAULT_LOG_LEVEL, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('--config','-c', action='store', help='Configuration file', default=DEFAULT_CONFIG_FILE)
	parser.add_argument('-b', action='store_true', default=False)
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
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
	# ECA
	#
	global eca
	os.environ['ECASOUND'] = '/usr/bin/ecasound --server'
	eca = ECA_CONTROL_INTERFACE(2)	# # debug level (0, 1, 2, ...)
	
	eca.command("cs-load /mnt/PIHU_APP/defender-headunit/ecp/jack_alsa_xover_2ch_m.ecs")
	eca.command("cs-connect")
	eca.command("start")
	
	#eca_get_indexes()
	printer('Initialized [OK]')
	
	print "DEBUG"
	print "All chains:"
	print eca.command("c-select pre")
	print "Selected:"
	print eca.command("c-selected")

	print "DEBUG"
	print "Chain: 'default', all operators:"
	print eca.command("cop-list")

	print "Chain: Pre, Operator: 1 (-ea; amplifier), all parmeters:"
	print eca.command('cop-select Amplify')
	print eca.command('copp-list')
	print eca.command('copp-select 1') # amp-%
	print eca.command('copp-selected')
	print eca.command('copp-get')
	print eca.command('copp-set 10')
	print eca.command('copp-get')
	time.sleep(5)
	eca.command('copp-set {0}'.format(test_volume))
	print eca.command('copp-get')
	
	


def main():

	global bus
	
	# Initialize the mainloop
	DBusGMainLoop(set_as_default=True)
	mainloop = gobject.MainLoop()

	# Initialize MQ message receiver
	gobject.idle_add(handle_mq_message)

	try:
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
	
