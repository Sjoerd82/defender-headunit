from RPi import GPIO

class GpioWrapper(object):
	"""
	Wrapper for agnostic use of either RPi.GPIO or pigpio.
	BCM pin mode
	"""
	IN		 = GPIO.IN
	OUT		 = GPIO.OUT
	HIGH	 = GPIO.HIGH
	LOW		 = GPIO.LOW
	FALLING	 = GPIO.FALLING
	RISING	 = GPIO.RISING
	PUD_UP   = GPIO.PUD_UP
	PUD_DOWN = GPIO.PUD_DOWN
	
	def __init__(self):
		GPIO.setmode(GPIO.BCM)
		self.softpwm = {}
	
	def setup(self, pin, in_out, pull_up_down=None, softpwm=False):
	
		# pwm pin
		if softpwm is True:
			ret = GPIO.setup(pin, in_out)
			frequency = 100	# 100Hz
			self.softpwm[pin] = GPIO.PWM(pin, frequency)
			return ret
		
		# regular pin
		if pull_up_down is None:
			return GPIO.setup(pin, in_out)
		elif pull_up_down is not None:
			return GPIO.setup(pin, in_out, pull_up_down)
		
	def input(self, pin):
		return GPIO.input(pin)
		
	def add_event_detect(self, pin, trigger, callback=None):
		return GPIO.add_event_detect(pin, trigger, callback)
	
	def setwarnings(self, on_off):
		return GPIO.setwarnings(on_off)
	
	def pwm_rgb(self, pin_r, pin_g, pin_b, rgbhex='#ffffff'):
		"""
		Non-blocking?
		"""
	
		def hex_to_rgb(value):
			"""Return (red, green, blue) for the color given as #rrggbb."""
			value = value.lstrip('#')
			lv = len(value)
			return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
			
		if pin_r in self.softpwm and pin_g in self.softpwm and pin_b in self.softpwm:
			# set duty cycle
			rgbhex = hex_to_rgb(rgb_value)
			self.softpwm[pin_r].start(rgbhex[0])
			self.softpwm[pin_g].start(rgbhex[1])
			self.softpwm[pin_b].start(rgbhex[2])
			
	def pwm_stop(self, pin):
		pass
			
	def cleanup(self):
		# do we need to stop any started PWM?
		return GPIO.cleanup()
