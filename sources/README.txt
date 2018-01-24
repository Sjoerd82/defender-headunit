A "source" consists of two files:

 - Python script
 - JSON configuration

Both must have the same name.

Concepts
------------------

Sub-Source	Source switchable via the "SOURCE" button. Think multiple USB drives.
		Not suitable for eg. FM stations, which should be swichable via the "NEXT" or "SEEK" button.

JSON configuration
------------------

The JSON configuration contains all kinds of *read-only* details.
The source can be further configured in the read-write file configuration.json.

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

Added by system:
available	bool
subsources	list

Python script
----------------

Init-function
Stuff that needs to run once

