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
     - cb_mpd_control()       com.arctura.mpd, from dbus_mpd.py
     - cb_udisk_device_add()  org.freedesktop.UDisks
     - cb_udisk_device_rem()  org.freedesktop.UDisks


ToDo:

 * headunit.py:
 - rename cb_-functions
 - include pid file
 1 handle udisks usb insert/removal

 * S70headunit:
 - check pid file
 - implement stop()

 * Linux:
 - Make PulseAudio logs readable in /var/log/messages (switch locale?)
 -