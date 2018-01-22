
from hu_utils import *

# ********************************************************************************
# Output wrapper
#

def printer( message, level=20, continuation=False, tag='STTNGS' ):
	#TODO: test if headunit logger exist...
	if continuation:
		myprint( message, level, '.'+tag )
	else:
		myprint( message, level, tag )


# ********************************************************************************
#
#
#
		
import time
from RPLCD.i2c import CharLCD

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

def loop_string(string, lcd, framebuffer, row, num_cols, postfix='', delay=0.3):
   padding = ' ' * num_cols
   s = string
   for i in range(len(s) - num_cols + 1 + len(postfix)):
      framebuffer[row] = s[i:i+num_cols-len(postfix)] + postfix
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

def charset( charset ):
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

        #lcd.create_char(0, chr_play)
        #lcd.create_char(1, chr_pause)
        lcd.create_char(4, chr_up)
        lcd.create_char(5, chr_down)
        lcd.create_char(6, chr_left)
        lcd.create_char(7, chr_right)

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

class lcd_mgr():

	framebuffer = [
			'',
			'']

	def __init__(self):
		lcd.clear()
		
	def write_to_lcd(lcd, framebuffer, num_cols):
	   """Write the framebuffer out to the specified LCD."""
	   lcd.home()
	   for row in framebuffer:
		 lcd.write_string(row.ljust(num_cols)[:num_cols])
		 lcd.write_string('\r\n')

	def set_fb_char( row, col, char ):
		self.framebuffer[row] = self.framebuffer[row][:col] + char + self.framebuffer[row][col+2:]
		
	
	def lcd_mgr( bla ):

		if bla == 'random_on':
			set_fb_char(1,10,'R')
		
		
		