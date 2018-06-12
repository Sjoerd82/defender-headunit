# MQ protocol

## Message format:

### Sending messages:

Format: `<path>[+return path]|[origin]|<command>[:arg1,arg2,argn]`

The [return path] is optional and can be used for filtering.
Examples:

`/source/subsource GET:0,4`
`/source/subsource GET:0,4 /flask/582`

The [origin] can optionally be used to identify the sending script.
This is particularily useful to ignore ones own messages.

### Sending data:

Data is send over the MQ with root path "/data"

Format: `/data/<path> <data>`

Examples:
`/data/source/subsource {data}`
`/data/flask/582 {data}`

In this example "flask" is the unique* application identifier.
The flask application can setup a subscription for "/data/flask/", the number can be an iterator to route back the received data to it's intended target.

# Modes

Modes can be used as global boolean states, a mode can thus either be True or False.
Modes may be grouped in mode sets. Per mode set only one mode may be True at a time.

# Data

## {data}:

Field | Value
--- | ---
`retval` | Return Code
`data` | Payload (can be anything, string, dict, etc.)

Example:
```
{
 "retval":200,
 "data": { payload* }
}
```

Payloads:

Structure | Value
--- | ---
`{int}` | [int](#int)
{bool} | [bool](#bool)
{source} | [source](#source)
{subsource} | [subsource](#subsource)
{state} | [state](#state)
{track} | [track](#track)
{volume} | [volume](#volume)
{level} | [level](#level)
{equalizer} | [equalizer](#equalizer)
{level} | [level](#level)
{device} | [device](#device)
{network} | [network](#network)
{mode} | [mode](#mode)
{timer} | [timer](#timer)
{available} | [available](#available)

### {int}:
Integer value

Field | Value
--- | ---
`int` | integer value

### {bool}:
Boolean value

Field | Value
--- | ---
`boolean` | `true` or `false`

### {source}:
Fields are partly defined by the source's .json file. The following fields are mandatory and are always be present:

Field | Value
--- | ---
`name` | Source identifying name (fm, bt, locmus, media, line)
`displayname` | Name for display purposes
`order` | Used to order the sources by
`controls` | List of available controls (used?)
`template` | Boolean; If true, this source can have subsources.

The following fields are added by the Source Controller, and are thus also always available:

Field | Value
--- | ---
`available` | Boolean; If true, the source is available

Optional fields:

Field | Value
--- | ---
`depNetwork` | Is dependent on WiFi/Internet
`random` | List of available random modes

If the source has subsources, then these are included in the "subsources" key.
```
Example:
{ "name": "media",
  "displayname": "Removeable Media",
  "order": 1,
  "type": "mpd",
  "depNetwork": false,
  "controls": {"ffwd": true, "rwnd": true, "prev": true, "next": true, "dirnext": true},
  "random": ["on","off"],
  "template": true,
  "subsources": [{ ... }]
  "subsource_key": ["uuid","label"],
  "filename_save": ["uuid","label"]
}
```

### {subsource}:
Fields are partly defined by the source's python code (add subsource function). The following fields are mandatory and are always present:

Field | Value
--- | ---
`displayname` | Name for display purposes
`order` | Used to order the sources by

The following fields are added by the Source Controller, and are thus also always available:

Field | Value
--- | ---
`available` | Boolean; If true, the source is available

Example:
```
{ "displayname": "/mnt/FlashDrive",
  "order": 1,
  "available": true
}
```

### {state}
Details about the player state. Only the state field is mandatory.

Field | Value
--- | ---
`state` | "play", "stop" or "paused"
`random` | "on", "off", "..."
`repeat` | "on", "off"
`time` | elapsed time of current track (optional)
`id` | ID of track being played, for MPD sources this is the songid (optional)
`filename` | name of file being played (optional)

### {track}
Details about what's playing. Only display is mandatory.
Which fields are present strongly depends on the type of source and the availability of metadata.
Sources are free to add their own tags. The ones mentioned below are the standardized.

Field | Value
--- | ---
`display` | Formatted string
`source` | Source name
`rds` | RDS information (FM)
`artist` | Artist name
`composer` | The artist who composed the song
`performer` | The artist who performed the song
`album` | Album name
`albumartist` | On multi-artist albums, this is the artist name which shall be used for the whole album
`title` | Song title
`length` | Track length (ms)
`elapsed` | Elapsed time (ms) --?
`track` | Decimal track number within the album
`disc` | The decimal disc number in a multi-disc album.
`folder` | The folder name on the media
`genre` | Music genre, multiple genre's might be delimited by semicolon, though this is not really standardized
`date` | The song's release date, may be only the year part (most often), but could be a full data (format?)

### {volume}
Volume level. Todo: mute?

Field | Value
--- | ---
`system` | "alsa", "ecasound", "jack", "pulseaudio", "mpd"
`device` | Ex. "hw:0,0", "default-sink", etc.
`simple_vol` | Temporary shortcut for ecasound pre-amp
`channels` | `[{level}]` list of levels
`muted` | Useful?

#### {level}

Field | Value
--- | ---
`channel` | Channel number, zero-based
`level` | 0-100 (?)

### {equalizer}
TODO

### {pos_folder}

Field | Value
--- | ---

Example:
```
{
    "position": "33"
    "folder": "/MyMusic/Foo Fighters - Walk"
}
```

### {device}
Details about a (removable) device. Only devicefile is mandatory, however, most fields will usually be populated.

Field | Value
--- | ---
`device` | Name of de Linux device
`label` | Partition label
`uuid` | Partition UUID
`mountpoint` | Mountpoint

Example:
```
{
    "device": "/dev/sda1",
    "label": "Summer_Music",
    "uuid": "f9",
    "mountpoint": "/media/Summer_Music"
}
```

### {network}

Network interface. There is not neccessarily a direct correlation between internet and interface.
The helper script checks internet availability, not persé for the newly up/downed interface.

Perhaps leave out the interface????

Example:
```
{
	"state": "up",
    "interface": "wlan0",
	"internet": "true"
}
```

Example:
```
{
	"state": "down",
    "interface": "eth0",
	"internet": "true"
}
```



### {mode}

Example:
```
{
    "mode": "random-genre"
}
```

### {timer}

Field | Value
--- | ---
`timer_sec` | Time in seconds

Example:
```
{
    "timer_sec": "60"
}
```

### {available}

Field | Value
--- | ---
`index` | Source index
`subindex` | Sub-Source index, will be ommited if not a sub-source
`availability` | True|False

Example:
```
{
  "index":1,
  "sub_index":0,
  "available":"True"
}
```