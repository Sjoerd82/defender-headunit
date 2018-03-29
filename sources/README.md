# Source Plugins

Source plugins are plugins that represent an audio (music) source.


## Concepts

An audio signal source a.k.a. "Source" is a provider of music. Examples of these are FM radio, MPD or SoundCloud.
Every source is defined by a Source Plugin. Source plugins are Python classes.

### Subsources
Every source has 1 or more subsources. Subsources are cycled through using a source button or source selector.

 - Subsources should be used to divide groups of music sources under a common source.
 - Subsources can be added and removed "on-the-fly".

*Example:* The stations of an FM radio source could be configured as subsources. This however, would require the user to cycle through a lot of sources to get to a different type of source and is very counter-intuitive. To select radio stations it's more intuitive to use "seek" and "next" buttons.
A media source however, could create a subsource for every connected drive.

In some cases you want to have multiple sources for a single music provider, as is the case with MPD.
For these cases we create a base Plugin Class to base several plugin sources on.

*Example:* "Local Music", "Media" and "Internet Radio" are all based on MPD, but have their own source plugin.


### Plugin System

Source plugins are implemented using [Yapsy](#Yapsy), a lightweight plugin system.


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

class MySourceClass(...,IPlugin)
```

The .yapsy file is required by Yapsy's plugin manager and looks like:

```
[Core]
Name = fm
Module = fm

[Documentation]
Author = Sjoerd Venema
Version = 1.0.0
Description = FM radio
```

The name and module must match your Python filename.
That's all.

Links:
[http://yapsy.sourceforge.net/](http://yapsy.sourceforge.net/)
[http://yapsy.readthedocs.io/en/latest/index.html](http://yapsy.readthedocs.io/en/latest/index.html)
[https://github.com/tibonihoo/yapsy](https://github.com/tibonihoo/yapsy)

## JSON configuration

The JSON configuration contains all kinds of static *read-only* details.
The source can be further configured and customized in the read-write file configuration.json in the `source_config` section.

Fields:
Field | Datatype | Description | Mandatory?
--- | --- | ---
`displayname` | string | Name displayed in displays | no (defaults to module name)
`enabled` | bool | Enable/Disable the source | no (default: True)
`order` | int | Used for sorting the position when cycling the source | no (default: 0)
`depNetwork` | bool | Depends on having a (wifi) network | no (default: False)
`controls` | dict | List of supported controls | no
`subsources` | list | List of subsources | yes*

*if not provided, will call XXX()

Subsources:
name

Added by system:
available	bool
subsources	list

Example (fm.json): 
```
{
	"displayname": "FM Radio",
	"enabled": true,
	"subsources": [ {"name":"fm"} ]
}
```

### configuration.json

Existing or new fields can be configured under the source_config section. Use the plugin's module name to match.

Example:
```
	, "source_config": {
		  "locmus": { "subsources" : 
		            [ { "label": "PD1", "musicdir": "/media/PIHU_DATA", "musicdir_mpd": "PIHU_DATA"}
		            , { "label": "PD2", "musicdir": "/media/PIHU_DATA2", "musicdir_mpd": "PIHU_DATA2" } ] }
		, "smb":    [ { "label": "Music1", "mountpoint": "/media/PIHU_SMB/music", "musicdir_mpd": "PIHU_SMB/music" } ]
		, "fm": {"frq_lo": 80}
	}
```


## Minimal Plugin class

A minimal working (but useless) source plugin would look like:

```
from yapsy.IPlugin import IPlugin
from modules.source_plugin import SourcePlugin

class sourceClass(SourcePlugin,IPlugin):

	def __init__(self):
		self.name = None
		
	def init(self, plugin_name):
		self.name = plugin_name	
		
	def check(self):
		return True

```

## Implementable methods

### init()

Called when Source Controller activates the plugin.

### post_add(sourceconfig)

Called after adding the plugin.
This is a good place to populate any subsources dynamically.
sourceconfig contains the complete configuration, including the parts from the main configuration (configuration.json).

### check()


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