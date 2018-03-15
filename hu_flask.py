#!/usr/bin/python

from flask import Flask
from flask import render_template
from flask import url_for
from flask import jsonify

app = Flask(__name__)

#
# Zero MQ
#
import zmq
#from zmq.utils import jsonapi
from time import sleep
import json

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
	 , "href:":"#" }
	,{ "title":"Preferences"
	 , "id":"prefs"
	 , "href:":"#" }
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

def publish_message(path,command="SET"):
	try:
		msg = "{0} {1}".format(path,command)
		
		print("Sending message : {0}".format(msg))
		publisher.send(msg)
	except Exception as e:
		print("error {0}".format(e))

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
	nav_curr_ix = 1
	return render_template('dash_base.html', title=page_title, nav_items=nav_items, nav_curr_ix=nav_curr_ix, nav_sources=nav_sources)

@app.route('/config', methods=['GET'])
@app.route('/config/locations', methods=['GET'])
def cfg_locs():
	global nav_items
	global nav_sources
	global nav_pills
	page_title = "System Settings"
	return render_template('dash_config.html', title=page_title, nav_items=nav_items, nav_pills=nav_pills, nav_sources=nav_sources)

@app.route('/config/save', methods=['POST'])
def cfg_save():
	page_title = "Save!"
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

@app.route('/hu/api/v1.0/source', methods=['GET'])
def get_source():
	# Retrieve list of sources
	publish_message("/source","GET")
	msg = receive_message("/data/source")
	#return msg
	return render_template('sources.html', sources=msg)
	#sources = [{ "code":"smb" }, { "code":"media" }]
	#return jsonify({'sources': sources})


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
	publish_message("/player/next","SET")
	return "OK"
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

# In python "__name__" will be
# "__main__" whenever the script
# file itself is called instead
# of being used as a library
if __name__ == '__main__':
	
	# TODO! get port number from configuration
	#url = "tcp://127.0.0.1:5556"
	#try:
	#	zmq_sck.bind(url)
	#	time.sleep(1)
	#except:
	#	exit(0) # TODO ... IT CANNOT RECOVER .. SOMEHOW!

	print "ZMQ Version {0}". format(zmq.pyzmq_version())
	
	port_client = "5559"
	zmq_ctx = zmq.Context()
	publisher = zmq_ctx.socket(zmq.PUB)
	publisher.connect("tcp://localhost:{0}".format(port_client))
	#zmq_sck_req = zmq_ctx.socket(zmq.REQ)

	subscriber = zmq_ctx.socket(zmq.SUB)
	port_server = "5560" #TODO: get port from config
	subscriber.connect ("tcp://localhost:{0}".format(port_server)) # connect to server


	# The default port it will run on here is 5000
	app.run(host='0.0.0.0', debug=False, use_reloader=False)
	
