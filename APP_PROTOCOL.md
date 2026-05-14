# Pioneer ControlApp 4.1.0 — Command Reference

Reverse-engineered from `jp.pioneer.avsoft.android.controlapp` 4.1.0
(2016-02-10). The Android wrapper exposes one JS bridge function
`SendCommandViaNative(cmd)`; everything else is in the bundled WebView
at `assets/AppendFiles/AppendedZipHtml.zip`.

## Command class hierarchy

```
CommandBase
└── CommandNap         (older NAP — NGD handshake)
    CommandRegM        (RGD handshake)
    └── CommandHiMicro ← X-HM72 (XC-HMxx mini systems)
        └── CommandSma
            └── CommandRegMFy14    (Zone-2)
                └── CommandSmc     (Tuner / DAB / EQ)
                    └── CommandNap2 (sleep / search / seek)
```

The class is selected by the `<gen>` integer in the `RGD`/`NGD`
response. X-HM72 → `RGD<001>` → app loads `nap/generation1/` UI but
accepts gen2-style FN codes (38/44/45).

## Handshake

```
client → ?NGD   ; ?RGD
device → RGD<001><XC-HM72/SYXE8><E0>
client → ?NGC ; ?P ; ?F ; ?GAP
```

## Send commands

Parameter notation: `nn` = 2 digits, `NNNNN` = 5 digits zero-padded.

### CommandBase

| Method                              | Wire        | Param |
|-------------------------------------|-------------|-------|
| `reqPower`                          | `?P`        | — |
| `powerOn` / `powerOff`              | `PO` / `PF` | — *(JSDoc labels are inverted vs Pioneer RS-232C spec; X-HM72 follows the spec: `PF` = On, `PO` = Standby)* |
| `reqInput`                          | `?F`        | — |
| `inputChange(nn)`                   | `nnFN`      | 2-digit |
| `playbackOperation(nn)`             | `nnPB`      | 2-digit |
| `getCurrentList`                    | `?GAP`      | — |
| `selectTheContentOnTheCurrentList(nn)` | `nnGFP`  | 2-digit |
| `displayTheQualifiedList(NNNNN)`    | `NNNNNGGP`  | 5-digit (move cursor) |
| `selectTheContentOnTheTotalOfTheList(NNNNN)` | `NNNNNGHP` | 5-digit (open item) |

### CommandNap

| Method              | Wire    |
|---------------------|---------|
| `reqGeneration`     | `?NGD`  |
| `reqFunctionFlag`   | `?NGC`  |

### CommandRegM (X-HM72 baseline)

| Method                            | Wire    | Notes |
|-----------------------------------|---------|-------|
| `reqVolume` / `volumeUp` / `volumeDown` | `?V` / `VU` / `VD` | |
| `reqMute` / `muteOn` / `muteOff`  | `?M` / `MO` / `MF` | |
| `listeningModeSet(xxxx)`          | `SR`    | ⚠ app bug: sends bare `SR`, drops param |
| `reqiPodControlKeyInfo`           | `?ICA`  | |
| `reqTunerPresetKeyInfo(nn)`       | `PR`    | ⚠ same bug: drops param |
| `reqGeneration` (override)        | `?RGD`  | |
| `reqMainZoneInputInfo`            | `?RGF`  | |

### CommandHiMicro (X-HM72 class)

| Method                       | Wire     | Param |
|------------------------------|----------|-------|
| `reqContentsList(p)`         | `pGIA`   | 10 chars (`sssss` + `eeeee`) |
| `playbackOperationCD(nn)`    | `nnCDP`  | 2-digit |

### CommandSma

| Method                                | Wire     | Param |
|---------------------------------------|----------|-------|
| `textEditInfo(t)`                     | `tTEI`   | 1–128 chars (search) |
| `reqAlbumArtUrlInfoForPlayingItem`    | `?GIC`   | — |

### CommandRegMFy14 (Zone-2 — not on X-HM72)

| Method                       | Wire             |
|------------------------------|------------------|
| `reqPowerZone2`              | `?AP`            |
| `powerOnZone2` / `powerOffZone2` | `APO` / `APF` |
| `reqVolumeZone2`             | `?ZV`            |
| `volumeUpZone2` / `volumeDownZone2` | `ZU` / `ZD` |
| `reqMuteZone2`               | `?Z2M`           |
| `muteOnZone2` / `muteOffZone2` | `Z2MO` / `Z2MF` |
| `reqInputZone2`              | `?ZS`            |
| `inputChangeZone2(nn)`       | `nnZS`           |
| `reqFunctionFlag` (override) | `?RGC`           |
| `reqZone2InputInfo`          | `?RGH`           |
| `reqContentsList(p)` (override) | `?GIA<p>`     |

### CommandSmc (Tuner / DAB / EQ)

| Method                       | Wire         |
|------------------------------|--------------|
| `eq(n)` / `pBass(n)`         | `nATC` / `nPBA` |
| `playbackOperationUsb(nn)`   | `nnUS`       |
| `tunerFreqIncrement` / `Decrement` | `TFI` / `TFD` |
| `tunerAutoTuning(n)`         | `nTAT`       |
| `tunerPresetIncrement` / `Decrement` | `TPI` / `TPD` |
| `tunerMemory`                | `08TN`       |
| `tunerStereoMonaural(n)`     | `nAUC`       |
| `DABStationTuning(n)`        | `nDBS`       |
| `DABPresetSetting(n)`        | `nDBP`       |

### CommandNap2

