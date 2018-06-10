#!/usr/bin/python

import sys
from time import sleep

sys.path.append('/mnt/PIHU_APP/defender-headunit'
from modules.hu_msg import MqPubSubFwdController

DEFAULT_PORT_PUB = 5559
DEFAULT_PORT_SUB = 5560

messaging = None

	
def main():

	print "Sends: /hello/world GET"

	#
	# ZMQ
	#
	global messaging
	messaging = MqPubSubFwdController('localhost',DEFAULT_PORT_PUB,DEFAULT_PORT_SUB)
	print("ZeroMQ: Creating Publisher: {0}".format(DEFAULT_PORT_PUB))
	messaging.create_publisher()
	sleep(1)
	ret = messaging.publish_command('/hello/world','GET')
	print ret

if __name__ == '__main__':
	main()
