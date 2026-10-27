"""Analogy: the ways a packer can fill one box — each turns the box's plain
contents into fewer bytes, and back again exactly.

Page encodings. Every encoder takes one page's PLAIN bytes (the values
packed back to back at the column's fixed width, as Day 2 stored them) and
returns encoded bytes; every decoder turns those bytes back into the very
same plain bytes. The encodings never need to know what the values mean.
"""

import struct
from collections.abc import Callable

# A 4-byte count, stored inside a page: how many distinct values a
# dictionary page holds.
COUNT = struct.Struct("<I")
# Dictionary codes are one byte each, so a dictionary holds at most 256 values.
MAX_DICTIONARY = 256


def split(codec: struct.Struct, data: bytes) -> list[bytes]:
    """Cut plain page bytes into one fixed-width piece per value."""
    return [data[k : k + codec.size] for k in range(0, len(data), codec.size)]


def plain(codec: struct.Struct, data: bytes) -> bytes:
    """Analogy: full-size compartments — the box packed as Day 2 packed it.

    The plain encoding stores the plain bytes unchanged.
    """
    return data


def from_plain(codec: struct.Struct, raw: bytes, rows: int) -> bytes:
    """Decode a plain page: its bytes already are the plain bytes."""
    return raw


def dictionary(codec: struct.Struct, data: bytes) -> bytes:
    """Analogy: the lid legend — every distinct value written once on the
    lid, and inside the box one small legend number per value.

    Layout: COUNT (how many distinct values), the distinct values at the
    column's width in first-seen order, then one 1-byte code per value.
    """
    values = split(codec, data)
    legend = list(dict.fromkeys(values))  # distinct, in first-seen order
    if len(legend) > MAX_DICTIONARY:
        raise ValueError(
            f"a dictionary holds at most {MAX_DICTIONARY} values; "
            f"this page has {len(legend)}"
        )
    code_of = {value: code for code, value in enumerate(legend)}
    codes = bytes(code_of[value] for value in values)
    return COUNT.pack(len(legend)) + b"".join(legend) + codes


def from_dictionary(codec: struct.Struct, raw: bytes, rows: int) -> bytes:
    """Decode a dictionary page: look every code up in the legend."""
    (count,) = COUNT.unpack(raw[: COUNT.size])
    codes_start = COUNT.size + count * codec.size
    legend = split(codec, raw[COUNT.size : codes_start])
    return b"".join(legend[code] for code in raw[codes_start:])


Encoder = Callable[[struct.Struct, bytes], bytes]
Decoder = Callable[[struct.Struct, bytes, int], bytes]

# Every encoding by the name the metadata records, in the order a packer
# tries them.
ENCODINGS: dict[str, tuple[Encoder, Decoder]] = {
    "plain": (plain, from_plain),
    "dictionary": (dictionary, from_dictionary),
}


def encode(name: str, codec: struct.Struct, data: bytes) -> bytes:
    """Encode one page's plain bytes with the encoding called `name`."""
    encoder, _ = ENCODINGS[name]
    return encoder(codec, data)


def decode(name: str, codec: struct.Struct, raw: bytes, rows: int) -> bytes:
    """Decode one page's stored bytes back to its plain bytes."""
    _, decoder = ENCODINGS[name]
    return decoder(codec, raw, rows)
