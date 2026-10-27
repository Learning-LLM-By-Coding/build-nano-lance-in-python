"""The orders table: its columns, its eight rows, and how one value becomes bytes."""

import struct

NAME_WIDTH = 12

# Analogy: the packing rule — every crate has the same four compartments,
# each one a fixed size, so where anything sits is plain arithmetic.
#
# Each column's values are packed with one `struct` format: "<" means
# little-endian with values back to back, no gaps; q = 8-byte int,
# d = 8-byte float, i = 4-byte int, 12s = 12 raw bytes.
COLUMNS = {
    "id": struct.Struct("<q"),
    "price": struct.Struct("<d"),
    "qty": struct.Struct("<i"),
    "name": struct.Struct(f"<{NAME_WIDTH}s"),
}
ROW_WIDTH = sum(codec.size for codec in COLUMNS.values())

Row = tuple[int, float, int, str]

ORDERS: list[Row] = [
    (101, 4.25, 3, "bolts"),
    (102, 12.5, 1, "hammer"),
    (103, 0.75, 40, "washers"),
    (104, 7.0, 2, "tape"),
    (105, 23.5, 1, "drill bits"),
    (106, 3.25, 12, "nails"),
    (107, 9.75, 4, "gloves"),
    (108, 15.0, 2, "padlock"),
]


# Analogy: the same eight orders as the shop really sends them — a name too
# long for its compartment, tags on most of them, and two prices nobody has
# quoted yet.
#
# Day 4's table: the same ids and quantities as ORDERS, but a price may be
# None (not known yet), a name may need more than NAME_WIDTH bytes, and tags
# is a list of words, possibly empty.
TaggedRow = tuple[int, float | None, int, str, list[str]]

TAGGED_ORDERS: list[TaggedRow] = [
    (101, 4.25, 3, "bolts", ["bulk"]),
    (102, 12.5, 1, "hammer", []),
    (103, None, 40, "washers", ["bulk", "small parts"]),
    (104, 7.0, 2, "tape", []),
    (105, 23.5, 1, "drill bits Ø6", ["fragile"]),
    (106, 3.25, 12, "nails", ["bulk"]),
    (107, None, 4, "gloves", []),
    (108, 15.0, 2, "padlock", ["gift", "fragile"]),
]


def pack_value(column: str, value: int | float | str) -> bytes:
    """Analogy: put one value into its compartment.

    Turns one value of `column` into exactly that column's width in bytes.
    Text is encoded as UTF-8 and padded with zero bytes up to NAME_WIDTH.
    """
    if isinstance(value, str):
        value = value.encode("utf-8")
        if len(value) > NAME_WIDTH:
            raise ValueError(
                f"{column} needs {len(value)} bytes; the slot holds {NAME_WIDTH}"
            )
    return COLUMNS[column].pack(value)


def unpack_value(column: str, raw: bytes) -> int | float | str:
    """Analogy: take one value out of its compartment.

    The reverse of `pack_value`: `raw` must be exactly the column's width.
    """
    (value,) = COLUMNS[column].unpack(raw)
    if isinstance(value, bytes):
        value = value.rstrip(b"\0").decode("utf-8")
    return value


def many_orders(n_rows: int) -> list[Row]:
    """Analogy: a busy week — the same eight orders, placed again and again.

    `n_rows` orders with ids 101, 102, 103, ...; order k repeats the price,
    quantity, and name of ORDERS[k % 8], so every value is predictable.
    """
    return [(101 + k, *ORDERS[k % len(ORDERS)][1:]) for k in range(n_rows)]


def many_tagged_orders(n_rows: int) -> list[TaggedRow]:
    """Analogy: a busy week of the shop's real orders.

    `n_rows` orders with ids 101, 102, 103, ...; order k repeats the price,
    quantity, name, and tags of TAGGED_ORDERS[k % 8].
    """
    return [
        (101 + k, *TAGGED_ORDERS[k % len(TAGGED_ORDERS)][1:]) for k in range(n_rows)
    ]
