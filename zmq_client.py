# client.py

import sys
import zmq

context = zmq.Context()

subscriber = context.socket (zmq.SUB)
subscriber.connect ("tcp://localhost:5556")
subscriber.setsockopt (zmq.SUBSCRIBE, '')

#print zmq.pyzmq_version()

while True:
	message = subscriber.recv()
	print(message)
