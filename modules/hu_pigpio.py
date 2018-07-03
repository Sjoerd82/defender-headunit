import pigpio

class GpioWrapper(object):
	"""
	Wrapper for agnostic use of either RPi.GPIO or pigpio.
	BCM pin mode
	"""
	HIGH	 = pigpio.HIGH
	LOW		 = pigpio.LOW
	FALLING	 = pigpio.FALLING
	RISING	 = pigpio.RISING
	PUD_UP   = pigpio.PUD_UP
	PUD_DOWN = pigpio.PUD_DOWN
	
	def __init__(self):
		self.GPIO = pigpio.pi()
	
	def setup(self, pin, in_out, pull_up_down=None):
		self.GPIO.set_mode(pin, in_out)
		self.GPIO.set_pull_up_down(pin, pull_up_down)
		
	def input(self, pin):
		return self.GPIO.read(pin)
		
	def add_event_detect(self, pin, trigger, callback=None):
		return self.GPIO.callback(pin, trigger, callback)
	
	def setwarnings(self,on_off):
		return self.GPIO.exceptions = on_off
		
	def cleanup(self):
		return self.GPIO.stop()
