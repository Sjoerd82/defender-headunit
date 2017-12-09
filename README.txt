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
 - implement url_check()
 - implement a better udisks drive removal, currently we don't know which drive was removed exactly
 - BlueTooth:
   - Retrieve sBtPlayer (now hardcoded)
   - Clean-Up BluePlayer class
   - Clean-Up BlueAgent class
 - Alsa:
   Not sure what's the exact status of Alsa now that we've implemented PA...
   - implement alsa_unmute()
   - alsa_get_volume(): untested with actual alsa mixer
 - FM, Line-In
 - Play sfx at independent volume  
 - Play sfx continuously for (potentially) long operations: mpd update, ...?
 - Samba:
   - Implement properly (now hardcoded)
 - Internet radio:
   - Support playlists (currently only URI's)
   - and fetch up-to-date playlist for a radio station
   - Move/mark dead stations

 * S70headunit:
 - check pid file
 - implement stop()

 * Linux:
 - Make PulseAudio logs readable in /var/log/messages (switch locale?)
 - PulseAudio watchdog
 - Make it work without PhatDAC
 - 