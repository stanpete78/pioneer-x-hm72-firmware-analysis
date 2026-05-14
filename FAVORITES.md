# X-HM72 Favorites — Direct Edit

Pioneer's vTuner backend is dead. Stock favorites resolve through it and all
fall back to the last cached stream. Workaround: write favorites directly into
the device's SDS using the FritzBox DLNA proxy as the resolver.

## SDS Layout

Port 9000 (unauth) — `cne/Favourites/`:

```
Entry0..Entry99       100 slots
  next                int — next slot, -1 = end of list
  Entry               str — SongDescriptor XML, empty = unused
FirstContent          int — head of content list
FirstFree             int — head of free list
NumberOfEntries       int — content + free combined
```

## Working Schema (upnp via FritzBox)

```xml
<SongDescriptor ActiveAudioResource="0"
                StationTitle="Soma Groove Salad"
                SourceContentBrowser="upnp"
                Artist="Soma Groove Salad"
                LiveStream="">
  <SongResource Url="http://192.168.1.1:49200/ST/AUDIO/DLNA-1-0/ice1.somafm.com/groovesalad-256-mp3"
                Mime="mp3" Bps="256000" Fs="44100" BitsPerSample="16" Channels="2"
                NoTimeSeek="" DLNA.ORG_OP="01"
                DLNA.ORG_FLAGS="01700000000000000000000000000000"/>
</SongDescriptor>
```

URL pattern: `http://<fritzbox>:49200/ST/AUDIO/DLNA-1-0/<host>/<path>`. Station
must already be configured under FritzBox → Heimnetz → Mediaserver →
Internetradio.

`SourceContentBrowser="RadioNative"` requires a live vTuner — broken, don't use.

## Discover URL via UPnP

```bash
SOAP='<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><u:Browse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1"><ObjectID>0</ObjectID><BrowseFlag>BrowseDirectChildren</BrowseFlag><Filter>*</Filter><StartingIndex>0</StartingIndex><RequestedCount>50</RequestedCount><SortCriteria></SortCriteria></u:Browse></s:Body></s:Envelope>'
curl -s -H 'Content-Type: text/xml; charset="utf-8"' \
     -H 'SOAPACTION: "urn:schemas-upnp-org:service:ContentDirectory:1#Browse"' \
     --data-binary "$SOAP" \
     http://192.168.1.1:49000/MediaServer/ContentDirectory/Control
```

Replace `<ObjectID>0</ObjectID>` with the Internetradio container ID, then with
the station container ID. The `<res protocolInfo="...">URL</res>` in the final
response is the proxy URL.

## Tools

| Tool | Purpose |
|------|---------|
| `tools/sds.py` | SDS shell wrapper (handles autocomplete echo) |
| `tools/p8102.py` | Port 8102 live tester |
| `tools/fav_backup.py` | Trace + JSON-backup the linked list |
| `tools/fav_add.py` | Add favorite (writes upnp XML, fixes pointers, reloads parser) |

## Add a Favorite

```bash
python3 tools/fav_backup.py                              # 1. snapshot
python3 tools/fav_add.py "Soma Groove Salad" \           # 2. write + reload
  "http://192.168.1.1:49200/ST/AUDIO/DLNA-1-0/ice1.somafm.com/groovesalad-256-mp3" \
  256000
python3 tools/p8102.py --wait 2 '?GAP'                   # 3. verify flag=102
```

Manual SDS sequence (when scripting fails):

```
get cne/Favourites/FirstContent       # current head, e.g. 9
get cne/Favourites/FirstFree          # free head, e.g. 3
get cne/Favourites/Entry3/next        # next free, e.g. 4

set cne/Favourites/Entry3/Entry '<SongDescriptor ...upnp.../>'
set cne/Favourites/Entry3/next 9      # new slot points to old head
set cne/Favourites/FirstFree 4        # advance free list
set cne/Favourites/FirstContent 3     # promote new slot to head
```

`set` parses values whitespace-delimited; wrap XML in single quotes — inner `"`
attributes do not need escaping.

## Parser Reload

After a write, the entry shows flag `100` (unknown type) and is not playable.
Cycle inputs `44FN → 45FN` (or power-cycle) to force re-parse — flag becomes
`102` (playable leaf). `fav_add.py` does this automatically.

## Delete a Favorite

Via port 8102 (need to be on input 45, row N 1-based):

```
NNNNNFCB              # → FCBNNNNN1 = ok, FCBNNNNN0 = rejected
```

Or via SDS — unlink from content list, link into free list:

```
set cne/Favourites/Entry<prev>/next <Entry<N>/next>
set cne/Favourites/Entry<N>/Entry ''
set cne/Favourites/Entry<N>/next <FirstFree>
set cne/Favourites/FirstFree <N>
```

## Notes

- Port 9000 accepts one connection at a time. A hung session blocks all further
  access — reboot if stuck.
- `NumberOfEntries` counts content + free; doesn't change when reusing a free slot.
- The UI total in `GDP...` appears to cap at 12 visible, but all linked entries
  render and play.
- Always run `fav_backup.py` before edits.
