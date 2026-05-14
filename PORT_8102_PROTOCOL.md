# Pioneer X-HM72 — Port 8102: Pioneer Tunneling Protocol

## Overview

Port 8102 is Pioneer's **PioTunnelingControlService** — a TCP tunnel that forwards commands between the network and the Pioneer host CPU (via SPI). This is the protocol used by the official **Pioneer Remote App** for iOS/Android.

Config in firmware binary:
```
[PioTunnelingControlService Enabled 1 MultipleClientPort 0 Port1 8102 Port2 0 Port3 0 EnabledQueryExAPI 0]
```

UPnP advertisement (in device description XML):
```xml
<av:X_ipRemoteTcpPort xmlns:av="http://www.pioneerelectronics.com/xmlns/av">8102</av:X_ipRemoteTcpPort>
<av:X_ipRemoteReady xmlns:av="http://www.pioneerelectronics.com/xmlns/av">1</av:X_ipRemoteReady>
```

---

## Protocol Format

Plain text, **not** eISCP/Onkyo protocol:

```
Command:  <CMD>\r\n
Response: <RESPONSE>\r\n
```

No authentication, no handshake required. Connect and send immediately.

While a TCP connection is open the device:

1. Sends `R\r\n` ("ready") about every 30 seconds as a heartbeat.
   **Verified live** — observed at ~30s intervals on a persistent socket.
2. Pushes unsolicited state updates when something changes:
   - Volume change → `VOLnnn`
   - Input change → `FNnn`
   - Menu refresh → full `GBP/GCP/GDP/GEP` block (see GUI Menu Protocol)
   - Icon change on entering a menu-based source → `ICA0` or `ICA1`
3. A client must demultiplex: incoming lines are either replies to its last
   command OR unsolicited pushes. The protocol has no request IDs.

```python
import socket
s = socket.socket()
s.connect(('192.168.1.12', 8102))
s.send(b'?P\r\n')      # query power
print(s.recv(64))       # b'PWR0\r\n'
```

---

## Live Device State (measured)

```
PWR0   → Power: ON
VOL000 → Volume: 0
MUT1   → Mute: ON
FN52   → Input: LineIn2
```

---

## Command Reference

### Power
| Command | Response | Description |
|---------|----------|-------------|
| `?P` | `PWR0`/`PWR1` | Query power (0=on, 1=standby) |
| `PF` | — | Power On |
| `PO` | — | Power Standby (**caution**) |

### Volume
| Command | Response | Description |
|---------|----------|-------------|
| `?V` | `VOL000`–`VOL185` | Query volume (0–185) |
| `VU` | — | Volume Up — observed step size **+8** in one test, +1 in another; appears context-dependent |
| `VD` | — | Volume Down — symmetric to `VU` |

### Mute
| Command | Response | Description |
|---------|----------|-------------|
| `?M` | `MUT0`/`MUT1` | Query mute. `MUT0` = muted, `MUT1` = not muted |
| `MO` | — | Mute MAIN zone (turn mute ON) |
| `MF` | — | unMute MAIN zone (turn mute OFF) |

> Pioneer convention (per official RS-232C spec): the digit `0` denotes the
> "active/engaged" state of the named function. So `MUT0` = mute is engaged
> (audio silent), `MUT1` = mute is not engaged (audio playing). Likewise
> `PWR0` = device active, `PWR1` = device standby.
>
> Live test on X-HM72 confirmed the state-flag transitions match Pioneer's
> spec, but the **front-panel display does not show a MUTE indicator** when
> triggered via this protocol on this model — audio effect at the speaker
> output not independently verified.

### Input Function
| Command | Response | Description |
|---------|----------|-------------|
| `?F` | `FN##` | Query current input (see table below) |
| `##FN` | — | Set input to specific source (see table) |
| `FU` | — | Function Up — cycle to next input |
| `FD` | — | Function Down — cycle to previous input |

**Input Function Codes (verified live on X-HM72):**

