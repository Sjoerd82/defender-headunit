# Source Plugins

Source plugins are plugins that represent an audio (music) source.

- [Concepts](#Concepts)
- [Architecture](#Architecture)
- [Yapsy, a plugin manager](#Yapsy-a-plugin-manager)
- [Configuration](#Configuration)
- [Resume playback](#Resume-playback)
- [Implementable methods](#Implementable-methods)
- [Minimal implementation example](#Minimal-implementation-example)

## Concepts

### Sources
An audio signal source a.k.a. "Source" is a provider of music, for example: FM radio, MPD or SoundCloud.
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


### Plugin manager

Source plugins are implemented using [Yapsy](#Yapsy), a lightweight plugin system.


## Architecture

A "source" consists of three files:

 - Python class module
 - Yapsy configuration
 - JSON configuration

Sources are loaded and managed by the Source Controller module.


## Yapsy, a plugin manager

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
- [http://yapsy.sourceforge.net/](http://yapsy.sourceforge.net/)
- [http://yapsy.readthedocs.io/en/latest/index.html](http://yapsy.readthedocs.io/en/latest/index.html)
- [https://github.com/tibonihoo/yapsy](https://github.com/tibonihoo/yapsy)

## Configuration

The JSON configuration contains all kinds of static *read-only* details.
The source can be further configured and customized in the read-write file configuration.json in the `source_config` section.
This configuration file will be merged into the Yapsy config file, in due time...

Fields:

Field | Datatype | Description | Mandatory? | Default value, if not provided
--- | --- | --- | --- | ---
`displayname` | string | Name of source, for displaying purposes | No | plugin name
`enabled` | bool | Enable/Disable the source | no | True
`order` | int | Used for sorting the position when cycling the source | no | 99
`category` | string | ... | No | default
`depNetwork` | bool | Depends on having a (wifi) network | no | False
`controls` | dict | List of supported controls | no? | ???

Plugin Categories: udisks, lan, internet, output, ...

Example (fm.json): 
```
{
	"displayname": "FM Radio",
	"enabled": true,
}
```

Added by system:
available	bool
subsources	list


### configuration.json

The plugin's configurable items can be added in the main configuration.json under section `source_config`.
Configurable items must be grouped under the plugin name, like so:
```
	, "source_config": {
		  "fm": { ... }
	}
```
Replace the dots with your configuration items. Please avoid the use of the following keys: "name", "subsources". Other predefined field may be used to override values created by the system, such as "displayname", "order"

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

## Resume playback

Resuming playback of the audio source at the position where the user left off is facilitated through saving key details to file.
The save location of these files is configured in the main configuration, under `directories.resume`.

The resume files are saved whenever an event is received by the SourceController that (may) change required resume data. These are events such as `/events/player/state`, `/events/player/track`, `/events/player/elapsed`, `/events/source/active`, `/events/system/shutdown`, `/events/system/reboot`.

### Resume files
There is one resume file written containing the source and there are resume files written for every subsource.

#### `resume`
The resume file containing the source to be resumed is called `resume`. It contains the names of the source and subsource to be resumed. The format is `<source name>:<subsource key>`
There is one source per line, the first line is the first source to be attempted to be resumed. Optionally, fallback sources may be listed on the successive lines.
To play any available subsource, the key may be substituted with a '*', or with a number indicating the subsource index. The latter may not reliably identify the exact same subsource, depending on its configuration.

For example:
```
media:f925ee5a
media:*
fm:0
*.*
```
Will attempt to resume playback of the media source identified by f925ee5a, if it's not available, will continue to play any available subsource of the media source. In case this fails, will attempt to play the first subsource (subsource 0) of the FM source. If this fails too, will continue to play any source that's available*.
(Sub)Sources may be exempt from automatic playback, by setting the `no_fallback` to true (not implemented). This may be useful to prevent for example audiobooks to be accidentally resumed.

PLEASE NOTE: Current implementation only writes the current source and no fallback sources...yet

#### Subsource resume files

### Position updates
If the hardware permits, the postition within a track may be saved every second. This may, however, put a strain on the system and/or SD card. The update frequency can be configured through `preferences.resume_position_update`. By default this value will be set to '0', meaning no updates.
When set to 0, position updates will be saved when user switches source or when shutting down. Depending on the hardware setup, the latter event might not always be caught.

### Implementation
The QuickPlay init script takes the first line from `resume` to load services in an optimized order for the specified source.
It will call the SourceController with the `--resume` switch


## Implementable methods

Method | Called | Short description | Arguments | super()?
--- | --- | --- | --- | ---
`__init__` | Creating of the plugin | Class initialization | None | Always
`on_init` | At loading the plugin | Source Initialization | ? | Always
`on_add` | After registering with SourceController | Called after adding the source | ? | No
`on_activate` | When subsource becomes active | | subindex | Optional
`on_event` | When an event occurs | | subindex | Optional
`check_availability` | After post-add, and accidentally during runtime | Determine availability of subsource(s) | No, defaults to available if not implemented | No
`add_subsource` | Creating sub-sources on the fly | On certain events | No | No
`discover` | | | |

Only __init__() is required.

Three functions are called when launching the Source Controller.
 1. init()
 2. post_add()
 3. check()

`check()` may also periodically be called after launch by the SourceController.

#### on_init()

Called when Source Controller activates the plugin. Use the super() function to call this method from the derived class where it sets up a number of variables. After the super() you may add code that must run once to initialize the source. Simply don't implement this method if there is no need for any initializion.

```
def on_init(self, plugin_name, sourceCtrl, logger):
```

Arguments: `Plugin Name, sourceCtrl, Logger`
Return: `True`, if all is OK
`False` if not (source will not be activated)

#### on_add()

Called after the source plugin is added and has received an index. This happens soon after on_init(), but now it has an index, so methods from the SourceController class can be called.

This is a good moment to add subsources. The method is called with its configuration as a dictionary as a parameter.

```
def on_add(self, sourceconfig):
```

Arguments: `sourceconfig`
Return: Nothing (Currently not being checked)

This is a good place to populate any subsources dynamically.
sourceconfig contains the complete configuration, including the parts from the main configuration (configuration.json).

#### on_activate()
...

#### on_event()

The Source Controller may call do_event() when certain events take place.
At this moment:
sc_sources.do_event('network',path,payload)
sc_sources.do_event('udisks',path,payload)	# do_event() executes the 'udisks' event
.... incomplete ....
to be changed to reflect MQ /events/-messages

#### check_availability()

Called for every source, at the end of the setup phase. This function checks the subsource(s) and returns availability.

```
def check_availability( self, subindex=None, onlychanges=True ):
```
Called by hu_source.check()

Arguments: `subindex` (optional), onlychanges (optional)
Return: None (if no subsources), List of dicts

This function must return a list with dicts for all or only the changed sources (depending on onlychanges parameter).
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

#### add_subsource()

Implementing this function makes it possible to add subsources on the fly.
Useful when the subsources are dynamic (for example: removable media).

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
