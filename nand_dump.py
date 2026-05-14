#!/usr/bin/env python3
"""NAND bootloader dump via fburn rd + XMODEM-CRC16."""

import socket
import sys
import time
import os

HOST = "192.168.1.12"
PORT = 9000
OUTPUT = "/Users/tim/Coding/Firmware_Analyser/Pioneer_X-HM72/nand_bootloader.bin"

SOH = 0x01
EOT = 0x04
ACK = 0x06
NAK = 0x15
CAN = 0x18

def crc16(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
    return crc & 0xFFFF


def recv_n(sock: socket.socket, n: int, timeout: float = 10.0) -> bytes:
    """Receive exactly n bytes, raise on timeout."""
    buf = b""
    deadline = time.time() + timeout
    while len(buf) < n:
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError(f"recv_n: want {n}, got {len(buf)}")
        sock.settimeout(min(remaining, 2.0))
        try:
            chunk = sock.recv(n - len(buf))
        except socket.timeout:
            continue
        if not chunk:
            raise ConnectionError("Socket closed")
        buf += chunk
    return buf


def recv_until(sock: socket.socket, marker: bytes, timeout: float = 15.0) -> bytes:
    """Receive bytes until marker found, return all data including marker."""
    buf = b""
    deadline = time.time() + timeout
    while marker not in buf:
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError(f"recv_until: marker {marker!r} not found in {len(buf)} bytes")
        sock.settimeout(min(remaining, 2.0))
        try:
            chunk = sock.recv(256)
        except socket.timeout:
            continue
        if not chunk:
            raise ConnectionError("Socket closed")
        buf += chunk
    return buf


def drain(sock: socket.socket, duration: float = 1.0):
    """Drain any pending data."""
    sock.settimeout(0.1)
    deadline = time.time() + duration
    total = 0
    while time.time() < deadline:
        try:
            d = sock.recv(4096)
            if d:
                total += len(d)
        except socket.timeout:
            break
    return total


def clear_line(sock: socket.socket):
    """Send Ctrl+U to clear any partial input, then Ctrl+C."""
    sock.sendall(b"\x15")  # Ctrl+U
    time.sleep(0.1)
    sock.sendall(b"\x03")  # Ctrl+C
    time.sleep(0.1)
    drain(sock, 0.5)


def wait_for_prompt(sock: socket.socket, timeout: float = 20.0) -> bool:
    """Wait for sds://> prompt."""
    buf = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        sock.settimeout(2.0)
        try:
            chunk = sock.recv(512)
        except socket.timeout:
            # Send a newline prod
            sock.sendall(b"\r\n")
            continue
        if not chunk:
            return False
        buf += chunk
        sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()
        if b"sds://" in buf and b">" in buf:
            return True
    return False


def xmodem_receive(sock: socket.socket, outpath: str, expected_blocks: int) -> int:
    """Perform XMODEM-CRC16 receive. Returns number of bytes written."""
    # Send initial C to request CRC mode
    print("[XMODEM] Sending 'C' to start CRC mode...")
    sock.sendall(b"C")

    received = 0
    expected_blk = 1
    last_data = b""
    retries = 0

    with open(outpath, "wb") as f:
        while True:
            # Read first byte to determine packet type
            sock.settimeout(15.0)
            try:
                first = recv_n(sock, 1, timeout=15.0)
            except TimeoutError:
                print(f"\n[XMODEM] Timeout waiting for block {expected_blk}")
                # Try sending C again
                if retries < 3:
                    retries += 1
                    sock.sendall(b"C")
                    continue
                break

            b = first[0]

            if b == EOT:
                print(f"\n[XMODEM] EOT received after {received} bytes ({received//128} blocks)")
                sock.sendall(bytes([ACK]))
                break

            if b == CAN:
                print(f"\n[XMODEM] CAN (cancel) received")
                break

            if b != SOH:
                print(f"\n[XMODEM] Unexpected byte 0x{b:02x}, draining...")
                drain(sock, 0.5)
                if retries < 5:
                    retries += 1
                    sock.sendall(b"C")
                continue

            # SOH received — read rest of block (132 bytes)
            rest = recv_n(sock, 132, timeout=5.0)
            blknum = rest[0]
            inv_blknum = rest[1]
            data = rest[2:130]
            crc_hi = rest[130]
            crc_lo = rest[131]
            crc_recv = (crc_hi << 8) | crc_lo
            crc_calc = crc16(data)

            # Validate block number
            if blknum != (expected_blk & 0xFF):
                print(f"\n[XMODEM] Block# mismatch: got {blknum}, expected {expected_blk & 0xFF}")
                # Could be a duplicate — if it's expected-1, just re-ACK
                if blknum == ((expected_blk - 1) & 0xFF):
                    print(f"  → Duplicate block, re-ACKing")
                    sock.sendall(bytes([ACK]))
                    continue
                sock.sendall(bytes([NAK]))
                continue

            if (blknum ^ inv_blknum) != 0xFF:
                print(f"\n[XMODEM] Block complement error: {blknum:02x} ^ {inv_blknum:02x} != FF")
                sock.sendall(bytes([NAK]))
                continue

            if crc_recv != crc_calc:
                print(f"\n[XMODEM] CRC error block {expected_blk}: got {crc_recv:04x}, calc {crc_calc:04x}")
                sock.sendall(bytes([NAK]))
                retries += 1
                continue

            # Good block
            f.write(data)
            received += len(data)
            expected_blk += 1
            retries = 0
            sock.sendall(bytes([ACK]))

            if expected_blk % 64 == 1:
                pct = received / (expected_blocks * 128) * 100
                print(f"\r[XMODEM] Block {expected_blk-1}/{expected_blocks} ({pct:.1f}%) {received} bytes", end="", flush=True)

    return received


def main():
    print(f"Connecting to {HOST}:{PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    print("Waiting for shell prompt...")
    # First drain any pending data (could be leftover XMODEM garbage)
    drained = drain(sock, 2.0)
    if drained:
        print(f"  Drained {drained} bytes of stale data")

    # Try to get to clean prompt
    clear_line(sock)
    time.sleep(0.3)

    if not wait_for_prompt(sock, timeout=20.0):
        print("ERROR: No shell prompt. Trying Ctrl+C + CR...")
        sock.sendall(b"\x03\r\n")
        time.sleep(1.0)
        drain(sock, 1.0)
        sock.sendall(b"\r\n")
        if not wait_for_prompt(sock, timeout=15.0):
            print("FATAL: Cannot get shell prompt")
            sock.close()
            sys.exit(1)

    print("\nGot prompt. Sending fburn rd command...")
    drain(sock, 0.5)

    # Send fburn command
    cmd = b"fburn rd 0 0x0 0x80000\r\n"
    sock.sendall(cmd)

    print("Waiting for 'Start xmodem now!'...")
    try:
        banner = recv_until(sock, b"xmodem", timeout=15.0)
        print(f"Got: {banner.decode('latin1', errors='replace').strip()}")
    except TimeoutError:
        print("ERROR: No xmodem prompt received")
        print("Raw data so far:")
        sock.close()
        sys.exit(1)

    # Small pause then start XMODEM
    time.sleep(0.2)

    # 512 KB / 128 bytes per block = 4096 blocks
    EXPECTED_BLOCKS = 4096
    print(f"\nStarting XMODEM-CRC16 receive ({EXPECTED_BLOCKS} blocks = 512 KB)...")

    n = xmodem_receive(sock, OUTPUT, EXPECTED_BLOCKS)
    print(f"\nDone: {n} bytes written to {OUTPUT}")

    sock.close()

    # Verify
    size = os.path.getsize(OUTPUT)
    print(f"File size: {size} bytes")
    if size > 0:
        with open(OUTPUT, "rb") as f:
            preview = f.read(32)
        print(f"First 32 bytes: {preview.hex()}")


if __name__ == "__main__":
    main()
