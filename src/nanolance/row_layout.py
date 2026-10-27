"""Analogy: one crate per order — all of an order's values packed together.

The row layout: the file is row 0's bytes, then row 1's, then row 2's, ...
Each row is ROW_WIDTH bytes, its values in column order.
"""

from pathlib import Path
from typing import BinaryIO

from nanolance.orders import COLUMNS, ROW_WIDTH, Row, pack_value, unpack_value


def write(path: Path, rows: list[Row]) -> None:
    """Write `rows` to `path` one whole row after another."""
    with open(path, "wb") as out:
        for row in rows:
            for column, value in zip(COLUMNS, row, strict=True):
                out.write(pack_value(column, value))


def read_row(f: BinaryIO) -> Row:
    """Read the row that starts at the file's current position."""
    raw = f.read(ROW_WIDTH)
    values = []
    start = 0
    for column, codec in COLUMNS.items():
        values.append(unpack_value(column, raw[start : start + codec.size]))
        start += codec.size
    return tuple(values)


def read_all(f: BinaryIO, n_rows: int) -> list[Row]:
    """Read every row, front to back. The file does not record how many
    rows it holds, so the caller has to say."""
    return [read_row(f) for _ in range(n_rows)]


def sum_column(f: BinaryIO, column: str, n_rows: int) -> int | float:
    """Analogy: the stock count, done crate by crate.

    Add up one column's values. In this layout the values sit inside every
    row, so every row is read whole.
    """
    position = list(COLUMNS).index(column)
    return sum(row[position] for row in read_all(f, n_rows))