| Code | Input | Verified | Notes |
|------|-------|----------|-------|
| `01FN` | Phono | ✅ switched | |
| `02FN` | CD | ✅ switched | |
| `17FN` | iPod | ✅ switched | Opens menu (`ICA0` + `GBP` block) |
| `38FN` | Internet Radio | ✅ switched | Opens menu — was mis-labelled "iPod/USB" before |
| `44FN` | Media Server (DLNA) | ✅ switched | Opens menu (Fritzbox, etc.) — was mis-labelled "AirPlay" before |
| `45FN` | Favorites (Internet Radio presets) | ✅ switched | Same content as 51/56 below — was mis-labelled "Spotify" before |
| `51FN` | Favorites alias | ✅ switched | Returns same menu as `45FN` |
| `52FN` | Line In | ✅ switched | |
| `56FN` | Favorites alias | ✅ switched | Returns same menu as `45FN` |
| `04FN` `05FN` `06FN` `10FN` `15FN` `19FN` `25FN` `33FN` `41FN` `46FN` `47FN` `48FN` `49FN` `50FN` | ❌ rejected | rejected | Listed in firmware but device silently ignores |

Test method: send `##FN`, wait 2.5s, drain pushes, query `?F`. The device pushes
`FNnn` on a successful switch and remains on the previous input if rejected.

**Input cycling:**

| Command | Function | Verified |
|---------|----------|----------|
| `FU` | Function Up — cycle to next input | not tested |
| `FD` | Function Down — cycle to previous input | not tested |

### Playback (PB commands)
Commands sent while in a playback source. Exact meaning depends on current input.

| Command | Likely Meaning |
|---------|----------------|
| `10PB` | Play |
| `11PB` | Pause |
| `12PB` | Stop |
| `13PB` | Skip Forward / Next |
| `14PB` | Skip Back / Prev |
| `15PB` | FF |
| `18PB` | Rewind |
| `20PB` | Menu/Home |
| `26PB` | Up |
| `27PB` | Down |
| `28PB` | Left |
| `29PB` | Right |
| `30PB` | Enter/OK |
| `31PB` | Return/Back |
| `32PB` | Shuffle |
| `36PB` | Repeat |
| `37PB` | Add to Favorites |
| `39PB` | ? |
| `40PB` | ? |
| `41PB` | ? |

### CD Player (CDP)
| Command | Meaning |
|---------|---------|
| `10CDP` | Play |
| `11CDP` | Pause |
| `12CDP` | Stop |
| `13CDP` | Skip |
| `20CDP` | ? |

### Network Services
| Command | Response | Description |
|---------|----------|-------------|
| `NSC` | `NSC\r\n` | Net Service Control (echo) |
| `NSK` | `NSK\r\n` | Net Service Key (echo) |
| `KOF` | — | Key Off |

### Display / Status

Commands marked ✅ verified responsive; — = empty response (may be unimplemented on HMx
or pure side-effect command).

| Command | Response | Verified | Description |
|---------|----------|----------|-------------|
| `?GIA` | — | — | Get display string (no response on HMx) |
| `?GIC` | `GIC000""` | ✅ | Get display info C |
| `?GAP` | — | — | Get something (no response on HMx) |
| `GFP` | — | — | Get FP (no response on HMx) |
| `GGP` | — | — | Get GP (no response on HMx) |
| `GHP` | — | — | Get HP (no response on HMx) |
| `?ICA` | `ICA0` | ✅ | Icon status |
| `FCA` | — | — | Function A (no response on HMx) |
| `FCB` | — | — | Function B (no response on HMx) |
| `PR` | — | — | Preset? (no response on HMx) |

### Device Info
| Command | Response | Verified | Description |
|---------|----------|----------|-------------|
| `?RGD` | `RGD<001><XC-HM72/SYXE8><E0>` | ✅ | Device ID / model info |
| `?RGF` | `RGF<64-char bitfield>` | ✅ | Remote feature capabilities |
| `?RGC` | — | — | Remote config? (no response on HMx) |

