# Source Plugins

Source plugins are plugins that represent a source.
A source plugin is simply a Python class that fulfills a number of pre-defined source-related functions, such as next track.

## Concepts

An audio signal source a.k.a. "Source" is a provider of music. Examples of these are FM radio, MPD or SoundCloud.
Every source is defined by a Source Plugin. Source plugins are Python classes.

Every source has 1 or more subsources. Subsources are cycled through using a source button or source selector.
The decision to divide a source into subsources must therefore not taken too lightly.

Subsources should be used to divide groups of music sources under a common source.
For example, The stations of an FM radio source could be configured as subsources. This however, would require the user to cycle through a lot of sources to get to a different type of source and is very counter-intuitive. To select radio stations it's more intuitive to use "seek" and "next" buttons.
A media source however, could create a subsource for every connected drive.

In some cases you want to have multiple sources for a single music provider, as is the case with MPD.
For these cases we create a base Plugin Class to base several plugin sources on.
For example, "Local Music", "Media" and "Internet Radio" are all based on MPD, but have their own source plugin.

Source plugins are implemented using YAPSY, a lightweight plugin system.


## Architecture

A "source" consists of three files:

 - Python class module
 - Yapsy configuration
 - JSON configuration

Sources are loaded and managed by the Source Controller module.


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

Example:
```
{
	"displayname": "FM Radio",
	"enabled": true
}
```

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