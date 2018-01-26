from RPLCD.i2c import CharLCD

def write_framebuffer(lcd, framebuffer):
        lcd.home()
        for row in framebuffer:
                lcd.write_string(row)
                lcd.write_string('\r\n')

# The PCF8574 I2C controller is
# located at i2c bus 1, at address 0x27
#lcd = CharLCD('PCF8574', 0x27)
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
              cols=16, rows=2, dotsize=8,
              charmap='A00',
              auto_linebreaks=True,
              backlight_enabled=True)


num_cols=16
framebuffer = [
		'Loading...',
		'']

lcd.clear()
lcd.home()
for row in framebuffer:
	lcd.write_string(row.ljust(num_cols)[:num_cols])
	lcd.write_string('\r\n')
