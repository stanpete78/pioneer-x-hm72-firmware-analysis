#!/usr/bin/env python3
"""Extract ALL HTML pages (including <html>-only, no DOCTYPE) with title-based names."""

import os
import re

FIRMWARE = "HMx2015APP1010_decrypted_correct.bin"
OUT_DIR = "webui"
os.makedirs(OUT_DIR, exist_ok=True)

with open(FIRMWARE, "rb") as f:
    data = f.read()

pages = []

# Find both <!DOCTYPE and bare <html> starts
for match in re.finditer(rb'(?:<!DOCTYPE[^>]+>\s*)?<html>', data, re.IGNORECASE):
    start = match.start()
    end_m = re.search(rb'</html>', data[start:start+500000], re.IGNORECASE)
    if not end_m:
        continue
    end = start + end_m.end()
    content = data[start:end]
    title_m = re.search(rb'<title>([^<]+)</title>', content, re.IGNORECASE)
    title = title_m.group(1).decode('latin1', 'replace').strip() if title_m else ''
    pages.append((start, end, title, content))

# Sort by offset
pages.sort(key=lambda x: x[0])

# Remove duplicates (same offset or content included in a larger page)
filtered = []
last_end = 0
for start, end, title, content in pages:
    if start < last_end:
        continue  # skip nested
    filtered.append((start, end, title, content))
    last_end = end

print(f"Found {len(filtered)} HTML pages\n")

# Sanitize title for filename
def safe_name(title, idx):
    if not title:
        return f"page_{idx:04d}.html"
    s = re.sub(r'[^a-zA-Z0-9_\- ]', '', title)
    s = s.strip().replace(' ', '_')[:50]
    return f"{s}.html" if s else f"page_{idx:04d}.html"

name_counts = {}
for i, (start, end, title, content) in enumerate(filtered):
    base = safe_name(title, i)
    n = name_counts.get(base, 0)
    name_counts[base] = n + 1
    fname = base if n == 0 else base.replace('.html', f'_{n}.html')
    path = os.path.join(OUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(content)
    print(f"  [{i:3d}] 0x{start:08X}  {len(content):6d}b  {fname}")
    if title:
        print(f"       Title: {title}")

print(f"\n{len(filtered)} files written to ./{OUT_DIR}/")
