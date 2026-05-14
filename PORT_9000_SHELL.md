# Pioneer X-HM72 — Port 9000: BridgeCo Debug Shell

## Overview

Port 9000 is an unauthenticated **BridgeCo SDS debug shell** — a fully interactive
command-line interface exposing the device's System Data Store (SDS), operating system,
threading, hardware registers, and runtime config. **No password, no handshake.**

```
$ nc 192.168.1.12 9000
sds://>
```

The shell is the `ShellThread` (thread 34) in the running KnOS RTOS. A separate
`TelnetServer` thread (35) manages incoming connections on this port.

The shell uses character-by-character autocomplete — every character you type is
echoed back with possible completions before the final response. This makes parsing
programmatic output noisy; `recv` after a command will contain the autocomplete
echo as well as the actual result.

---

## Port Map (complete)

| Port  | Service | Notes |
|-------|---------|-------|
| 80    | Pioneer Web Control (HTTP) | goform ASP framework |
| 443   | HTTPS | Same web control |
| 1900  | UPnP/SSDP | Discovery |
| 5000  | AirPlay (AirTunes/190.9) | Digest auth required |
| 8080  | BridgeCo WAA legacy web server | IR control, screen capture |
| 8102  | PioTunnelingControlService | Pioneer IP Remote (TCP→SPI) |
| 9000  | **BridgeCo debug shell** | No auth — this document |
| 10000 | TelnetShell | Configured, **currently inactive** |
| 10100 | EthDRC (Ethernet Direct Remote Control) | Configured, **inactive** |
| 49154 | TCPIPTunnel (RemoteRegisters) | Configured, **inactive** |

---

## Python Access

```python
import socket, time, re

s = socket.socket()
s.settimeout(5)
s.connect(('192.168.1.12', 9000))

def cmd(c, wait=0.8):
    s.send((c + '\r\n').encode())
    time.sleep(wait)
    s.settimeout(1.5)
    resp = b''
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            resp += chunk
    except: pass
    return resp.decode('latin1', 'replace')

def getval(attr):
    r = cmd('get ' + attr)
    m = re.search(r'Value=\s*(.*)', r)
    return m.group(1).strip() if m else None

# Examples
print(cmd('version'))
print(getval('cne/NTP/Server1'))    # ntp.nict.jp
print(getval('cne/AirTunes/ModelName'))  # XC-HM72
```

**Important:** The shell permits only **one TCP connection at a time**. Rapid
reconnects will be refused. Space commands 0.3–0.5 s apart.

---

## Command Reference

Full command list from `help`:

| Command | Description |
|---------|-------------|
| `help` | List all commands |
| `get <path>` | Read value of a config attribute |
| `set <path> <value>` | Write value to a config attribute |
| `ls [path]` | List contents of a directory in SDS |
| `cd <dir>` | Change working directory |
| `pwd` | Print current directory |
| `rm` | Resource Manager commands |
| `version` | Print firmware/component versions |
| `subver` | Print Sub-CPU version |
| `netcfg` | Print full network config (IP, SSID, MAC, etc.) |
| `net` | TCP/IP networking commands |
| `ping <ip>` | Ping a host |
| `iperf` | TCP/UDP bandwidth measurement tool |
| `wpa` | wpa_supplicant CLI (WiFi key management) |
| `os th` | List all running threads (149 on live device) |
| `os blk/byte/cne/evt/free/load/map` | OS memory/event stats |
| `os standby / suspend / running` | Change power mode |
| `os uartcfg` | UART configuration |
| `sys ver` | Show all component versions with CVS tags |
| `sys reboot` | Soft reboot (PowerManager) |
| `sys reset` | Hard reset |
| `sys gpio` | GPIO commands |
| `sys spi` | SPI commands |
| `sys memdump` | Raw memory dump |
| `sys wlan` | WLAN related commands |
| `rd <addr> <count>` | Read raw memory (8/16/32-bit) |
| `wr <addr> <value>` | Write raw memory (**dangerous**) |
| `persparam rd/rds/wr/wrs/clr/reset` | NVRAM persistent parameter access |
| `fburn` | Flash burn commands (**dangerous — can brick device**) |
| `filetransfer` | File transfer |
| `spicmd / spikey / spilist / spilog / spisend` | SPI debug |
| `piotun` | Pioneer Tunneling debug |
| `upnp` | UPnP control point |
| `ssdp` | SSDP enable/disable/send |
| `dbgprt` | Debug print config |
| `remote` | Send IR remote button codes |
| `k` | Send debug key code |
| `drcTst` | DRC remote control test |
| `apple` | Apple-specific commands |
| `ipod` | Serial iPod access |
| `ipodauth` | iPod authentication coprocessor |
| `usb` | USB commands |
| `bat <name>` | Execute a batch file of commands |
| `shell [-s]` | Shell config (show current settings) |
| `guard` | Guard test |
| `flashtest` | Flash test |
| `nap` | NAP service commands |
| `napster` | Napster test |
| `nc play/stop/pause/stat` | Playback control |
| `reg` | Register test |
| `rtp` | RTP commands |
| `ave` | Audio/Video Engine shell |
| `avr` | AVR test |
| `btb` | Bluetooth test |
| `capp` | ControlApp test |
| `extcmd` | NMP side ExternalCmd |
| `lltd -enable/-disable` | Link Layer Topology Discovery |
| `probe <ip>` | Probe IP address |
| `resource` | MediaResourceManager commands |
| `rdm` | RDM FileSystem test |
| `pictureplayer` | Picture player commands |
| `clear` | Clear shell history |

