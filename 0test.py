locations1 = [ ["/media/PIHU_DATA","PIHU_DATA"], ["/media/PIHU_DATA1","PIHU_DATA1"] ]

locations = []
locations.append( ("/media/PIHU_DATA","PIHU_DATA") )
locations.append( ("/media/PIHU_DATA1","PIHU_DATA1") )

#for md, mp in locations:
for loc in locations:
	md = loc[0]
	mp = loc[1]
	print ("loop:")
	print md
	print mp
	
print locations1
print locations