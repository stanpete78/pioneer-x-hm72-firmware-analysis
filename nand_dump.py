#!/usr/bin/env python3
"""Dump NAND at given address and length via fburn rd + XMODEM-CRC16."""

import socket, sys, time, os

HOST = "192.168.1.12"
PORT = 9000

SOH = 0x01
EOT = 0x04
ACK = 0x06
NAK = 0x15
CAN = 0x18

def crc16(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
    return crc & 0xFFFF

def recv_n(sock, n, timeout=10.0):
    buf = b""
    deadline = time.time() + timeout
    while len(buf) < n:
        rem = deadline - time.time()
        if rem <= 0: raise TimeoutError(f"recv_n: want {n}, got {len(buf)}")
        sock.settimeout(min(rem, 2.0))
        try:
            chunk = sock.recv(n - len(buf))
        except socket.timeout: continue
        if not chunk: raise ConnectionError("closed")
        buf += chunk
    return buf

def recv_until(sock, marker, timeout=20.0):
    buf = b""
    deadline = time.time() + timeout
    while marker not in buf:
        if time.time() > deadline: raise TimeoutError(f"marker {marker!r} not found")
        sock.settimeout(2.0)
        try:
            chunk = sock.recv(256)
            if chunk: buf += chunk
        except socket.timeout: pass
    return buf

def drain(sock, t=1.0):
    sock.settimeout(0.1)
    buf = b""
    deadline = time.time() + t
    while time.time() < deadline:
        try: chunk = sock.recv(4096); buf += chunk if chunk else b""
        except socket.timeout: break
    return buf

def xmodem_receive(sock, outpath, expected_blocks):
    print(f"[XMODEM] Sending 'C'...")
    sock.sendall(b"C")
    received = 0
    expected_blk = 1
    retries = 0
    with open(outpath, "wb") as f:
        while True:
            try:
                first = recv_n(sock, 1, timeout=15.0)
            except TimeoutError:
                if retries < 3:
                    retries += 1
                    sock.sendall(b"C")
                    continue
                break
            b = first[0]
            if b == EOT:
                sock.sendall(bytes([ACK]))
                print(f"\n[XMODEM] EOT after {received} bytes ({received//128} blocks)")
                break
            if b == CAN:
                print("\n[XMODEM] CAN")
                break
            if b != SOH:
                drain(sock, 0.3)
                if retries < 5:
                    retries += 1
                    sock.sendall(b"C")
                continue
            rest = recv_n(sock, 132, timeout=5.0)
            blknum = rest[0]; inv = rest[1]; data = rest[2:130]
            crc_recv = (rest[130] << 8) | rest[131]
            if blknum != (expected_blk & 0xFF):
                if blknum == ((expected_blk - 1) & 0xFF):
                    sock.sendall(bytes([ACK]))
                    continue
                sock.sendall(bytes([NAK]))
                continue
            if (blknum ^ inv) != 0xFF:
                sock.sendall(bytes([NAK]))
                continue
            if crc16(data) != crc_recv:
                sock.sendall(bytes([NAK]))
                retries += 1
                continue
            f.write(data)
            received += len(data)
            expected_blk += 1
            retries = 0
            sock.sendall(bytes([ACK]))
            if expected_blk % 256 == 1:
                pct = received / (expected_blocks * 128) * 100
                print(f"\r[XMODEM] {pct:.1f}% ({received//1024} KB)", end="", flush=True)
    return received

def dump_nand(flash_id, addr, length, output_path):
    blocks = (length + 127) // 128
    print(f"Dumping NAND flash{flash_id} 0x{addr:x}+0x{length:x} ({length//1024} KB, {blocks} blocks) → {output_path}")

    sock = socket.socket()
    sock.connect((HOST, PORT))
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    # Drain any stale XMODEM data and get clean prompt
    drain(sock, 1.0)
    sock.sendall(b"\r\n")
    time.sleep(0.5)
    out = drain(sock, 2.0)
    if b"sds://" not in out:
        # Try harder
        sock.sendall(b"\x03\r\n")
        time.sleep(0.5)
        out2 = drain(sock, 2.0)
        if b"sds://" not in out and b"sds://" not in out2:
            raise RuntimeError(f"No prompt: {(out+out2)[-100:]}")
    drain(sock, 0.3)

    cmd = f"fburn rd {flash_id} 0x{addr:x} 0x{length:x}\r\n".encode()
    print(f"Sending: {cmd.decode().strip()}")
    sock.sendall(cmd)

    banner = recv_until(sock, b"xmodem", 15.0)
    print(f"Got: {banner.decode('latin1', errors='replace').split(chr(10))[-2].strip()}")
    time.sleep(0.2)

    n = xmodem_receive(sock, output_path, blocks)
    sock.close()

    size = os.path.getsize(output_path)
    print(f"\nDone: {size} bytes written")
    if size > 0:
        with open(output_path, "rb") as f:
            preview = f.read(48)
        print(f"First 48 bytes: {preview.hex()}")
        print(f"As ASCII: {preview}")
    return n

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: nand_dump2.py <flash_id> <hex_addr> <hex_len> <output>")
        sys.exit(1)
    flash_id = int(sys.argv[1])
    addr = int(sys.argv[2], 16)
    length = int(sys.argv[3], 16)
    output = sys.argv[4]
    dump_nand(flash_id, addr, length, output)
