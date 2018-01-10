
from hu_utils import *

import copy
import logging
from logging import Formatter
import re


#********************************************************************************
#
# Markup
#

tagcolors = {
  'source'	: 'yellow'
 ,'plugin'	: 'blue'
 #SOURCES:
 ,'mpd'		: 'cyan'
 ,'fm'		: 'turquoise_4'
 ,'locmus'	: 'cyan'
 ,'media'	: 'cyan'
 ,'bt'		: 'light_blue'
 ,'line'	: 'green'
 ,'stream'	: 'deep_pink_1b'
 ,'smb'		: 'dark_orange'
 }

# return an (ANSI) formatted tag
def tag ( tagname, format='ANSI', tagsize=6 ):
	if tagname == '' or tagname == None:
		return ''
		
	#If first character of the tag is a dot, it is a 'continuation'
	if tagname[0] == '.':
		bCont = True
	else:
		bCont = False

	if bCont:
		tagname = tagname[1:].upper()
		ftag = str('.').rjust(len(tagname),'.')
	else:
		ftag = tagname.upper()

	if format == 'ANSI':
		# Get/Set Color
		if tagname.lower() in tagcolors:
			color = tagcolors[tagname.lower()]
		else:
			color = 'white'
	
		if bCont:
			ctag = ' {0} '.format(colorize(ftag.center(tagsize),color))
		else:
			ctag = '[{0}]'.format(colorize(ftag.center(tagsize),color))
	else:
		if bCont:
			ctag = ' {0} '.format(ftag.center(tagsize))
		else:
			ctag = '[{0}]'.format(ftag.center(tagsize))
			
	return ctag
	#return self.colorize(ftag.center(self.tag_size),color)

#********************************************************************************
#
# Logging formatters
#

class ColoredFormatter(Formatter):
 
	def __init__(self, patern):
		Formatter.__init__(self, patern)
 
	def colorer(self, text, color=None):
		#if color not in COLORS:
		#    color = 'white'
		#clr = COLORS[color]
		#return (PREFIX + '%dm%s' + SUFFIX) % (clr, text)
		return None
 
	def format(self, record):
		colored_record = copy.copy(record)
		#levelname = colored_record.levelname
		#color = MAPPING.get(levelname, 'white')
		#colored_levelname = self.colorer(levelname, color)
		#colored_record.levelname = 'MyLevel' #colored_levelname

		#print colored_record.levelname
		
		# Markup specialstrings
		colored_record.msg = colored_record.msg.replace('[OK]',colorize('[OK]','light_green'))
		colored_record.msg = colored_record.msg.replace('[FAIL]',colorize('[FAIL]','light_red'))

		#Colorize according to error level
		if colored_record.levelno == LL_WARNING:
			fmessage = colorize(colored_record.msg,'orange_red_1')
		elif colored_record.levelno == LL_ERROR:
			fmessage = colorize(colored_record.msg,'light_red')
		elif colored_record.levelno == LL_CRITICAL:
			fmessage = colorize(colored_record.msg,'white','red')
		else:
			fmessage = colored_record.msg

		colored_record.msg = fmessage
		
		# Markup tag
		if not colored_record.tag == '':
			colored_record.tag = tag(colored_record.tag)+' '

		return Formatter.format(self, colored_record)

class RemAnsiFormatter(Formatter):
 
	def __init__(self, patern):
		Formatter.__init__(self, patern)

	def format(self, record):
		record_copy = copy.copy(record)
		
		# Remove any ANSI formatting
		record_copy.msg = re.sub('\033[[](?:(?:[0-9]*;)*)(?:[0-9]*m)', '', record_copy.msg)
	
		# Remove any ANSI formatting from the tag, if any..
		#if 'tag' in colored_record:
		#if colored_record.has_key('tag'):
		#if colored_record.extra  is not None:
		record_copy.tag = re.sub('\033[[](?:(?:[0-9]*;)*)(?:[0-9]*m)', '', record_copy.tag)
		if not record_copy.tag == '':
			record_copy.tag = tag(record_copy.tag,format='None')+' '
			#record_copy.tag = '['+record_copy.tag.upper()+']'

		#levelname = colored_record.levelname
		#color = MAPPING.get(levelname, 'white')
		#colored_levelname = self.colorer(levelname, color)
		#colored_record.levelname = 'MyLevel' #colored_levelname
		#colored_record.message = self.remansi(colored_record.message) #.upper()
		#colored_record.levelname = "blaa" #colored_record.levelname.lower()
		return Formatter.format(self, record_copy)
