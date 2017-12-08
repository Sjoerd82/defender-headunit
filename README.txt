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

 * S70headunit:
 - check pid file
 - implement stop()

 * Linux:
 - Make PulseAudio logs readable in /var/log/messages (switch locale?)
 -