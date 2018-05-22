# Headless Headunit
The "Hidden Headless Headunit"; Until a better name comes up..

Software for easy control of a headless "head unit".
Designed for "hidden" applications, such as classic- or custom cars, yachts, suitcase boomboxes or bookshelve audio.

Intended for Raspberry Pi embedded Linux.

*Primary goals:*
- Intuitive and easy to control without display
- Ultrashort time-to-play (fast boot, start/resume playback)
- Audiophile quality
- Modular

## Short description

This application is essentially a set of Python micro services, communicating with eachother using ZeroMQ, build on top of a customized Buildroot image for the Raspberry Pi Zero.

## Features

"Out of the Box" features:

 + Supports (simple) display output (but this is completely optional)
 + Supports a wide range of music sources
 + Supports a wide range of input controls
 + Supports a wide range of music formats
 + Supports a wide range of music "sources" out of the box
 + Supports third-party plugins to support additional sources or input controls
 + Supports character displays
 + Active crossover filters

PLANNED:
 - CAN-bus input and output

####  List of supported sources:
 + FM radio (based on ... chipset)
 + Internet radio
 + Internal SD card
 + USB drive
 + Bluetooth
 + Windows network shares (SMB/CIFS)
 
 PLANNED:
 - Aux In
 - NFS (low prio)
 ? AirPlay (does this still exist?)

#### List of supported input methods:
 + Resistor network style remote controls, Sony RM-X2S pre-configured.
 + Android/iPhone: MPD client
 
 PLANNED:
 - Keyboard (via USB,BT)
 - Infrared, LIRC (via GPIO(TSSOP),USB,MIC)
 - RF remote (USB)
 - REST HTTP/API
 - CAN-bus controls
 - GPIO button
 - Pot meter controls for Volume, Bass, Treble and/or balance (via ADC) (not recommended, unless it's the only control*)
 - Incremental Encoder for Volume, Bass, Treble and/or balance (via GPIO)
 - Incremental Encoder w/button(s) (BMW iDrive style) (via GPIO)
 - Android/iPhone (full control, beyond only MPD)

## Modular

Core micro services:
 - Source Controller
 - ZeroMQ "forwarder" (simple service that binds the ZMQ pub and sub ports)
 
Other important micro services are:
 - Volume Control (pulse or jack)
 - Remote Control(s)
 - RESTful Web Server
 - QuickPlay (script only?) /Plugin Controller (?)
 - UDisks
 - Display output

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

### RESTful Web Server

A Python Flask+Bootstrap http daemon. This webserver provides an easy way to configure the system (if it has WiFi or ethernet), it also provides an API for third party apps. TODO: Android Retrofit app.

### Quick Play

Python script to resume a previous audio source as quickly as possible.

### UDisks

Daemon that listens to the UDisks D-Bus daemon and forwards drive (dis)connect events over MQ.

### Display

Output (using plugins?????) Daemon.


### PLUGINS

There are two types of supported plugins:

 1) Auto-executed executionables (currently only tested with Python scripts) which are connected to the main program via the DBus.
    TODO: somehow register the callback procedures in the main loop..
    Located in: /plugins
    List of plugins:
    * control/dbus_ads1x15.py
    * control/dbus_keyboard.py
    * output/dbus_2606a.py

 2) Python scripts that are more closely coupled with the main program via the import
    Located in:
    * /sources	Source plugins
    * ?		?

### FILES

1. configuration.json
2. settings.json, HU_SOURCE, HU_VOLUME
3. < source >/settings.json
4. < source >/< key >.p
5. state.json (deprecate?)

#### configuration.json
Centralized configuration file. Aims to be the only configuration file you'll ever need to change.
Default location: /mnt/PIHU_CONFIG (the FAT32 partition, so it's configurable by plugging the SD card into a PC)
Will see occasional writing.

#### settings.json, HU_SOURCE
Operational settings which need to be persisted and restores over reboots. The files HU_SOURCE and HU_VOLUME are separate file for easy reading during boot.
Location: /mnt/PIHU_CONFIG
Read at boot. Write at shutdown. Optionally write every n seconds. ~to be refined...

#### <source>/settings.json


Operational settings per source

#### <source>/<key>.p
Resume playback information (pickled)

#### state.json
Operational state. May be kept on a ramdrive (no need for persistance).
May be used to read from to quickly get state information. Will see a lot of R/W.


### Global Flag files

Set in /root
`DEBUG_MODE` Sets default log level to debug (can still be overridden on the command line)
`WLAN-WPA`	Sets the network to client (WPA) mode
`WLAN-AP`	Set the network to AP (access point) mode


# Tools

## config-tool

The config-tool takes care of various configuration files on the system.

## mq_recv

Monitors MQ traffic. Prints all MQ messages to screen.

## mq_cmd

Send out a standardized command over MQ or a custom MQ message.
Currently still called cmd (todo).




# Hardware

Tailored for the Raspberry Pi Zero

Hardware | Input* | Output | Tested
--- | --- | ---
Native GPIO (PWM) | None | 2x | No
Pimoroni PhatDAC | None | 2x | Yes
Behringer UCA202/UCA222 | 2x | 2x | No
CMedia CM106 | 2x | 8x | No


* Needed for external audio sources such as FM or AUX.
Without inputs you can still control these sources, but you won't be able to control the volume or do DSP.
To control AUX, you will need an stereo plugin jack with insert detection hooked up to the GPIO (or use a switch).


Reference Setup

01 					3v3 Power
03 BCM 2 (SDA)		i2c:
05 BCM 3 (SCL)		i2c: WS282x LED string, ADC
07 BCM 4 (GPCLK0)	.
09 Ground			-
11 BCM 17			.
13 BCM 27			.
15 BCM 22			.
17 3v3 Power		-
19 BCM 10 (MOSI)	SPI MOSI
21 BCM 9 (MISO)		SPI MISO
23 BCM 11 (SCLK)	SPI CLCK
25 Ground			SPI GND
27 BCM 0 (ID_SD)	Encoder2 DT
29 BCM 5			Encoder2 CLK
31 BCM 6			Encoder1 DT
33 BCM 13 (PWM1)	Encoder1 CLK
35 BCM 19 (MISO)	DAC (i2s)
37 BCM 26			Encoder1 SW
39 Ground			-

02 5v Power			
04 5v Power			
06 Ground			-
08 BCM 14 (TXD)		.
10 BCM 15 (RXD)		.
12 BCM 18 (PWM0)	.
14 Ground			-
16 BCM 23			.
18 BCM 24			DAC (i2s)
20 Ground			-
22 BCM 25			Buzzer
24 BCM 8 (CE0)		SPI chip-select 0
26 BCM 7 (CE1)		SPI chip-select 1
28 BCM 1 (ID_SC)	.
30 Ground			-
32 BCM 12 (PWM0)	.
34 Ground			-
36 BCM 16			.
38 BCM 20 (MOSI)	.
40 BCM 21 (SCLK)	DAC (i2s)

SPI: display, CAN
FM+RDS (i2c or spi?)

Free: 17

Remote Control Pwr
Remote Control Button 1 (on ADC)
Remote Control Button 2 (on ADC)
Buzzer
Led 1 (power button)
Power Button
Aux detection

Free: 13

IR receiver (1-3?)
Encoder for Control (evt. ook vol, bas, trb)

RGB led 1, R
RGB led 1, G
RGB led 1, B
RGB led 2, R
RGB led 2, G
RGB led 2, B
Battery LEDs

3x Encoder for Vol., Bass and Treble (=9 pins)