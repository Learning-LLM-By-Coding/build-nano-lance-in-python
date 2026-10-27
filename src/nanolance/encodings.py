"""Analogy: the ways a packer can fill one box — each turns the box's plain
contents into fewer bytes, and back again exactly.

Page encodings. Every encoder takes one page's PLAIN bytes (the values
packed back to back at the column's fixed width, as Day 2 stored them) and
returns encoded bytes; every decoder turns those bytes back into the very
same plain bytes. The encodings never need to know what the values mean.
"""

import struct
from collections.abc import Callable
from itertools import groupby

# A 4-byte count, stored inside a page: how many distinct values a
# dictionary page holds, or how long one run is.
COUNT = struct.Struct("<I")
# Dictionary codes are one byte each, so a dictionary holds at most 256 values.
MAX_DICTIONARY = 256
# One byte at the start of a bit-packed page: how many bits each value takes.
WIDTH = struct.Struct("<B")


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


def run_length(codec: struct.Struct, data: bytes) -> bytes:
    """Analogy: stacks — equal values side by side stacked together, one
    value with a sticker saying how many.

    Layout: for each run of equal values, the value at the column's width
    followed by COUNT, the run's length.
    """
    runs = [
        value + COUNT.pack(len(list(run))) for value, run in groupby(split(codec, data))
    ]
    return b"".join(runs)


def from_run_length(codec: struct.Struct, raw: bytes, rows: int) -> bytes:
    """Decode a run-length page: repeat every value as often as its run says."""
    step = codec.size + COUNT.size
    plain = []
    for start in range(0, len(raw), step):
        value = raw[start : start + codec.size]
        (length,) = COUNT.unpack(raw[start + codec.size : start + step])
        plain.append(value * length)
    return b"".join(plain)


def whole_numbers(codec: struct.Struct, data: bytes) -> list[int]:
    """The page's values as whole numbers, refusing any other kind of value."""
    values = [value for (value,) in codec.iter_unpack(data)]
    if not all(isinstance(value, int) and value >= 0 for value in values):
        raise ValueError("bit-packing needs whole numbers that are not negative")
    return values


def bit_packed(codec: struct.Struct, data: bytes) -> bytes:
    """Analogy: snug compartments — every compartment in the box cut down to
    the size its largest value needs.

    Layout: WIDTH (the bits per value: the largest value's bit length), then
    every value in exactly that many bits, value 0 in the lowest bits, the
    last byte filled up with zero bits.
    """
    values = whole_numbers(codec, data)
    width = max(values, default=0).bit_length()
    packed = 0
    for position, value in enumerate(values):
        packed |= value << (position * width)
    n_bytes = (len(values) * width + 7) // 8  # round up to whole bytes
    return WIDTH.pack(width) + packed.to_bytes(n_bytes, "little")


def from_bit_packed(codec: struct.Struct, raw: bytes, rows: int) -> bytes:
    """Decode a bit-packed page: cut `rows` values of WIDTH bits each."""
    (width,) = WIDTH.unpack(raw[: WIDTH.size])
    packed = int.from_bytes(raw[WIDTH.size :], "little")
    mask = (1 << width) - 1  # `width` one-bits
    return b"".join(
        codec.pack((packed >> (position * width)) & mask) for position in range(rows)
    )


Encoder = Callable[[struct.Struct, bytes], bytes]
Decoder = Callable[[struct.Struct, bytes, int], bytes]

# Every encoding by the name the metadata records, in the order a packer
# tries them.
ENCODINGS: dict[str, tuple[Encoder, Decoder]] = {
    "plain": (plain, from_plain),
    "dictionary": (dictionary, from_dictionary),
    "run-length": (run_length, from_run_length),
    "bit-packed": (bit_packed, from_bit_packed),
}


def encode(name: str, codec: struct.Struct, data: bytes) -> bytes:
    """Encode one page's plain bytes with the encoding called `name`."""
    encoder, _ = ENCODINGS[name]
    return encoder(codec, data)


def decode(name: str, codec: struct.Struct, raw: bytes, rows: int) -> bytes:
    """Decode one page's stored bytes back to its plain bytes."""
    _, decoder = ENCODINGS[name]
    return decoder(codec, raw, rows)


def smallest(codec: struct.Struct, data: bytes) -> tuple[str, bytes]:
    """Analogy: the weigh-in — the box packed every way, each packing weighed,
    and the lightest kept.

    Encode the page with every encoding that accepts its values and return
    the name and bytes of the smallest result; a tie keeps the encoding that
    comes first in ENCODINGS, so plain wins a draw.
    """
    best_name, best = "plain", data
    for name in ENCODINGS:
        try:
            raw = encode(name, codec, data)
        except ValueError:
            continue  # this encoding refuses these values
        if len(raw) < len(best):
            best_name, best = name, raw
    return best_name, best
