# client.py

import sys
import zmq

context = zmq.Context()

subscriber = context.socket (zmq.SUB)
subscriber.connect ("tcp://localhost:5555")
subscriber.setsockopt (zmq.SUBSCRIBE, "test")

while True:
	message = subscriber.recv()
	print(message)
