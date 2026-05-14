#!/usr/bin/env python3
"""SDS shell helper (port 9000)."""
import socket
import sys
import time

HOST = "192.168.1.12"
PORT = 9000


def open_shell():
    s = socket.socket()
    s.settimeout(4)
    s.connect((HOST, PORT))
    time.sleep(0.4)
    return s


PROMPT = "sds://>"


def read_until_prompt(s, timeout=4.0):
    end = time.monotonic() + timeout
    buf = b""
    s.settimeout(0.2)
    while time.monotonic() < end:
        try:
            chunk = s.recv(8192)
            if not chunk:
                break
            buf += chunk
            if buf.rstrip().endswith(PROMPT.encode()):
                break
        except socket.timeout:
            if buf.rstrip().endswith(PROMPT.encode()):
                break
            continue
    return buf.decode("latin1", "replace")


def cmd(s, c):
    # Ctrl-U clears line buffer, fresh start
    s.send(b"\x15")
    time.sleep(0.05)
    s.send(c.encode() + b"\r\n")
    raw = read_until_prompt(s, timeout=5.0)
    # Filter autocomplete echo: keep lines that don't look like incremental echoes
    out_lines = []
    for line in raw.splitlines():
        ls = line.strip()
        if not ls or ls == PROMPT:
            continue
        # autocomplete echo lines start with the typed prefix and grow incrementally,
        # often a full sequence on one line — drop anything that contains repeated
        # prefix tokens of the entered command
        if " " in ls and ls.count(c.split()[0]) >= 3:
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


if __name__ == "__main__":
    s = open_shell()
    for c in sys.argv[1:]:
        print(f"\n>>> {c}")
        print(cmd(s, c))
    s.close()
