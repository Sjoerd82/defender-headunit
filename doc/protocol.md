# MQ protocol

## Message format:

### Sending messages:

Format: `<path> <command> [return path]`

The [return path] is optional and can be used for filtering.
Examples:

`/source/subsource GET:0,4`
`/source/subsource GET:0,4 /flask/582`

### Sending data:

Data is send over the MQ with root path "/data"

Format: `/data/<path> <data>`

Examples:
`/data/source/subsource {data}`
`/data/flask/582 {data}`

In this example "flask" is the unique* application identifier.
The flask application can setup a subscription for "/data/flask/", the number can be an iterator to route back the received data to it's intended target.

# Data
{data}:

{
 "retval":200,
 "data": {}		<-- optional
}


{bool}
{source}
{subsource}


{source}:
Fields are partly defined by the source's .json file. The following fields are mandatory and are always be present:
 - name
 - displayname
 - order
 - controls
 - template

The following fields are added by the Source Controller, and are thus also always available:
 - available

If the source has subsources, then these are included in the "subsources" key.

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

{subsource}:
Fields are partly defined by the source's python code (add subsource function). The following fields are mandatory and are always present:
 - displayname
 - order

The following fields are added by the Source Controller, and are thus also always available:
 - available

Example:
{ "displayname": "/mnt/FlashDrive",
  "order": 1,
  "available": true
}