### GUI Menu Protocol (`?GAP` + `GBP`/`GCP`/`GDP`/`GEP`)

**Live-verified** on X-HM72. Active when device is in a menu-capable input
(iPod `17FN`, Internet Radio `38FN`, Media Server `44FN`, Favorites
`45/51/56FN`). Silent on inputs without a menu (LineIn `52FN`, Phono `01FN`,
CD `02FN`).

**Query the current screen:**
```
?GAP
```

Returns a 4-line block describing the entire visible menu state:

```
GBPnn                                    — count of GEP entries currently shown
GCPwwxy0z0"SCREEN_LABEL"                  — screen header (see fields below)
GDPaaaaabbbbbccccc                        — display range over total
GEPnnxxx"item label"                      — one per entry
```

Field meanings:

| Field | Meaning |
|-------|---------|
| `GBPnn` | `nn` = 2-digit count of currently-shown entries |
| `GCPwwxy0z0"label"` | `ww` = screen type (2 digits); `x` = list-update flag; `y` = top-menu-key-enabled; `z` = return-key-enabled. Label in quotes is the screen name |
| `GDPaaaaabbbbbccccc` | `aaaaa` = start index (5-digit), `bbbbb` = end index, `ccccc` = total count |
| `GEPnnxxx"label"` | `nn` = display-row position; `xxx` = entry flags (e.g. `101` = highlighted, `001` = unhighlighted, `102`/`002` indicate playable list items) |

**Live example — Internet Radio Favorites (`45FN`)**:
```
GBP08
GCP01100000000000000"Top Menu"
GDP000010000800013          ← items 1-8 of 13 total
GEP01102"Deutschlandfunk"   ← highlighted (suffix 102)
GEP02002"Deutschlandfunk Kultur"
GEP03002"Deutschlandfunk Nova"
GEP04002"SWR1 Baden-Wrttemberg"
GEP05002"SWR3"
GEP06002"DASDING 90.8"
GEP07002"181.fm - Christmas Mix"
GEP08002"181.fm - Christmas Classics"
```

**Navigation commands (verified):**

| Command | Function | Verified |
|---------|----------|----------|
| `NNNNNGHP` | Select & open list item at index NNNNN (5-digit zero-padded) | ✅ `00001GHP` opened Fritzbox sub-menu |
| `31PB` | Back / return to parent | ✅ navigated back from sub-menu to top |
| `30PB` | Enter / confirm | not tested |
| `NNNNNGGP` | Scroll to row NNNNN | not tested |

**Live example — drilling into a folder:**

Starting on `44FN` (Media Server):
```
?GAP        → GBP01 | GCP..."Top Menu" | GDP000010000100001 | GEP01101"Fritzbox"
00001GHP    → GBP06 | GCP..."Fritzbox"  | GDP000010000600006
              GEP01101"Musik"
              GEP02001"Bilder"
              GEP03001"Filme"
              GEP04001"Internetradio"
              GEP05001"Podcasts"
              GEP06001"Datei-Index"
31PB        → back to top menu (GBP01 | GEP01101"Fritzbox")
```

Note: `00001GHP` both *selects* and *opens* the item — it's not a separate
highlight/enter step. Use `NNNNNGGP` to just scroll without opening.

### Status / Station Query API (`?STA` – `?STP`)

A separate command table at firmware offset `0x00017158` defines a family of
16 status/state queries: `?STA`, `?STB`, `?STC`, `?STD`, `?STE`, `?STF`,
`?STG`, `?STH`, `?STI`, `?STJ`, `?STK`, `?STL`, `?STM`, `?STN`, `?STO`, `?STP`.

Each command has its own ~316-byte handler block. These were likely used by
the official remote app to read structured device state (currently playing
track, station metadata, browse list state, etc.) — exact semantics not yet
decoded. Not tested live to avoid disrupting playback.

---

## Verified Command Status (live test on XC-HM72, firmware 1.010)

