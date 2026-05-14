# Pioneer X-HM72 Firmware Analysis
## File: HMx2015APP1010.fw (v1.010)

---

## File Overview

| Field | Value |
|---|---|
| File size | 12,359,712 bytes (11.79 MB) |
| Outer CRC32 | 0xbd98f690 (covers 0x20..EOF, **VERIFIED**) |
| Format | Pioneer `bCoD` firmware container v3 |
| Build stamp | 2015-06-09 13:35:29 |
| Module name | `JB21_UI_Generic` |

---

## Target Platform

| Field | Value |
|---|---|
| SoC | **BridgeCo/SMSC DM870A** |
| Architecture | **ARM926EJ** (ARM32 little-endian) |
| Board name | JB21 (Pioneer internal designation) |
| Debug interface | SDS shell on TCP port 9000 |
| NAND access | `fburn rd <flash_id> <addr> <len>` via XMODEM-CRC16 |

> Note: Earlier analysis incorrectly identified the architecture as MIPS. The DM870A is ARM.

---

## Header Structure (0x00 – 0xDF)

### Outer Wrapper (0x00 – 0x1F, 32 bytes)
| Offset | Value | Description |
|---|---|---|
| 0x00 | `00000000` | padding |
| 0x04 | `0x00BC9800` = 12,359,680 | payload_size (= file_size − 32) |
| 0x10 | `0xbd98f690` | CRC32 of `data[0x20:]` ✓ |

### bCoD Header (0x20 – 0xCF, per wml11b.c)
| Offset | Value | Description |
|---|---|---|
| 0x20 | `bCoD` | magic |
| 0x24 | 3 | version |
| 0x28 | `20150609133529  ` | build timestamp (16 bytes) |
| 0x38 | 132 (0x84) | header size |
| 0x3C | 9857 (0x2681) | unknown field |

### Section Descriptor Table (0x40 – 0xCF, 9 × 16 bytes)

Raw entries (per file):
```
entry[0] @0x0040: 000200bd  0007f510  00000102  8be109f4
entry[1] @0x0050: 000000c0  00300000  0080466c  9c8552f9
entry[2] @0x0060: 00b00000  00000000  00000000  00000000
entry[3] @0x0070: 0080472c  00000000  0000c290  b59d27bc
entry[4] @0x0080: 00020000  00000000  00000000  00000000
entry[5] @0x0090: 008109bc  00e00000  003b8d1c  9097d421
entry[6] @0x00a0: 00400000  00000000  00000000  00000000
entry[7] @0x00b0: 0000d43c  003a7bac  00003d34  00000000
entry[8] @0x00c0: (zeros)
```

Parsed section layout (wml11b.c field mapping):
| Section | bCoD offset | Size | CRC32 | Notes |
|---|---|---|---|---|
| Image | 0xC0 (= 0x00 in payload) | 0x80466C bytes | 0x9c8552f9 ✓ | ARM firmware image |
| CNE | 0x80472C | 0xC290 bytes | 0xb59d27bc ✓ | Config/settings store |
| FFS Resources | ~0x8108FC (decrypted) | 0x3B8D1C bytes | 0x9097d421 | BridgeCo FFS resource container |

> `image_offset = 0xC0` is relative to the bCoD header start (0x20), so absolute file offset = 0x20 + 0xC0 = **0xE0** — where encrypted payload begins.

### Module Identifier (0xD0 – 0xDF)
`JB21_UI_Generic\0` — 16 bytes null-terminated

### Payload (0xE0 – EOF)
Encrypted with Blowfish-ECB + fixed IV XOR — **fully decrypted** (see below).

---

## Encryption — SOLVED

### Cipher
**Blowfish-ECB + fixed-IV XOR** (NOT AES, NOT CBC):

```
For each 8-byte block k:
    P[k] = BF_ECB_decrypt(C[k]) XOR iv_const
```

where `iv_const = b'hcba0256'` is applied identically to every block.

This is **not** standard CBC/OFB/CFB. The "IV" is a static XOR mask applied uniformly.

### Key and IV

Source: NAND CNE config store at physical NAND offset **0x048570**

```
BCDEncryption_BFKey = xMH51VAHreenoiPx   (16-byte Blowfish key)
BCDEncryption_BFIV  = hcba0256            (8-byte static XOR mask)
```

Extracted from `nand_cne.bin` (64 KB dump of NAND 0x040000–0x04FFFF).

### Known-Plaintext Verification

