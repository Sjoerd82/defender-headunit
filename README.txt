The "Hidden Headless Headunit" until a better name comes to mind..

Software for easy control of a headless head unit (car radio).
 
Designed to be intuitive and easy to control without display.
Designed for "hidden" applications, such as classic- or custom cars, yachts, suitcase boomboxes or bookshelve audio.
Designed to support a (simple) display, but this is completely optional.

 + Intended for Raspberry Pi embedded Linux, and largely build around MPD.
 + Supports a wide range of music sources.
 + Supports a wide range of input controls.
 + Supports a very wide range of music formats.
 + Supports a wide range of music sources out of the box.
 + Supports third-party plugins to support additional sources or input controls.
 PLANNED:
 + Supports character displays and CAN-bus output.

 List of supported sources:
 + FM radio (based on ... chipset)
 + Internet radio
 + Internal SD card
 + USB drive
 + Bluetooth
 + Windows network shares (SMB/CIFS)
 PLANNED:
 + Aux In
 + NFS (low prio)
 ? AirPlay (does this still exist?)

 List of supported input methods:
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

PLUGINS
-------
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


--old--
Program flow:

 - init()
    alsa_init()
    pa_init()
    mpc_init()
    bt_init()
    load_settings()
    source_check()

 - mainloop()
   Listens and acts on dbus signals:
     - cb_remote_btn_press()  com.arctura.remote, from dbus_remote.py
     - cb_mpd_event()         com.arctura.mpd, from dbus_mpd.py
     - cb_udisk_device_add()  org.freedesktop.UDisks
     - cb_udisk_device_rem()  org.freedesktop.UDisks


Button presses:
 SOURCE
  -> source_stop()
     -> xxx_stop()
  -> source_next()
     -> save_settings()
  -> source_play()
     ..
 UPDATE
  -> locmus_update()
     -> mpc_update('PIHU_DATA')
     -> locmus_check

ToDo:

 * headunit.py:
 - include pid file
 - re-check internet connection
 - don't double check availability
 - add timer, to do:
   - delayed volume save
   - internet connection check
 - implement a better udisks drive removal, currently we don't know which drive was removed exactly
 - Bluetooth:
   - Retrieve sBtPlayer (now hardcoded)
   - Clean-Up BluePlayer class
   - Clean-Up BlueAgent class
 - Play sfx at independent volume  
 - Play sfx continuously for (potentially) long operations: mpd update, ...?
 - SMB:
   - Implement smb_check()
 - Alsa:
   Not sure what's the exact status of Alsa now that we've implemented PA...
   - implement alsa_unmute()
   - alsa_get_volume(): untested with actual alsa mixer
 BUGS:
 - MPD:
   - Update, esp. during init() takes *WAY* too long [~10min?----], and, unless it's the first boot, is not crucial.
 IMPROVEMENTS:
 - url_check()
   - support https
   - support incomplete url's, eg. missing http://
 - mpc_get_PlaylistDirs() runs in the background, but we never check .if_alive()..
 - Use more colors in console
 - Move "QuickPlay" mechanism to init.d for "real-early-play"(tm)
 FUTURE:
 - FM, Line-In
 - Samba:
   - Implement properly (now hardcoded)
 - Internet radio:
   - Support playlists (currently only URI's)
   - and fetch up-to-date playlist for a radio station
   - Move/mark dead stations
   - APP: Search and Add stations

 * S70headunit:
 - check pid file
 - implement stop()

 * Linux:
 - Make PulseAudio logs readable in /var/log/messages (switch locale?)
 - PulseAudio watchdog
 - Make it work without PhatDAC
 
 * Considerations
 - Use NetworkManager + DBus to act on network changes