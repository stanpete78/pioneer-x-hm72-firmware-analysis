#!/usr/bin/env python3
"""Extract embedded HTML/JS/CSS files from Pioneer X-HM72 decrypted firmware."""

import os
import re

FIRMWARE = "HMx2015APP1010_decrypted_correct.bin"
OUT_DIR = "webui"

os.makedirs(OUT_DIR, exist_ok=True)

with open(FIRMWARE, "rb") as f:
    data = f.read()

# Find all null-terminated or length-prefixed strings that look like HTML/JS filenames
# BridgeCo embeds files as raw bytes with filename references in the code
# Strategy: find "<!DOCTYPE" or "<html" markers, then scan backward for null to find filename,
# and forward for </html> to find end.

# Also extract .js and .css by looking for their content patterns

results = []

# Pattern 1: find HTML documents
for match in re.finditer(rb'<!DOCTYPE HTML', data, re.IGNORECASE):
    start = match.start()
    # Find end: </html> tag
    end_match = re.search(rb'</html>', data[start:start+500000], re.IGNORECASE)
    if end_match:
        end = start + end_match.end()
        results.append(("html", start, end))

# Pattern 2: look for filenames referenced just before HTML blocks
# BridgeCo stores filename as null-terminated string followed by content
# Try to find filename by looking backwards from start for printable chars ending in .html/.js/.css
def find_filename_before(data, pos, max_back=256):
    """Try to find a filename string just before pos."""
    # look for null-terminated string ending just before pos
    segment = data[max(0, pos-max_back):pos]
    # scan backward for null byte, then check if that region is a valid filename
    for i in range(len(segment)-1, -1, -1):
        if segment[i] == 0:
            candidate = segment[i+1:]
            try:
                s = candidate.decode("ascii")
                if re.match(r'^[\w\-./]+\.(html|htm|js|css|xml|asp)$', s, re.IGNORECASE):
                    return s
            except Exception:
                pass
    return None

# Write extracted HTML files
html_count = 0
for kind, start, end in results:
    content = data[start:end]
    fname = find_filename_before(data, start)
    if not fname:
        fname = f"page_{html_count:04d}.html"
    else:
        # sanitize path separators
        fname = fname.replace("/", "_").lstrip("_")

    out_path = os.path.join(OUT_DIR, fname)
    # avoid overwrites
    if os.path.exists(out_path):
        base, ext = os.path.splitext(fname)
        out_path = os.path.join(OUT_DIR, f"{base}_{html_count}{ext}")

    with open(out_path, "wb") as f:
        f.write(content)
    print(f"  [0x{start:08X}] {out_path}  ({len(content)} bytes)")
    html_count += 1

# Also extract JavaScript files (look for "function " at start of content blocks)
js_results = []
for match in re.finditer(rb'(?:^|\x00)([\w\-]+\.js)\x00', data):
    fname_bytes = match.group(1)
    try:
        fname = fname_bytes.decode("ascii")
    except Exception:
        continue
    pos = match.end()
    # read up to 200KB or next null-padded section
    chunk = data[pos:pos+200000]
    # find end: look for double-null or next filename marker
    end_idx = chunk.find(b'\x00\x00\x00\x00')
    if end_idx > 100:
        content = chunk[:end_idx].rstrip(b'\x00')
        if content and b'function' in content:
            out_path = os.path.join(OUT_DIR, fname)
            if not os.path.exists(out_path):
                with open(out_path, "wb") as f:
                    f.write(content)
                print(f"  [0x{pos:08X}] {out_path}  ({len(content)} bytes)")

print(f"\nDone. {html_count} HTML files extracted to ./{OUT_DIR}/")
print("Open with: open webui/page_0000.html")
