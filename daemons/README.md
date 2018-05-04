# Micro services

Micro services communicate over ZeroMQ.

Core micro services:

Service | Script | Description
--- | --- | ---
Source Controller | `hu_src_ctrl.py` | Selects audio source and controls playback.
ZeroMQ "forwarder" | `zmq_forwarder.py` | Simple service that `bind` the ZMQ pub and sub ports

Other (optional) micro services are:

Service | Script | Description
--- | --- | ---
Ecasound controller | `control_eca.py` | Sets volume and EQ levels of the Ecasound server
ADS1x15 controller | `control_ads1x15.py` | Input via the i2c ADS1x15 ADC (Sony RM-3X)
GPIO controller | `control_gpio.py` | Input via the GPIO, support for buttons and encoders
RESTful Web Server | `web/web_flask.py` | Web console for configuration and playback controls
MPD | `listen_mpd.py` | Listens for MPD events
UDisks | `listen_udisks.py` | Listens for D-bus messages related to removal or insert of USB drives
1601 display output | display_1601.py | Output to the 1601 i2c display

? MPD
? QuickPlay (script only?) /Plugin Controller (?)

Additional input, output or general purpose plugins are easily added.
All modules are loosely integrated, so you can easily customize to match your own particular installation.
Or, go with our reference installation based around MPD, Jack and Ecasound. This setup opens up a wealth of audiophile plugins and customizations.

### Source Controller

Selects audio source and controls playback.
Sources are YAPSY plugins (Python).

### Volume Controller

PulseAudio and Jack Volume Controllers have been abandoned in favor of Ecasound.

### Remote Controllers

Connects any type of input.
Remote Controls are (Python) daemons.

## GPIO controller
The GPIO controller enables use of switches and encoders. Configure the controls in the configuration:

Rotary encoder, device section:

Field | Description
--- | ---
`name` | ID
`type` | `rotenc`
`clk` | Pin 1 (BCM*)
`dt` | Pin 2 (BCM*)

Switch, device section:

Field | Description
--- | ---
`name` | ID
`type` | `sw`
`pin` | Pin number (BCM*)
`gpio_on` | Logic level for "on". Valid: `high`\`1` or `low`\`0`
`debounce` | OPTIONAL. Debounce time in ms 
`gpio_pullupdown` | OPTIONAL. `true | "down" | "up"`
`gpio_edgedetect` | OPTIONAL. `"rising" | "falling" | "both"`

Function section:

Field | Description
--- | ---
`name` | not used...
`function` | function ID*
`short_press` | List of (switch) device(s)
`long_press` | List of (switch) device(s)
`encoder` | Device ID of encoder
`mode` | Required mode for this function
`mode_toggle` | Toggles this mode on/off
`mode_select` | Loops through a list of modes
`mode_reset` | Remove mode afer this number of seconds

List of supported functions:


Example for three encoders and three switches.
In this example we have three encoders with build-in switch.
The encoders are used to control Bass, Treble and Volume.
The Bass and Treble switches are used to go to the prev/next track and the Volume switch selects next source ('short press').
A long press on the volume encoder would poweroff the system.
A long press on the either the Bass and Treble encoders would go to the prev/next folder.
Pressing the Bass and Treble switch simultaniously toggles random on/off.
Pressing the Bass, Treble and Volume switch simultaniously enters/leaves a "menu mode".
While in menu mode, the Bass and Treble encoders are used for scrolling the menu.
While in menu mode, the Bass and Treble switches serve to select items in the menu.
```
		{
			  "name": "Control: GPIO"
			, "init.d":"S72ctrlgpio"
			, "gpio_mode":"BCM"
			, "controls": [
				{ 	  "name": "encoder1"
					, "type": "rotenc"
					, "clk":13
					, "dt":6
					, "control":"volume"
				},
				{ 	  "name": "switch1"
					, "type": "mom"
					, "sw":5
					, "control_short":"source"
					, "control_long":"volume"
				}
			]
		}
```

### RESTful Web Server

A Python Flask+Bootstrap http daemon. This webserver provides an easy way to configure the system (if it has WiFi or ethernet), it also provides an API for third party apps. TODO: Android Retrofit app.

### Quick Play

Python script to resume a previous audio source as quickly as possible.

### UDisks

Daemon that listens to the UDisks D-Bus daemon and forwards drive (dis)connect events over MQ.

### Display

Output (using plugins?????) Daemon.

# Configuration

Micro Services are configured in the main `configuration.json` under section `services` (list).
There are two mandatory fields: `name` and `init.d`. Service settings that apply only to the service can be stored here (#todo, move settings for flask, etc. in here). More generic settings have their own separate section.

Example:
```
	"services": [
		{
			  "name":"ZMQ Forwarder"
			, "init.d":"S30zmqfwd"
		}
```
