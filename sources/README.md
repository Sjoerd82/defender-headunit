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
--- | --- | --- | ---
`enabled` | bool | Enable/Disable the source | no (default: True)
`order` | int | Used for sorting the position when cycling the source | no (default: 0)
`depNetwork` | bool | Depends on having a (wifi) network | no (default: False)
`controls` | dict | List of supported controls | no
`subsources` | list | List of subsources | no*

*if omitted must be added by post_add() or check() functions.

Subsources:
name

Field | Datatype | Description | Mandatory?
--- | --- | --- | ---
`displayname` | string | Name displayed in displays | no (defaults to module name)
`order` | int | Used for sorting the position when cycling the source | no (default: 0)


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

### Starting up

Three functions are called when launching the Source Controller.
 1. init()
 2. post_add()
 3. check()

None of these methods are required be implemented.
`check()` may also periodically be called after launch by the SourceController.

#### init()

Called when Source Controller activates the plugin.

Arguments: `Plugin Name, Logger`
Return: `True`, if all is OK
`False` if not (source will not be activated)

#### post_add(sourceconfig)

Called after adding the plugin.

Arguments: sourceconfig
Return: Currently not being checked

This is a good place to populate any subsources dynamically.
sourceconfig contains the complete configuration, including the parts from the main configuration (configuration.json).


#### check()

Called for every source, at the end of the setup phase. This function checks if the source is ready.

```
def check(self, sourceCtrl):
```

Arguments: sourceCtrl, subindex
Return: None (if no subsources), List of dicts

This function must return a list with dicts for all or only the changed sources.
If a subindex is given only the subsource with that index need to be checked.

```
avchg = []
avchg_subsource = {}
avchg_subsource['index'] = 1
avchg_subsource['subindex'] = 1
avchg_subsource['availability'] = True

avchg.append(avchg_subsource)
return avchg

```

If check() is not implemented this will make the source available.

### Source control

All methods are called by the SourceController with the arguments SrcCtrl (reference to SourceController), index and subindex.
Additional arguments may be passed by hu_src_ctrl.py

Method | Description | Extra parameters
--- | --- | ---
`play` | Start playback | `position`
`stop` | Stop playback | 
`next` | Next track | `cnt` (number of tracks to advance)
`prev` | Prev track | `cnt` (number of tracks to go back)
`pause` | Pause | mode
`random` | Set random mode |  mode
`seekfwd` | Seek | 
`seekrev` | Seek | 
`update` | Update (MPD) | location
`get_state` | Get states (playing,random,repeat) | -
`get_details` | Get all details | -

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