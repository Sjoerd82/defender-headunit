def getAvailableSubCnt(lSource, index):

		if not 'subsources' in lSource[index]:
			return None
		
		c = 0
		for subsource in lSource[index]['subsources']:
			if subsource['available']:
				c += 1
		return c

def next( lSource, iCurrentSource, reverse=False ):

	def source_iterator(ix_start, ix_stop, j_start, reverse):
		#
		# if no current source, we'll loop through the sources until we find one
		#
		# TODO CHECK IF i_start isn't at the end of the list!
		
		# python list slicing
		# step -1 reverses direction
		# the start and end needs to be reversed too
		# 
		original_start = ix_start
		
		if reverse:
			step = -1
			logtext = "to prev."
		else:
			step = 1
			logtext = "to next"
		
		# loop sources
		for source in lSource[ix_start:ix_stop:step]:
		
			# source available and has *no* sub-sources:
			if not source['template'] and source['available']:
				print('NEXT: Switching {0} {1}: {2:s}'.format(logtext,ix_start,source['displayname']))
				iCurrentSource[0] = ix_start
				iCurrentSource[1] = None
				return iCurrentSource
			
			# sub-source and available:
			elif source['template'] and source['available']:
			
				# reverse initialize sub-sources loop
				if reverse and j_start is None:
					j_start = len(source['subsources'])-1
								
				# reset sub-loop counter to 0
				if ix_start > original_start and j_start > 0:
					j_start = 0
			
				# loop sub-sources:
				for subsource in source['subsources'][j_start::step]:

					if subsource['available']:
						print('NEXT: Switching {0}: {1}/{2}: {3:s}'.format(logtext,ix_start,j_start,subsource['displayname']))
						iCurrentSource[0] = ix_start
						iCurrentSource[1] = j_start
						return iCurrentSource
						
					j_start += step

			ix_start += step

		return None

	#
	# check if we have at least two sources
	#

	#
	# check if iCurrentSource is set
	# (in that case, set the next available, and return index)
	#

	#
	# determine starting positions
	#
	
	#
	# Current source is a Sub-Source
	#
	if not iCurrentSource[1] is None: # and
		
		if not reverse:
			
			# set source start point
			start = iCurrentSource[0]
			
			# set sub-source start point
			if iCurrentSource[1] is None:
				ssi_start = 0
			else:
				ssi_start = iCurrentSource[1]+1	#next sub-source (+1) isn't neccesarily available, but this will be checked later
				#print "Starting Sub-Source loop at {0}".format(ssi_start)

		elif reverse:
			
			#if the current sub-source is the first, the don't loop sub-sources, but start looping at the previous source
			ss_cnt = getAvailableSubCnt(lSource, iCurrentSource[0])
			if iCurrentSource[1] == 0 or ss_cnt-1 == 0:
			#if iCurrentSource[1] == 0 or ssi_start == 0:
				start = iCurrentSource[0]-1	# previous source
				ssi_start = None			# identifies to start at the highest sub-source
			else:
				start = iCurrentSource[0]	# current source
				ssi_start = ss_cnt-2		# previous sub-source
			
	#
	# Current source is *not* a Sub-Source:
	#
	elif iCurrentSource[1] is None:

		if not reverse:
		
			start = iCurrentSource[0]+1
			ssi_start=0
			
		elif reverse:
		
			# if the current source is the first, then start at the last source
			if iCurrentSource[0] == 0:
				start = len(lSource)-1 #use function	# start at the last item in the list
			else:
				start = iCurrentSource[0]-1		# previous source
			
			ssi_start=None
	
	# loop through sources
	# source_iterator returns next source index, or None, in case no next available was found
	res = source_iterator(start, None, ssi_start, reverse)
	
	# if nothing was found, "wrap-around" to beginning/ending of list
	if res == None:
			
		if not reverse:
			stop = start-1	# stop before current source
			start = 0		# start at the beginning
			ssi_start = 0
			return source_iterator(start, stop, ssi_start, reverse)
			
		elif reverse:
			stop = start	# stop at the current source
			start = len(lSource)-1 #use function	# start at the last item in the list
			ssi_start = None
			return source_iterator(start, stop, ssi_start, reverse)
		
	else:
		return res
		


lSource = []

source1_subs = []
source2_subs = []
source6_subs = []

source1_subs.append( {'displayname':'media: /media/SJOERD', 'available':True} )

source2_subs.append( {'displayname':'locmus: /media/PIHU_DATA', 'available':True} )
source2_subs.append( {'displayname':'locmus: /media/PIHU_DATA2', 'available':True} )

source6_subs.append( {'displayname':'smb: /media/PIHU_SMB/music', 'available':True} )

source0 = {'template':False, 'displayname':'FM', 'available':True}
source1 = {'template':True, 'displayname':'Removable Media', 'available':True, 'subsources':source1_subs}
source2 = {'template':True, 'displayname':'Internal Storage', 'available':True, 'subsources':source2_subs}
source3 = {'template':False, 'displayname':'Bluetooth', 'available':False}
source4 = {'template':False, 'displayname':'AUX', 'available':False}
source5 = {'template':False, 'displayname':'Internet Radio', 'available':False}
source6 = {'template':True, 'displayname':'Network Share', 'available':True, 'subsources':source6_subs}
source7 = {'template':False, 'displayname':'Test', 'available':True}


lSource.append(source0)
lSource.append(source1)
lSource.append(source2)
lSource.append(source3)
lSource.append(source4)
lSource.append(source5)
lSource.append(source6)
lSource.append(source7)


#iCurrentSource = [0,None]
#print "====== start ======"
#print lSource
#print iCurrentSource
print "==================="

print "------ <NEXT>  0,None  => 1,0"
print next( lSource, [0,None] )

print "------ <NEXT>  1,0  => 2,0"
print next( lSource, [1,0] )

print "------ <NEXT>  2,0  => 2,1"
print next( lSource, [2,0] )

print "------ <NEXT>  2,1  => 6,0"
print next( lSource, [2,1] )

print "------ <NEXT>  6,0  => 7,None"
print next( lSource, [6,0] )

print "------ <NEXT>  7,None  => 0,None (loop 2)"
print next( lSource, [7,None] )

print "------ <PREV>  7,None  => 6,0"
print next( lSource, [7,None], True )

print "------ <PREV>  6,0  => 2,1"
print next( lSource, [6,0], True )

print "------ <PREV>  2,1  => 2,0"
print next( lSource, [2,1], True )

print "------ <PREV>  2,0  => 1,0"
print next( lSource, [2,0], True )

print "------ <PREV>  1,0  => 0,None"
print next( lSource, [1,0], True )

print "------ <PREV>  0,None  => 7,None (loop 2)"
print next( lSource, [0,None], True )

