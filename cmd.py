#!/usr/bin/python

# cmd.py, the swiss army knife for the headunit 
#

# See: def parse_args() for usage

# TODO:
# commands specific to daemons, microservices or plugins should not be hardcoded here.
# currently these are:
# - status udisks
# - ecasound chain setup
# - merge config-tool in here

import os
import json
import sys
from time import sleep

sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController
from hu_commands import Commands

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "Headunit CLI"
LOG_TAG = None
LOGGER_NAME = "None"

DESCRIPTION = "Send a MQ command"
DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560
RETURN_PATH = '/cmdpy/'

args = None
args1 = None
messaging = None

cfg_main = None		# main
cfg_zmq = None		# Zero MQ

commandX = Commands()	#TODO: rename

mq_cmd = None
mq_path = None
mq_args = None
mq_rpath = None
	
# ********************************************************************************
# Load configuration
#
def load_cfg_main():
	"""
	LOAD MAIN CONFIGURATION
	Returns a dictionary containing the configuration (json.load)
	"""
	config = configuration_load(LOGGER_NAME,args1.config)
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
				
# ********************************************************************************
def print_dict(obj, nested_level=0):
	spacing = '   '
	key_line = 20
	if type(obj) == dict:
		print '{0}{{'.format((nested_level) * spacing)
		for k, v in obj.items():
			uitlijnen = 20 - (nested_level*2) - len(k) - nested_level
			uitlijn = ' ' * uitlijnen
			if hasattr(v, '__iter__'):
				print '{0}{1}:'.format((nested_level + 1) * spacing, k)
				print_dict(v, nested_level + 1)
			else:
				print '{0}{1}{2}: "{3}"'.format((nested_level + 1) * spacing, k, uitlijn, v)
		print '{0}}}'.format(nested_level * spacing)
	elif type(obj) == list:
		print '{0}['.format((nested_level) * spacing)
		for v in obj:
			if hasattr(v, '__iter__'):
				print_dict(v, nested_level + 1)
			else:
				print '{0}"{1}"'.format((nested_level + 1) * spacing, v)
		print '{0}]'.format((nested_level) * spacing)
	else:
		print '{0}{1}'.format(nested_level * spacing, obj)
		
