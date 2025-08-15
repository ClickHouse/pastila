#!/usr/bin/python3

import base64
import json
import os
import sys
from random import randint
from typing import List
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

#
# Script to upload/download to/from pastila.nl from command line.
# Put it somewhere in PATH and use like this:
#
# % echo henlo | pastila.py
# https://pastila.nl/?cafebabe/c8570701492af2ac7269064a661686e3#oj6jpBCRzIOSGTgRFgMquA==
#
# % pastila.py 'https://pastila.nl/?cafebabe/c8570701492af2ac7269064a661686e3#oj6jpBCRzIOSGTgRFgMquA=='
# henlo
#


def sipHash128(m: bytes) -> str:
    mask = (1 << 64) - 1

    def rotl(v: List[int], offset: int, bits: int) -> None:
        v[offset] = ((v[offset] << bits) & mask) | ((v[offset] & mask) >> (64 - bits))

    def compress(v: List[int]) -> None:
        v[0] += v[1]
        v[2] += v[3]
        rotl(v, 1, 13)
        rotl(v, 3, 16)
        v[1] ^= v[0]
        v[3] ^= v[2]
        rotl(v, 0, 32)
        v[2] += v[1]
        v[0] += v[3]
        rotl(v, 1, 17)
        rotl(v, 3, 21)
        v[1] ^= v[2]
        v[3] ^= v[0]
        rotl(v, 2, 32)

    v = [0x736F6D6570736575, 0x646F72616E646F6D, 0x6C7967656E657261, 0x7465646279746573]
    offset = 0
    while offset < len(m) - 7:
        word = int.from_bytes(m[offset : offset + 8], "little")
        v[3] ^= word
        compress(v)
        compress(v)
        v[0] ^= word
        offset += 8

    buf = bytearray(8)
    buf[: len(m) - offset] = m[offset:]
    buf[7] = len(m) & 0xFF

    word = int.from_bytes(buf, "little")
    v[3] ^= word
    compress(v)
    compress(v)
    v[0] ^= word
    v[2] ^= 0xFF
    compress(v)
    compress(v)
    compress(v)
    compress(v)

    hash_val = ((v[0] ^ v[1]) & mask) + (((v[2] ^ v[3]) & mask) << 64)
    s = f"{hash_val:032x}"
    return "".join(s[i : i + 2] for i in range(30, -2, -2))


def is_valid_hex(s: str) -> bool:
    return bool(s) and all(c in "0123456789abcdefABCDEF" for c in s)


def error(s: str) -> None:
    sys.stderr.write(f"error: {s}\n")
    sys.exit(1)


def load(url: str) -> bytes:
    parsed = urlparse(url)
    try:
        fingerprint, hash_hex = parsed.query.split("/", maxsplit=1)
    except ValueError:
        error(f"invalid url: {url}")
    hash_hex = hash_hex.split(".", maxsplit=1)[0]  # for .diff, .md etc
    key = parsed.fragment
    if not (is_valid_hex(fingerprint) and is_valid_hex(hash_hex)):
        error(f"invalid url: {url}")

    query = (
        "SELECT content, is_encrypted FROM "
        f"data_view(fingerprint = '{fingerprint}', hash = '{hash_hex}') FORMAT JSON"
    )

    req = Request(
        "https://uzg8q0g12h.eu-central-1.aws.clickhouse.cloud/?user=paste",
        data=query.encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req) as response:
            body = response.read().decode("utf-8")
    except Exception as e:
        error(f"failed to fetch paste: {e}")

    j = json.loads(body)
    if j["rows"] != 1:
        error("paste not found")
    # if 'statistics' in j: sys.stderr.write(f"{j['statistics']}")
    content, is_encrypted = (
        j["data"][0]["content"],
        j["data"][0]["is_encrypted"],
    )  # type: str, int

    if not is_encrypted:
        return content.encode("utf-8")

    if not key:
        error("paste is encrypted, but no key provided in the URL")
    decoded = base64.b64decode(content)
    cipher = Cipher(
        algorithms.AES(base64.b64decode(key)),
        modes.CTR(b"\x00" * 16),
        backend=default_backend(),
    )
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(decoded) + decryptor.finalize()
    return decrypted


def save(data: bytes) -> str:
    key = os.urandom(16)
    url_suffix = ""
    cipher = Cipher(
        algorithms.AES(key), modes.CTR(b"\x00" * 16), backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(data) + encryptor.finalize()
    data = base64.b64encode(encrypted)
    url_suffix = "#" + base64.b64encode(key).decode()

    h = sipHash128(data)
    fingerprint = f"{randint(0, 0xFFFFFFFF):08x}"

    payload = json.dumps(
        {
            "fingerprint_hex": fingerprint,
            "hash_hex": h,
            "content": data.decode(),
            "is_encrypted": 1,
        }
    )
    req = Request(
        "https://uzg8q0g12h.eu-central-1.aws.clickhouse.cloud/?user=paste",
        data="INSERT INTO data (fingerprint_hex, hash_hex, content, is_encrypted) "
        f"FORMAT JSONEachRow {payload}".encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req):
            pass
    except Exception as e:
        error(f"failed to save paste: {e}")

    return f"https://pastila.nl/?{fingerprint}/{h}{url_suffix}"


if __name__ == "__main__":
    if len(sys.argv) == 1:
        data = sys.stdin.buffer.read()
        print(save(data))
    elif len(sys.argv) == 2:
        data = load(sys.argv[1])
        sys.stdout.buffer.write(data)
    else:
        print("usage: pastila.py [url]")
        sys.exit(1)
