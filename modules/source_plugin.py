class BaseSourceClass(object):

	def __init__(self):
		self.printer('C Base Source Class Init', level=LL_DEBUG)
		#pass

	# output wrapper
	def printer(self, message, level=LL_INFO, tag=LOG_TAG):
		self.logger.log(level, message, extra={'tag': tag})
		
	def init( self, sourceCtrl ):
		self.printer('Initializing...')

	def check( self, sourceCtrl, subSourceIx=None ):
		self.printer('Checking availability...')
		ix = sourceCtrl.index('name','locmus')	# source index
		locations = []							# list of tuples; index: 0 = mountpoint, 1 = mpd dir, 2 = availability.
		subsource_availability_changes = []		# list of changes
						
		if subSourceIx is None:
			subsources = sourceCtrl.subsource_all( ix )
			for subsource in subsources:
				locations.append( (subsource['mountpoint'], subsource['mpd_dir'], subsource['available']) )
			ssIx = 0
		else:
			subsource = sourceCtrl.subsource( ix, subSourceIx )
			locations.append( (subsource['mountpoint'], subsource['mpd_dir'], subsource['available']) )
			ssIx = subSourceIx

		# check mountpoint(s)
		for location in locations:
		
			mountpoint = location[0]
			mpd_dir = location[1]
			original_availability = location[2]
			new_availability = None

			self.printer('Checking local folder: {0}, current availability: {1}'.format(mountpoint,original_availability))
			
			# check if the dir exists:
			if not os.path.exists(mountpoint):
				self.printer(" > Local music directory does not exist.. creating {0}".format(mountpoint),LL_WARNING)
				os.makedirs(mountpoint)
				if not os.path.exists(mountpoint):
					self.printer(" > [FAIL] Could not create directory",LL_WARNING)
					
				# obviously there will no be any music in that new directory, so marking it unavailable..
				new_availability = False
				
			else:
				
				if not os.listdir(mountpoint):
					self.printer(" > Local music directory is empty.",LL_WARNING)
					new_availability = False
				else:
					self.printer(" > Local music directory present and has files.",LL_INFO)
					
					if not self.mpdc.is_dbdir( mpd_dir ):
						self.printer(" > Running MPD update for this directory.. (wait=True) ALERT! LONG BLOCKING OPERATION AHEAD...")
						self.mpdc.update_db( mpd_dir, True )	#TODO: don't wait! set available on return of update..
						if not self.mpdc.is_dbdir( mpd_dir ):
							self.printer(" > Nothing to play marking unavailable...")
							new_availability = False
						else:
							self.printer(" > Music found after updating")
							new_availability = True
					else:
						new_availability = True
			
			if new_availability is not None and new_availability != original_availability:
				sourceCtrl.set_available( ix, new_availability, ssIx )
				subsource_availability_changes.append({"index":ix,"subindex":ssIx,"available":new_availability})

			ssIx+=1
		
		return subsource_availability_changes
		
		
	#def play( self, sourceCtrl, resume={} ):