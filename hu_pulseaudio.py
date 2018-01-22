import subprocess
from subprocess import call
from subprocess import Popen, PIPE

from hu_utils import *

class pa_volume_handler():

	VOL_INCR = "5%"

	def __init__(self, sink):
		self.pa_sink = sink

	def vol_set_pct(self, volume):
		vol_pct = str(volume) + "%"
		call(["pactl", "set-sink-volume", self.pa_sink, vol_pct])
		
	def vol_up(self):
		vol_chg = "+" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.pa_sink, vol_chg])
		
	def vol_down(self):
		vol_chg = "-" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.pa_sink, vol_chg])

	def vol_get(self):
		#pipe = Popen("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'")
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		vol = subprocess.check_output("/root/pa_volume.sh")
		return int(vol.splitlines()[0])


# ********************************************************************************
# PulseAudio
# Use 0-100 for volume.
#
def pa_sfx_load():
	printer('Loading sound effects', tag="PULSE")
	call(["pactl","upload-sample",sDirRoot+"/sfx/startup.wav", "startup"])
	call(["pactl","upload-sample",sDirRoot+"/sfx/beep_60.wav", "beep_60"])
	call(["pactl","upload-sample",sDirRoot+"/sfx/beep_70.wav", "beep_70"])
	call(["pactl","upload-sample",sDirRoot+"/sfx/beep_60_70.wav", "beep_60_70"])
	call(["pactl","upload-sample",sDirRoot+"/sfx/beep_60_x2.wav", "beep_60_x2"])
	call(["pactl","upload-sample",sDirRoot+"/sfx/error.wav", "error"])
	call(["pactl","upload-sample",sDirRoot+"/sfx/bt.wav", "bt"])


#def pa_sfx( sfx ):
# in hu_utils...

def pa_set_volume( volume ):
	printer('Setting volume', tag="PULSE")
	pavol = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')
	pavol.vol_set_pct(volume)

def pa_get_volume():
	printer('Getting volume', tag="PULSE")
	pavol = pa_volume_handler('alsa_output.platform-soc_sound.analog-stereo')
	return pavol.vol_get()

