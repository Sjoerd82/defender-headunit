#!/usr/bin/python

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
from hu_msg import MqPubSubFwdController


# *******************************************************************************
# Global variables and constants
#
DESCRIPTION = "Flask HTTP server"
LOG_TAG = 'FLASK'
LOGGER_NAME = 'flask'
API_VERSION = '/hu/api/v1.0'
SUBSCRIPTIONS = ['/source/','/player/']

DEFAULT_CONFIG_FILE = '/etc/configuration.json'
DEFAULT_PORT_WWW = 8289
DEFAULT_PASSWORD = None
DEFAULT_LOG_LEVEL = LL_INFO
DEFAULT_PORT_SUB = 5560
DEFAULT_PORT_PUB = 5559

logger = None
args = None
messaging = None
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
		
"""		
def publish_message(message):
	try:
		url = "tcp://127.0.0.1:5556"
		zmq_sck.bind(url)
		time.sleep(1)	# IMPORTANT !!
		msg = "{0} |{1}".format("test",message)
		#msg = "test"
		#print("Sending message : {0}".format(msg))
		topic = "test"
		message = "hello world"
		zmq_sck.send("%s %s" % (topic, message))
		#zmq_sck.send(msg)
	except Exception as e:
		print("error {0}".format(e))
	finally:
		# You wanna unbind the publisher to keep
		# receiving the published messages
		# Otherwise you would get a - Adress already in use - error
		zmq_sck.unbind(url)
"""

#
# Routes
#
@app.route('/')
def home():
	global nav_items
	global nav_sources
	page_title = "Landing page"
	nav_ix_main = 1
	return render_template('dash_base.html', title=page_title, nav_items=nav_items, nav_ix_main=nav_ix_main, nav_sources=nav_sources)

@app.route('/config', methods=['GET'])
@app.route('/config_locations', methods=['GET'])
def cfg_locs():
	global nav_items
	global nav_sources
	global nav_pills
	page_title = "System Settings"
	nav_ix_main = 1
	nav_ix_sub = 1
	return render_template('dash_config.html', title=page_title, nav_items=nav_items, nav_pills=nav_pills, nav_sources=nav_sources, nav_ix_main=nav_ix_main, nav_ix_sub=nav_ix_sub)

@app.route('/config_preferences', methods=['GET'])
def cfg_prefs():
	global nav_items
	global nav_sources
	global nav_pills
	global configuration
	
	page_title = "System Settings"
	nav_ix_main = 1
	nav_ix_sub = 2
	#startup_opts = ["Resume","FM","USB"]
	startup_opts = [
	 { "title":"Resume same source","source":"resume" }
	,{ "title":"FM Radio","source":"fm" }
	,{ "title":"Local media","source":"locmus" }
	,{ "title":"USB","source":"media" }]
	#TODO: SubSource!
	#TODO: Check if key's are present..
	config = {
	   "startup_source":configuration['preferences']['start_source']
	 , "autoplay_media":""
	 , "autoplay_aux":""
	 , "remember_rnd":""
	 , "min_elapsed_sec":configuration['preferences']['threshold_elapsed_sec']
	 , "min_track_sec":configuration['preferences']['threshold_total_sec']
	}
	
	if 'media_autoplay' in configuration['preferences'] and configuration['preferences']['media_autoplay']:
		config['autoplay_media'] = 'checked'
		
	if 'autoplay_aux' in configuration['preferences'] and configuration['preferences']['autoplay_aux']:
		config['autoplay_aux'] = 'checked'

	if 'retain_random' in configuration['preferences'] and configuration['preferences']['retain_random']:
		config['retain_random'] = 'checked'
		
	return render_template('dash_config.html', title=page_title, nav_items=nav_items, nav_pills=nav_pills, nav_sources=nav_sources, nav_ix_main=nav_ix_main, nav_ix_sub=nav_ix_sub, config=config, startup_opts=startup_opts)

