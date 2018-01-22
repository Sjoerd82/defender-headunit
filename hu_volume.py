
import subprocess
from subprocess import call
from subprocess import Popen, PIPE

class VolumeController():

	#Percentage to increase the volume with, if no increment given
	VOL_INCR = 5
	iVolume = 0
	iVolumeAtt = 30
	bAtt = False
	sSink = 'default'	# 'alsa_output.platform-soc_sound.analog-stereo'

	def __init__( self, sink=sSink ):
		print('[VOLUME] Initializing...')
		#iVolume = getFromPulse...	#todo...
		#pipe = Popen("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'")
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		#pipe = subprocess.check_output("pactl list sinks | grep '^[[:space:]]Volume:' | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'", shell=True)
		try:
			vol = subprocess.check_output("/root/pa_volume.sh")
			self.iVolume = int(vol.splitlines()[0])
		except:
			print('[VOLUME] ERROR running /root/pa_volume.sh')
		

	def get( self ):
		vol = subprocess.check_output("/root/pa_volume.sh")
		self.iVolume = int(vol.splitlines()[0])
		return self.iVolume
	
	def set( self, volpct, sink=sSink ):
		vol_pct = str(iVolume) + "%"
		call(["pactl", "set-sink-volume", self.pa_sink, vol_pct])

	#set Att volume
	def setAtt( self, volpct, sink=sSink ):
		self.iVolumeAtt = volpct

	#set or toggle Att state
	def att( self, state ):
		if state == 'toggle':
			if self.bAtt:
				self.bAtt = False
			else:
				self.bAtt = True
		elif state == 'on':
			self.bAtt = True
		elif state == 'off':
			self.bAtt = False
		
		if self.bAtt:
			self.set( iVolumeAtt )

		return bAtt

	def getAtt( self ):
		return iVolumeAtt
	
	def setIncr( self, increment ):
		self.increment = increment
	
	def getIncr( self ):
		return self.VOL_INCR
	
	def up( self, sink=sSink ):
		# always reset Att. state at manual vol. change
		bAtt = False
		# change volume
		vol_chg = "+" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.sSink, vol_chg])

	def down( self, sink=sSink ):
		# always reset Att. state at manual vol. change
		bAtt = False
		# change volume
		vol_chg = "-" + self.VOL_INCR
		call(["pactl", "set-sink-volume", self.sSink, vol_chg])
		
	def pulseGetSinks( self ):
		print('TODO')
	
#class Equalizer():
	#todo
	
"""
	
  sinks		GetSinks ()
		SetVolume ( sink, percentage )		sink = default|...
  volume*	GetVolume ( sink )
		SetVolumeAtt ( percentage )
  volume	GetVolumeAtt ()
		SetVolumeIncrement ( percentage )
  pct		GetVolumeIncrement ()
		VolumeIncr ()
		VolumeDecr ()
		SetAttState ( state )		state = on|off|toggle
  state		GetAttState ()
		SetEqualizer ( band, level )	band = ?, level = ?
  equalizer	GetEqualizer ( band )
"""