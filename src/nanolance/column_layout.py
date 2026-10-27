"""Analogy: one aisle per column — every order's id together, then every
price, then every quantity, then every name.

The column layout: the file is column 0's values for all rows, then column
1's, and so on. Value k of every column belongs to row k.
"""

from pathlib import Path
from typing import BinaryIO

from nanolance.orders import COLUMNS, Row, pack_value, unpack_value


def write(path: Path, rows: list[Row]) -> None:
    """Write `rows` to `path` one whole column after another."""
    with open(path, "wb") as out:
        for position, column in enumerate(COLUMNS):
            for row in rows:
                out.write(pack_value(column, row[position]))


def column_start(column: str, n_rows: int) -> int:
    """Analogy: how far down the warehouse an aisle begins.

    The byte offset of `column`'s first value: every column before it takes
    up n_rows values of its own width.
    """
    start = 0
    for name, codec in COLUMNS.items():
        if name == column:
            return start
        start += n_rows * codec.size
    raise KeyError(column)


def read_column(f: BinaryIO, column: str, n_rows: int) -> list[int | float | str]:
    """Analogy: walk to one aisle and carry the whole aisle back.

    One seek to the column's start, one read of all its values.
    """
    width = COLUMNS[column].size
    f.seek(column_start(column, n_rows))
    raw = f.read(n_rows * width)
    return [
        unpack_value(column, raw[k * width : (k + 1) * width]) for k in range(n_rows)
    ]


def read_all(f: BinaryIO, n_rows: int) -> list[Row]:
    """Read every column, then zip them back into rows."""
    columns = [read_column(f, column, n_rows) for column in COLUMNS]
    return list(zip(*columns, strict=True))


def sum_column(f: BinaryIO, column: str, n_rows: int) -> int | float:
    """Analogy: the stock count, done in one aisle.

    Add up one column's values, reading only that column.
    """
    return sum(read_column(f, column, n_rows))