@app.route('/config_save', methods=['POST'])
def cfg_save():
	page_title = "Save!"
	if request.method == 'POST':
		section = request.form['config_section']
		print section
		if section == 'prefs':
			print request.form['cfg_prf_startup_source']

			if 'cfg_prf_autoplay_media' in request.form:
				print request.form['cfg_prf_autoplay_media']
				configuration['preferences']['media_autoplay'] = request.form['cfg_prf_autoplay_media']

			if 'cfg_prf_autoplay_aux' in request.form:
				print request.form['cfg_prf_autoplay_aux']
				configuration['preferences']['autoplay_aux'] = request.form['cfg_prf_autoplay_aux']
			
			if 'cfg_prf_retain_random' in request.form:
				print request.form['cfg_prf_retain_random']
				configuration['preferences']['retain_random'] = request.form['cfg_prf_retain_random']
			
			if 'cfg_prf_min_elapsed_sec' in request.form:
				print request.form['cfg_prf_min_elapsed_sec']
				configuration['preferences']['threshold_elapsed_sec'] = request.form['cfg_prf_min_elapsed_sec']
				
			if 'cfg_prf_min_track_sec' in request.form:
				print request.form['cfg_prf_min_track_sec']
				configuration['preferences']['threshold_total_sec'] = request.form['cfg_prf_min_track_sec']
				
			with open(args.config,'w') as outfile:
				json.dump(configuration, outfile)
	
	message = "Your changes have been saved."
	return render_template('dash_cfg_saved.html', title=page_title, nav_pills=nav_pills, message=message)

	
@app.route('/poweroff', methods=['GET'])
def poweroff():
	page_title = "Power Off"
	nav_curr_ix = 9
	# Shows two buttons:
	# [ Reboot ] [ Power Off ]
	"""
	buttons = [ {
	   btn_reboot = {
		 "Caption":"Reboot"
		,"href":"#" }
	}
	,{ btn_halt = {
		 "Caption":"Power Off"
		,"href":"#" }
	]
	"""
	return render_template('dash_poweroff.html', title=page_title, nav_items=nav_items, nav_curr_ix=nav_curr_ix, nav_sources=nav_sources) #, buttons=buttons)


@app.route('/reboot', methods=['GET'])
def reboot():

	#publish_message('/system/reboot', 'SET')
	#publish_message('/player/next', 'SET')
	global messaging
	messaging.publish_request('/system/reboot', 'SET', None)
	messaging.publish_request('/player/next', 'SET', None)
	return "SEND x2"
	
#app.route('/api')
"""

GET  /source                            Retrieve list of sources
GET  /source/<id>                       Retrieve source <id>
GET  /source/available                  Retrieve list of available sources
GET  /source/<id>/subsource             Retrieve list of subsources
GET  /source/<id>/subsource/<id>        Retrieve subsource <id> of source <id>
GET  /source/<id>/subsource/available   Retrieve list of available subsourcesof source <id>
POST /source/<id>                       Set active source to <id> 
POST /source/<id>/subsource/<id>        Set active subsource to <id>
POST /source/next                       Set active (sub)source to the next available
POST /source/prev                       Set active (sub)source to the prev available
GET  /player                            Retrieve current player state (pause/play/stopped, random)
GET  /player/track                      Retrieve current playing track (incl. ID3)
GET  /player/folders                    Retrieve list of folders
POST /player/pause/...                  Set pause on|off|toggle
POST /player/state/...                  Set state play|pause|stop, toggle random
POST /player/random/...                 Set random on|off|toggle|special modes
POST /player/randommode/<mode>          Set random mode: folder|artist|genre|all
POST /player/track/<track>              <playlist id>
GET  /player/next                       Next track
GET  /player/prev                       Prev track
POST /player/seekfwd                    Seek fwd
POST /player/seekrev                    Seek rev
POST /player/seek/<incr_sec>            Seek increment (seconds)
GET  /playlist                          Retrieve current playlist
GET  /playlist/<..>                     Retrieve saved playist #todo
GET  /volume                            Retrieve current volume
GET  /equalizer/<band>                  Retrieve EQ
POST /volume/<vol>                      Set volume. Vol= up|down|+n|-n|att (incr,decr is in %)
POST /volume/att/<level>                Set ATT volume. Level in %.
POST /volume/increment/<incr>           Set increments for Volume up/down
POST /equalizer/<band>/<level>          Set EQ level for band
GET  /config                            Retrieve current configuration
GET  /config/<path:config>              Retrieve a ci group or ci item
POST /config/<path:config>/<value>      Set ci item
GET  /plugin/<path:config>              Get from a plugin
GET  /plugin/api                        Get api from plugin
POST /plugin/<path:config>              Set for a plugin
"""

