# Pioneer X-HM72 — Web Interface Documentation

Discovered by live analysis of device at 192.168.1.12. No authentication required on any endpoint.

---

## Architecture: Two Separate Web Servers

| Port | Stack | Era | Purpose |
|------|-------|-----|---------|
| 80   | Pioneer "Web Control" | ~2014 | User-facing setup UI |
| 8080 | BridgeCo/WAA legacy | ~2004 | Engineering remote control + live screen capture |
| 443  | (no response) | — | Dead / TLS not configured |
| 1900 | UPnP SSDP | — | Device discovery |

---

## Port 80 — Pioneer Web Control

### Root redirect chain
```
GET /  →  301  →  /index.asp  →  JS redirect  →  /index.html
```

### Active pages

| Path | Title | Content |
|------|-------|---------|
| `/index.html` | Web Control | Main entry, links to sub-pages |
| `/1000/system_information.asp` | Network Setup | Full device info (see below) |
| `/1000/friendly_name.asp` | Network Setup | Read/write device name |
| `/1000/airplay_password.asp` | Network Setup | Read/write AirPlay password (**plaintext!**) |
| `/1000/firmware_update_start.asp` | Network Setup | Firmware update trigger |
| `/1000/wireless_network_config.asp` | Network Setup | WiFi SSID/security config |
| `/1000/wireless_network_config_mode.asp` | Network Setup | WPS/manual mode select |
| `/SystemDataHandler.asp` | — | Live JSON device state |

### Live device info (from system_information.asp)

```javascript
write_field_2(
  "s9784.5032.1010",  // firmware version
  "<DEVICE_NAME>", // friendly name
  "1",                 // wifi enabled
  "<WIFI_SSID>",          // SSID
  "<DEVICE_MAC>", // MAC
  "1",                 // DHCP on
  "192.168.1.12",      // IP
  "255.255.255.0",     // subnet
  "192.168.1.1",       // gateway
  "192.168.1.1",       // DNS1
  "0.0.0.0",           // DNS2
  "off",               // proxy state
  "", "0",             // proxy server, port
  "0.0.0.0"            // WAN address
);
```

### Live JSON state (SystemDataHandler.asp)

```json
{"PowerState":1,"IpodExtraCurrentValues":500}
```

- `PowerState`: 1 = on, 2 = standby
- `IpodExtraCurrentValues`: 500 = no iPod; -500 = iPod connected (SMA model specific)

### Write endpoints (goform — all on port 80)

All goform endpoints redirect (HTTP 302) on success.

| Endpoint | Method | Parameters | Effect |
|----------|--------|------------|--------|
| `/goform/formHandlerConfigureDMPName` | POST | `DMPName=<name>` | Change friendly name (max 50 chars, ASCII 0x20–0x7E) |
| `/goform/aformHandlerConfigureAirplayPassword` | POST | `AirplayPassword=<pw>` | Change AirPlay password |
| `/goform/formHandlerConfigureNetworkSettings` | POST | network params | Change IP/proxy settings |
| `/goform/formHandlerConfigureNetworkSettingsEx` | POST | network params | Alternative network config |
| `/goform/formHandlerConfigureWiFiSettings` | POST | WiFi params | Change SSID/key |
| `/goform/formPrepareFirmwareUpdateHandler` | GET | `FUOption=LAN&button=Start` | **Trigger firmware update** — times out (long-running) |

**Example — rename device:**
```bash
curl -X POST http://192.168.1.12/goform/formHandlerConfigureDMPName \
  --data "DMPName=MeinStereo"
```

### cfg.js — feature flags (hardcoded per model)

```javascript
{
  model: "HMx",
  system_information: true,
  wirless_configuration: true,
  network_configuration: false,   // IP/proxy page hidden
  network_standby: false,          // page not compiled in
  friendly_name: true,
  parental_lock: false,            // not compiled in
  port_number_setting: false,      // not compiled in
  airplay_password: true,
  pandora_account: false,          // disabled (EU model)
  sirius_account: false,           // disabled (EU model)
  spotify_account: false,          // disabled (this firmware version)
  firmware_update: true
}
```

Pages whose feature flag is `false` in cfg.js are still served but the menu entry is not rendered.
Pages whose flag corresponds to a 404 are not compiled into the firmware at all.

---

## Port 8080 — BridgeCo/WAA Legacy Interface

### Active pages

