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
| `VU` | — | Volume Up |
| `VD` | — | Volume Down |

### Mute
| Command | Response | Description |
|---------|----------|-------------|
| `?M` | `MUT0`/`MUT1` | Query mute (0=off, 1=on) |
| `MF` | — | Mute Off |
| `MO` | — | Mute On |

### Input Function
| Command | Response | Description |
|---------|----------|-------------|
| `?F` | `FN##` | Query current input (see table below) |
| `##FN` | — | Set input to ## |

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
| Command | Response | Description |
|---------|----------|-------------|
| `?GIA` | — | Get display string (no response) |
| `?GIC` | `GIC000""` | Get display info C |
| `?GAP` | — | Get something (no response) |
| `GFP` | — | Get FP |
| `GGP` | — | Get GP |
| `GHP` | — | Get HP |
| `?ICA` | `ICA0` | Icon status |
| `FCA` | — | Function A |
| `FCB` | — | Function B |
| `PR` | — | Preset? |

### Device Info
| Command | Response | Description |
|---------|----------|-------------|
| `?RGD` | `RGD<001><XC-HM72/SYXE8><E0>` | Device ID / model info |
| `?RGF` | `RGF<64-char bitfield>` | Remote feature capabilities |
| `?RGC` | — | Remote config? |

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
