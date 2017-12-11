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
 - Alsa:
   Not sure what's the exact status of Alsa now that we've implemented PA...
   - implement alsa_unmute()
   - alsa_get_volume(): untested with actual alsa mixer
 - Play sfx at independent volume  
 - Play sfx continuously for (potentially) long operations: mpd update, ...?
 - SMB:
   - Implement smb_check()
 BUGS:
 - MPD:
   - Update, esp. during init() takes *WAY* too long [~10min?----], and, unless it's the first boot, is not crucial.
 IMPROVEMENTS:
 - url_check()
   - support https
   - support incomplete url's, eg. missing http://
 - Run mpc_get_PlaylistDirs() in the background for better performance
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