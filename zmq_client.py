# client.py

import sys
import zmq

context = zmq.Context()

subscriber = context.socket (zmq.SUB)
#subscriber.connect ("tcp://172.16.8.192:5555")
subscriber.connect ("tcp://127.0.0.1:5555")
subscriber.setsockopt (zmq.SUBSCRIBE,b"beer")

while True:
	message = subscriber.recv()
	print(message)