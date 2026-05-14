# Pioneer ControlApp — Complete Protocol Reference

## Source

Extracted from **ControlApp 4.1.0** for Android
(`jp.pioneer.avsoft.android.controlapp`, package date 2016-02-10).
The Android APK ships its UI as a bundled WebView (HTML+JS) inside
`assets/AppendFiles/AppendedZipHtml.zip`. The Java wrapper exposes one
JS function — `SendCommandViaNative(cmd)` — that pushes a string over
TCP/8102 to the device.

This document captures every command the app can send, every response
it parses, and every state semantic encoded in its JavaScript.

---

## Identification handshake

The app handshakes the device on connect:

```
?NGD   → expects "NGD<gen><model>"        ← older NAP protocol
?RGD   → expects "RGD<gen><model><cap0>"  ← newer protocol (RegM/HiMicro/SMC/Nap2)
```

The integer in `<gen>` selects which UI bundle is loaded:
`./generation0/`, `./generation1/`, `./generation2/`, `./generation3/`.

X-HM72 returns `RGD<001><XC-HM72/SYXE8><E0>` → generation 1 — but the
FN codes it accepts match generation 2 (38=IRadio, 44=Music Server,
45=Favorites). The X-HM72 firmware is therefore a **hybrid**: it
declares as gen1 to the app but supports the gen2 input set.

After RGD/NGD the app issues:

```
?NGC   → Network-standby flag           (response: NGC0 disabled / NGC1 enabled)
?P     → Power state                    (response: PWR0/PWR1/PWR2)
?F     → Currently selected input       (response: FNnn)
?GAP   → Current screen + list state    (response: GBP, GCP, GDP, GEP block)
```

Then it polls `?GAP` on user interactions plus listens for unsolicited
pushes (the device emits FNnn / VOLnnn / MUTn / R-heartbeat asynchronously).

---

## Command class hierarchy

`basic/js/command.js` defines a class tree. The product class determines
which methods are available:

```
CommandBase
├── CommandNap                          (NAP — older NGD-handshake)
└── CommandRegM                         (RegM — newer RGD-handshake)
    └── CommandHiMicro                  ← X-HM72 (and other XC-HMxx)
        └── CommandSma                  (SMA)
            └── CommandRegMFy14         (FY14 receivers, Zone2 support)
                └── CommandSmc          (SMC — tuner / DAB / EQ)
                    └── CommandNap2     (NAP2 — sleep/search/seek)
```

X-HM72 is the **HiMicro** class. It inherits everything from
CommandBase, CommandNap-receive-tags, and CommandRegM, plus HiMicro
adds the contents-list and CD-playback commands.

The app at runtime is not necessarily limited to its declared class —
on X-HM72 we verified that some Nap2 (KOF) and SMC commands behave as
no-ops but don't error. Anything outside the HiMicro feature set is
silently dropped.

---

## All commands the app can send

Lines below are paraphrased from `basic/js/command.js` (the JSDoc
comments and method bodies) plus the per-generation `Detail.html`
files. Verified-on-X-HM72 status is from our own live testing
(see PORT_8102_PROTOCOL.md for details).

### Class CommandBase (every model)

| Method                            | Wire                | Parameter rule          | X-HM72 |
|-----------------------------------|---------------------|-------------------------|--------|
| `reqPower()`                      | `?P`                | —                       | ✅      |
| `powerOn()`                       | `PO`                | —                       | ⚠️ doc says "Power On" but on RegM-family `PF` is On — see note below |
| `powerOff()`                      | `PF`                | —                       | ⚠️ ditto |
| `reqInput()`                      | `?F`                | —                       | ✅      |
| `inputChange(nn)`                 | `nnFN`              | 2-digit                  | ✅ for 01/02/17/38/44/45/51/52/56 |
| `playbackOperation(nn)`           | `nnPB`              | 2-digit                  | partial (see PB table) |
| `getCurrentList()`                | `?GAP`              | —                       | ✅ in menu context |
| `selectTheContentOnTheCurrentList(nn)` | `nnGFP`         | 2-digit                  | not tested |
| `displayTheQualifiedList(nnnnn)`  | `nnnnnGGP`          | 5-digit                  | ✅ moves cursor |
| `selectTheContentOnTheTotalOfTheList(nnnnn)` | `nnnnnGHP`  | 5-digit                  | ✅ for hierarchical menus; ❌ for flat favorites lists |

