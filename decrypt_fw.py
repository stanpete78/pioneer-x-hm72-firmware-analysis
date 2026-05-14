#!/usr/bin/env python3
"""Decrypt Pioneer X-HM72 bCoD v3 firmware.

Cipher: Blowfish-ECB + fixed IV XOR
  P[k] = BF_ECB_decrypt(C[k]) XOR iv_const   (for every 8-byte block k)
Key and IV from CNE config store (NAND 0x048570):
  BCDEncryption_BFKey = xMH51VAHreenoiPx
  BCDEncryption_BFIV  = hcba0256  (used as static XOR mask, NOT CBC IV)
"""

import sys, zlib
from Crypto.Cipher import Blowfish

KEY = b'xMH51VAHreenoiPx'
IV  = b'hcba0256'          # 8-byte static XOR mask

# bCoD header offsets (relative to bCoD magic at file+0x20)
BCOD_OUTER = 0x20           # outer wrapper size in Pioneer .fw
PAYLOAD_OFFSET = 0x20 + 0xC0   # = 0xE0

def decrypt_payload(data: bytes) -> bytes:
    n = (len(data) // 8) * 8
    ecb = Blowfish.new(KEY, Blowfish.MODE_ECB)
    dec = ecb.decrypt(data[:n])
    result = bytearray(n)
    for i in range(0, n, 8):
        for j in range(8):
            result[i+j] = dec[i+j] ^ IV[j]
    return bytes(result) + data[n:]

def decrypt_fw(fw_path: str, out_path: str):
    fw = open(fw_path, 'rb').read()
    payload = fw[PAYLOAD_OFFSET:]
    dec = decrypt_payload(payload)
    open(out_path, 'wb').write(dec)

    # Verify
    image_size = 0x80466C
    cne_size   = 0x00C290
    crc_img = zlib.crc32(dec[:image_size]) & 0xffffffff
    crc_cne = zlib.crc32(dec[image_size:image_size+cne_size]) & 0xffffffff
    print(f"Written: {out_path} ({len(dec)} bytes)")
    print(f"Image CRC: 0x{crc_img:08x}  {'✓' if crc_img==0x9c8552f9 else '✗ MISMATCH'}")
    print(f"CNE CRC:   0x{crc_cne:08x}  {'✓' if crc_cne==0xb59d27bc else '✗ MISMATCH'}")

if __name__ == '__main__':
    fw  = sys.argv[1] if len(sys.argv) > 1 else 'HMx2015APP1010.fw'
    out = sys.argv[2] if len(sys.argv) > 2 else fw.replace('.fw', '_decrypted.bin')
    decrypt_fw(fw, out)
