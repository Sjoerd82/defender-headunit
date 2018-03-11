
def test_match( dTest, dMatchAgainst ):
	matches = set(dTest.items()) & set(dAgainst.items())
	if len(matches) == len(dTest):
		return True
	else:
		return False

#ALL (1) match:
dTest1 = {'mountpoint':'/media/PIHU_DATA2'}

#ALL (3) match:
dTest2 = {'mountpoint':'/media/PIHU_DATA2', 'key1': 'val1', 'key2':'val2'}

#2 match, 1 no match:
dTest3 = {'mountpoint':'/media/PIHU_DATA2', 'key1': 'val1', 'key3':'val3'}

#1 match, 2 no match:
dTest4 = {'mountpoint':'/media/PIHU_DATA2', 'key4': 'val4', 'key3':'val3'}

#NONE (3) match (both on key and value):
dTest5 = {'X':'/media/PIHU_DATA2', 'key4': 'val4', 'key3':'val3'}

#NONE (3) match (only on value):
dTest6 = {'mountpoint':'/media/PIHU_DATA1', 'key1': 'val4', 'key2':'val3'}

#ALL (3) match, but in reversed order:
dTest7 = {'key2':'val2', 'key1': 'val1', 'mountpoint':'/media/PIHU_DATA2'}


dAgainst = {'key1':'val1','key2':'val2','mountpoint':'/media/PIHU_DATA2', 'key5':'val5'}
#dAgainst = {'key2':'val2','key1':'val1','mountpoint':'/media/PIHU_DATA2', 'key5':'val5'}



shared_items = set(dTest1.items()) & set(dAgainst.items())
print " OK {0} items in dTest, {1} matches. Test: {2}".format( len(dTest1), len(shared_items), test_match(dTest1,dAgainst) )

shared_items = set(dTest2.items()) & set(dAgainst.items())
print " OK {0} items in dTest, {1} matches. Test: {2}".format( len(dTest2), len(shared_items), test_match(dTest2,dAgainst) )

shared_items = set(dTest3.items()) & set(dAgainst.items())
print "NOK {0} items in dTest, {1} matches. Test: {2}".format( len(dTest3), len(shared_items), test_match(dTest3,dAgainst) )

shared_items = set(dTest4.items()) & set(dAgainst.items())
print "NOK {0} items in dTest, {1} matches. Test: {2}".format( len(dTest4), len(shared_items), test_match(dTest4,dAgainst) )

shared_items = set(dTest5.items()) & set(dAgainst.items())
print "NOK {0} items in dTest, {1} matches. Test: {2}".format( len(dTest5), len(shared_items), test_match(dTest5,dAgainst) )

shared_items = set(dTest6.items()) & set(dAgainst.items())
print "NOK {0} items in dTest, {1} matches. Test: {2}".format( len(dTest6), len(shared_items), test_match(dTest6,dAgainst) )

shared_items = set(dTest7.items()) & set(dAgainst.items())
print " OK {0} items in dTest, {1} matches. Test: {2}".format( len(dTest7), len(shared_items), test_match(dTest7,dAgainst) )