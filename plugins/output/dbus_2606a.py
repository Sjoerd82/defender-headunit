#!/usr/bin/python

# ********************************************************************************
#
# Dbus receiver
#

from hu_utils import *

dbus_addr = "com.arctura.d1606a"
outputName='d1606a'
outputName_long = 'LCD 1606a'

# ********************************************************************************
# Output wrapper
#

# TODO!!! the "headunit"-logger is no longer accessible once this script is started "on its own"..
def myprint( message, level, tag ):
	print("[{0}] {1}".format(tag,message))

def printer( message, level=20, continuation=False, tag="d1606a" ):
	#TODO: test if headunit logger exist...
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


printer('Starting Output: LCD 1606a')

		
# ********************************************************************************
#
# Dbus libraries
#
# #TODO, check if these are actually all required..
#
import dbus, dbus.service, dbus.exceptions
import sys

from dbus.mainloop.glib import DBusGMainLoop
import gobject

import os

# ********************************************************************************
#
#
#
		
import time
from RPLCD.i2c import CharLCD
import threading

def write_framebuffer(lcd, framebuffer):
        lcd.home()
        for row in framebuffer:
                lcd.write_string(row)
                lcd.write_string('\r\n')


def marquee(string, lcd, framebuffer, row, num_cols, delay=0.3):
   padding = ' ' * num_cols
   #s = padding + string + padding
   s = string
   for i in range(len(s) - num_cols + 1):
      framebuffer[row] = s[i:i+num_cols]
      write_to_lcd(lcd, framebuffer, num_cols)
      time.sleep(delay)


def loop_return(string, lcd, framebuffer, row, num_cols):
   framebuffer[row] = string[0:16]
   write_to_lcd(lcd, framebuffer, num_cols)

def loop_string1(string, lcd, framebuffer, row, num_cols, delay=0.3):
   padding = ' ' * num_cols
   #s = padding + string + padding
   s = string
   for i in reversed(range(len(s) - num_cols + 1)):
      framebuffer[row] = s[i:i+num_cols]
      #print framebuffer[row]
      write_to_lcd(lcd, framebuffer, num_cols)
      time.sleep(delay)


def lcd_menu( entry, counter, hasSub=False, isFirst=False, isLast=False, showCount=True, isHeader=False ):

        framebuffer = [
                '',
                '']

        lcd.clear()

		#framebuffer[0] = entry.ljust(16)
        #
        #if len(entry) =< 16:
        #       framebuffer[0] = entry.ljust(16)
        #else:
        #       loop_string(entry,lcd,framebuffer,0,16,delay=0)

        #if not isHeader and showCount:
                #lcd.write_string('1/3 ')
                #lcd.write_string('1: ')
                #lcd.write_string(str(counter))
                #lcd.write_string(': ')
                #lcd.write_string(entry)
        #       framebuffer[0] = entry
        #elif len(entry) <= 12:
        #       lcd.write_string(entry)
        #elif len(entry) > 12:
        #       loop_string(entry,lcd,framebuffer,0,16,delay=0)

        #if showCount and isHeader:
        #       #lcd.cursor_pos = (0,14)
        #       #lcd.write_string(' 3')
        #       framebuffer[0] = "               3"


        # BUILD SECOND ROW:

        if showCount and not isHeader:
                framebuffer[1] = framebuffer[1] + ' {0}/4  '.format(counter)

        if not isFirst:
                # UP ARROW
                #lcd.cursor_pos = (1,1)
                #lcd.write_string('\x04')
                #framebuffer[1] = framebuffer[1][:9] + '\x04' + framebuffer[1][10:]
                framebuffer[1] = framebuffer[1] + '\x04'
        else:
                framebuffer[1] = framebuffer[1] + ' '

        if not isLast:
                # DOWN ARROW
                #lcd.cursor_pos = (1,0)
                #lcd.write_string('\x05')
                #framebuffer[1][2] = '\x05'
                #framebuffer[1] = framebuffer[1][:11] + '\x05' + framebuffer[1][12:]
                framebuffer[1] = framebuffer[1] + '\x05'
        else:
                framebuffer[1] = framebuffer[1] + ' '

        if len(entry) <= 16:
                framebuffer[0] = entry.ljust(16)
        else:
                framebuffer[0] = entry[1:16]

        # BUILD FIRST ROW:

        if hasSub:
                framebuffer[0] = "{0}{1}".format( entry[0:15].ljust(15), '\x07' )
        else:
                framebuffer[0] = entry[0:16].ljust(16)

        write_framebuffer(lcd, framebuffer)

        if len(entry) > 16:
			while True:
				time.sleep(1)
				loop_string(entry,lcd,framebuffer,0,16,postfix='\x07',delay=0)
				time.sleep(1)
				# reset to beginning

				if hasSub:
						framebuffer[0] = "{0}{1}".format( entry[0:15].ljust(15), '\x07' )
				else:
						framebuffer[0] = entry[0:16].ljust(16)

				write_framebuffer(lcd, framebuffer)

                #loop_string1(entry,lcd,framebuffer,0,16,delay=0)

