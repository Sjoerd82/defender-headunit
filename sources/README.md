# Source Plugins

Source plugins are plugins that represent a source.
A source plugin is simply a Python class that fulfills a number of pre-defined source-related functions, such as next track.

## Architecture

A "source" consists of three files:

 - Python script
 - Yapsy configuration
 - JSON configuration

The 

## Concepts

Sub-Source	Source switchable via the "SOURCE" button. Think multiple USB drives.
		Not suitable for eg. FM stations, which should be swichable via the "NEXT" or "SEEK" button.

 
## Yapsy

Yapsy is a lightweight plugin system.

A source plugin derives its class from Yapsy's IPlugin, which provides an entry point.

```
from yapsy.IPlugin import IPlugin

class MySourceClass(IPlugin, ...
```

The .yapsy file is required by Yapsy's plugin manager and looks like:

```
[Core]
Name = fm
Module = fm

[Documentation]
Author = Sjoerd Venema
Version = 0.1
Description = FM radio
```

The name and module must match your Python filename.
That's all.

Links:
{http://yapsy.sourceforge.net/}
{http://yapsy.readthedocs.io/en/latest/index.html}
{https://github.com/tibonihoo/yapsy}

## JSON configuration

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


## Minimal Plugin class

```
from yapsy.IPlugin import IPlugin
from modules.hu_utils import *
from modules.source_plugin import SourcePlugin

class sourceClass(IPlugin,SourcePlugin):

	def __init__(self):
		self.name = None
		
	def init(self, plugin_name):
		self.name = plugin_name	
		
	def check(self):
		return True

```

## Implementable methods



Python script
----------------

Functions:
 __init__()	Stuff that needs to run once, at first loading of the class
 init()		Stuff that needs to run once, at functional loading of the source
		Executed when the source is added ( via: loadSourcePlugins->add_a_source->Source.sourceInit(indexAdded) )
 check()		Determine availability
		Parameters:
			sourceCtrl	Required; Object; Reference to Sources
			subSourceIx	Optional; int	; If present, check Sub-Source instead

 __del__()	Stuff that needs to run when the source gets discarded (close connections, etc.)