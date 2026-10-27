"""Analogy: trays inside a box — values of any length kept in trays of
fixed-size compartments, so the packer's methods still work on every tray.

Variable-length values. A page that holds them is stored as several
buffers ("trays"), each one a run of fixed-width values that Day 3's
encodings can pack: OFFSET-wide positions, and BYTE-wide UTF-8 text. Strings
and lists follow Apache Arrow's variable-size binary and list layouts.
"""

import struct
from itertools import pairwise

# One offset: a position in a page's text, 4 bytes, so up to 4 GiB per page.
OFFSET = struct.Struct("<I")
# One byte of UTF-8 text.
BYTE = struct.Struct("<B")

# The names variable-length columns record as their format: text, and a
# list of texts per row.
STRING = "string"
STRING_LIST = "list<string>"

# A column's kind: a fixed-width codec (Days 1–3), or the name of a
# variable-length kind.
Kind = struct.Struct | str
Value = int | float | str | list[str]


def kind_of(format_name: str) -> Kind:
    """The column kind a metadata "format" names."""
    if format_name in (STRING, STRING_LIST):
        return format_name
    return struct.Struct(format_name)


def format_of(kind: Kind) -> str:
    """The "format" the metadata records for a column kind."""
    return kind if isinstance(kind, str) else kind.format


def offsets(lengths: list[int]) -> bytes:
    """Analogy: the end marks — a mark beside the strip where each value ends.

    len(lengths) + 1 offsets: 0, then the running total of the lengths, so
    value k lies between offsets k and k + 1.
    """
    ends = [0]
    for length in lengths:
        ends.append(ends[-1] + length)
    return b"".join(OFFSET.pack(end) for end in ends)


def spans(raw: bytes) -> list[tuple[int, int]]:
    """Every value's (start, stop) from a tray of offsets."""
    return list(pairwise(end for (end,) in OFFSET.iter_unpack(raw)))


def string_trays(values: list[str]) -> dict[str, bytes]:
    """Analogy: the letter strip and its end marks — every name's letters
    written back to back, and a mark where each one ends.

    Two trays: "offsets" (len(values) + 1 of them), and "data" (every value's
    UTF-8 bytes back to back, no padding).
    """
    data = [value.encode("utf-8") for value in values]
    return {"offsets": offsets([len(text) for text in data]), "data": b"".join(data)}


def strings_from(trays: dict[str, bytes]) -> list[str]:
    """The strings back from their "offsets" and "data" trays."""
    data = trays["data"]
    return [data[start:stop].decode("utf-8") for start, stop in spans(trays["offsets"])]


def list_trays(values: list[list[str]]) -> dict[str, bytes]:
    """Analogy: bundles — each order's tags tied together, every bundle's
    tags on one letter strip, and a mark where each bundle ends.

    Three trays: "list offsets" (len(values) + 1 of them, counted in items),
    then every item of every list, stored as string_trays stores strings.
    """
    items = [item for value in values for item in value]
    return {
        "list offsets": offsets([len(value) for value in values]),
        **string_trays(items),
    }


def lists_from(trays: dict[str, bytes]) -> list[list[str]]:
    """The lists back: the items first, then cut by the list offsets."""
    items = strings_from(trays)
    return [items[start:stop] for start, stop in spans(trays["list offsets"])]


def fixed_tray(codec: struct.Struct, values: list[Value]) -> bytes:
    """Analogy: Day 1's packing rule, for any compartment size.

    Values back to back at the codec's width. Text is UTF-8, zero-padded,
    and refused when it needs more bytes than the width.
    """
    parts = []
    for value in values:
        if isinstance(value, str):
            value = value.encode("utf-8")
            if len(value) > codec.size:
                raise ValueError(
                    f"text needs {len(value)} bytes; the slot holds {codec.size}"
                )
        parts.append(codec.pack(value))
    return b"".join(parts)


def fixed_values(codec: struct.Struct, plain: bytes) -> list[Value]:
    """Cut plain bytes into values; fixed-width text loses its zero padding."""
    values = []
    for (value,) in codec.iter_unpack(plain):
        if isinstance(value, bytes):
            value = value.rstrip(b"\0").decode("utf-8")
        values.append(value)
    return values


def trays(kind: Kind, values: list[Value]) -> dict[str, bytes]:
    """Analogy: lay out one box's trays before the packer packs each one.

    One page's values as plain trays, by name: a fixed-width column has one,
    "values"; a string column has "offsets" and "data"; a list column has
    "list offsets" before those two.
    """
    if kind == STRING:
        return string_trays(values)
    if kind == STRING_LIST:
        return list_trays(values)
    return {"values": fixed_tray(kind, values)}


def tray_codec(kind: Kind, name: str) -> struct.Struct:
    """The fixed width of one tray's values, which its encoding works on."""
    if name in ("list offsets", "offsets"):
        return OFFSET
    if name == "data":
        return BYTE
    return kind  # "values": the column's own codec


def values_from(kind: Kind, trays: dict[str, bytes]) -> list[Value]:
    """One page's values back from its decoded (plain) trays."""
    if kind == STRING:
        return strings_from(trays)
    if kind == STRING_LIST:
        return lists_from(trays)
    return fixed_values(kind, trays["values"])