class dbusService( dbus.service.Object ):

	lcd = None
	framebuffer = [
			'',
			'']
	num_cols = 16
	#threads = []
	t = None

	def __init__( self, bus_name ):
		#ehm?
		super(dbusService,self).__init__(bus_name, "/com/arctura/2606a")

		self.lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
                   cols=16, rows=2, dotsize=8,
                   charmap='A00',
                   auto_linebreaks=True,
                   backlight_enabled=True)
	
		self.framebuffer[0] = '                '
		self.framebuffer[1] = '                '
		self.lcd.clear()
		self.charset()

class lcd_mgr():

	lcd = None
	framebuffer = [
			'',
			'']
	num_cols = 16
	#threads = []
	t = None

	displaydata_cdc = {}
	
	def __init__( self ):

		self.lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
                   cols=16, rows=2, dotsize=8,
                   charmap='A00',
                   auto_linebreaks=True,
                   backlight_enabled=True)
	
		self.framebuffer[0] = '.               '
		self.framebuffer[1] = '               .'
		self.lcd.clear()
		self.charset()

	def set_fb( self, fb ):
		self.framebuffer = fb
		
	def write_to_lcd( self ):
	   """Write the framebuffer out to the specified LCD."""
	   self.lcd.home()
	   for row in self.framebuffer:
		 self.lcd.write_string(row.ljust(self.num_cols)[:self.num_cols])
		 self.lcd.write_string('\r\n')

	def set_fb_str( self, row, col, txt ):
		self.framebuffer[row] = self.framebuffer[row][:col] + txt + self.framebuffer[row][col+len(txt):]
	
	def lcd_text( self, txt ):
		self.set_fb_str(0,0,txt)
		self.write_to_lcd()
		
	def lcd_play( self, artist, track, filename, tracknumber, tracktotal ):
		#self.lcd_text( '{1}{2}/{3}'.format('\x00',tracknumber,tracktotal) )
		self.set_fb_str(1,0,'{0}{1}/{2}'.format('\x00',tracknumber,tracktotal))
		
		# Various display modes:
		# 1) Artist - Trackname
		if not artist == None and not track == None:
			testtxt = '{0} - {1}'.format(artist, track)
		else:
			testtxt = filename
		
		self.lcd_text( testtxt )

		#not the right place to stop... stop at every display change... hmm, write_to_lcd??
		#threads[0].stop()
		#self.t.stop() 			THREADS CAN'T BE STOPPED IN PYTHON!!! ---- multiprocessing ? asyncio ?
		
		if len(testtxt) > 16:
			#todo run under separate thread! (or atleast async..)
			self.loop_string( testtxt, 0, delay=0 )
			time.sleep(2)
			self.lcd_text( testtxt )
			#self.t = threading.Thread(target=self.worker, args=(testtxt,))
			#threads.append(t)
			#self.t.start()
			#self.worker( testtxt, 0, delay=0 )
	
	def lcd_ding( self, bla ):

		if bla == 'src_usb':	 
			self.set_fb_str(1,1,'USB')
			self.write_to_lcd()
		elif bla == 'update_on':	 
			self.set_fb_str(1,5,'UPD')
			self.write_to_lcd()
		elif bla == 'random_on':
			self.set_fb_str(1,9,'RND')
			self.write_to_lcd()
		elif bla == 'att_on':	 
			self.set_fb_str(1,13,'ATT')
			self.write_to_lcd()

	def worker( self, string ):
		while True:
			self.loop_string( string, 0, delay=0 )
			time.sleep(2)
			self.lcd_text( string )
			time.sleep(2)

	def loop_string( self, string, row, postfix='', delay=0.3 ):
		padding = ' ' * self.num_cols
		s = string
		for i in range(len(s) - self.num_cols + 1 + len(postfix)):
			self.framebuffer[row] = s[i:i+self.num_cols-len(postfix)] + postfix
			self.write_to_lcd()
			time.sleep(delay)
	  
	def charset( self ):
		"""
		chr_play = (
				0b10000,
				0b11000,
				0b11100,
				0b11110,
				0b11100,
				0b11000,
				0b10000,
				0b00000
		)
		"""
		chr_play = (
				0b00000,
				0b10000,
				0b11000,
				0b11100,
				0b11000,
				0b10000,
				0b00000,
				0b00000
		)
		chr_pause = (
				0b11011,
				0b11011,
				0b11011,
				0b11011,
				0b11011,
				0b11011,
				0b11011,
				0b00000
		)
		chr_up = (
				0b00000,
				0b00100,
				0b01110,
				0b11111,
				0b00100,
				0b00100,
				0b00100,
				0b00000
		)
		chr_down = (
				0b00000,
				0b00100,
				0b00100,
				0b00100,
				0b11111,
				0b01110,
				0b00100,
				0b00000
		)

		chr_left = (
				0b00000,
				0b00000,
				0b00100,
				0b01100,
				0b11111,
				0b01100,
				0b00100,
				0b00000
		)

		chr_right = (
				0b00000,
				0b00000,
				0b00100,
				0b00110,
				0b11111,
				0b00110,
				0b00100,
				0b00000
		)

		self.lcd.create_char(0, chr_play)
		self.lcd.create_char(1, chr_pause)
		self.lcd.create_char(4, chr_up)
		self.lcd.create_char(5, chr_down)
		self.lcd.create_char(6, chr_left)
		self.lcd.create_char(7, chr_right)