| Path | Content |
|------|---------|
| `/` | Redirects to `/index.html` |
| `/index.html` | Presentation page (blank) |
| `/remote_control.html` | Simple button-based remote |
| `/remote_control2.html` | **Full remote control** (image map + 36 IR commands) |
| `/screen_display.html` | Live screen capture loop (polls `screen_capture2.bmp` every 500ms) |
| `/config_tcpip.html` | TCP/IP settings (BridgeCo UPnP template style) |
| `/config_wireless.html` | Wireless configuration |
| `/config_device.html` | Device name setting |
| `/WAA_Display.gif` | 240×161px remote control image (served live) |

### IR Control API

**Endpoint:** `POST http://192.168.1.12:8080/screen_display.html`  
**Form field:** `upnp_tpl_tag_code=HtmlPageServiceID:action:actHtmlIrControl:argIrControl`  
**Command field:** `argIrControl=<command>`

```bash
# Example: send Play/Pause
curl -X POST http://192.168.1.12:8080/screen_display.html \
  --data "upnp_tpl_tag_code=HtmlPageServiceID:action:actHtmlIrControl:argIrControl&argIrControl=Play_Pause"
```

**Full command list:**

| Category | Commands |
|----------|----------|
| Power | `Power` |
| Volume | `VolumeUp`, `VolumeDown`, `Mute` |
| Navigation | `ScrollUp`, `ScrollDown`, `Cancel`, `Home`, `Select` |
| Playback | `Play_Pause`, `Stop`, `PlayAll`, `FF_Next`, `FR_Prev`, `ChannelUp`, `ChannelDown` |
| Playback modes | `Repeat`, `Shuffle` |
| Number pad | `Number0` … `Number9` |
| Presets | `Store`, `Favourites` |
| Sources | `Network`, `IRadio` |
| System | `Reboot` |
| Streaming | `LikeIt`, `DislikeIt` (Pandora-style) |
| Info | `Information` |

### Screen Capture

`GET http://192.168.1.12:8080/screen_capture2.bmp?<timestamp>`

Returns a 256px-wide BMP of the device's LCD display. Returns empty (0 bytes) when device is in standby or display not active. The JavaScript in screen_display.html polls this every 500ms with a cache-busting timestamp.

---

## Security Notes

- **No authentication** on either web server (port 80 or 8080)
- **AirPlay password visible in plaintext** at `/1000/airplay_password.asp`
- **Reboot** possible without credentials via IR command
- **Device rename** possible without credentials
- Any device on the local network can fully control the unit

---

## Firmware Update Mechanism

From `fu.js`:
1. JS first calls `GET /SystemDataHandler.asp` to check `PowerState != 2` (not in standby)
2. If OK, form submits `GET /goform/formPrepareFirmwareUpdateHandler?FUOption=LAN&button=Start`
3. Device contacts Pioneer's update server and downloads firmware
4. Process is long-running; connection times out from client side

The update checks `PowerState` but does not verify any token or session. Triggering it redirects the device to contact Pioneer's update infrastructure — those servers may be offline (2015 firmware).

**Potential custom firmware path:** If the update server URL is hardcoded in the firmware binary (likely), it could be redirected via `/etc/hosts` or DNS spoofing on the local network to serve a patched firmware file.

---

## Firmware Update: Complete Flow & Custom Firmware Path

### Update URLs (hardcoded in firmware binary, both return 404 since ~2020)

```
PrimaryFWDescriptionUrl:   http://www.pioneerelectronics.com/Wr5Ch9makajA/AVR/10mid/fwUpdateDescriptionFile.xml
SecondaryFWDescriptionUrl: http://www.pioneerelectronics.com/Wr5Ch9makajA/AVR/10mid/fwUpdateDescriptionFile.xml
FirmwareIndexPage:         http://www.bridgeco-jukeblox.net/download/index.xml  (BridgeCo/DM870 updater)
```

### Update flow (reconstructed from firmware code)

1. `GET /goform/formPrepareFirmwareUpdateHandler?FUOption=LAN&button=Start`  
   → Renders `firmware_update_start_indication.asp`
2. `aspNotifyHostDM870UpdateStart()` — tells Pioneer CPU to start DM870 update
3. `aspSetRebootInBSL()` — reboots into bootloader mode
4. DM870 fetches `fwUpdateDescriptionFile.xml`
5. XML contains: new firmware version, `DownloadURL`, `XTEAEncryptedBlowfishKey`, `XTEAEncryptedBlowfishInitialVector`
6. Device downloads firmware from `DownloadURL`, decrypts with Blowfish key, flashes to NAND
7. After 40s → redirect to `http://pioneer.home/bl_index.asp`

### Custom firmware via DNS spoofing (viable, Pioneer servers dead)

