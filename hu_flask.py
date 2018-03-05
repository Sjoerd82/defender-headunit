from flask import Flask
from flask import render_template
app = Flask(__name__)

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
	output = []
	for rule in app.url_map.iter_rules():

		if len(rule.defaults) >= len(rule.arguments):
			url = url_for(rule.endpoint, **(rule.defaults or {}))
			links.append((url, rule.endpoint))
			
		#options = {}
		#for arg in rule.arguments:
		#	options[arg] = "[{0}]".format(arg)
		#
		#methods = ','.join(rule.methods)
		#url = url_for(rule.endpoint, **options)
		#line = urllib.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, url))
		#output.append(line)
	
	return render_template("api.html", links=links)
	#for line in sorted(output):
	#	print line

@app.route('/hu/api/v1.0/source', methods=['GET'])
def get_source():
	#get sources from MQ
	#stub:
	sources = [{ "code":"smb" }, { "code":"media" }]
	return jsonify({'sources': sources})
	
@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
	return render_template('hello.html', name=name)
	
	