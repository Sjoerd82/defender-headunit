#
# Collection of functions used everywhere.
# Has no dependencies*
#

# myprint()
import logging

# Third party modules
from colored import fg, bg, attr

#log levels
LL_CRITICAL = 50
LL_ERROR = 40
LL_WARNING = 30
LL_INFO = 20
LL_DEBUG = 10
LL_NOTSET = 0

# Defines how to handle output
def myprint( message, level=LL_INFO, tag=""):
	logger = logging.getLogger('headunit')
	logger.log(level, message, extra={'tag': tag})

# Add ANSI markup to a string
def colorize ( string, foreground, background='black' ):
	colorized = fg(foreground) + bg(background) + string + attr('reset')
	return colorized

def pa_sfx( sfx ):

	#global sPaSfxSink
	#global bBeep
	sPaSfxSink = "alsa_output.platform-soc_sound.analog-stereo"
	bBeep = False
	
	if bBeep:
		beep()
	else:
		if sfx == 'startup':
			call(["pactl", "play-sample", "startup", sPaSfxSink])
		elif sfx == 'button_feedback':
			call(["pactl", "play-sample", "beep_60", sPaSfxSink])
		elif sfx == 'error':
			call(["pactl", "play-sample", "error", sPaSfxSink])
		elif sfx == 'mpd_update_db':
			call(["pactl", "play-sample", "beep_60_70", sPaSfxSink])
		elif sfx == 'bt':
			call(["pactl", "play-sample", "bt", sPaSfxSink])
		elif sfx == 'reset_shuffle':
			call(["pactl", "play-sample", "beep_60_x2", sPaSfxSink])