Ground truth: 4 KB NAND image dump (`nand_image_4k.bin`) from NAND address 0x300080 (BridgeCo boot image).

For blocks 0–7, computed `needed_XOR[k] = BF_ECB_dec(C[k]) XOR P_NAND[k]`.
All 8 values = `6863626130323536` = ASCII `hcba0256` — cipher confirmed.

### Why CBC Block-0 Was a False Positive

In CBC: `P[0] = BF_dec(C[0]) XOR IV`
In ECB+XOR: `P[0] = BF_dec(C[0]) XOR iv_const`

Since `IV = iv_const = hcba0256`, both give identical results for block 0 only.
Divergence starts at block 1 (CBC XORs with C[0]; ECB+XOR always uses iv_const).

### Partial-Block Boundary

`image_size = 0x80466C` — not divisible by 8 (remainder 4). The last 4 bytes of the Image section share a Blowfish block with the first 4 bytes of the CNE section. The full payload must be decrypted as one contiguous stream for both section CRCs to verify.

### Decryption Script

`decrypt_fw.py` — verified, both section CRCs pass:

```python
KEY = b'xMH51VAHreenoiPx'
IV  = b'hcba0256'   # static XOR mask, NOT a CBC IV
PAYLOAD_OFFSET = 0xE0

def decrypt_payload(data: bytes) -> bytes:
    n = (len(data) // 8) * 8
    ecb = Blowfish.new(KEY, Blowfish.MODE_ECB)
    dec = ecb.decrypt(data[:n])
    result = bytearray(n)
    for i in range(0, n, 8):
        for j in range(8):
            result[i+j] = dec[i+j] ^ IV[j]
    return bytes(result) + data[n:]
```

Output: `HMx2015APP1010_decrypted.bin` (12,359,488 bytes = file_size − 0xE0)

---

## Decrypted Image Analysis

### BridgeCo Image Sub-Header (decrypted bytes 0–31)
```
5555aaaa 01000000  a5a5a5a5 00da4000
f9030000 783048b1  08000000 a5a5a5a5
00800000 80203000  6c268000 8eb07f5c
...
```

Fields at offset 32–47 (NAND addressing):
- NAND address: `0x302080`
- Compressed data size: `0x80266C`
- Decompressed target: `0x0040FA00`

### Binwalk Results (`fw_image_section.bin`)
- ARM32 little-endian code throughout
- `BridgeCo AG` copyright strings
- Web UI assets: HTML/JavaScript, GIF images
- Crypto libraries: AES S-boxes, SHA-256 tables, CRC32 tables
- Media: libpng, libjpeg code
- WPA2/Wireless stack

### Security-Relevant Strings
- `TelnetTunnelingService` — Telnet tunneling may be activatable via SDS shell
- `adminPassword` — admin password configuration key
- `Port1`–`Port4` configuration strings — port forwarding/tunneling config
- `BCDEncryption_BFKey`, `BCDEncryption_BFIV` — encryption config keys (confirmed in NAND CNE)

---

## FFS Resources Section

Decrypted offset ~0x8108FC, size 0x3B8D1C bytes (~3.7 MB).
Starts with magic `FFSResources` — BridgeCo Flash File System resource container.
Contains multi-language UI strings, web UI assets, and application resources.
Format: BridgeCo proprietary FFS — not yet fully parsed.

---

## NAND Layout (Known)

| Physical Address | Content |
|---|---|
| 0x000000 | Bootloader (512 KB, `fburn rd 0 0x0 0x80000`) |
| 0x040000 | CNE config store (`nand_cne.bin` — 64 KB dumped) |
| 0x048570 | `BCDEncryption_BFKey` / `BCDEncryption_BFIV` entries |
| 0x300000 | BridgeCo firmware image start |
| 0x300080 | BridgeCo image header (`nand_image_4k.bin` — 4 KB dumped) |
| 0x302080 | Compressed ARM code (per sub-header) |

---

## Next Steps

1. **Ghidra analysis**: Load `fw_image_section.bin` as ARM LE, base address TBD (likely 0x0040FA00 per decompressed target field)
2. **FFS Resources parsing**: Implement BridgeCo FFS format parser to extract UI strings and web assets
3. **TelnetTunnelingService**: Investigate whether Telnet tunneling can be activated via SDS shell commands
4. **Full NAND map**: Dump complete NAND to understand full flash layout (bootloader, kernel, rootfs if present)
5. **Port tunneling**: Analyse Port1–4 config — may allow opening additional TCP services
