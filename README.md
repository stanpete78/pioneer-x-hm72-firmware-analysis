# Pioneer X-HM72 Firmware Analysis

Reverse engineering of the Pioneer X-HM72 micro HiFi system firmware — decryption, NAND access, and platform analysis.

The firmware encryption has been fully broken. This repo provides tools and documentation so others can inspect their own device firmware.

> **Legal note**: This is interoperability research on a device the author owns.
> Under EU Directive 2009/24/EC (implemented in German law as §69e UrhG), reverse
> engineering for interoperability is permitted. The HTML pages in `webui/` are
> excerpts of Pioneer firmware content shown for analysis context only — Pioneer
> holds the copyright. The repo does not redistribute the firmware binary itself.

**Device**: Pioneer X-HM72 (micro HiFi system, ~2015)
**Firmware**: `HMx2015APP1010.fw` (v1.010, 2015-06-09)
**Platform**: BridgeCo/SMSC DM870A — **ARM926EJ**, not MIPS as initially guessed

---

## Quick Start

**Requirements**: Python 3, `pycryptodome`

```bash
pip install pycryptodome
```

1. Download the official firmware from Pioneer's support site (`HMx2015APP1010.fw`)
2. Decrypt it:

```bash
python3 decrypt_fw.py HMx2015APP1010.fw HMx2015APP1010_decrypted.bin
```

Expected output:
```
Written: HMx2015APP1010_decrypted.bin (12359488 bytes)
Image CRC: 0x9c8552f9  ✓
CNE CRC:   0xb59d27bc  ✓
```

3. Analyse with binwalk, Ghidra, strings, etc.

---

## Firmware Format

Pioneer uses a proprietary `bCoD` v3 container format (BridgeCo firmware format).

### File Layout

```
0x000000  Pioneer outer wrapper (32 bytes)
           └─ CRC32 of 0x20..EOF, payload_size
0x000020  bCoD v3 header (0xC0 bytes)
           ├─ magic "bCoD", version 3
           ├─ build timestamp: "20150609133529"
           ├─ module name: "JB21_UI_Generic"
           └─ 9-entry section descriptor table
0x0000E0  Encrypted payload (Blowfish-ECB + XOR)
           ├─ Image section  (offset 0x000, size 0x80466C)  ARM firmware
           ├─ CNE section    (offset 0x80474C, size 0xC290)  config store
           └─ FFS Resources  (~0x8108FC, size 0x3B8D1C)     UI assets
```

`wml11b.c` (included) is a public domain parser for the bCoD format — useful reference for field offsets.

---

## Encryption

### Cipher

**Blowfish-ECB + fixed IV XOR** — every 8-byte block uses the same XOR mask:

```
P[k] = BF_ECB_decrypt(C[k])  XOR  iv_const
```

This is *not* standard CBC/OFB/CFB. The "IV" is a static 8-byte XOR mask applied uniformly to every block.

### Keys

The key and IV are stored in plaintext in the device's CNE config area (NAND offset `0x048570`):

```
BCDEncryption_BFKey = xMH51VAHreenoiPx   (16-byte Blowfish key)
BCDEncryption_BFIV  = hcba0256            (8-byte static XOR mask)
```

These are hardcoded in every X-HM72 unit.

### How We Found Them

The device exposes an **SDS debug shell** on TCP port 9000 with a `fburn rd` command that reads raw NAND pages via XMODEM-CRC16. We dumped the CNE config block (NAND `0x040000`, 64 KB) and found the keys in plaintext at offset `0x8570`.

Cipher mode was confirmed via known-plaintext attack: dumping 4 KB of the firmware image from NAND (`0x300080`) and comparing against the encrypted `.fw` blocks — all blocks yielded the identical XOR value `hcba0256`.

---

## NAND Access

The device runs an SDS shell on **TCP port 9000** (connect over LAN). The `fburn` command provides raw NAND read/write access — no authentication required on a local network.

### NAND Layout (partial)

| Physical Address | Content |
|---|---|
| `0x000000` | Bootloader (~512 KB) |
| `0x040000` | CNE config store |
| `0x048570` | Encryption keys (plaintext) |
| `0x300000` | BridgeCo firmware image |
| `0x300080` | ARM image sub-header |
| `0x302080` | Compressed ARM code |

### Dumping NAND

