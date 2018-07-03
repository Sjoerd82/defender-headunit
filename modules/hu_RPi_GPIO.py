from RPi import GPIO

class GpioWrapper(object):
	"""
	Wrapper for agnostic use of either RPi.GPIO or pigpio.
	BCM pin mode
	"""
	HIGH	 = GPIO.HIGH
	LOW		 = GPIO.LOW
	FALLING	 = GPIO.FALLING
	RISING	 = GPIO.RISING
	PUD_UP   = GPIO.PUD_UP
	PUD_DOWN = GPIO.PUD_DOWN
	
	def __init__(self):
		GPIO.setmode(GPIO.BCM)
	
	def setup(self, pin, in_out, pull_up_down=None):
		return GPIO.setup(pin, in_out, pull_up_dow)
		
	def input(self, pin):
		return GPIO.input(pin)
		
	def add_event_detect(self, pin, trigger, callback=None):
		return GPIO.add_event_detect(pin, trigger, callback)
	
	def setwarnings(self, on_off):
		return GPIO.setwarnings(on_off)
	
	def cleanup(self):
		return GPIO.cleanup()