def parse_args():

	def msg(name=None):
		return '''Headunit Command Interpreter
	   %(prog)s -h
	   %(prog)s [options] [help] <command> [args]
	   %(prog)s [options] mq <-p path> <-c mq-command> [-a] [-r]
	'''

	def epi(name=None):
		epilog = "List of commands:\n"
		epilog += list_of_commands_descr()
		epilog += '\nRun "{0} help <command>" explains how to use the command\n'.format(os.path.basename(__file__))
		return epilog

	def list_of_commands_descr():
		cmd_list = ""
		for cmd in commandX.function_mq_map:
			cmd_list += " {0:20} {1}\n".format(cmd['name'],cmd['description'])
		return cmd_list

	import argparse
	global args1
	global args
	DEFAULT_LOG_LEVEL = LL_INFO
	DEFAULT_CONFIG_FILE = '/etc/configuration.json'

	# cmd.py -h										Show available commands and switches
	# cmd.py [options] [help] <command> [args]		Execute command, with optional parmeter
	# cmd.py [options] <mq> <-p> <-c> [-a] [-r] 	Execute specified path and command, with optional parameters and return path
	
	parser = argparse.ArgumentParser(description=None, usage=msg(), epilog=epi(), formatter_class=argparse.RawDescriptionHelpFormatter) #, add_help=False)
	
	# options:
	parser.add_argument('-v', action='store_true', help='Verbose')
	#parser.add_argument('--debug', action='store_true', help='Debug on')
	parser.add_argument('--loglevel', action='store', default=DEFAULT_LOG_LEVEL, type=int, choices=[LL_DEBUG, LL_INFO, LL_WARNING, LL_CRITICAL], help="log level DEBUG=10 INFO=20", metavar=LL_INFO)
	parser.add_argument('--config','-c', action='store', help='Configuration file', default=DEFAULT_CONFIG_FILE)
	parser.add_argument('--port_pub',  action='store')
	parser.add_argument('--port_sub', action='store')
	parser.add_argument('--port_publisher', action='store')
	parser.add_argument('--port_subscriber', action='store')
	
	p2 = argparse.ArgumentParser( parents = [ parser ], add_help=False )
	subparsers = p2.add_subparsers()
	
	# status
	parser_status = subparsers.add_parser('status')
	parser_status.add_argument('status_of_what', action='store', nargs='*')
	parser_status.set_defaults(which='status')

	# status
	parser_status = subparsers.add_parser('config')
	parser_status.add_argument('status_of_what', action='store', nargs='*')
	parser_status.set_defaults(which='config')
	
	# command help
	parser_help = subparsers.add_parser('help')
	parser_help.add_argument('command', action='store', nargs='*')
	parser_help.set_defaults(which='help')

	# MQ
	parser_mq = subparsers.add_parser('mq')
	parser_mq.add_argument('-p', action='store', nargs='?', const='None')	# required, but not marking here to avoid argparse feedback
	parser_mq.add_argument('-c', action='store', nargs='?', const='None')	# required, but not marking here to avoid argparse feedback
	parser_mq.add_argument('-a', action='store')
	parser_mq.add_argument('-r', action='store_true')
	#parser_mq.add_argument('-j','--json', action='store_true')
	parser_mq.set_defaults(which='mq')

	# commands
	for command in commandX.function_mq_map:
		parser_cmd = subparsers.add_parser(command['name'])
		parser_cmd.add_argument('command_args', action='store', nargs='*')
		parser_cmd.set_defaults(which=command['name'])
	
	args1, unknown_args = parser.parse_known_args()
	
	if not unknown_args:
		program = os.path.basename(__file__)
		print "Headunit Command Interpreter"
		print "{0} -h".format(program)
		print "{0} [options] status [daemons|udisks]".format(program)
		print "{0} [options] config <section>".format(program)
		print "{0} [options] [help] <command> [args]".format(program)
		print "{0} [options] mq <-p path> <-c mq-command> [-a] [-r]".format(program)
		print ""
		print "Useful examples:"
		print '"{0} -h"         List of commands'.format(program)
		print '"{0} status all" System status overview'.format(program)
		print '"{0} config"     Display configuration'.format(program)
		exit(0)

	args = p2.parse_args()
	

def setup():
	
	global logger
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)
	logger = log_create_console_loghandler(logger, args1.loglevel, LOG_TAG) 	# output to console

	#
	# Configuration
	#
	global cfg_main
	#global cfg_zmq	#only used here(?)

	cfg_main = load_cfg_main()
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)

	# zeromq
	if not args1.port_publisher and not args1.port_subscriber:
		cfg_zmq = load_cfg_zmq()
	else:
		if args1.port_publisher and args1.port_subscriber:
			pass
		else:
			load_cfg_zmq()
	
		# Pub/Sub port override
		if args1.port_publisher:
			configuration['zeromq']['port_publisher'] = args1.port_publisher
		if args1.port_subscriber:
			configuration['zeromq']['port_subscriber'] = args1.port_subscriber

	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
		
	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Subscriber: {0}".format(DEFAULT_PORT_SUB))
	messaging.create_subscriber()

	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()
	sleep(1)	#very much needed, TODO: add to messaging module

	
