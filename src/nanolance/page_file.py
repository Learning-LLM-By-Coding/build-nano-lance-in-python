"""Analogy: every aisle cut into sealed boxes — a box holds up to
ROWS_PER_PAGE values, and a picker carries only the boxes a question needs.

The page file: each column is stored as a run of pages, one column after
another. A page is one read's worth of a single column's values.
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from nanolance.orders import COLUMNS, Row, pack_value

ROWS_PER_PAGE = 100


@dataclass(frozen=True)
class Page:
    """Analogy: one line of a box list — where a box sits, how many bytes it
    weighs, and how many values it holds.

    `offset` is the page's first byte in the file, `size` its length in
    bytes, `rows` the number of values in it.
    """

    offset: int
    size: int
    rows: int


def write(
    path: Path, rows: list[Row], rows_per_page: int = ROWS_PER_PAGE
) -> dict[str, list[Page]]:
    """Write `rows` column by column, each column cut into pages of up to
    `rows_per_page` values. Returns every column's list of pages."""
    pages: dict[str, list[Page]] = {}
    with open(path, "wb") as out:
        for position, column in enumerate(COLUMNS):
            pages[column] = []
            for first in range(0, len(rows), rows_per_page):
                chunk = rows[first : first + rows_per_page]
                data = b"".join(pack_value(column, row[position]) for row in chunk)
                page = Page(offset=out.tell(), size=len(data), rows=len(chunk))
                pages[column].append(page)
                out.write(data)
    return pages


def read_page(f: BinaryIO, codec: struct.Struct, page: Page) -> list[int | float | str]:
    """Analogy: walk to one box and carry it back whole.

    One seek, one read of `page.size` bytes, cut into values by `codec`.
    """
    f.seek(page.offset)
    raw = f.read(page.size)
    values = []
    for (value,) in codec.iter_unpack(raw):
        if isinstance(value, bytes):
            value = value.rstrip(b"\0").decode("utf-8")
        values.append(value)
    return values


def read_column(
    f: BinaryIO, codec: struct.Struct, pages: list[Page]
) -> list[int | float | str]:
    """Analogy: carry back every box of one aisle, in order."""
    return [value for page in pages for value in read_page(f, codec, page)]


def read_rows(
    f: BinaryIO, codec: struct.Struct, pages: list[Page], start: int, stop: int
) -> list[int | float | str]:
    """Analogy: fetch a stretch of one aisle, opening only the boxes that
    hold it.

    Rows `start` up to (not including) `stop`. A page whose rows all fall
    outside that range is skipped without a seek or a read.
    """
    values = []
    first = 0  # the row number of the current page's first value
    for page in pages:
        if first < stop and start < first + page.rows:
            page_values = read_page(f, codec, page)
            values.extend(page_values[max(start - first, 0) : stop - first])
        first += page.rows
    return values