---

## SDS Filesystem Structure

```
sds://
├── static/
│   ├── Networking/
│   ├── Configuration/
│   ├── Controller/
│   ├── ViewModeControl/
│   ├── Pioneer/
│   │   ├── Configuration/
│   │   │   ├── System/
│   │   │   ├── Sound/
│   │   │   ├── ParentalLock/
│   │   │   ├── Bluetooth/
│   │   │   ├── Network/
│   │   │   └── Usb/
│   │   ├── State/
│   │   │   ├── UPnP/
│   │   │   ├── IRadioLastPlay/
│   │   │   ├── DigitalInUSB/
│   │   │   ├── ErrorCount/
│   │   │   ├── JBConnect/
│   │   │   ├── TextDisplayInfo/
│   │   │   ├── CommonDisplayInfo/
│   │   │   ├── PowerState          (leaf)
│   │   │   ├── ScreenSaverStatus   (leaf)
│   │   │   └── ...
│   │   └── Others/
│   ├── Metadata/
│   ├── cardea/
│   ├── albumarturl             (leaf)
│   ├── iPodOnSwitchA           (leaf)
│   └── SwitchA_Status          (leaf)
│
└── cne/
    ├── Presets/
    ├── Favourites/
    ├── HistoryBrowser/
    ├── FMTuner/
    ├── AMTuner/
    ├── Networking/
    ├── Spotify/
    ├── AirTunes/
    ├── Pioneer/
    │   ├── Configuration/
    │   │   ├── System/           (Scroll, FontType, AutoPowerDown, InputFunction)
    │   │   ├── ParentalLock/
    │   │   ├── Bluetooth/        (Mode, PinCode)
    │   │   ├── FriendlyName/     (DefaultName, UserSettingName, AppendMac, DefaultValueSet)
    │   │   ├── JBDirect/
    │   │   ├── FirmwareVersion/  (ApprovedAirplayVersion)
    │   │   ├── FirmwareDownload/
    │   │   ├── SpotifyRemote/
    │   │   └── AutoChangePlayScreen/
    │   ├── State/
    │   │   ├── IRadioLastPlay/
    │   │   ├── WacMode           (leaf)
    │   │   ├── Generation        (leaf)
    │   │   ├── Model             (leaf)
    │   │   ├── Destination       (leaf)
    │   │   ├── DestDivision      (leaf)
    │   │   └── SetupNavi         (leaf)
    │   ├── ModelId/              (Year, Item)
    │   ├── RemoteControlKey/
    │   ├── ControlApp/
    │   ├── Function/
    │   ├── Mode/
    │   └── VerInf/               (Combine)
    ├── FirmwareUpdate/           (see below)
    ├── FirmwareDownload/         (see below)
    ├── PioTunnelingControlService/
    ├── TelnetTunelling/
    ├── CommunicationSettings/
    ├── NTP/
    ├── EnhancedFeatures/
    ├── Spotify/
    ├── SDDPDevicedata/
    ├── AMXBeacon/
    ├── Control4/
    ├── Shell/
    ├── System/
    │   ├── ExceptionHandling/
    │   ├── Nap/
    │   ├── Equalizer/
    │   ├── Wavetunes/
    │   ├── DisplaySettings/
    │   └── Threads/
    └── ...
```