#@app.route('/hu/api/v1.0/source', methods=['GET'])
@app.route(API_VERSION+'/source', methods=['GET'])
def get_source():
	print "DEBUG!! get_source()"
	# Retrieve list of sources
	#messaging.send_command('/source/primary','GET')
	#messaging.subscribe('/data/source')
	#sources = messaging.receive_poll('/data/source',5000)
	
	#retmsg = messaging.send_to_server('/source/primary GET')
	#retmsg = messaging.client_request('/source/primary','GET', None, 5000)
	#retmsg = messaging.publish_command('/source/primary','GET')
	#sleep(1)
	retmsg = messaging.publish_command('/source/primary','GET', None, True, 5000, '/bladiebla/')
	print retmsg
	return retmsg
	
	if not sources:
		return "Nothing returned"
	else:
		return sources
		#return render_template('sources.html', sources=sources)


@app.route('/hu/api/v1.0/source/<int:source_id>', methods=['GET'])
def get_source_id(source_id):
	"""Another. It does nothing."""
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

@app.route('/hu/api/v1.0/source/available', methods=['GET'])
def get_source_available():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

@app.route('/hu/api/v1.0/source/<int:source_id>/subsource', methods=['GET'])
def get_source_id_subsource(source_id):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

@app.route('/hu/api/v1.0/source/<int:source_id>/subsource/<int:subsource_id>', methods=['GET'])
def get_source_id_subsource_id(source_id,subsource_id):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

@app.route('/hu/api/v1.0/source/<int:source_id>/subsource/available', methods=['GET'])
def get_source_id_subsource_available(source_id):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set active source to <id> 
@app.route('/hu/api/v1.0/source/<int:source_id>', methods=['POST'])
def post_source_id(source_id):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set active subsource to <id>
@app.route('/hu/api/v1.0/source/<int:source_id>/subsource/<int:subsource_id>', methods=['POST'])
def post_source_id_subsource_id(source_id,subsource_id):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set active (sub)source to the next available
@app.route('/hu/api/v1.0/source/next', methods=['GET'])
def post_source_next():
	messaging.send_command("/player/next","SET")
	retmsg = messaging.send_to_server("Hoi Oliebol!")
	return retmsg
	#stub = [{'a':'a'},{'b':'b'}]
	#return jsonify({'stub':stub})

#Set active (sub)source to the prev available
@app.route('/hu/api/v1.0/source/prev', methods=['POST'])
def post_source_prev():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve current player state (pause/play/stopped, random)
@app.route('/hu/api/v1.0/player', methods=['GET'])
def get_player():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve current playing track (incl. ID3)
@app.route('/hu/api/v1.0/player/track', methods=['GET'])
def get_player_track():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve list of folders
@app.route('/hu/api/v1.0/player/folders', methods=['GET'])
def get_player_folders():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set pause on|off|toggle
@app.route('/hu/api/v1.0/player/pause/<mode>', methods=['POST'])
def post_player_pause_mode(mode):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set state play|pause|stop
@app.route('/hu/api/v1.0/player/state/<mode>', methods=['POST'])
def post_player_state_mode(mode):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set random on|off|toggle|special modes
@app.route('/hu/api/v1.0/player/random/<mode>', methods=['POST'])
def post_player_random_mode(mode):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set random mode: folder|artist|genre|all
@app.route('/hu/api/v1.0/player/randommode/<mode>', methods=['POST'])
def post_player_randommode_mode(mode):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#<playlist id>
@app.route('/hu/api/v1.0/player/track/<track>', methods=['POST'])
def post_player_track_track(track):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Next track
@app.route('/hu/api/v1.0/player/next', methods=['GET'])
def get_player_next():
	publish_message("/player/next","SET")	
	#stub = [{'a':'a'},{'b':'b'}]
	#return jsonify({'stub':stub})
	return "OK"

