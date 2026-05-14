#!/usr/bin/env python3
"""Backup the Favourites linked list from the X-HM72 SDS."""
import json
import re
import sys
import time

sys.path.insert(0, '/Users/tim/Coding/Firmware_Analyser/Pioneer_X-HM72/tools')
from sds import open_shell, cmd


def parse_value(s):
    m = re.search(r'Value=\s*(.*)', s, re.DOTALL)
    return m.group(1).rstrip() if m else None


def get(s, path):
    raw = cmd(s, f"get {path}")
    return parse_value(raw)


def main():
    s = open_shell()

    meta = {
        "FirstContent": get(s, "cne/Favourites/FirstContent"),
        "FirstFree": get(s, "cne/Favourites/FirstFree"),
        "NumberOfEntries": get(s, "cne/Favourites/NumberOfEntries"),
        "Enabled": get(s, "cne/Favourites/Enabled"),
    }
    print("Meta:", meta)

    # Trace content list from FirstContent until we hit a terminator
    visited = []
    cur = int(meta["FirstContent"])
    while cur not in visited and 0 <= cur < 100 and len(visited) < 110:
        nxt = get(s, f"cne/Favourites/Entry{cur}/next")
        ent = get(s, f"cne/Favourites/Entry{cur}/Entry")
        visited.append({"slot": cur, "next": nxt, "Entry": ent})
        try:
            cur = int(nxt)
        except (ValueError, TypeError):
            break

    free_chain = []
    cur = int(meta["FirstFree"])
    seen = set()
    while cur not in seen and 0 <= cur < 100 and len(free_chain) < 110:
        seen.add(cur)
        nxt = get(s, f"cne/Favourites/Entry{cur}/next")
        free_chain.append({"slot": cur, "next": nxt})
        try:
            cur = int(nxt)
        except (ValueError, TypeError):
            break

    snap = {"meta": meta, "content_list": visited, "free_list": free_chain}
    with open("/Users/tim/Coding/Firmware_Analyser/Pioneer_X-HM72/favourites_backup.json", "w") as f:
        json.dump(snap, f, indent=2, ensure_ascii=False)

    print(f"Content list: {len(visited)} entries")
    for v in visited:
        m = re.search(r'StationTitle="([^"]*)"', v["Entry"] or "")
        print(f"  slot {v['slot']:2d} → next {v['next']:>3}  {m.group(1) if m else '(empty)'}")
    print(f"Free list: {len(free_chain)} entries, chain: " + " → ".join(str(x['slot']) for x in free_chain[:20]) + ("..." if len(free_chain) > 20 else ""))

    s.close()


if __name__ == "__main__":
    main()
