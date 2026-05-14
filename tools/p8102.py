#!/usr/bin/env python3
"""Port 8102 tester for X-HM72.

Usage:
    python3 tools/p8102.py CMD [CMD ...]            send one or more, then listen 2s
    python3 tools/p8102.py --wait 5 CMD              wait 5s after sends
    python3 tools/p8102.py --listen 10                no send, just listen
    python3 tools/p8102.py --host 192.168.1.12 ...

Lines from device are decoded and timestamped.
"""
import argparse
import socket
import sys
import time

DEFAULT_HOST = "192.168.1.12"
DEFAULT_PORT = 8102


def drain(sock, seconds):
    end = time.monotonic() + seconds
    buf = b""
    sock.settimeout(0.2)
    while time.monotonic() < end:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                print("[disconnected]")
                return
            buf += chunk
            while b"\r\n" in buf:
                line, buf = buf.split(b"\r\n", 1)
                ts = time.strftime("%H:%M:%S")
                try:
                    print(f"{ts}  < {line.decode('utf-8', 'replace')}")
                except Exception:
                    print(f"{ts}  < {line!r}")
        except socket.timeout:
            continue
    if buf:
        print(f"  [partial buffer: {buf!r}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--wait", type=float, default=2.0,
                    help="seconds to listen after sends (default 2)")
    ap.add_argument("--listen", type=float, default=0.0,
                    help="seconds to listen without sending")
    ap.add_argument("--gap", type=float, default=0.3,
                    help="seconds between commands (default 0.3)")
    ap.add_argument("cmds", nargs="*", help="commands to send (no CRLF)")
    args = ap.parse_args()

    s = socket.socket()
    s.settimeout(3.0)
    s.connect((args.host, args.port))

    if args.listen and not args.cmds:
        print(f"[listening {args.listen}s]")
        drain(s, args.listen)
        s.close()
        return

    for i, cmd in enumerate(args.cmds):
        line = cmd.encode("ascii") + b"\r\n"
        ts = time.strftime("%H:%M:%S")
        print(f"{ts}  > {cmd}")
        s.send(line)
        if i < len(args.cmds) - 1:
            drain(s, args.gap)

    drain(s, args.wait)
    s.close()


if __name__ == "__main__":
    main()
