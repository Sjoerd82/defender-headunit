A "source" consists of two files:

 - Python script
 - JSON configuration

Both must have the same name.

JSON configuration
------------------

Fields:
name		string
displayname	string
order		int
type		string	<- not used atm
depNetwork	bool
controls	dict
sourceInit	list, first field reserved for an object pointing to the Python script (will be added by the system)
sourceCheck	"
sourcePlay	"
sourceStop	"
template	bool
defaultconfig	list

Added by system:
available	bool
subsources	list