#Prev track
@app.route('/hu/api/v1.0/player/prev', methods=['POST'])
def post_player_prev():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Seek fwd
@app.route('/hu/api/v1.0/player/seekfwd', methods=['POST'])
def post_player_seekfwd():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Seek rev
@app.route('/hu/api/v1.0/player/seekrev', methods=['POST'])
def post_player_seekrev():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Seek increment (seconds)
@app.route('/hu/api/v1.0/player/seek/<incr_sec>', methods=['POST'])
def post_player_seek_incrsec(incr_sec):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve current playlist
@app.route('/hu/api/v1.0/playlist', methods=['GET'])
def get_playlist():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve saved playlists #todo
@app.route('/hu/api/v1.0/playlists', methods=['GET'])
def get_playlists():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve saved playist #todo
@app.route('/hu/api/v1.0/playlist/<id>', methods=['GET'])
def get_playlist_id(id):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve current volume
@app.route('/hu/api/v1.0/volume', methods=['GET'])
def get_volume():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve EQ
@app.route('/hu/api/v1.0/equalizer/<band>', methods=['GET'])
def get_equalizer_band(band):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set volume. Vol= up|down|+n|-n|att (incr,decr is in %)
@app.route('/hu/api/v1.0/volume/<vol>', methods=['POST'])
def post_volume_vol(vol):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set ATT volume. Level in %.
@app.route('/hu/api/v1.0/volume/att/<level>', methods=['POST'])
def post_volume_att_level(level):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set increments for Volume up/down
@app.route('/hu/api/v1.0/volume/increment/<incr>', methods=['POST'])
def post_volume_increment_incr(incr):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set EQ level for band
@app.route('/hu/api/v1.0/equalizer/<band>/<level>', methods=['POST'])
def post_equalizer_band_level(band,level):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve current configuration
@app.route('/hu/api/v1.0/config', methods=['GET'])
def get_config():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Retrieve a ci group or ci item
@app.route('/hu/api/v1.0/config/<path:config>', methods=['GET'])
def get_config_path(path):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set ci item
@app.route('/hu/api/v1.0/config/<path:config>/<value>', methods=['POST'])
def post_config_path_value(path,value):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Get plugin api
@app.route('/hu/api/v1.0/plugin/api', methods=['GET'])
def get_plugin_api():
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Get something from a plugin
@app.route('/hu/api/v1.0/plugin/<path:config>', methods=['GET'])
def get_plugin_path(path):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})

#Set something for a plugin
@app.route('/hu/api/v1.0/plugin/<path:config>', methods=['POST'])
def post_plugin_path(path):
	stub = [{'a':'a'},{'b':'b'}]
	return jsonify({'stub':stub})


# This is an endpoint which prints the
# number we want to print in response
# and also publishes a message containing the number
#@app.route("/print/<int:number>", methods = ['GET'])
#def printNumber(number):
#	response = 'Number %d' % number
#	#publish_message('number%d' % number)
#	publish_message1(number)
#	return response

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


	#
	# ZMQ
	#
	global messaging
	printer("ZeroMQ: Initializing")
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	
	printer("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()

	printer("ZeroMQ: Creating Subscriber: {0}".format(DEFAULT_PORT_SUB))
	messaging.create_subscriber(SUBSCRIPTIONS)


def main():

	#
	# Load configuration
	#
	configuration = load_configuration()
	
	# The default port it will run on here is 5000
	app.run(host='0.0.0.0', debug=False, use_reloader=False)

	
if __name__ == '__main__':
	
	parse_args()
	setup()
	main()

	