**Power On/Off naming caveat:** The CommandBase JSDoc labels `PO` as
"Power On" and `PF` as "Power Off", but the inheriting CommandRegM
class (and the live X-HM72 behavior) follows Pioneer's RS-232C spec
where `PO` = standby and `PF` = on. The CommandBase comments appear to
be inverted. Always treat `PF` as power-on and `PO` as standby.

### Class CommandNap (older NAP devices)

| Method                | Wire    | Notes |
|-----------------------|---------|-------|
| `reqGeneration()`     | `?NGD`  | Older handshake — also supported by HiMicro |
| `reqFunctionFlag()`   | `?NGC`  | Network-standby flag query |

Receive tags: `NGD`, `NGC`.

### Class CommandRegM (covers HiMicro / X-HM72)

| Method                              | Wire    | X-HM72 |
|-------------------------------------|---------|--------|
| `reqVolume()`                       | `?V`    | ✅      |
| `volumeUp()`                        | `VU`    | ✅      |
| `volumeDown()`                      | `VD`    | ✅      |
| `reqMute()`                         | `?M`    | ✅      |
| `muteOn()`                          | `MO`    | ⚠️ state-flag flips but front-panel display does not update |
| `muteOff()`                         | `MF`    | ⚠️ same |
| `listeningModeSet(xxxx)`            | `xxxxSR` | 4-char param. **Note:** bug in app source — the if-check requires param.length == 4 but the actual sendCommand is `"SR"` (no param appended). Likely defective in 4.1.0. |
| `reqiPodControlKeyInfo()`           | `?ICA`  | ✅ returns `ICA0` |
| `reqTunerPresetKeyInfo(nn)`         | `PR`    | Note: similar bug — checks `nn` length but only sends bare `PR` |
| `reqGeneration()` (override)        | `?RGD`  | ✅ returns `RGD<001><XC-HM72/SYXE8><E0>` |
| `reqMainZoneInputInfo()`            | `?RGF`  | ✅ returns `RGF<bitfield>` |

Receive tags: `SR`, `ICA`, `RGD`, `RGF`.

### Class CommandHiMicro adds (X-HM72 class)

| Method                       | Wire             | Parameter rule | X-HM72 |
|------------------------------|------------------|----------------|--------|
| `reqContentsList(p)`         | `pGIA`           | 10-char param  | App calls this for partial list refresh; live X-HM72 returns `GIB...` |
| `playbackOperationCD(nn)`    | `nnCDP`          | 2-digit        | Used when input is CD (02FN). 10/11/12/13/20 are app-defined sub-codes |

Receive tag added: `GIB`.

### Class CommandSma adds (SMA — album art / text-edit)

CommandSma inherits from HiMicro, so X-HM72 also accepts these.

| Method                                  | Wire     | Parameter rule | X-HM72 |
|-----------------------------------------|----------|----------------|--------|
| `textEditInfo(t)`                       | `tTEI`   | 1–128 chars (search/text input) | not tested |
| `reqAlbumArtUrlInfoForPlayingItem()`    | `?GIC`   | —                              | ✅ verified live: returns `GIC000""` when no art available |

Receive tag added: `GIC` — `GIC<status>"<url>"`.

### Class CommandRegMFy14 adds (Zone-2 + GIA-prefix variant)

These exist in the binary but the X-HM72 has only one zone.

| Method                  | Wire           |
|-------------------------|----------------|
| `reqPowerZone2()`       | `?AP`          |
| `powerOnZone2()`        | `APO`          |
| `powerOffZone2()`       | `APF`          |
| `reqVolumeZone2()`      | `?ZV`          |
| `volumeUpZone2()`       | `ZU`           |
| `volumeDownZone2()`     | `ZD`           |
| `reqMuteZone2()`        | `?Z2M`         |
| `muteOnZone2()`         | `Z2MO`         |
| `muteOffZone2()`        | `Z2MF`         |
| `reqInputZone2()`       | `?ZS`          |
| `inputChangeZone2(nn)`  | `nnZS`         |
| `reqFunctionFlag()`     | `?RGC` (override) |
| `reqZone2InputInfo()`   | `?RGH`         |
| `reqContentsList(p)`    | `?GIA<p>` (override — prefix instead of suffix) |