> Command names and string format extracted from the firmware binary
> (constant pool at file offset `0x0015a3e0`). Command **semantics** follow
> Pioneer's published RS-232C protocol (cross-checked against the spec sheet
> at <https://blog.mikepoulson.com/2011/06/programmatically-controlling-pioneer.html>).
> The firmware does not contain documentation strings — semantics had to be
> inferred from Pioneer's external convention, then validated by live test.

| Status | Commands |
|--------|----------|
| ✅ Confirmed working with documented response | `?P`, `?V`, `?M`, `?F`, `?GIC`, `?ICA`, `?RGD`, `?RGF`, `NSC`, `NSK`, `?GAP` (in menu context) |
| ✅ Confirmed effective state change | `VU`, `VD` (volume display verified by user), `01FN`/`02FN`/`17FN`/`38FN`/`44FN`/`45FN`/`51FN`/`52FN`/`56FN` (input switches with `FNnn` push confirmation), `NNNNNGHP` select-and-open, `31PB` back |
| ⚠️ State toggles but display unchanged | `MF`, `MO` (`?M` flips between MUT0/MUT1 as expected, but front panel shows no MUTE indicator — audio effect unverified) |
| ❓ No response on HMx | `?RGC`, `?GIA`, `?GAP` outside menu, `GFP`, `GGP`, `GHP` bare, `FCA`, `FCB`, `PR`, `?MUT` long form (gets `R` ACK only), `?FL`/`?PWR`/`?VOL`/`?FN` long forms, `?L`/`?S`/`?R`/`?AST`, `?STA`–`?STP` family (only `?STH` returns `R`) |
| ❌ Rejected (FN codes not implemented on HMx) | `04FN`, `05FN`, `06FN`, `10FN`, `15FN`, `19FN`, `25FN`, `33FN`, `41FN`, `46FN`, `47FN`, `48FN`, `49FN`, `50FN` |
| ⏭️ Not tested | `PF`, `PO`, all `PB` (except `31PB` verified), all `CDP`, `FU`/`FD`, `NNNNNGGP` scroll, `30PB` enter |

---

## RGD Response Format

```
RGD<001><XC-HM72/SYXE8><E0>
     │    │              └── Capability byte (0xE0 = 11100000)
     │    └── Model/Serial: "XC-HM72" model, "SYXE8" variant/serial prefix
     └── Zone/version: 001
```

---

## RGF Capability Bitfield

```
RGF0110000000000000020000000000000000000010000011110001100011110000
    ││                │                   │     ││││  ││  ││││
    │└── bit 1: set   │                   │     ││││  ││  └┴┴┴── bits 56-59
    └─── bit 0: 0     └── bit 17: value=2 │     │││└──┴┴── bits 44-47
                                           └─────┴┴┴── bits 38, 44-47
```

Active bit positions: 1, 2, 17, 38, 44, 45, 46, 47, 51, 52, 56, 57, 58, 59

Likely mapping (Pioneer proprietary, not fully decoded):
- Bits 1-2: Volume + Mute control
- Bit 17: value=2 (extended zone?)
- Bit 38: iPod/USB support
- Bits 44-47: AirPlay, Spotify, DAB, BT Audio support
- Bits 51-52: Input types
- Bits 56-59: Network service flags

---

## Python Control Example

For one-shot queries (single connection, single command):

```python
import socket, time

def pioneer_cmd(host, cmd, port=8102):
    s = socket.socket()
    s.settimeout(3)
    s.connect((host, port))
    s.send((cmd + '\r\n').encode())
    time.sleep(0.3)
    s.settimeout(0.3)
    resp = b''
    try:
        resp = s.recv(256)
    except: pass
    s.close()
    return resp.decode('latin1', 'replace').strip()

# Examples (verified working on X-HM72)
print(pioneer_cmd('192.168.1.12', '?P'))    # PWR0
print(pioneer_cmd('192.168.1.12', '?V'))    # VOL005
print(pioneer_cmd('192.168.1.12', 'VU'))    # Volume up (status pushed)
print(pioneer_cmd('192.168.1.12', '38FN'))  # Switch to Internet Radio
```