| Method                          | Wire             | Param |
|---------------------------------|------------------|-------|
| `sleep(nnn)`                    | `nnnSAB`         | 3-digit minutes |
| `startSearch(t)`                | `tNSC`           | 1–128 chars |
| `seek(hhmmss)`                  | `hhmmssNSK`      | ≤ 6 chars |
| `networkPlayScreenTimer(n)`     | `nNPT`           | ≤ 1 char |
| `playbackOperationDAB(n)`       | `nDBS`           | 1 char |
| `keyOff`                        | `KOF`            | — |
| `SRKeyEvent(t, kkkkkkkk)`       | `tkkkkkkkkROI`   | 1-char type + 8-char keycode |

### Inline literals in `Detail.html`

Not exposed via the class methods — sent directly from UI handlers:

| UI action                            | Wire        | Generations |
|--------------------------------------|-------------|-------------|
| Long-press row → Favorite (input ≠ 45) | `NNNNNFCA` | all — Add |
| Long-press row → Favorite (input = 45) | `NNNNNFCB` | all — Remove |
| Back / breadcrumb                    | `31PB`      | all |
| Tap row → Enter                      | `30PB`      | all |
| Bottom Play (when not playing)       | `10PB`      | all |
| Bottom Pause (when playing)          | `11PB`      | all |
| Top "SKIP REV" button                | `12PB`      | all *(labels mismatch behavior on X-HM72: 12PB stops)* |
| Top "STOP" button                    | `20PB`      | all |
| Top "SKIP FWD" button                | `13PB`      | all |
| Sort key                             | `37PB`      | gen2/3 |
| Server / TopMenu                     | `36PB`      | gen2/3 |
| Power button                         | `34PB`, `35PB` | gen2/3 |
| Exit playback view                   | `2NPT`      | gen2/3 |

## Receive tags

Parser: `nap/generation*/js/ClassStatusProduct.js → ExeProcReceiveCommand()`.

| Tag    | Format                       | Meaning |
|--------|------------------------------|---------|
| `R`    | `R`                          | Heartbeat (~30 s) |
| `NGD`  | `NGD<gen><model>`            | Older generation + model |
| `NGC`  | `NGC0` / `NGC1`              | Network-standby flag (0 disabled, 1 enabled) |
| `RGD`  | `RGD<gen><model><cap0>`      | Newer generation + model + first cap byte |
| `RGF`  | `RGF<64-bit-field>`          | Main-zone feature bitfield |
| `RGC`  | `RGC…`                       | Function flag (RegMFy14+) |
| `RGH`  | `RGH<zone2-bits>`            | Zone-2 inputs |
| `PWR`  | `PWR0` / `PWR1` / `PWR2`     | On / Cold Standby / Network Standby |
| `VOL`  | `VOLnnn`                     | 0–185 |
| `MUT`  | `MUT0` / `MUT1`              | 0 muted, 1 unmuted |
| `FN`   | `FNnn`                       | Current input |
| `SR`   | `SR<mode>`                   | Listening mode |
| `ICA`  | `ICA0` / `ICA1`              | Icon state |
| `GBP`  | `GBPnn`                      | Visible row count |
| `GCP`  | `GCPwwxy0z0"label"`          | Screen header (`ww` = type) |
| `GDP`  | `GDP<aaaaa><bbbbb><ccccc>`   | Window start / end / total |
| `GEP`  | `GEPnnxxx"label"`            | Display row — flags context-dependent |
| `GIB`  | `GIB…`                       | Specific rows from `?…GIA` |
| `GIC`  | `GIC<status>"<url>"`         | Album art URL |
| `APR`  | `APR0`/`APR1`                | Zone-2 power |
| `ZV`   | `ZVnnn`                      | Zone-2 volume |
| `Z2MUT`| `Z2MUTn`                     | Zone-2 mute |
| `Z2F`  | `Z2Fnn`                      | Zone-2 input |

`GCP` / `GEP` decoding → [PORT_8102_PROTOCOL.md](PORT_8102_PROTOCOL.md).

## Favorites mechanism (source)

`Detail.html → TapEndFavoriteButtonInPopover()`:

```javascript
var command = ("0000" + (popoverRow+1)).slice(-5);
command += (selectedInput == "45") ? "FCB" : "FCA";
SendCommand(command);
```

- `popoverRow` is the 0-based row of the long-pressed item.
- Add `FCA`: sent on any input except `45` (Favorites).
- Remove `FCB`: sent only when on input `45`.
- Response: `FC[AB]NNNNNr` (trailing `r` = `1` success, `0` rejected).

## Sequence example

```
?NGD                                       (older path; times out on newer-only devices)
?RGD       → RGD<001><XC-HM72/SYXE8><E0>
?NGC       → NGC1
?P         → PWR0
?F         → FN45
?GAP       → GBP08
             GCP01100000000000200"Top Menu"
             GDP000010000800013
             GEP01102"Deutschlandfunk"
             …
00013FCB   → FCB000131
             GCP00100100…"Favorite removed"
             GCP01100…"Top Menu"
             GDP000090001200012
             GEP04102"ByteFM Stream"
```

## Source map

| Topic                       | File |
|-----------------------------|------|
| Command classes             | `basic/js/command.js` |
| Wire layer (`SendCommand`)  | `nap/generation*/js/common/Communication.js` |
| Handshake                   | `nap/js/ClassStatusProductForHome.js` |
| Receive parser              | `nap/generation*/js/ClassStatusProduct.js` |
| Input tables                | `nap/generation*/js/ClassStatusProduct.js → SetDefaultInputInfo()` |
| FCA / FCB                   | `nap/generation*/Detail.html → TapEndFavoriteButtonInPopover()` |
| Inline `nnPB` literals      | `nap/generation*/Detail.html` |
