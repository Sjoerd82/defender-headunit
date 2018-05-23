#!/usr/bin/python

#
# GPIO output
# Venema, S.R.G.
# 2018-05-23
#
# Description of the daemon goes here.. 
# 

import sys						# path
import os						# 
from time import sleep

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *
from hu_msg import MqPubSubFwdController
from hu_gpio import GpioController

# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "Description, shown when using the help (-h) switch"
BANNER = "Startup banner"
LOG_TAG = 'TMPTAG'
LOGGER_NAME = 'template'
SUBSCRIPTIONS = ['/path/']

# global variables
logger = None
args = None
messaging = None
gpio = None

# configuration
cfg_main = None		# main
cfg_daemon = None	# daemon
cfg_zmq = None		# Zero MQ
cfg_gpio = None		# GPIO setup

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# ********************************************************************************
# Load configuration
#
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

#********************************************************************************
# Parse command line arguments
#
def parse_args():

	global args
	import argparse
	parser = default_parser(DESCRIPTION,BANNER)
	# additional command line arguments mat be added here
	args = parser.parse_args()

def setup():

	#
	# Logging
	#  Output will be logged to the syslog, if -b specified, otherwise output will be printed to console
	#
	global logger
	log_address = None
	if args.b: log_address='/dev/log') 	# output to syslog
	logger = log_getlogger(LOGGER_NAME,args.loglevel,LOG_TAG,log_address)
		
	#
	# Configuration
	#
	global cfg_main
	global cfg_zmq
	global cfg_daemon

	# main
	cfg_main = load_cfg_main(LOGGER_NAME)
	if cfg_main is None:
		printer("Main configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
	
	# zeromq
	cfg_zmq = load_cfg_zmq(cfg_main,args.port_publisher,args.port_subscriber)
	if cfg_zmq is None:
		printer("Error loading Zero MQ configuration.", level=LL_CRITICAL)
		exit(1)
			
	# daemon
	cfg_daemon = load_cfg_daemon(cfg_main,os.path.basename(__file__))
	if cfg_daemon is None:
		printer("Daemon configuration could not be loaded.", level=LL_CRITICAL)
		exit(1)
		
	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',config['port_publisher'],config['port_subscriber'])
	
	printer("ZeroMQ: Creating Publisher: {0}".format(config['port_publisher']))
	messaging.create_publisher()

	#
	# GPIO
	#
	gpio = GpioController(cfg_gpio)
	

	printer('Initialized [OK]')
		
def main():		

	while True:
		sleep(0.1)


if __name__ == "__main__":
	parse_args()
	setup()
	try:
		main()
	finally:
		GPIO.cleanup()
	