For interactive use (browsing the menu, watching events), keep one
persistent connection and demultiplex incoming lines:

```python
import socket, time, re

s = socket.socket()
s.settimeout(8)
s.connect(('192.168.1.12', 8102))

def send_and_collect(cmd, wait=1.5):
    s.send((cmd + '\r\n').encode())
    time.sleep(wait)
    s.settimeout(0.8)
    buf = b''
    try:
        while True:
            chunk = s.recv(2048)
            if not chunk: break
            buf += chunk
    except socket.timeout: pass
    return buf.decode('latin1','replace').strip()

# Switch to Media Server and walk the top menu
print(send_and_collect('44FN', wait=3))             # FN44 + initial menu push
state = send_and_collect('?GAP')                    # full menu state
print(state)
# Parse GEP entries:
for m in re.finditer(r'GEP\d{2}\d{3}"([^"]*)"', state):
    print('  item:', m.group(1))

# Open first item, then go back
print(send_and_collect('00001GHP'))
print(send_and_collect('31PB'))

s.close()
```

---

## Architecture Note

Port 8102 is NOT a direct connection to the BridgeCo DM870 — it's a TCP-to-SPI tunnel implemented by the DM870 that forwards commands to the Pioneer host CPU (Pioneer-branded ARM processor). The DM870 handles WiFi and TCP; the Pioneer CPU handles audio, inputs, amplifier control.

This means:
1. Commands that control audio hardware (volume, mute, input) → forwarded to Pioneer CPU
2. Commands for network streaming (NSC, NSK) → handled by DM870 directly
3. Response echoes like `NSC\r\n` = DM870 acknowledgment; actual Pioneer CPU responses have data (e.g. `VOL000`)

---

## Two Pioneer Services on Port 8102

The firmware exposes **two different Pioneer service implementations** on the
same TCP port — both reachable via the PioTunneling tunnel:

| Service (firmware class) | Purpose | Status |
|--------------------------|---------|--------|
| `Pio_ControlAppService`  | Basic RS-232C-style protocol (`MO`/`MF`/`##FN`/`?V`, etc.) — everything documented above | ✅ Always active |
| `Pio_iControlAvService`  | Rich app-facing API: favorites, browse, UPnP search, album art, seek, playscreen timer | ⚠️ Gated by `EnabledQueryExAPI=0` |

The `Pio_iControlAvService` is the implementation behind the (now-defunct)
official Pioneer **iControlAV5** iOS/Android app. The firmware contains the
service code, but the Extended Query API is disabled by default. The error
string `cpPioTunnelingControlService->QueryEx returns false.` (at firmware
offset `0x000184a6`) confirms the gating.

### iControlAV5 Action Vocabulary (internal IDs from firmware)

```
ICAV_CAPP_ADD_FAV          — Add current source/track to favourites
ICAV_CAPP_REMOVE_FAV       — Remove from favourites
ICAV_CAPP_BROWSE_INFO      — Get menu / browse list info
ICAV_CAPP_UPNP_SEARCH      — Trigger UPnP search for content
ICAV_CAPP_SEEK             — Seek within a track
ICAV_CAPP_DISP_QUALIFIED   — Display refinement query
ICAV_CAPP_SELECT_TOTAL     — Confirm a selection
ICAV_CAPP_PLAYSCREENTIMER  — Play-screen timer event
ICAV_ALBUMART_INFO_ACTIVE  — Album art info, active
ICAV_ALBUMART_INFO_PASSIVE — Album art info, passive
```

These are C++ enum / log-tag names found in the firmware. The TCP command
syntax that maps to each (e.g. `?XFAV`, `XADDF`, etc.) is **not yet decoded**
— would require the original app APK or a packet capture from when the app
was still functional.

### ControlApp Key Code Vocabulary (`eIEKC_CApp_*`)

