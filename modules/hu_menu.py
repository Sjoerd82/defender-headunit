#import uuid

class Menu():

	lMenu = []			# list of all menu items.
	id = 0				# unique id counter.
	#todo: make it multi-user
	currentMenu = None	#None = Main Menu

	def add( self, entry ):
		#todo: add unique id
		entry['uid'] = self.id
		self.id += 1
		self.lMenu.append( entry )	

	def execute( self, id ):
		#todo
		print id

	def recursive_index( self, lst, index_path ):
		if index_path:
			return self.recursive_index(lst[index_path[0]],index_path[1:])
		else:
			return lst
		
	# path is a list of id's
	# e.g. getMenu( [ 7, 1, 2 ]
	def getMenu( self, index_path ):
		#return self.recursive_index( self.lMenu, index_path )
		print self.lMenu
		return None
	
	def menuList( self, entry=None, subentry=None, formatting='numbered', ansi=False, header=None, backoption=True ):
		#todo: add parameter for dependencies
		retMenu = []
		menulevel = []
		#todo, check if entry is an int.
		
		# Main Menu
		if entry == None:
			menulevel = self.lMenu
		# Sub menu off main menu
		if not entry == None:
			if subentry == None and 'sub' in self.lMenu[entry]:
				menulevel = self.lMenu[entry]["sub"]
			else:
				# Sub menu of a menu item
				if 'sub' in self.lMenu[entry] and self.lMenu[entry]["sub"] == None:
					print "Whoaha! No entry/subentry {0}/{1}".format(entry,subentry)
				else:
					if 'sub' in self.lMenu[entry] and 'sub' in self.lMenu[entry]["sub"][subentry]:
						menulevel = self.lMenu[entry]["sub"][subentry]["sub"]
					else:
						return None

		if menulevel == None:
			return None

		if header and entry == None:
			retMenu.append('--[ MAIN MENU                 ]---------')
		elif header and subentry == None:
			retMenu.append('--[ {0:25} ]---------'.format( self.lMenu[entry]['entry']) )
		elif header and not subentry == None:
			retMenu.append('--[ {0:25} ]---------'.format( self.lMenu[entry]['sub'][subentry]['entry'] ))

		autohotkey = 48	# ascii code for zero
		for entry in menulevel:
			hotkey = ""
			postfix = ""
			#check dependencies:
			displayEntry = True
			displayText = entry["entry"]
			"""
			if 'dependencies' in entry:
				for dependency in entry['dependencies']:
					if dependency == "current_source":
						source = entry['dependencies']['current_source']
						displayEntry = testCurrentSource(source)
					elif dependency == "source_available":
						source = entry['dependencies']['source_available']
						displayEntry = testGetSourceAvailability(source)
						if not displayEntry:
							break
					elif dependency == "network_connected":
						displayEntry = testConnection()
						if not displayEntry:
							break
					elif dependency == "internet_available":
						displayEntry = testInternet()
						if not displayEntry:
							break
			"""			
			
			#additional formatting:
			if displayEntry:
				#generate a hotkey 0-9 A-Z
				if 'sub' in entry or 'run' in entry or ( 'type' in entry and entry['type'] in ("toggle") ):
					hotkey = chr(autohotkey)+". "
					autohotkey+=1
					if autohotkey == 58:
						autohotkey = 65
					
				#generate a postfix
				if 'sub' in entry and not entry["sub"] == None:
					postfix = " >"
				if 'type' in entry and entry['type'] == "toggle":
					postfix = " T"
				
				#put it together
				displayText = "{0:3}{1:32}{2}".format(hotkey,displayText,postfix)
				
			#display
			if displayEntry:
				retMenu.append(displayText)
				
		if backoption:
			retMenu.append( "Y. Back" )
			retMenu.append( "Z. Exit menu" )
			
		return retMenu
		
	def menuDisplay( self, entry=None, subentry=None, header=None ):
		menuitems = self.menuList( entry=entry, subentry=subentry, header=header )

		if menuitems == None:
			print("No entries in this menu (entry: {0})".format(entry))
			return False
			
		for entry in menuitems:
			print entry
