# Port 8102 — Pioneer Tunneling Control Protocol

Plain-text TCP protocol used by the Pioneer ControlApp. No auth, no
handshake — connect and send. Lines terminated with `\r\n`.

```
[PioTunnelingControlService Enabled 1 Port1 8102 EnabledQueryExAPI 0]
```

UPnP advertisement (port 8080 `description.xml`):
```xml
<av:X_ipRemoteTcpPort>8102</av:X_ipRemoteTcpPort>
```

## Connection model

- Single socket, full-duplex, no request IDs.
- Heartbeat: device pushes bare `R\r\n` every ~30 s.
- Async state pushes: `VOLnnn`, `FNnn`, `MUTn`, full menu blocks.
- Client must demultiplex replies from pushes.

```python
import socket
s = socket.socket(); s.connect(('192.168.1.12', 8102))
s.send(b'?P\r\n'); print(s.recv(64))   # b'PWR0\r\n'
```

## Commands

Conventions: `nn` = 2 digits, `NNNNN` = 5-digit zero-padded.
Status: ✅ verified live on XC-HM72/SYXE8 fw 1.010 · ⚠️ accepted but no useful effect · ❌ no effect · ⏭ untested.

### Power

| Cmd  | Response                    | Notes |
|------|-----------------------------|-------|
| `?P` | `PWR0` / `PWR1` / `PWR2`    | 0 = On, 1 = Cold Standby, 2 = Network Standby ✅ |
| `PF` | —                           | Power On (wakes from PWR1; ❌ does not wake from PWR2) |
| `PO` | —                           | Standby |

### Volume / Mute

| Cmd  | Response       | Notes |
|------|----------------|-------|
| `?V` | `VOLnnn`       | 0–185 ✅ |
| `VU` | push `VOLnnn`  | ✅ step varies by context |
| `VD` | push `VOLnnn`  | ✅ |
| `?M` | `MUT0` / `MUT1`| 0 = muted, 1 = unmuted (Pioneer convention) ✅ |
| `MO` | push `MUTn`    | ⚠️ flag flips, front-panel shows no indicator |
| `MF` | push `MUTn`    | ⚠️ same |

### Input (`FN`)

| Cmd      | Notes |
|----------|-------|
| `?F`     | → `FNnn` ✅ |
| `nnFN`   | Switch input |
| `FU` / `FD` | ❌ no effect on X-HM72 |

Verified input codes (9 of 21 in firmware accepted):

| Code | Input              | Notes |
|------|--------------------|-------|
| `01` | Phono              | |
| `02` | CD                 | |
| `17` | iPod               | opens menu |
| `38` | Internet Radio     | opens menu (vTuner service offline) |
| `44` | Media Server (DLNA)| opens menu |
| `45` | Favorites          | opens flat preset list |
| `51` | Favorites alias    | = 45 |
| `52` | Line In            | |
| `56` | Favorites alias    | = 45 |

Rejected: `04 05 06 10 15 19 25 33 41 46 47 48 49 50`.

### Playback (`PB`)

| Cmd   | Function                  | Status |
|-------|---------------------------|--------|
| `10PB`| Play                      | ❌ no-op |
| `11PB`| Pause                     | ❌ no-op on live streams (elapsed keeps ticking) |
| `12PB`| Stop                      | ✅ |
| `13PB`| Skip forward              | ⚠️ disconnects to error, does not advance preset |
| `14PB`| Skip back                 | ⚠️ same |
| `20PB`| Top Menu / Home           | ⏭ |
| `26PB` `27PB` `28PB` `29PB` | Up / Down / Left / Right | ⏭ |
| `30PB`| Enter                     | ⚠️ triggers playback view but does not commit highlighted preset |
| `31PB`| Back / return             | ✅ |
| `32PB`| Shuffle                   | ⏭ |
| `34PB` `35PB` | Power-related (gen2/3 UI)   | ⏭ |
| `36PB`| TopMenu key (gen2/3 UI)   | ⏭ |
| `37PB`| Sort key (gen2/3 UI)      | ⏭ |
| `39PB` `40PB` `41PB` | unknown | ⏭ |

CD playback (input `02FN`): `nnCDP` where `nn` ∈ {10, 11, 12, 13, 20}. ⏭

### Menu / list navigation

| Cmd          | Function                                | Status |
|--------------|-----------------------------------------|--------|
| `?GAP`       | Query screen + list state               | ✅ |
| `NNNNNGGP`   | Move cursor to absolute index N         | ✅ |
| `NNNNNGHP`   | Open item at index N                    | ✅ folders / ❌ flat preset lists |
| `?ssseeeGIA` | Request rows `sss..eee` content (10-digit param) | ⏭ |
| `nnGFP`      | Select content on current list          | ⏭ |