```bash
# Dump 64 KB CNE block (contains encryption keys)
python3 nand_dump.py 0 0x040000 0x10000 nand_cne.bin

# Dump bootloader (512 KB)
python3 nand_dump.py 0 0x000000 0x80000 nand_bootloader.bin

# Dump arbitrary region
python3 nand_dump.py <flash_id> <hex_addr> <hex_len> <output.bin>
```

**Requirements**: Device reachable at `192.168.1.12:9000` (edit `HOST`/`PORT` in the script). Device must be at the `sds://>` prompt — if stuck in a previous XMODEM transfer, send 3× `CAN` (0x18) bytes to abort.

---

## Decrypted Image Contents

Running `binwalk` / `strings` on the decrypted image reveals:

- ARM32 LE code (BridgeCo AG copyright)
- Embedded web UI (HTML, JavaScript, GIF images)
- Crypto libraries: AES S-boxes, SHA-256, CRC32
- Media libraries: libpng, libjpeg
- WPA2 wireless stack

### Interesting Strings

```
TelnetTunnelingService
adminPassword
BCDEncryption_BFKey
BCDEncryption_BFIV
Port1 / Port2 / Port3 / Port4
```

`TelnetTunnelingService` and `Port1`–`Port4` suggest the device may support Telnet tunneling that can be activated via the SDS shell — not yet investigated.

---

## Security Notes

- The SDS shell on port 9000 requires no authentication and allows raw NAND read/write over a local network connection. Anyone on the same network can dump or overwrite the device's flash.
- Encryption keys are stored in plaintext in NAND and are identical across all devices of this model.
- Pioneer no longer actively supports the X-HM72. This information is published for interoperability and security research purposes.

---

## Files

### Documentation

| File | Description |
|---|---|
| `ANALYSIS.md` | Full firmware analysis: bCoD format, cipher derivation, NAND layout, KPA |
| `PORT_8102_PROTOCOL.md` | Pioneer IP Remote protocol — volume, input, playback, menu, favorites (with status: ✅ live-verified / ⏭ untested) |
| `PORT_9000_SHELL.md` | BridgeCo SDS debug shell — command reference, SDS filesystem tree, port map, threads, NAND read via `fburn` |
| `APP_PROTOCOL.md` | ControlApp 4.1.0 command class hierarchy (`CommandBase` → `CommandHiMicro`), full send/receive command list, JS source references |
| `WEB_INTERFACE.md` | HTTP server on port 80 — goform handlers, ASP-page inventory, remote-control form schema |
| `FAVORITES.md` | Edit favorites directly via SDS — vTuner is dead, so use any local UPnP/DLNA media server as the stream resolver |

### Scripts (offline — operate on firmware/dump files)

| File | Description |
|---|---|
| `decrypt_fw.py` | Decrypt a `.fw` file → raw binary using the embedded Blowfish key + XOR mask |
| `nand_dump.py` | Dump arbitrary NAND regions via the port 9000 `fburn` command + XMODEM-CRC16 |
| `extract_html.py` | Pull the embedded web UI out of the decrypted firmware → `webui/` |
| `wml11b.c` | Public domain bCoD container parser — reference for field offsets |

### Tools (online — talk to a running device on the LAN)

| File | Description |
|---|---|
| `tools/p8102.py` | Port 8102 tester — send commands, listen for async pushes with timestamps |
| `tools/sds.py` | Port 9000 SDS shell wrapper — handles the per-character autocomplete echo |
| `tools/fav_backup.py` | Trace `cne/Favourites/` linked list → `favourites_backup.json` |
| `tools/fav_add.py` | Insert a favorite (`upnp` schema + DLNA stream URL) + auto-trigger parser reload |

All tools default to `192.168.1.12` — edit `HOST` at the top to match your device.

### Extracts

| Path | Description |
|---|---|
| `webui/` | 51 ASP/HTML pages from the device's embedded web UI, paths preserved |

Binary artifacts (firmware dumps, decrypted images, screenshots, the ControlApp APK) are excluded — bring your own.

---

## References

- BridgeCo DM870A platform (SMSC/Microchip)
- bCoD firmware format: see `wml11b.c` for field offsets
- XMODEM-CRC16 protocol (standard)
- pycryptodome: https://pycryptodome.readthedocs.io

---

## License

Original code in this repository (`decrypt_fw.py`, `nand_dump.py`, `extract_html.py`) is released under the **MIT License**.

`wml11b.c` is public domain.

Pioneer firmware is copyright Pioneer Corporation — not included here.
