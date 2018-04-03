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

### Source Controller

Selects audio source and controls playback.
Sources are YAPSY plugins (Python).

### Volume Controller

PulseAudio Volume Controller has been abandoned in favor of Jack.

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

### ENV
HU_CONFIG_FILE
HU_RUN_COUNT
