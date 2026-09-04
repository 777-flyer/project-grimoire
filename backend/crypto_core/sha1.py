"""SHA-1 (FIPS 180-4), implemented from the spec. Used only by totp.py, for
compatibility with authenticator apps that hard-code HMAC-SHA1."""

_MASK32 = 0xFFFFFFFF

_H0 = (0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0)


def _rotl(x, n):
    return ((x << n) | (x >> (32 - n))) & _MASK32


def _pad(message: bytes) -> bytes:
    length_bits = (len(message) * 8) & 0xFFFFFFFFFFFFFFFF
    padded = message + b"\x80"
    while len(padded) % 64 != 56:
        padded += b"\x00"
    padded += length_bits.to_bytes(8, "big")
    return padded


def sha1(message: bytes) -> bytes:
    """Return the 20-byte SHA-1 digest of message."""
    padded = _pad(message)
    h0, h1, h2, h3, h4 = _H0

    for block_start in range(0, len(padded), 64):
        block = padded[block_start:block_start + 64]
        w = [0] * 80
        for i in range(16):
            w[i] = int.from_bytes(block[i * 4:i * 4 + 4], "big")
        for i in range(16, 80):
            w[i] = _rotl(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1)

        a, b, c, d, e = h0, h1, h2, h3, h4

        for i in range(80):
            if i < 20:
                f = (b & c) | (~b & d)
                k = 0x5A827999
            elif i < 40:
                f = b ^ c ^ d
                k = 0x6ED9EBA1
            elif i < 60:
                f = (b & c) | (b & d) | (c & d)
                k = 0x8F1BBCDC
            else:
                f = b ^ c ^ d
                k = 0xCA62C1D6

            temp = (_rotl(a, 5) + f + e + k + w[i]) & _MASK32
            e = d
            d = c
            c = _rotl(b, 30)
            b = a
            a = temp

        h0 = (h0 + a) & _MASK32
        h1 = (h1 + b) & _MASK32
        h2 = (h2 + c) & _MASK32
        h3 = (h3 + d) & _MASK32
        h4 = (h4 + e) & _MASK32

    return b"".join(word.to_bytes(4, "big") for word in (h0, h1, h2, h3, h4))


def sha1_hex(message: bytes) -> str:
    return sha1(message).hex()
