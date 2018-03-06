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
import time

zmq_ctx = zmq.Context()
zmq_sck = zmq_ctx.socket(zmq.PUB)

# TODO! get port number from configuration
url = "tcp://127.0.0.1:5555"

print zmq.pyzmq_version()

def publish_message1(message):
	try:
		msg = "{0} |{1}".format("test",message)
		print("Sending message : {0}".format(msg))
		zmq_sck.send(msg)
	except Exception as e:
		print("error {0}".format(e))

		
def publish_message(message):
	try:
		url = "tcp://127.0.0.1:5555"
		zmq_sck.bind(url)
		#msg = "{0} |{1}".format("test",message)
		#msg = "test"
		#print("Sending message : {0}".format(msg))
		topic = "test"
		message = "hello world"
		zmq_sck.send("%d %d" % (topic, message))
		#zmq_sck.send(msg)
	except Exception as e:
		print("error {0}".format(e))
	finally:
		# You wanna unbind the publisher to keep
		# receiving the published messages
		# Otherwise you would get a - Adress already in use - error
		zmq_sck.unbind(url)

#
# Routes
#

@app.route('/')
def hello_world():
	pages = [
	  {"title":"State/Control","id":"state"}
	 ,{"title":"Playlist","id":"playlist"}
	 ,{"title":"Config","id":"config"}
	 ,{"title":"API","id":"api"}
	 ,{"title":"Logs","id":"log"}
	]
	print pages
	return render_template('index.html', pages=pages)
	
@app.route('/api')
def list_routes():
	import urllib
	links = []
	for rule in app.url_map.iter_rules():

		#if len(rule.defaults) >= len(rule.arguments):
		#	url = url_for(rule.endpoint, **(rule.defaults or {}))
		#	links.append((url, rule.endpoint))
			
		options = {}
		for arg in rule.arguments:
			options[arg] = "[{0}]".format(arg)
		
		methods = ','.join(rule.methods)
		url = url_for(rule.endpoint, **options)
		#line = urllib.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, url))
		links.append((url, rule.endpoint))
		#links.append(line)
	
	return render_template("api.html", links=links)
	#for line in sorted(links):
	#	print line

	
"""

GET /source								Retrieve list of sources
GET /source/<id>						Retrieve source <id>
GET /source/available					Retrieve list of available sources
GET /source/<id>/subsource				Retrieve list of subsources
GET /source/<id>/subsource/<id>			Retrieve subsource <id> of source <id>
GET /source/<id>/subsource/available	Retrieve list of available subsourcesof source <id>
POST /source/<id>						Set active source to <id> 
POST /source/<id>/subsource/<id>		Set active subsource to <id>
POST /source/next						Set active (sub)source to the next available
POST /source/prev						Set active (sub)source to the prev available

"""

@app.route('/hu/api/v1.0/source', methods=['GET'])
def get_source():
	#get sources from MQ
	#stub:
	sources = [{ "code":"smb" }, { "code":"media" }]
	return jsonify({'sources': sources})

"""
@app.route('/hu/api/v1.0/source/<int:source_id>', methods=['GET'])
@app.route('/hu/api/v1.0/source/available', methods=['GET'])
@app.route('/hu/api/v1.0/source/<int:source_id>/subsource', methods=['GET'])
@app.route('/hu/api/v1.0/source/<int:source_id>/subsource/<int:subsource_id>', methods=['GET'])
@app.route('/hu/api/v1.0/source/<int:source_id>/subsource/available', methods=['GET'])

#Set active source to <id> 
@app.route('/hu/api/v1.0/source/<int:source_id>', methods=['POST'])

#Set active subsource to <id>
@app.route('/hu/api/v1.0/source/<int:source_id>/subsource/<int:subsource_id>', methods=['POST'])

#Set active (sub)source to the next available
@app.route('/hu/api/v1.0/source/next', methods=['POST'])

#Set active (sub)source to the prev available
@app.route('/hu/api/v1.0/source/prev', methods=['POST'])
	
"""


@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
	return render_template('hello.html', name=name)
	

# This is an endpoint which prints the
# number we want to print in response
# and also publishes a message containing the number
@app.route("/print/<int:number>", methods = ['GET'])
def printNumber(number):
	response = 'Number %d' % number
	#publish_message('number%d' % number)
	publish_message(number)
	return response

# In python "__name__" will be
# "__main__" whenever the script
# file itself is called instead
# of being used as a library
if __name__ == '__main__':
	# The default port it will run on here is 5000
	app.run(host='0.0.0.0', debug=True)
	
