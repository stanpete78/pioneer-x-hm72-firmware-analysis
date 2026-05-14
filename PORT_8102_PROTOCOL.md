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
1. Sends `R\r\n` ("ready") roughly every 30 seconds as a heartbeat
2. Pushes unsolicited state updates when something changes — e.g. a volume
   change at the device emits `VOLnnn`, an input change emits `FNnn`, a menu
   refresh emits a full `GBP`/`GCP`/`GDP`/`GEP` block. A client should treat
   incoming lines as either replies-to-our-command or push events.

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
| `?P` | `PWR0`/`PWR1`/`PWR2` | Query power state |
| `PO` | — | Power On |
| `PF` | — | Power Off / Standby |

Power state codes (per Pioneer VSX RS-232C spec — model behaviour may vary):
- `PWR0` = ON (operating)
- `PWR1` = Cold standby (network off, only IR remote can wake)
- `PWR2` = Network standby (network on, can be woken via `PO`)

> The X-HM72 must have "Network Standby" enabled in its menu for `PO` to work
> when the device is in standby. Otherwise the TCP socket is unreachable.

### Volume
| Command | Response | Description |
|---------|----------|-------------|
| `?V` | `VOL000`–`VOL185` | Query volume (0–185) |
| `VU` | — | Volume Up — observed step size **+8** in one test, +1 in another; appears context-dependent |
| `VD` | — | Volume Down — symmetric to `VU` |

### Mute
| Command | Response | Description |
|---------|----------|-------------|
| `?M` (or `?MUT`) | `MUT0`/`MUT1` | Query mute. `MUT0` = muted, `MUT1` = not muted (per Pioneer VSX spec) |
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

**Input Function Codes (`##FN`):**

| Code | Input |
|------|-------|
| `01FN` | Phono |
| `02FN` | CD |
| `04FN` | DVD/BD |
| `05FN` | TV |
| `06FN` | Sat/Cable |
| `10FN` | Video 1 |
| `15FN` | DVR/BDR |
| `17FN` | iPod |
| `19FN` | (unknown) |
| `25FN` | Internet Radio |
| `33FN` | Adapter Port |
| `38FN` | iPod/USB |
| `41FN` | iPod/USB (rear?) |
| `44FN` | AirPlay |
| `45FN` | Spotify |
| `48FN` | (unknown) |
| `49FN` | Game |
| `50FN` | BT Audio |
| `51FN` | DAB |
| `52FN` | LineIn2 |
| `56FN` | (unknown) |

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

Commands marked ✅ verified responsive; — = empty response (may require menu
context — many of these are GUI-list-related and only respond when the device
is in a list-based source like Internet Radio, Media Server, iPod menu, etc.).

| Command | Response | Verified | Description |
|---------|----------|----------|-------------|
| `?GIA` | — | — | Get display string (likely menu-context dependent) |
| `?GIC` | `GIC000""` | ✅ | Get display info C |
| `?GAP` | `GBP…GCP…GDP…GEP…` block | (in context) | **Get All Page** — returns the entire GUI menu state (see GUI Menu Protocol below) |
| `?ICA` | `ICA0` / `ICA1` | ✅ | Icon status (`ICA1` = iPod/USB icon on, `ICA0` = off) |
| `PR` | — | — | Preset? (no response on HMx — see Tuner Presets below for `NNPR`) |
| `FCA`, `FCB`, `GFP`, `GGP`, `GHP` | — | — | When sent bare, no response. `GGP` / `GHP` are actually navigation commands with a prefix — see below |

### GUI Menu Protocol (`?GAP` / `GBP` / `GCP` / `GDP` / `GEP` / `GHP` / `GGP`)

