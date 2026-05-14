#!/usr/bin/env python3
"""Add a working favorite to X-HM72 via direct SDS write.

The Pioneer's native vTuner backend is dead, so we use the FritzBox DLNA proxy
(SourceContentBrowser="upnp") which the device accepts as a playable stream.

Usage:
    python3 fav_add.py "Station Name" <fritzbox-dlna-url> [bps]

URL must be the FritzBox proxy URL:
    http://192.168.1.1:49200/ST/AUDIO/DLNA-1-0/<host>/<path>

Discover URLs via UPnP browse (see FAVORITES.md) — or first add the station in
the FritzBox web UI under "Heimnetz → Mediaserver → Internetradio".
"""
import socket
import sys
import time

sys.path.insert(0, '/Users/tim/Coding/Firmware_Analyser/Pioneer_X-HM72/tools')
from sds import open_shell, cmd


def parse_int(raw):
    import re
    m = re.search(r'Value=\s*(-?\d+)', raw)
    return int(m.group(1)) if m else None


def build_xml(title, url, artist=None, bps=128000):
    artist = artist or title
    return (
        f'<SongDescriptor ActiveAudioResource="0" '
        f'StationTitle="{title}" '
        f'SourceContentBrowser="upnp" '
        f'Artist="{artist}" '
        f'LiveStream="">'
        f'<SongResource Url="{url}" '
        f'Mime="mp3" '
        f'Bps="{bps}" '
        f'Fs="44100" '
        f'BitsPerSample="16" '
        f'Channels="2" '
        f'NoTimeSeek="" '
        f'DLNA.ORG_OP="01" '
        f'DLNA.ORG_FLAGS="01700000000000000000000000000000"/>'
        f'</SongDescriptor>'
    )


def trigger_reload():
    """Cycle input 44→45 via port 8102 so the device re-parses the favorites."""
    s = socket.socket()
    s.settimeout(3)
    s.connect(('192.168.1.12', 8102))
    s.send(b'44FN\r\n')
    time.sleep(1.5)
    s.send(b'45FN\r\n')
    time.sleep(1.0)
    try:
        s.recv(2048)
    except socket.timeout:
        pass
    s.close()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    title = sys.argv[1]
    url = sys.argv[2]
    bps = int(sys.argv[3]) if len(sys.argv) > 3 else 128000

    xml = build_xml(title, url, bps=bps)
    s = open_shell()

    cur_first_content = parse_int(cmd(s, "get cne/Favourites/FirstContent"))
    cur_first_free = parse_int(cmd(s, "get cne/Favourites/FirstFree"))
    next_free = parse_int(cmd(s, f"get cne/Favourites/Entry{cur_first_free}/next"))

    print(f"FirstContent={cur_first_content} FirstFree={cur_first_free} (next free={next_free})")
    print(f"Writing slot {cur_first_free}: {title}")
    print(f"  URL: {url}")

    target = cur_first_free
    cmd(s, f"set cne/Favourites/Entry{target}/Entry '{xml}'")
    cmd(s, f"set cne/Favourites/Entry{target}/next {cur_first_content}")
    cmd(s, f"set cne/Favourites/FirstFree {next_free}")
    cmd(s, f"set cne/Favourites/FirstContent {target}")
    s.close()

    print("Triggering parser reload via input cycle 44FN → 45FN ...")
    time.sleep(1)
    trigger_reload()
    print("Done. Check device — new favorite should be at top of list with flag 102.")


if __name__ == "__main__":
    main()
