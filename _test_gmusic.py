# -*- coding: utf-8 -*-
#from gmusicapi import Api
from gmusicapi import Mobileclient

gm_lib_pos = 0
library = None

def ask_for_credentials():
	"""Make an instance of the api and attempts to login with it.
	Return the authenticated api.
	"""
	api = Mobileclient()
	logged_in = False
	#attempts = 0
	#while not logged_in and attempts < 3:
	email = 'srg.venema@gmail.com'	#raw_input("Email: ")
	password = 'LuxMundi777'		#getpass()
	logged_in = api.login(email, password, Mobileclient.FROM_MAC_ADDRESS)
	#attempts += 1
	return api

def gm_init():
	global library
	
    api = ask_for_credentials()
    if not api.is_authenticated():
        print "Sorry, those credentials weren't accepted."
        return
    print "Successfully logged in."
    print
    #Get all of the users songs.
    #library is a big list of dictionaries, each of which contains a single song.
    print "Loading library...",
    library = api.get_all_songs()
    print "done."
    print len(library), "tracks detected."
    print


def play_next():
	
	global gm_lib_pos
	gm_lib_pos+=1
	
def play():
	
	
def demonstration():
    #Show some info about a song. There is no guaranteed order;
    # this is essentially a random song.	
    first_song = library[0]
    print "The first song I see is '{}' by '{}'.".format(
        first_song["title"],
        first_song["artist"])
    #We're going to create a new playlist and add a song to it.
    #Songs are uniquely identified by 'song ids', so let's get the id:
    song_id = first_song["id"]
    print (api.get_stream_url(song_id))
    #It's good practice to logout when finished.
    api.logout()
    print "All done!"

if __name__ == '__main__':
	gm_init()
	demonstration()