Receive tags: `APR`, `ZV`, `Z2MUT`, `Z2F`, `RGC`, `RGH`.

### Class CommandSmc adds (SMC — tuner / DAB)

| Method                          | Wire       | Param  |
|---------------------------------|------------|--------|
| `eq(n)`                         | `nATC`     | 1-digit EQ index |
| `pBass(n)`                      | `nPBA`     | 1-digit P-Bass on/off |
| `playbackOperationUsb(nn)`      | `nnUS`     | 2-digit |
| `tunerFreqIncrement()`          | `TFI`      | — |
| `tunerFreqDecrement()`          | `TFD`      | — |
| `tunerAutoTuning(n)`            | `nTAT`     | 1-digit |
| `tunerPresetIncrement()`        | `TPI`      | — |
| `tunerPresetDecrement()`        | `TPD`      | — |
| `tunerMemory()`                 | `08TN`     | — (stores current freq as preset) |
| `tunerStereoMonaural(n)`        | `nAUC`     | 1-digit |
| `DABStationTuning(n)`           | `nDBS`     | 1-digit |
| `DABPresetSetting(n)`           | `nDBP`     | 1-digit |

### Class CommandNap2 adds (NAP2)

| Method                          | Wire             | Param |
|---------------------------------|------------------|-------|
| `sleep(nnn)`                    | `nnnSAB`         | 3-digit sleep minutes |
| `startSearch(text)`             | `<text>NSC`      | 1–128 chars (UTF-8 search keyword) |
| `seek(hhmmss)`                  | `<hhmmss>NSK`    | ≤ 6 chars (target time) |
| `networkPlayScreenTimer(n)`     | `nNPT`           | ≤ 1 char |
| `playbackOperationDAB(n)`       | `nDBS`           | 1-digit |
| `keyOff()`                      | `KOF`            | — |
| `SRKeyEvent(t, k)`              | `tkkkkkkkkROI`   | 1-char type + 8-char keycode |

### Commands not in command.js (hard-coded inline in `Detail.html`)

The actual UI buttons in each generation's `Detail.html` send several
commands not exposed via the class methods — they're string literals
inline. The most important on X-HM72 (gen1 / gen2 inputs):

| UI action                       | Wire     | Notes |
|---------------------------------|----------|-------|
| Long-press list item → "Favorite" button (input ≠ 45) | `NNNNNFCA` | 5-digit row index + `FCA` — **Add to Favorites** |
| Long-press list item → "Favorite" button (input = 45) | `NNNNNFCB` | 5-digit row index + `FCB` — **Remove from Favorites** |
| Hardware "Back" / breadcrumb tap      | `31PB`   | Return / go up one level |
| Tap a list row to play            | `30PB`           | Enter / OK (sent after `NNNNNGGP` moves cursor) |
| Top playback button "STOP"        | `12PB`           | gen1 source code labels it "SKIP REV" but on X-HM72 it stops the stream |
| Top playback button "Menu/Home"   | `20PB`           | gen1 labels "STOP" |
| Top playback button "Skip Forward"| `13PB`           | gen1 labels "SKIP FWD" |
| Bottom button "Play"              | `10PB`           | Sent when screenType ≠ 2 |
| Bottom button "Pause"             | `11PB`           | Sent when screenType == 2 (i.e. currently playing) |
| Sort menu (gen2/3 only)           | `36PB`, `37PB`   | TopMenu / Sort keys — DIFFERENT meaning from gen1 |
| Power button (long-press to off)  | `34PB`, `35PB`   | gen2/3 only |
| Network play-screen timer disable | `2NPT`           | Sent on gen2/3 when exiting playback view |

### Inline commands the app sends during scroll

When the user scrolls a list, the app autonomously sends:

```
NNNNNGGP    ← move cursor to absolute item N (start of new visible window)
NNNNNFFFFFGIA  ← request rows N..F display info  (10-char param: 5+5)
```

Followed by parsing `GIB` rows that come back.

---

## Receive tags & parsing rules

`basic/js/command.js` declares the receive tags each class listens for;
`generation1/js/ClassStatusProduct.js` has the actual parsing in
`ExeProcReceiveCommand()`.