```
[Router DNS override or local dnsmasq]
www.pioneerelectronics.com → 192.168.1.XX  (your machine)
```

Serve a fake XML at the exact URL path. Device will download and flash whatever firmware file you point it to.

**`EncryptionMandatory: 0`** in config — firmware does NOT need to be encrypted.  
Known keys if encryption wanted:
- `BCDEncryption_BFKey: xMH51VAHreenoiPx`
- `BCDEncryption_BFIV: hcba0256`

### Update filename mapping

```
Self (DM870/BridgeCo): HMx2015APP
Host (Pioneer CPU):    HM72_82_Sub_
```

The device can update both its DM870 (BridgeCo) and the host Pioneer ARM CPU independently.

---

## Embedded Config Block (0x0080B500 in decrypted binary)

Complete default configuration baked into the firmware:

### Firmware Update
```
PrimaryFWDescriptionUrl    http://www.pioneerelectronics.com/Wr5Ch9makajA/AVR/10mid/fwUpdateDescriptionFile.xml
BCDEncryption_BFKey        xMH51VAHreenoiPx
BCDEncryption_BFIV         hcba0256
EncryptionMandatory        0
```

### Network Services
```
TelnetShellEnable   1          (configured ON, but port 8000 closed on live device)
TelnetShellPort     8000
CommunicationSettings:
  Shell             UART1
  TelnetPort        10000      (second Telnet, also closed on live device)
  TCPIPTunnelPort   49154
  EthDRCPort        10100      (Ethernet DRC)
  AlbumArtOverRR    1
NTP Enabled, Server: ntp.nict.jp
```

### Features enabled (EU model)
```
IRadio, MServer, DMR, AirPlay, Favorites, SpotifyPhase2
iPod, iPodUSB (1600mA), Din1, Input, CD, Tuner, LineIn
DAB, HostBT, LineIn2
```

### Features disabled (EU model)
```
SiriusXM, Pandora, Rhapsody, VTuner, SpotifyRemote, Aupeo
USB, BTAudio, AirJam, FM, HDMI1-7, BD, DVD, DVR
Video1/2, TV/SAT, CDR/Tape, Phono, MultiCh, SatCbl, Game
```

### Other notable config
```
ModelId: Item=32, Year=15 (2015)
ModelName (AirTunes): XC-HM82
RemoteControlKey DeviceKeyId: 223
AirPlay ApprovedVersion: 9784
Parental Lock PassCode: 0000 (default)
Bluetooth PinCode: 0
Alarm1/2: inactive
TimeFormat: 24h, DateFormat: dmy, TimeZone: 0
BCORadioClient: http://persephone.bc-int.net:8080/  (BridgeCo internal test server)
```

---

## All Open Ports (live device)

| Port | Protocol | Service | Status |
|------|----------|---------|--------|
| 80   | HTTP | Pioneer Web Control | **Active** |
| 443  | HTTPS | — | Open but no response |
| 1900 | UDP | UPnP SSDP | Open |
| 8080 | HTTP | BridgeCo/WAA legacy web | **Active** |
| 8102 | TCP | **Pioneer IP Remote** | **Active** — responds to eISCP |
| 9000 | TCP | Unknown | Open |
| 8000 | TCP | Telnet Shell | Configured ON, closed |
| 10000 | TCP | Telnet (UART bridge) | Closed |
| 10100 | TCP | Ethernet DRC | Closed |
| 49154 | TCP | TCPIP Tunnel (RemoteReg) | Closed |

### Port 8102 — Pioneer IP Remote (eISCP)

The `X_ipRemoteTcpPort` = 8102 from UPnP description. This is the Pioneer AV Control App protocol.

Tested commands:
- `NJA` → responds `R\r\n` (Ready)
- Other standard eISCP commands (`PWR`, `MVL`, etc.) → timeout

Packet format (eISCP):
```python
data = b'!1' + command.encode() + b'\r'
packet = b'ISCP' + (16).to_bytes(4,'big') + len(data).to_bytes(4,'big') + b'\x01\x00\x00\x00' + data
```

---

## Open Questions

- What does `formHandlerConfigureWiFiSettings` accept? (POST params not yet mapped)
- `screen_capture2.bmp` returns 0 bytes — device may need active display / non-standby state
- What is the full Pioneer IP Remote command set on port 8102? (`NJA` responds, others timeout)
- Port 9000: unknown service, open but no HTTP response
- TelnetShell (port 8000): configured enabled but closed. Activation sequence unknown — may require factory mode or UART trigger
- UPnP SSDP discovery timed out — device did not respond to multicast within test window