def main():

	global mq_cmd
	global mq_path
	global mq_args
	global mq_rpath

	if args.which == 'status':
	
		if not args.status_of_what:
			print "Valid options for status are:"
			print " status daemons    Display daemon status"
			print " status mpd        Display mpd status"
			print " status eca        Display ecasound status"
			print " status udisks     Display removable drives"
			print " status sources    Display source details"	#TODO
			print " status all        All of the above"
			exit(0)

		if args.status_of_what[0] == 'all' or args.status_of_what[0] == 'daemons':
			if 'daemons' not in cfg_main:
				return
			else:
				print "Daemon status:"
				print "{0:19} {1:15} PID   Status".format("Service","init.d")
				print "------------------- --------------- ----- ------------"
				for daemon in cfg_main['daemons']:
					dmn_status = "Unknown"
					dmn_pid = ""
					if 'pid_file' in daemon:
						pid_file = os.path.join(cfg_main['directories']['pid'],daemon['pid_file'])
						if os.path.exists(pid_file):
							with open(pid_file,'r') as f_pid:
								dmn_pid = int(f_pid.readline().strip())
								try:
									dmn_status = colorize("Running",'light_green_2')
									os.kill(dmn_pid,0)
								except:
									dmn_status = colorize("Not running",'light_red')
									
					print "{0:19} {1:15} {2:<5} {3}".format(daemon['name'],daemon['init.d'],dmn_pid,dmn_status)
								
		if args.status_of_what[0] == 'web' or args.status_of_what[0] == 'www' or args.status_of_what[0] == 'flask':
			print "Webserver: "
			print "Outputs"
			
		if args.status_of_what[0] == 'mpd':	#args.status_of_what[0] == 'all' or #BROKEN
			print "MPD status:"
			print "Outputs"
			
		if args.status_of_what[0] == 'eca':	#args.status_of_what[0] == 'all' or #BROKEN
			print "Ecasound status:"
			print "Chainsetup: ?"
			print 'Run "ecamonitor" for more details'

		if args.status_of_what[0] == 'all' or args.status_of_what[0] == 'udisks':
			print "UDisks status:"
			print "{0:10} {1:20} {2:11} {3:30}".format("Device","UUID","Label","Mountpoint")
			print "{0:-<10} {1:-<20} {2:-<11} {3:-<30}".format("-","-","-","-")
			ret = messaging.publish('/udisks/devices','GET',wait_for_reply=True)
			if ret == False or ret is None:
				print "[FAIL]"
			else:
				if type(ret) == dict:
					#if 'retval' in ret: print "Return code: {0}".format(ret['retval'])
					if 'payload' in ret:
						#print "Return data:"
						#print_dict(ret['payload'])
						if not ret['payload']:
							print "No removable devices registered with udisks."
						else:
							for device in ret['payload']:
								#print "{0:10} {1:20} {2:11} {3:30}".format(ret['payload']['device'],ret['payload']['UUID'],ret['payload']['Label'],ret['payload']['Mountpoint'])
								print "{0:10} {1:20} {2:11} {3:30}".format(device['device'],device['uuid'],device['label'],device['mountpoint'])
						
				elif type(ret) == str:
					print "weird.. a string?!"
					print ret

		if args.status_of_what[0] == 'all' or args.status_of_what[0] == 'source' or args.status_of_what[0] == 'sources':
			print "Sources:"
			
			ret = messaging.publish('/source/primary','GET',wait_for_reply=True,timeout=1000)
			if ret == False or ret is None:
				print "[FAIL]"
			else:
				print ret
				
		exit(0)

	if args.which == 'config':
		
		if not args.status_of_what:
			print "Displays configuration."
			print " Usage: show-config <section> [subsection]"
			print ""
			print "Config file has the following sections:"
			print type(cfg_main)
			for section in cfg_main:
				print "   {0}".format(section)
			exit(0)
		else:
			if args.status_of_what[0] in cfg_main:
				if len(args.status_of_what) == 1:
					print cfg_main[args.status_of_what[0]]
				else:
					print "subsections not implemented yet"
					print cfg_main[args.status_of_what[0]]
			else:
				print "Section not found: {0}".format(args.status_of_what[0])
				print "Config file has the following sections:"
				print type(cfg_main)
				for section in cfg_main:
					print "   {0}".format(section)
				exit(0)
			
		exit(0)

		
	# Handle: help
	if args.which == 'help':
		if not args.command:
			print "Available commands:"
			print list_of_commands_descr()
			print 'Run "{0} help <command>" for more details'.format(os.path.basename(__file__))
			exit(1)
		elif args.command[0] in commandX.command_list:
			ix = commandX.command_list.index(args.command[0])
			print "{0}".format(commandX.function_mq_map[ix]['description'])
			param_string = ""
			if 'params' in commandX.function_mq_map[ix]:
				param_help = ""
				for param in commandX.function_mq_map[ix]['params']:
					if param['required']:
						param_string += "<"+param['name']+"> "
					else:
						param_string += "["+param['name']+"] "
					param_name = param['name']
					if 'help' in param:
						param_help += " {0:12}{1}\n".format(param_name,param['help'])
						param_name = ""
					if 'choices' in param:
						param_help += " {0:12}{1}\n".format(param_name,param['choices'])
						param_name = ""
					if 'default' in param:
						param_help += " {0:12}Default: {1}\n".format(param_name,param['default'])
						param_name = ""
			print "Syntax:\n {0} {1}".format(args.command[0],param_string)
			if not param_help == "":
				print "Parameters:"
				print "{0}".format(param_help)
			exit(0)
		else:
			print "Unknown command: {0}".format(args.command[0])
			print 'Run "{0} help" for a list of commands'.format(os.path.basename(__file__))
			exit(1)
		
	# MQ command
	if args.which == 'mq':
	
		if not args.p:
			print "error: argument -p is required"
		elif args.p == 'None':
			print "error: argument -p syntax: -p path"
	
		if not args.c:
			print "error: argument -c is required"
		elif args.c == 'None':
			print "error: argument -c syntax: -c command; example: GET, PUT, DATA"
		
		mq_path = args.p
		mq_cmd = args.c
		print "DEBUG --  DOING MQ! {0} {1} {2}".format(mq_path,mq_cmd,mq_args)
		ret = messaging.publish(mq_path,mq_cmd)
		#ret = messaging.publish('/udisks/devices','GET',[])
		print ret
		
		#TODO
		mq_cmd = None
		mq_path = None
		mq_args = None
		mq_rpath = None
		mq_param = None
		exit(0)
	
	# Pre-defined command
	if args.which in commandX.command_list:
		ix = commandX.command_list.index(args.which)

		mq_cmd = commandX.function_mq_map[ix]['command']
		mq_path = commandX.function_mq_map[ix]['path']
		if 'params_override' in commandX.function_mq_map[ix]:
			mq_args = commandX.function_mq_map[ix]['params_override']
		else:
		
			""" JSON
			params = {}
			for pix, command_arg in enumerate(args.command_args):
				key = commandX.function_mq_map[ix]['params'][pix]['name']
				params[key] = command_arg
			
			mq_args = json.dumps(params)
			"""
			
			""" PLAIN """
			mq_args = ",".join(args.command_args)
			
		#if mq_cmd == 'GET':
		#mq_rpath = RETURN_PATH
		if 'wait_for_reply' in commandX.function_mq_map[ix] and commandX.function_mq_map[ix]['wait_for_reply'] == False:
			mq_rpath = None
		else:
			mq_rpath = RETURN_PATH
			
		if mq_args == "{}":
			mq_args = None
	
	# debug
	#print "excuting command! {0} {1} with params {2}".format(mq_cmd,mq_path,mq_args)

	# ******************************************************************************************************************
	
	
	# todo: check, is it ok to include an empty mq_args?
	if mq_rpath is not None:
		ret = messaging.publish(mq_path,mq_cmd,mq_args,wait_for_reply=True,timeout=6000,response_path=RETURN_PATH)
	else:
		ret = messaging.publish(mq_path,mq_cmd,mq_args,wait_for_reply=False)
		
	if ret == True:
		print "Send: [OK]"
	elif ret == False or ret is None:
		print "Send: [FAIL]"
	else:
		if type(ret) == dict:
			if 'retval' in ret: print "Return code: {0}".format(ret['retval'])
			if 'payload' in ret:
				print "Return data:"
				print_dict(ret['payload'])
		elif type(ret) == list:
			print_dict(ret)
		elif type(ret) == str:
			print ret
		else:
			print type(ret)
			print ret
					
	"""
	# FOR DEBUGGING PURPOSES
	elif args.command == 'events-udisks-add':
		cmd = 'DATA'
		path = '/events/udisks/added'
		params = '{"device":"/dev/sda1", "mountpoint":"","uuid":"f9dc11d6-01","label":""}'
	"""
	
	#ret = messaging.publish('/source/primary','GET', None, True, 5000, RETURN_PATH)
	#print ret
	exit(0)
	
if __name__ == '__main__':
	parse_args()
	setup()
	main()

