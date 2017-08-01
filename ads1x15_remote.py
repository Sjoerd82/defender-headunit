# Simple demo of reading each analog input from the ADS1x15 and printing it to
# the screen.
# Author: Tony DiCola
# License: Public Domain
import time
from subprocess import call

# Import the ADS1x15 module.
import Adafruit_ADS1x15


# Create an ADS1115 ADC (16-bit) instance.
#adc = Adafruit_ADS1x15.ADS1115()

# Or create an ADS1015 ADC (12-bit) instance.
adc = Adafruit_ADS1x15.ADS1015()

# Note you can change the I2C address from its default (0x48), and/or the I2C
# bus by passing in these optional parameters:
#adc = Adafruit_ADS1x15.ADS1015(address=0x49, busnum=1)

# Choose a gain of 1 for reading voltages from 0 to 4.09V.
# Or pick a different gain to change the range of voltages that are read:
#  - 2/3 = +/-6.144V
#  -   1 = +/-4.096V
#  -   2 = +/-2.048V
#  -   4 = +/-1.024V
#  -   8 = +/-0.512V
#  -  16 = +/-0.256V
# See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.
GAIN = 2/3

BUTTON01_LO = 180
BUTTON01_HI = 190
BUTTON02_LO = 220
BUTTON02_HI = 260
BUTTON03_LO = 310
BUTTON03_HI = 330
BUTTON04_LO = 380
BUTTON04_HI = 410
BUTTON05_LO = 460
BUTTON05_HI = 490
BUTTON06_LO = 560
BUTTON06_HI = 580
BUTTON07_LO = 640
BUTTON07_HI = 670
BUTTON08_LO = 740
BUTTON08_HI = 770
BUTTON09_LO = 890
BUTTON09_HI = 910
BUTTON10_LO = 1050
BUTTON10_HI = 1100

def button_press ( func ):

    # Execute

    if func == 'SHUFFLE':
       print('Toggling shuffle')
       call(["mpc", "random"])
    elif func == 'ATT':
       print('ATT mode')
    elif func == 'TRACK_NEXT':
       print('Next track')
       call(["mpc", "next"])
    elif func == 'TRACK_PREV':
       print('Prev. track')
       call(["mpc", "prev"])

    # Feedback beep
    call(["gpio", "write", "6", "1"])
    time.sleep(0.05)
    call(["gpio", "write", "6", "0"])

    # Wait until button is released

    value_0 = adc.read_adc(0)
    press_count = 0
    while value_0 > 600:
        value_0 = adc.read_adc(0)
        time.sleep(0.1)
        press_count+=1
        if func == 'TRACK_NEXT' and press_count == 10:
            break
        elif func == 'TRACK_PREV'  and press_count == 10:
            break

#print('Reading ADS1x15 values, press Ctrl-C to quit...')
call(["gpio", "mode", "6", "out"])
call(["gpio", "write", "6", "0"])

# Print nice channel column headers.
#print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} |'.format(*range(4)))
#print('-' * 37)
# Main loop.
while True:
    # Read channel 0
    value_0 =  adc.read_adc(0, gain=GAIN)
    #print(value_0)

    if BUTTON01_LO <= value_0 <= BUTTON01_HI:
        print('BUTTON01')
        #Bottom button
    elif BUTTON02_LO <= value_0 <= BUTTON02_HI:
        print('BUTTON02')
        #Side button, met streepje
    elif BUTTON03_LO <= value_0 <= BUTTON03_HI:
        print('BUTTON03')
        #VOL
    elif BUTTON04_LO <= value_0 <= BUTTON04_HI:
        print('BUTTON04')
        #VOL
    elif BUTTON05_LO <= value_0 <= BUTTON05_HI:
        print('BUTTON05')
        button_press('TRACK_PREV')
    elif BUTTON06_LO <= value_0 <= BUTTON06_HI:
        print('BUTTON06')
        button_press('TRACK_NEXT')
    elif BUTTON07_LO <= value_0 <= BUTTON07_HI:
        print('BUTTON07')
        button_press('SHUFFLE')
    elif BUTTON08_LO <= value_0 <= BUTTON08_HI:
        print('BUTTON08')
        button_press('ATT')
    elif BUTTON09_LO <= value_0 <= BUTTON09_HI:
        print('BUTTON09')
        button_press('SOURCE')
    elif BUTTON10_LO <= value_0 <= BUTTON10_HI:
        print('BUTTON10')
        #Off

    time.sleep(0.1)
