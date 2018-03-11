
def next( lSource, iCurrentSource, reverse=False ):

	def getAvailableSubCnt(lSource, index):

		if not 'subsources' in lSource[index]:
			return None
		
		c = 0
		for subsource in lSource[index]['subsources']:
			if subsource['available']:
				c += 1
		return c

	def source_iterator(i_start, i_end, j_start, reverse):
		#
		# if no current source, we'll loop through the sources until we find one
		#
		# TODO CHECK IF i_start isn't at the end of the list!
		
		# python list slicing
		# step -1 reverses direction
		# the start and end needs to be reversed too
		# 
		if reverse:
			#start = i_end		# inclusive
			#stop = i_start-1	# exclusive
			start = i_start
			stop = i_end
			step = -1
			logtext = "to prev."
			#print "START: {0}".format(start)
			#print "STOP: {0}".format(stop)
		else:
			start = i_start		# inclusive
			stop = None
			if not i_end is None:
				stop = i_end+1		# exclusive
			step = 1
			logtext = "to next"
			#print start
			#print stop
		
		for source in lSource[start:stop:step]:
			#print "DEBUG B -- {0}".format(source)
			# no sub-source and available:
			if not source['template'] and source['available']:
				print('NEXT: Switching {0} {1}: {2:s}'.format(logtext,start,source['displayname']))
				iCurrentSource[0] = start
				iCurrentSource[1] = None
				return iCurrentSource
			
			# sub-source and available:
			elif source['template'] and source['available']:

				#print "wa??! j_start={0}".format(j_start)
				
				#if j_start is None:
				#	j_start = 0
				
				# Reverse initialize sub-sources loop
				if reverse and j_start is None:
					j_start = len(source['subsources'])-1
					#print "rev sub loop: {0}".format(j_start)
			
				for subsource in source['subsources'][j_start::step]:
					#print "DEBUG C {0}".format(subsource)
					if subsource['available']:
						print('NEXT: Switching {0}: {1}/{2}: {3:s}'.format(logtext,start,j_start,subsource['displayname']))
						iCurrentSource[0] = start
						iCurrentSource[1] = j_start
						return iCurrentSource
						
					j_start += step

			start += step
			# reset sub-loop counter to 0
			if start > i_start and j_start > 0:
				#print "reset!"
				#j_start = None
				#iCurrentSource[1] = None
				j_start = 0
			
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
	# si  = source index
	# ssi = sub-source index
	#
	# _cur = current (starting) index
	# _end = ending index
	#
	
	# Current source is a sub-source:
	if ( not iCurrentSource[1] == None ): # and
		 #(not reverse and getAvailableSubCnt(lSource, iCurrentSource[0]) > iCurrentSource[1]+1 ) ):
		# then first check if there are more sub-sources after the current..
		# there are more available sub-sources..
		#print "Current Source is a Sub-Source"
		if not reverse:
			si_cur = iCurrentSource[0]
			si_end = None
			#ssi_start = iCurrentSource[1]+1	#next sub-source (+1) isn't neccesarily available, but this will be checked later
			if iCurrentSource[1] is None:
				#print "Starting Sub-Source loop at 0"
				ssi_start = 0
			else:
				ssi_start = iCurrentSource[1]+1	#next sub-source (+1) isn't neccesarily available, but this will be checked later
				#print "Starting Sub-Source loop at {0}".format(ssi_start)
		else:
			ssi_start = getAvailableSubCnt(lSource, iCurrentSource[0])-1
			if iCurrentSource[1] == 0 or ssi_start == 0:
				#print "starting prev source"
				si_cur = iCurrentSource[0]-1
				ssi_start = None
			else:
				ssi_start += -1
				#print "starting same source j_start={0}".format(ssi_start)
				si_cur = iCurrentSource[0]
			si_end = None
			
		
		
	# Current source is not a sub-source:
	else:

		#print "Current Source is NOT a Sub-Source"
		# no more available sub-sources
		if not reverse:
			si_cur = iCurrentSource[0]+1
			si_end = None
			ssi_start=0
		else:
		
			# start at the top
			if iCurrentSource[0] == 0:
				si_cur = hival = len(lSource)-1 #use function
			else:
				si_cur = iCurrentSource[0]-1
			
			si_end = None
			ssi_start=0
		
	#print "Doing first loop"
	# source_iterator returns next source index, or None, in case no next available was found
	res = source_iterator(si_cur, si_end, ssi_start, reverse)
	
	if res == None:
		# Let's start from the beginning till current
		ssi_start = 0
		#print "DEBUG still here..."
		
		if not reverse:
			return source_iterator(0, si_cur-1, ssi_start, reverse)
		else:
			hival = len(lSource)-1 #use function
			return source_iterator(hival, si_cur, ssi_start, reverse)
		
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

