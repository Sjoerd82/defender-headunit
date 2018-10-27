#!/usr/bin/python

#
# Flask Web Server
# Venema, S.R.G.
# 2018-04-26
#
# Flask is lightweight HTTP server.
#
# We implement a number of pages and an API.
# Pages are implemented in nav_items[]
# 
# 

from flask import Flask
from flask import render_template
from flask import request
from flask import url_for
from flask import jsonify
#from flask_restful import Resource, Api

app = Flask(__name__)
#api = Api(app)

import sys
from time import sleep
import json

#sys.path.append('../modules')
sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *


# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "Flask HTTP server"
LOG_TAG = 'FLASK'
LOGGER_NAME = 'flask'
API_VERSION = '/hu/api/v1.0'
SUBSCRIPTIONS = ['/source/','/player/']
RETURN_PATH = '/bladiebla/'

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_PORT_WWW = 8289
DEFAULT_PASSWORD = None
DEFAULT_LOG_LEVEL = LL_INFO

logger = None
args = None
configfile_found = None
configuration = None

# ********************************************************************************
# Output wrapper
#
def printer( message, level=LL_INFO, continuation=False, tag=LOG_TAG ):
	logger.log(level, message, extra={'tag': tag})

# ********************************************************************************
# Load configuration
#
def load_configuration():

	# utils # todo, present with logger
	configuration = configuration_load(LOGGER_NAME,args.config)
	
	if not configuration or not 'flask' in configuration:
		printer('Error: Configuration not loaded or missing Flask, using defaults:')
		printer('HTTP port: {0}'.format(DEFAULT_PORT_WWW))
		printer('Default Password: {0}'.format(DEFAULT_PASSWORD))
		configfile_found = False
		configuration = { "flask": { "port_www": DEFAULT_PORT_WWW, "password":DEFAULT_PASSWORD } }
	else:
		if not 'port_www' in configuration['flask']:
			configuration['flask']['port_www'] = DEFAULT_PORT_WWW
			printer('Port missing in configuration, using default HTTP port: {0}'.format(DEFAULT_PORT_WWW))
		
		if not 'password'  in configuration['flask']:
			configuration['flask']['password'] = DEFAULT_PASSWORD
			printer('Password missing in configuration, using default password: {0}'.format(DEFAULT_PORT_WWW))
			
		configfile_found = True
	
	return configuration
	
#********************************************************************************
# Navigation
#

nav_items = [{
	   "title":"Home"
	 , "feather":"home"
	 , "href":"/"
	}
	,{ "title":"Equalizer"
	 , "feather":"sliders"
	 , "href":"#"
	}
	,{ "title":"Plugins"
	 , "feather":"shopping-bag"
	 , "href":"#"
	}
	,{ "title":"WiFi"
	 , "feather":"wifi"
	 , "href":"#"
	}
	,{ "title":"Bluetooth"
	 , "feather":"bluetooth"
	 , "href":"#"
	}
	,{ "title":"System"
	 , "feather":"settings"
	 , "href":"/config"
	}
	,{ "title":"Logs"
	 , "feather":"file-text"
	 , "href":"#"
	}
	,{ "title":"API"
	 , "feather":"share-2"
	 , "href":"#"
	}
	,{ "title":"Power Off"
	 , "feather":"power"
	 , "href":"poweroff"
	}]

nav_sources = [
	 { "title":"FM Radio"
	 , "feather":"radio"
	 , "href":"#"
	}
	,{ "title":"Local Music"
	 , "feather":"hard-drive"
	 , "href":"#"
	}
	,{ "title":"Internet Radio"
	 , "feather":"bookmark"
	 , "href":"#"
	}
	,{ "title":"SoundCloud"
	 , "feather":"cloud"
	 , "href":"#"
	}
	,{ "title":"Network Shares"
	 , "feather":"server"
	 , "href":"#"
	}]
	
nav_pills = [
	 { "title":"Locations"
	 , "id":"locations"
	 , "href:":"config_locations" }
	,{ "title":"Preferences"
	 , "id":"prefs"
	 , "href:":"config_preferences" }
	,{ "title":"Volume"
	 , "id":"volume"
	 , "href:":"#" }
	,{ "title":"Updates"
	 , "id":"updates"
	 , "href:":"#" }
	,{ "title":"MPD"
	 , "id":"mpd"
	 , "href:":"#" }
	,{ "title":"SMB"
	 , "id":"smb"
	 , "href:":"#" }
	,{ "title":"ZeroMQ"
	 , "id":"zmq"
	 , "href:":"#" }
	,{ "title":"Web"
	 , "id":"web"
	 , "href:":"#" }
	,{ "title":"System"
	 , "id":"system"
	 , "href:":"#" }
	,{ "title":"Logging"
	 , "id":"logging"
	 , "href:":"#" } ]

	 
def receive_message(path):
	subscriber.setsockopt(zmq.SUBSCRIBE, path)
	messagedata = subscriber.recv()
	data = messagedata[len(path)+1:]
	message = json.loads(data)
	return message
		
#
# Routes (pages)
#
@app.route('/')
def home():
	global nav_items
	global nav_sources
	page_title = "Landing page"
	nav_ix_main = 1

#********************************************************************************
# Parse command line arguments and environment variables
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


def main():

	#
	# Load configuration
	#
	configuration = load_configuration()
	
	# set port
	if 'flask' in configuration and 'port' in configuration['flask']:
		flask_port = configuration['flask']['port_www']
	else:
		flask_port = DEFAULT_PORT_WWW
	
	# start server
	try:
		app.run(host='0.0.0.0', port=flask_port, debug=False, use_reloader=False)
	except:
		func = request.environ.get('werkzeug.server.shutdown')
		if func is None:
			raise RuntimeError('Not running with the Werkzeug Server')
		func()
	
if __name__ == '__main__':
	
	parse_args()
	setup()
	main()

	