| Tag    | Format                          | Meaning |
|--------|---------------------------------|---------|
| `R`    | bare `R\r\n`                    | Heartbeat (~ every 30s while socket open) |
| `NGD`  | `NGD<gen><model>`               | Older generation + model (NAP only) |
| `NGC`  | `NGC0` / `NGC1`                 | Network-standby disabled / enabled |
| `RGD`  | `RGD<gen><model><cap0>`         | Newer generation + model + first capability byte |
| `RGF`  | `RGF<64-char bitfield>`         | Main-zone feature capabilities |
| `RGC`  | `RGC...`                        | Function flag (RegMFy14 and later) |
| `RGH`  | `RGH<zone2-input-bits>`         | Zone2 inputs (irrelevant on X-HM72) |
| `PWR`  | `PWR0` / `PWR1` / `PWR2`        | Power state — see semantics below |
| `VOL`  | `VOLnnn`                        | Volume 0–185 |
| `MUT`  | `MUT0` / `MUT1`                 | Mute on / off (per Pioneer convention `0` = "active state of the named function" → MUT0 = muted) |
| `FN`   | `FNnn`                          | Selected input |
| `SR`   | `SR<mode>`                      | Listening-mode index |
| `ICA`  | `ICA0` / `ICA1`                 | iPod-style control icon (status) |
| `GBP`  | `GBPnn`                         | Count of visible rows on current screen |
| `GCP`  | `GCPwwxy0z0"label"`             | Screen header. `ww`=screen type, x/y/z = list-update / topmenu-enable / return-enable flags. See [PORT_8102_PROTOCOL.md](PORT_8102_PROTOCOL.md) for decoded values. |
| `GDP`  | `GDPaaaaabbbbbccccc`            | Window range over total: 5-digit start, end, total |
| `GEP`  | `GEPnnxxx"label"`               | One display row. `xxx` decoded in PORT_8102 doc — list-mode = highlight + type, playback-mode = field id |
| `GIB`  | `GIB...`                        | Specific rows requested via `?...GIA` |
| `GIC`  | `GIC<status>"<url>"`            | Album art URL for currently playing item (SMA-class and later). X-HM72 returns `GIC000""` for streams without art |
| `APR`  | `APR0`/`APR1`                   | Zone-2 power (not on X-HM72) |
| `ZV`   | `ZVnnn`                         | Zone-2 volume (not on X-HM72) |
| `Z2MUT`| `Z2MUTn`                        | Zone-2 mute (not on X-HM72) |
| `Z2F`  | `Z2Fnn`                         | Zone-2 input (not on X-HM72) |

### Power-state semantics (from `ReceivePowerStatus`)

```javascript
if      ( "PWR0" ) statusPower = 0;   // Power On
else if ( "PWR1" ) statusPower = 1;   // Cold Standby
else if ( "PWR2" ) statusPower = 2;   // Network Standby
```

- **`PWR0`**: device on, audio active.
- **`PWR1`**: cold standby — TCP socket may close; device usually
  reachable only via Wake-On-LAN.
- **`PWR2`**: network standby — TCP socket on port 8102 stays alive
  and responds to `?P`/`?V`/etc., but `PF` does *not* wake the unit
  from this mode reliably (verified on X-HM72: PF returned silently,
  PWR2 persisted). On X-HM72 this state is what the device enters when
  the user presses the front-panel Power button.

### `NGC` Network-standby flag

`NGC0` = setting disabled (device drops TCP on standby).
`NGC1` = setting enabled (device keeps TCP up in network-standby).

The app caches this in `flgNetworkStanby`. There is no explicit *set*
command in the JS for toggling this flag; on X-HM72 it can only be
changed via the front-panel menu or via SDS shell on port 9000.

---

## Favorites mechanism (verified live)

From `nap/generation*/Detail.html`, `TapEndFavoriteButtonInPopover()`:

```javascript
var command = ("0000" + (popoverRow+1)).slice(-5);
if ( "45" != statusProduct.selectedInput ) {   // Not on Favorites input
    command += "FCA";                          // Add to Favorites
} else {                                        // On Favorites input (45)
    command += "FCB";                          // Remove from Favorites
}
SendCommand( command );
```

### `NNNNNFCA` — Add current row to Favorites

