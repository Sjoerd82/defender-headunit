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
	return render_template('index.html', pages=pages)
	
@app.route('/api')
def list_routes():
	import urllib
	output = []
	for rule in app.url_map.iter_rules():

		options = {}
		for arg in rule.arguments:
			options[arg] = "[{0}]".format(arg)

		methods = ','.join(rule.methods)
		url = url_for(rule.endpoint, **options)
		line = urllib.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, url))
		output.append(line)
	
	for line in sorted(output):
		print line

@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
	return render_template('hello.html', name=name)
	
	