Internal key codes used by `Pio_ControlAppService` to dispatch incoming
network commands to the audio system. Each maps to a 1-byte IR key code on
the Pioneer host CPU side (e.g. `MuteOn = 0xA6`, `MuteOff = 0xA7`):

```
PowerOn / PowerOff / PowerStatus
VolumeUp / VolumeDown / VolumeValue        (set specific volume, not only up/down)
MuteOn / MuteOff / MuteStatus
InputToggle / InputReverse / InputStatus / InputInformation
PlaybackStatus / Play / Pause / Stop / Next / Previous / Random / Repeat
Ok / TopMenu / Cancel
LikeIt / Favorites / AlbumArtInfo / GenerationStatus / IPodCtrlKeyInfo
PB_CD_Play / PB_CD_Pause / PB_CD_Stop / PB_CD_Next / PB_CD_Previous
ListeningmodeAuto / ListeningmodeAdvsurr / ListeningmodeAlc / ListeningmodeEcomode

Per-input keys: CD, DVD, BD, DVR, TV, SAT, Video, Game, Line, AudioIn,
                Tuner, IRadio, IPodDock, IPodUSB, HOSTBT (Bluetooth),
                MServer, MHL, HDMI1, Pandora, Adapterport
```

Total: 59 named key codes. Most map 1-to-1 to a basic protocol command we
already documented (e.g. `MuteOn` ↔ `MO`, `VolumeUp` ↔ `VU`). The richer
ones (`VolumeValue`, `LikeIt`, `Favorites`, `ListeningmodeXxx`) suggest the
basic protocol can do more than the visible verb names imply, but the TCP
command syntax for them isn't documented.

### Enabling the Extended API (untested, potentially risky)

From the BridgeCo debug shell on port 9000:
```
set cne/PioTunnelingControlService/EnabledQueryExAPI 1
```

This flips the gate from `0` to `1` and might unlock the iControlAV API for
new connections. **Not yet attempted on the live device** — could affect
existing services or require a reboot to take effect.

---

## Sources

Command **names** were extracted from this firmware binary (constant pool at
file offset `0x0015a3e0`, GUI query handlers from `0x00017158`). Command
**semantics** were inferred from publicly documented Pioneer VSX-series
protocol references and then cross-checked against the X-HM72 live:

- [schaffman5 / VSX-1022_Commands](https://github.com/schaffman5/VSX-1022_Commands/blob/master/Pioneer_VSX-1022_Commands_2012.txt)
  — GUI menu protocol (`?GAP` + `GBP`/`GCP`/`GDP`/`GEP`, `NNNNNGHP`,
  `NNNNNGGP`) — verified working on X-HM72 with the live-tested examples
  shown above.
- [Arno Welzel — Control AV receivers by Pioneer over the network](https://arnowelzel.de/en/control-av-receivers-by-pioneer-over-the-network)
  — basic protocol overview, `R\r\n` heartbeat (verified on X-HM72).
- [Mike Poulson — Programmatically Controlling Pioneer Receivers](https://blog.mikepoulson.com/2011/06/programmatically-controlling-pioneer.html)
  — mute semantics (`MO`=mute on, `MF`=mute off, `MUT0`=muted).
- [crowbarz / ha-pioneer_async issue #95](https://github.com/crowbarz/ha-pioneer_async/issues/95)
  — VSX-528 reverse-engineering: model-specific FN-code variations, ACK-only
  command list (much of this **does not apply** to X-HM72; testing showed
  most of the ACK-only commands are completely silent on this model).

**X-HM72-specific divergence from VSX-series docs (live-tested):**
- `?MUT`/`?PWR`/`?VOL`/`?FN` long forms — not implemented (silent or `R` ACK only).
- `?L`/`?S`/`?R`/`?AST`/`BAUP`/`BADN`/etc. tone controls — silent.
- Many `FNxx` codes referenced in firmware are silently rejected — only
  9 of 21 candidates actually switch the input.
- FN codes 44, 45, 51, 56 differ from VSX naming (see verified table).