---

## Live Config Values

### Network / Communication

```
netcfg output:
  IP-Address       = 192.168.1.12
  NetMask          = 255.255.255.0
  Gateway          = 192.168.1.1
  DNS1             = 192.168.1.1
  DHCP             = true
  DriverName       = WLAN
  MacAddress       = <DEVICE_MAC>
  CneName          = WlanCfg
  SSID             = <WIFI_SSID>
  Network mode     = BSS (managed)
  Signal quality   = Good
  Phy type         = 11g
  Security mode    = WPA-WPA2-PSK-AES(CCMP)+TKIP
  BSSID            = <ROUTER_BSSID>
```

### Communication Settings

| Attribute | Value | Notes |
|-----------|-------|-------|
| `TelnetPort` | 10000 | Port for the Pioneer TelnetShell (inactive) |
| `Shell` | TELNET | Shell type configured |
| `TCPIPTunnel` | REMOTE_REGISTERS | TCP tunnel type |
| `TCPIPTunnelPort` | 49154 | TCP tunnel port (inactive) |
| `EthDRC` | ENABLE | Ethernet Direct Remote Control enabled in config |
| `EthDRCPort` | 10100 | EthDRC port (inactive) |
| `HostController` | SPI | Pioneer CPU connected via SPI |
| `iPodControl` | UART0 | iPod protocol over UART0 |

### Firmware Update

| Attribute | Value |
|-----------|-------|
| `PrimaryFWDescriptionUrl` | `http://www.pioneerelectronics.com/Wr5Ch9makajA/AVR/10mid/fwUpdateDescriptionFile.xml` |
| `EncryptionMandatory` | **0** — unencrypted firmware accepted |
| `ProductId` | 0 |
| `BlowfishKey` | (empty — not set at runtime) |

### AirTunes (AirPlay)

| Attribute | Value |
|-----------|-------|
| `ModelName` | XC-HM72 |
| `SpeakerName` | (empty — uses device name) |
| `PasswordRequired` | **0** — no AirPlay password |
| `FBoot` | — |

### NTP

| Attribute | Value |
|-----------|-------|
| `Server1` | ntp.nict.jp |
| `Enabled` | 1 |

### Spotify

