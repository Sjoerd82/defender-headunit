
# Source control

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
