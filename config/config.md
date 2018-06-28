#Configuration

configuration.json


##configuration.json

##GPIO configuration

##MPD Audio Input/Output
There are a number of ways to get your audio source to your output.

Pre Configured:

"Alsa: HiFiberry DAC 32-bit"
"Alsa: Behringer UCA202 16-bit"
MPD -> Alsa -> Hardware

"Alsa: Loopback 16-bit"
"Alsa: Loopback 32-bit"
MPD -> Alsa -> Ecasound ->

To make this work select an appropiate chainsetup in Ecasound.

"fifo"
MPD -> Fifo -> Ecasound? ->

"Pipe"
MPD -> Pipe -> Ecasound -> Alsa

"Jack"
MPD -> Jack -> ?