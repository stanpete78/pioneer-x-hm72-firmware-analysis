#!/usr/bin/env python3
"""Extract HTML/ASP pages from decrypted Pioneer X-HM72 firmware.

Two extraction strategies are used:

1. Filename-prefixed blocks
   Pioneer's web content is stored as `<path>\x00<!DOCTYPE...>` records.
   This gives 30 files with their real firmware paths (notice/, /1000/*.asp, etc).

2. Content fingerprinting for BridgeCo WAA pages
   The WAA pages are packed back-to-back with no path prefix.
   We identify them by signature in the HTML body and map to their real
   filename (the path the BridgeCo HTTP server serves them under on port 8080).

Usage: python3 extract_html.py <decrypted_firmware.bin> [output_dir]
"""

import os
import re
import sys


# Map of (search-substring, real WAA filename). Matched in order; first hit wins.
WAA_FINGERPRINTS = [
    (b'document.Power.submit()',                'remote_control2.html'),  # 22 KB, 34 buttons
    (b'screen_capture2.bmp',                    'screen_display.html'),
    (b'src="remote_control2.html"',             'remote_if_framed2.html'),
    (b'src="remote_control.html"',              'remote_if_framed.html'),
    (b'<title>Wave Radio Testpage</title>',     'test.html'),
    (b'<title>Network Status</title>',          'status_network.html'),
    (b'<title>Hard Boot information</title>',   'hard_boot_information.html'),
    (b'<title>Hard Boot</title>',               'hard_boot_frame.html'),
    (b'<title>Soft Boot information</title>',   'soft_boot_information.html'),
    (b'<title>Soft Boot</title>',               'soft_boot_frame.html'),
    (b'<title>Firmware status</title>',         'status_firmware.html'),
    (b'<title>TCP/IP Settings</title>',         'config_tcpip.html'),
    (b'<title>Wireless Configuration</title>',  'config_wireless.html'),
    (b'<title>Device Configuration</title>',    'config_device.html'),
    (b'<title>Configuration</title>',           'configuration_frame.html'),
    (b'<title>FAQ</title>',                     'faq_frame.html'),
    (b'<title>Troubleshooting</title>',         'troubleshooting_frame.html'),
    (b'<title>Factory Defaults</title>',        'factory_def_frame.html'),
    (b'<title>Top Frame</title>',               'header.html'),
    (b'<title>Left Frame</title>',              'menu.html'),
    # Catch-all for the smaller WAA Screen Capture (image-map remote, no JS)
    (b'<title>WAA Screen Capture</title>',      'remote_control.html'),
]


def extract_prefixed(data: bytes) -> dict:
    """Find `<path>\x00<DOCTYPE|<html>` records — Pioneer's labelled web content."""
    pattern = re.compile(
        rb'((?:/[\w./-]+/)?[\w.-]+\.(?:html|asp))\x00'
        rb'(<!DOCTYPE|<html|<HTML)',
        re.IGNORECASE,
    )
    out = {}
    for m in pattern.finditer(data):
        name = m.group(1).decode('latin1').lstrip('/')
        start = m.start(2)
        end = data.find(b'</html>', start)
        if end < 0:
            continue
        body = data[start:end + 7]
        if name not in out or len(body) > len(out[name]):
            out[name] = body
    return out


def extract_waa(data: bytes, taken: set) -> dict:
    """Carve back-to-back <html>...</html> blocks and identify WAA pages by signature."""
    out = {}
    for m in re.finditer(rb'<html>', data, re.IGNORECASE):
        start = m.start()
        end = data.find(b'</html>', start)
        if end < 0:
            continue
        body = data[start:end + 7]
        # Skip blocks already covered by prefixed extraction
        if any(body == v for v in taken):
            continue
        # Match against fingerprints
        for sig, fname in WAA_FINGERPRINTS:
            if sig in body and fname not in out:
                out[fname] = body
                break
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    firmware = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else 'webui'

    with open(firmware, 'rb') as f:
        data = f.read()

    prefixed = extract_prefixed(data)
    waa = extract_waa(data, set(prefixed.values()))

    os.makedirs(out_dir, exist_ok=True)
    all_files = {**prefixed, **waa}

    for name, body in sorted(all_files.items()):
        path = os.path.join(out_dir, name)
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'wb') as f:
            f.write(body)

    print(f'Wrote {len(all_files)} files to {out_dir}/')
    print(f'  {len(prefixed)} with explicit firmware paths')
    print(f'  {len(waa)} BridgeCo WAA pages identified by content signature')


if __name__ == '__main__':
    main()