def worker():

	global mylcd
	global fb_global
	i = 0
	fb_old = ""
	
	while True:
		#i += 1
		#mylcd.set_fb_str(0,13,str(i))
		if fb_old <> fb_global:
			mylcd.set_fb(fb_global)
			fb_old = fb_global
		#mylcd.write_to_lcd()
		
		
		
# callback, keep it short! (blocks new input)
def cb_display( displaydata ):

	global fb_global
	
	def fbmod( fb, row, col, txt ):
		fb[row] = fb[row][:col] + txt + fb[row][col+len(txt):]
		return fb

	
	printer('DBUS event received: {0}'.format(displaydata), tag='d1606a')

	if 'rnd' in displaydata:
		if displaydata['rnd'] == '1' or displaydata['rnd'] == 'on':
			fbmod( fb_global, 1,9,'RND')
		else:
			fbmod( db_global, 1,9,'   ')

			
	#print displaydata
	"""
	if 'src' in displaydata:
		#if not mylcd.displaydata_cdc['src'] == displaydata['src']:
		#max 4 chars:
		mylcd.set_fb_str(1,1,displaydata['src'][:4].ljust(4))

	if 'upd' in displaydata:
		if displaydata['upd'] == '1':
			mylcd.set_fb_str(1,5,'UPD')
		else:
			mylcd.set_fb_str(1,5,'   ')

	if 'rnd' in displaydata:
		if displaydata['rnd'] == '1' or displaydata['rnd'] == 'on':
			mylcd.set_fb_str(1,9,'RND')
		else:
			mylcd.set_fb_str(1,9,'   ')
			
	if 'att' in displaydata:
		if displaydata['att'] == '1':
			mylcd.set_fb_str(1,13,'ATT')
		else:
			mylcd.set_fb_str(1,13,'   ')

	if 'info' in displaydata:
		mylcd.lcd_text(displaydata['info'][:16].ljust(16))

	#commit changes
	mylcd.write_to_lcd()
	"""
	
	#todo... merge!
	#mylcd.displaydata_cdc = displaydata
	
	
	#if bla == 'src_usb':
	#		self.set_fb_str(1,1,'USB')
	#		self.write_to_lcd()
#		elif bla == 'update_on':	 
#			self.set_fb_str(1,5,'UPD')
#			self.write_to_lcd()
#		elif bla == 'random_on':
#			self.set_fb_str(1,9,'RND')
#			self.write_to_lcd()
#		elif bla == 'att_on':	 
#			self.set_fb_str(1,13,'ATT')
#			self.write_to_lcd()

			
	#print
	#print event['random']	#OK:	1
	#print event['artist']	#OK:	The Midnight
	#print event['random']
	
	#print event[u'random']
	#print event[u'artist']
	
	#disp = lcd_mgr()
	#disp.lcd_text(event)
	
	
	#if event == "player":
	#
	#	disp = lcd_mgr()
	#	disp.lcd_play( 'artist', 'title', 'file.mp3', 'track', 42 )
				
# ********************************************************************************
#
# Main loop
#

mylcd = lcd_mgr()
mylcd.lcd_text('loading...')


fb_global = [
		'',
		'']


t = threading.Thread(target=worker)
#threads.append(t)
t.start()

#
# Initialize the mainloop
#
DBusGMainLoop(set_as_default=True)

#
# main loop
#
mainloop = gobject.MainLoop()

#
# DBus: system bus
# On a root only embedded system there may not be a usable session bus
#
bus = dbus.SystemBus()


# Declare a name where our service can be reached
#try:
#	bus_name = dbus.service.BusName(dbus_addr,
#                                    bus=dbus.SystemBus(),
#                                    do_not_queue=True)
#	printer('DBus OK: {0}'.format(dbus_addr))
#except dbus.exceptions.NameExistsException:
#	printer("DBus: Service is already running")
#	sys.exit(1)

#
# Connect Callback functions to DBus Signals
#
bus.add_signal_receiver(cb_display, dbus_interface = "com.arctura.display")
	
# Run the loop
try:
    #dbusService(bus_name)
    mainloop.run()
except KeyboardInterrupt:
    printer("keyboard interrupt received")
except Exception as e:
    printer("Unexpected exception occurred: '{}'".format(str(e)))
finally:
    printer("quitting...")
    mainloop.quit()