| Attribute | Value |
|-----------|-------|
| `Enabled` | 1 |
| `Active_User` | 1 |
| `UserAgent` | 2014 HM |
| `Version` | 1.0 |
| `AppKey` | 320-byte hex key (Pioneer's Spotify Connect partner key) |
| `usr1`–`usr5` | (Spotify account usernames, if logged in) |
| `blob1`–`blob5` | (Spotify auth blobs, if logged in) |
| `Remote_Name` | (Spotify Connect display name) |

### Enhanced Features (License Keys)

| Attribute | Value |
|-----------|-------|
| `HDAudioKey` | `<32-char hex value redacted>` |
| `GaplessPlaybackKey` | (empty) |
| `NetworkApiKey` | (empty) |
| `AIFFKey` | (empty) |
| `PathRecoveryKey` | (empty) |
| `PartyModeKey` | (empty) |
| `SeekSupportKey` | (empty) |
| `HDAudio192Key` | (empty) |

### Device Identity

| Attribute | Value |
|-----------|-------|
| `cne/Pioneer/State/Model` | XC-HM72/SYXE8 |
| `cne/Pioneer/ModelId/Year` | 15 (2015) |
| `cne/Pioneer/ModelId/Item` | 32 |
| `cne/Pioneer/State/Generation` | 1 |
| `cne/Pioneer/State/Destination` | 2 |
| `cne/SDDPDevicedata/Model` | XC-HM72 |
| `cne/SDDPDevicedata/Manufacturer` | Control4 |
| `cne/SDDPDevicedata/Enabled` | 0 |

### Third-Party Control

| System | Status |
|--------|--------|
| Control4 SDDP | Disabled (`SDDPEnable = 0`) |
| AMX Beacon | Disabled (`BeaconEnable = 0`) |

---

## System Versions

```
sys ver output:
  Library                 Version   Build Date        CVS Tag
  KnOS (Release)          9857      2015-06-05        JB2Generic32MB-3_8_0-9857_ER
  APP:JB21.0-Ref/HW:JukeBlox2  9857  2015-06-05      JB2Generic32MB-3_8_0-9857_ER
  AudioHWService          9857      2015-06-05        hal_service-3_3_0-9857_ER
  DM870_HAL               9857      2015-06-05        PSM_SDRAM-1_0_0-9857_ER
  ViewGlue                9857      2015-06-05        JB2Generic32MB-3_8_0-9857_ER
  Presets                 9857      2015-06-05        presets-3_2_0-9857_ER
  Favourites              9857      2015-06-05        presets-3_2_0-9857_ER
  History                 9857      2015-06-05        presets-3_2_0-9857_ER

Component    CreationDate  ID   Version  BaseAddr
Bootloader   20140410      2    1        0x000A0080
Cne          20150609      132  9857     0x00040080
Image        20150609      132  9857     0x00300080
```

Device version: **NMP 1.010 / HST/SUB 1.000 / DSP 1.76/1.06/1.04**

---

## Running Threads (selected)

149 threads total. Key threads:

| # | Name | State | Notes |
|---|------|-------|-------|
| 34 | ShellThread | rdy | **This shell** (port 9000) |
| 35 | TelnetServer | sem | Listening for connections |
| 47 | Webserver | sem | HTTP server (port 80/8080) |
| 73 | SPI Receiver | sem | SPI link to Pioneer CPU |
| 79 | SpotifyServiceThread | rdy | Spotify Connect (active) |
| 81 | DrcTunneling | susp | DRC tunnel (suspended) |
| 117 | LltdResponder | comp | Windows Network Map |
| 120 | IREventHandlerThread | q | IR remote input |
| 121 | IRInputAbstraction_TX | sleep | IR transmit |
| 138 | TCP2SPI1 | sem | Port 8102 → SPI tunnel |
| 134–137 | PioCb/Mc/Rx/TxTunnelingControlServ | q | Pioneer tunneling |
| 148 | AirPlayMain | sem | AirPlay streaming |
| 149 | AirPlayDACP | sem | AirPlay remote control |
| 21 | WpaSupplicant | sleep | WiFi auth |
| 129 | ConfigureiTunes | q | iTunes/WAC config |

---

## Security Notes

1. **No authentication** — anyone on the LAN can connect to port 9000 and get full shell access.
2. **`set` command allows live config changes** — including `FirmwareUrl`, `EncryptionMandatory`, AirPlay passwords, etc.
3. **`wr <addr> <value>`** — direct raw memory write. Can corrupt any RAM address.
4. **`fburn`** — direct flash write. Can brick the device permanently.
5. **`persparam wr`** — write NVRAM persistent parameters (survive reboot).
6. **`sys reset`** and **`sys reboot`** — reboot/reset device without confirmation.
7. **`wpa`** — full wpa_supplicant CLI access including WPA keys in memory.
8. **Spotify AppKey visible** in `cne/Spotify/AppKey` — Pioneer's partner key for Spotify Connect.
9. **HD Audio license key** visible in `cne/EnhancedFeatures/HDAudioKey`.

---

## Enabling the Inactive Shell on Port 10000

The `TelnetShell` on port 10000 is configured (`Shell=TELNET`, `TelnetPort=10000`)
but the service is not listening. To start it (untested):

```
set cne/CommunicationSettings/TelnetPort 10000
```

Or trigger it via the `os shell` command from within the port 9000 shell.

---

## Port 5000: AirPlay

```
HTTP/1.1 401 Unauthorized
Server: AirTunes/190.9
WWW-Authenticate: Digest realm="airplay", nonce="..."
```

AirTunes version 190.9. Password authentication uses HTTP Digest. Since
`cne/AirTunes/PasswordRequired = 0`, connecting without a password should
work via the standard AirPlay protocol (not raw HTTP).

---

## Architecture Note

Port 9000 lives entirely within the **BridgeCo DM870A** (ARM926EJ). All commands
operate on the BridgeCo KnOS RTOS and its CNE/SDS config store. Pioneer CPU
state (volume, input, power) is not directly accessible here — it is accessed
via SPI (threads `SPI Receiver`, `TCP2SPI1`) and can be controlled indirectly
via the Pioneer Tunneling service on port 8102.