This is the protocol the official Pioneer remote app used to navigate menus,
browse radio stations, and select tracks. Active when the device is in a
list-based source (Internet Radio `25FN`, Media Server, iPod, Pandora,
Favorites). Documented in the [Pioneer VSX-1022 RS-232C spec](https://github.com/schaffman5/VSX-1022_Commands/blob/master/Pioneer_VSX-1022_Commands_2012.txt).

**Query the current menu state:**
```
?GAP
```
The device responds with a block of status lines:
```
GBPnn                                — list size (nn = number of displayed entries)
GCPwwxy0z0"SCREEN_LABEL"             — screen header
GDPaaaaabbbbbccccc                   — display range and total count
GEPnnxxx"LABEL"                      — entry n, repeated for each item
GEPnnxxx"LABEL"
...
```

| Code | Meaning |
|------|---------|
| `GBPnn` | `nn` = zero-padded count of GEP entries currently shown |
| `GCPwwxy0z0"label"` | `ww` = screen type (00–99); `x` = hierarchical-list-update flag (0/1); `y` = top-menu-key-enabled (0/1); `z` = return-key-enabled (0/1); `"label"` = current screen name |
| `GDPaaaaabbbbbccccc` | `aaaaa` = start index of shown range; `bbbbb` = end index; `ccccc` = total entry count (all 5-digit zero-padded). Example: `GDP000010000800031` = entries 1–8 of 31 |
| `GEPnnxxx"label"` | One entry. `nn` = display row (01–08 typically); rest = entry metadata + label |

**Navigation commands** (5-digit zero-padded item index + suffix):

| Command | Function |
|---------|----------|
| `NNNNNGHP` | **Select** list item at index NNNNN (`00002GHP` = pick item 2) |
| `NNNNNGGP` | **Scroll** to position NNNNN (`00050GGP` = jump to row 50) |
| `30PB` | Enter key (confirm selection) |
| `31PB` | Return / back key (go up one level) |

**Example: navigate Internet Radio favorites**
```
25FN          → switch to Internet Radio
?GAP          → device returns GBP04 GCP01... GDP000010000400015 GEP01... GEP02... etc.
00003GHP      → highlight item 3
30PB          → enter (open station / play)
31PB          → back to parent list
```

The Internet Radio source on this device sends `R\n` heartbeats every ~30
seconds while connected; menu state updates are pushed asynchronously when
the device's UI changes.

### Tuner Presets

| Command | Function |
|---------|----------|
| `NNPR` | Recall tuner preset NN (01–30). Example: `05PR` = preset 5 |

The X-HM72 has FM/AM/DAB tuners — these are reached via `02FN` (Tuner) and
preset slots are populated via the front panel or via the iControlAV app's
favorites-management commands (not yet decoded for direct TCP use).

### Listening Modes (`NNNNSR`)

4-digit zero-padded code followed by `SR`. Per Pioneer VSX-1022 spec:

| Command | Mode |
|---------|------|
| `0005SR` | Auto / Direct |
| `0010SR` | ALC / Standard |
| `0100SR` | Advanced Surround |

The X-HM72 is a 2-channel stereo so most surround modes don't apply — `0010SR`
(Standard) is the expected default. Other 4-digit codes likely exist for
Stereo, Pure Audio, etc. (model-dependent).

### Device Info
| Command | Response | Verified | Description |
|---------|----------|----------|-------------|
| `?RGD` | `RGD<001><XC-HM72/SYXE8><E0>` | ✅ | Device ID / model info |
| `?RGF` | `RGF<64-char bitfield>` | ✅ | Remote feature capabilities |
| `?RGC` | — | — | Remote config? (no response on HMx) |

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
| ✅ Confirmed working with documented response | `?P`, `?V`, `?M`, `?F`, `?GIC`, `?ICA`, `?RGD`, `?RGF`, `NSC`, `NSK` |
| ✅ Confirmed effective state change | `VU`, `VD` (volume changes visible on display, user-verified) |
| ⚠️ State toggles but display unchanged | `MF`, `MO` (`?M` flips between MUT0/MUT1 as expected, but front panel shows no MUTE indicator — audio effect unverified) |
| ❓ No response, function unclear | `?RGC`, `?GIA`, `?GAP`, `GFP`, `GGP`, `GHP`, `FCA`, `FCB`, `PR` |
| ⏭️ Not tested (would change user-facing state) | `PF`, `PO`, all `##FN`, all `PB`, all `CDP` |

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

# Examples
print(pioneer_cmd('192.168.1.12', '?P'))    # PWR0
print(pioneer_cmd('192.168.1.12', '?V'))    # VOL000
print(pioneer_cmd('192.168.1.12', 'VU'))    # Volume Up
print(pioneer_cmd('192.168.1.12', '25FN'))  # Switch to Internet Radio
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

These are C++ enum / log-tag names found in the firmware. Most of the
"missing" functionality these names hint at is actually exposed through the
standard menu/GUI protocol documented above (`?GAP` + `NNNNNGHP` + `30PB`):
- `ADD_FAV` / `REMOVE_FAV` are reachable as menu actions when the device
  is in the "Favorites" input (`45FN`) or in Internet Radio context — the
  app sent a `30PB` (enter) on the right menu entry.
- `BROWSE_INFO` corresponds to `?GAP` returning the full screen state.
- `UPNP_SEARCH` is triggered by navigating into Media Server (`44FN`) and
  selecting the search entry.
- `SEEK` is `30PB` on a playback screen with a specific time index.

So the iControlAV5 app didn't need a separate command vocabulary for these
features — it built them on top of the GUI menu protocol. The `EnabledQueryExAPI`
gate likely controls **passive metadata streaming** (album art retrieval,
high-frequency status pushes) rather than action invocation.

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

Command-name extraction came from this firmware (`HMx2015APP1010.fw`).
Command **semantics** were sourced from publicly documented Pioneer VSX-series
RS-232C/IP protocol references, then cross-checked against the X-HM72's
behaviour where safely testable:

- [Arno Welzel — "Control AV receivers by Pioneer over the network"](https://arnowelzel.de/en/control-av-receivers-by-pioneer-over-the-network)
  — basic protocol overview, heartbeat behaviour, input/volume/mute commands
- [Pioneer VSX-1022 Commands (schaffman5/VSX-1022_Commands)](https://github.com/schaffman5/VSX-1022_Commands/blob/master/Pioneer_VSX-1022_Commands_2012.txt)
  — definitive GUI menu protocol (`?GAP` / `GBP` / `GCP` / `GDP` / `GEP` /
  `NNNNNGHP` / `NNNNNGGP`), tuner presets (`NNPR`), listening modes (`NNNNSR`)
- [Mike Poulson — "Programmatically Controlling Pioneer Receivers"](https://blog.mikepoulson.com/2011/06/programmatically-controlling-pioneer.html)
  — mute command semantics
- [crowbarz/ha-pioneer_async #95 — VSX-528 reverse-engineering](https://github.com/crowbarz/ha-pioneer_async/issues/95)
  — `R` heartbeat, ACK-only commands list, model-specific FN-code variations

The X-HM72 may diverge from the VSX-series in detail (e.g. its FN code 45 is
likely Spotify rather than Favorites because of firmware-side feature flags),
so treat documented codes as the **starting point** and verify on the device
when in doubt.