- Send while on a non-Favorites input (e.g. Internet Radio `38FN` or
  Media Server `44FN`) with the cursor on the row you want to save.
- `NNNNN` = 1-based, 5-digit zero-padded **absolute** index in the
  current list.
- The app sends this after the user long-presses a row and taps the
  "Favorite" icon in the resulting pop-over.
- **Not verified live on X-HM72**: vTuner backend is offline so we
  cannot reach a non-favorited Internet Radio station for testing.

### `NNNNNFCB` — Remove from Favorites

- Send while on `45FN` (Favorites input) with cursor on the row to
  remove.
- **Verified live on X-HM72 (2026-05-14):**
  - Sent `00013FCB` with cursor on item 13 (`ByteFM`).
  - Device responded `FCB000131\r\n` plus a 4-row screen with
    `"Favorite removed"` placeholder, then the new top menu of length 12.
  - List count went 13 → 12 immediately.
  - The trailing digit of the response (`1` in this case, `0` we saw
    earlier when index was out of range) appears to be a result flag:
    `0` = no-op / rejected, `1` = removed.

### Response format

```
FCB <5-digit-index> <result>\r\n
```

Example success: `FCB000131` = "Removed item 13 (success)".

The device additionally pushes the next `GBP/GCP/GDP/GEP` block as if
the user had navigated, so the app can render the updated list without
sending another `?GAP`.

---

## What the X-HM72 does NOT support (despite command being in app)

From live tests vs app's expected behavior:

- **Volume sliders (`?V`/`VU`/`VD`)** — the X-HM72 does respond, but the
  gen1 Detail.html UI does not render a slider (the gen1 UI assumes
  the device is a streaming player without integrated amp).
- **Zone-2 commands (`?AP`/`APO`/`?ZV`/...)** — single-zone device.
- **`SR` listening mode** — app code is broken anyway (sends bare "SR"
  without param); X-HM72 returns nothing.
- **`PR` tuner preset** — bug in app code (bare "PR"); X-HM72 returns nothing.
- **CD `CDP` family (10CDP / 11CDP / ...)** — only meaningful when on
  CD input (02FN). Not tested.
- **DAB / Tuner family (`TFI`/`TPI`/`DBS`/...)** — X-HM72 has no DAB
  hardware. Tuner FM might work but not tested.
- **`SAB` sleep timer** — X-HM72 has a sleep menu in its front panel
  but the network command `nnnSAB` was not tested.

---

## Sequence example: the app starting up

```
client → ?NGD          (older path; will time out if newer-only device)
client → ?RGD          (newer path)
device → RGD<001><XC-HM72/SYXE8><E0>
client → ?NGC
device → NGC1
client → ?P
device → PWR0
client → ?F
device → FN45
client → ?GAP
device → GBP08
         GCP01100000000000200"Top Menu"
         GDP000010000800013
         GEP01102"Deutschlandfunk"
         GEP02002"Deutschlandfunk Kultur"
         …
         GEP08002"181.fm - Christmas Classics"
```

After this the app renders the Favorites list and shows the popover
"Favorite" button as a Remove action (because input == 45).

---

## Source map (reverse-engineering reference)

| Topic                       | File |
|-----------------------------|------|
| All command classes         | `assets/AppendFiles/AppendedZipHtml.zip → basic/js/command.js` |
| TCP wire layer (`SendCommand`) | `nap/generation*/js/common/Communication.js` |
| Native bridge wrapper       | `nap/generation*/js/common/AccessNativeApp.js` |
| Generation handshake        | `nap/js/ClassStatusProductForHome.js` |
| Receive parser (gen1)       | `nap/generation1/js/ClassStatusProduct.js` `ExeProcReceiveCommand()` |
| Input table (gen2)          | `nap/generation2/js/ClassStatusProduct.js` `SetDefaultInputInfo()` |
| Favorite Add/Remove (FCA/FCB) | `nap/generation*/Detail.html` `TapEndFavoriteButtonInPopover()` |
| Playback buttons            | `nap/generation*/Detail.html` (search for `10PB`, `11PB`, `12PB`, `13PB`, `20PB`) |
| Sort/Server buttons (gen2/3)| `nap/generation2/Detail.html` (search for `36PB`, `37PB`) |