### Favorites (decoded from ControlApp)

| Cmd         | Function                                  | Input  | Status |
|-------------|-------------------------------------------|--------|--------|
| `NNNNNFCA`  | Add row N to Favorites                    | ≠ 45   | ⏭ untestable (vTuner offline) |
| `NNNNNFCB`  | Remove row N from Favorites               | = 45   | ✅ `00013FCB` → ByteFM removed, count 13→12 |

Response: `FC[AB]NNNNNr` where `r` = result flag (`1` success, `0` rejected). Device also pushes a "Favorite removed" placeholder + new list.

### Device info

| Cmd    | Response                              |
|--------|---------------------------------------|
| `?RGD` | `RGD<gen><model><cap0>` — `RGD<001><XC-HM72/SYXE8><E0>` |
| `?RGF` | `RGF<64-char bitfield>` main-zone features |
| `?ICA` | `ICA0` / `ICA1` icon status ✅ |
| `?GIC` | `GIC<status>"<url>"` album art (✅ returns `GIC000""` for streams) |
| `?NGD` | older-format generation+model |
| `?NGC` | `NGC0`/`NGC1` network-standby flag |

## Responses (unsolicited / async)

| Tag    | Format                          | Meaning |
|--------|---------------------------------|---------|
| `R`    | `R\r\n`                         | Heartbeat (~30 s) |
| `PWR`  | `PWR0` / `PWR1` / `PWR2`        | Power state push |
| `VOL`  | `VOLnnn`                        | Volume push |
| `MUT`  | `MUTn`                          | Mute push |
| `FN`   | `FNnn`                          | Input push |
| `GBP`  | `GBPnn`                         | Visible row count |
| `GCP`  | `GCPwwxy0z0"label"`             | Screen header — see below |
| `GDP`  | `GDP<aaaaa><bbbbb><ccccc>`      | Window start, end, total (5-digit each) |
| `GEP`  | `GEPnnxxx"label"`               | One display row — flag decoding below |
| `GIB`  | `GIB…`                          | Specific rows from `?…GIA` |
| `GIC`  | `GIC<status>"<url>"`            | Album art URL |
| `ICA`  | `ICA0` / `ICA1`                 | Icon state |

### `GCP` screen type (first 2 digits)

| `ww` | Screen        |
|------|---------------|
| `00` | Error / empty |
| `01` | List menu     |
| `02` | Now Playing   |
| `06` | Connecting    |

### `GEP` flags

On list screen (`GCP01…`), `xxx` = `H_T`:
- **H**: 1 = highlighted, 0 = not
- **T**: 1 = folder/container, 2 = playable leaf

| `xxx` | Meaning                |
|-------|------------------------|
| `001` | Folder, not highlighted|
| `101` | Folder, highlighted    |
| `002` | Leaf, not highlighted  |
| `102` | Leaf, highlighted      |
| `000` | Empty / error          |

On Now Playing screen (`GCP02…`), `xxx` = field id:

| `xxx` | Field         |
|-------|---------------|
| `020` | Track title   |
| `021` | Artist / station |
| `022` | Album         |
| `023` | Elapsed time  |
| `026` | Codec         |
| `029` | Bitrate       |
| `034` | Total time    |

### `RGD` capability byte

```
RGD<001><XC-HM72/SYXE8><E0>
     │   │              └ first capability byte
     │   └ model
     └ generation (parsed as int → app loads /generation1/ UI)
```

### `RGF` capability bitfield (64 bits)

Active bits on X-HM72: `1, 2, 17, 38, 44, 45, 46, 47, 51, 52, 56, 57, 58, 59`.
Bit-to-feature mapping not fully decoded.

## Architecture notes

- 8102 is a TCP-to-SPI tunnel implemented by the BridgeCo DM870.
- Audio / amp / input commands forwarded to the Pioneer host CPU.
- DM870-handled: `NSC`, `NSK`, network state.

## Two services share port 8102

| Service                    | Status  |
|----------------------------|---------|
| `Pio_ControlAppService`    | always on — commands above |
| `Pio_iControlAvService`    | gated by `EnabledQueryExAPI` — implementation **hard-disabled on X-HM72** |

Setting `/cne/PioTunnelingControlService/EnabledQueryExAPI 1` via the
port-9000 shell **does not activate** the Extended API, even after
`sys reboot`. Flag persists in SDS but no new commands respond and
`NNNNNGHP` on Favorites still resumes the device's default stream
instead of activating the highlighted preset.

## See also

- [APP_PROTOCOL.md](APP_PROTOCOL.md) — full ControlApp command class hierarchy + receive tags
- [PORT_9000_SHELL.md](PORT_9000_SHELL.md) — BridgeCo SDS debug shell
