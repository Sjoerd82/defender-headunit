# Headless Headunit
The "Hidden Headless Headunit"; Until a better name comes up..

Software for easy control of a headless "head unit".
Designed for "hidden" applications, such as classic- or custom cars, yachts, suitcase boomboxes or bookshelve audio.

Intended for Raspberry Pi embedded Linux, and build upon PulseAudio and MPD.

*Primary goal:* Intuitive and easy to control without display.

## Features

 + Supports (simple) display output (but this is completely optional)
 + Supports a wide range of music sources
 + Supports a wide range of input controls
 + Supports a wide range of music formats
 + Supports a wide range of music "sources" out of the box
 + Supports third-party plugins to support additional sources or input controls
 + Supports character displays
 PLANNED:
 - CAN-bus input and output

###  List of supported sources:
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

### List of supported input methods:
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
3. state.json

#### configuration.json
Centralized configuration file. Aims to be the only configuration file you'll ever need to change.
Default location: /mnt/PIHU_CONFIG (the FAT32 partition, so it's configurable by plugging the SD card into a PC)
Will see occasional writing.

#### settings.json, HU_SOURCE, HU_VOLUME
Operational settings which need to be persisted and restores over reboots. The files HU_SOURCE and HU_VOLUME are separate file for easy reading during boot.
Location: /mnt/PIHU_CONFIG
Read at boot. Write at shutdown. Optionally write every n seconds. ~to be refined...

#### state.json
Operational state. May be kept on a ramdrive (no need for persistance).
May be used to read from to quickly get state information. Will see a lot of R/W.
