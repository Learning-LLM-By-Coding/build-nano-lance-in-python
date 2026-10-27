"""Analogy: every aisle cut into sealed boxes — a box holds up to
ROWS_PER_PAGE values, and a picker carries only the boxes a question needs.

The page file: each column is stored as a run of pages, one column after
another. A page is one read's worth of a single column's values. After the
pages come the column metadata (every column's format and page list, as
JSON), and last a fixed-size footer that says where the metadata is.
"""

import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO

from nanolance.counting import CountingFile
from nanolance.orders import COLUMNS, Row, pack_value

ROWS_PER_PAGE = 100

# Analogy: the wall card at the back — always the same size, always the
# last thing in the warehouse, so a picker knows where to find it.
#
# The footer: metadata offset (8 bytes), metadata size (8 bytes), format
# version (4 bytes), and the magic bytes that name the format (4 bytes).
FOOTER = struct.Struct("<QQI4s")
MAGIC = b"NLNC"
VERSION = 1


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


@dataclass(frozen=True)
class Metadata:
    """Analogy: what the picker knows after reading the wall card and the
    box lists it points to.

    Everything a reader needs, taken from the file itself: the format
    version, the row count, each column's codec, and each column's pages.
    """

    version: int
    rows: int
    codecs: dict[str, struct.Struct]
    pages: dict[str, list[Page]]


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

        metadata = {
            "rows": len(rows),
            "columns": [
                {
                    "name": column,
                    "format": codec.format,
                    "pages": [asdict(page) for page in pages[column]],
                }
                for column, codec in COLUMNS.items()
            ],
        }
        raw = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
        metadata_offset = out.tell()
        out.write(raw)
        out.write(FOOTER.pack(metadata_offset, len(raw), VERSION, MAGIC))
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


def read_metadata(f: CountingFile) -> Metadata:
    """Analogy: walk to the back wall, read the wall card, then the box
    lists it points to.

    Two seeks and two reads: the footer (the file's last FOOTER.size
    bytes), then the column metadata at the offset the footer gives.
    """
    f.seek(f.size - FOOTER.size)
    footer = f.read(FOOTER.size)
    metadata_offset, metadata_size, version, magic = FOOTER.unpack(footer)
    f.seek(metadata_offset)
    metadata = json.loads(f.read(metadata_size))
    columns = metadata["columns"]
    return Metadata(
        version=version,
        rows=metadata["rows"],
        codecs={c["name"]: struct.Struct(c["format"]) for c in columns},
        pages={c["name"]: [Page(**page) for page in c["pages"]] for c in columns},
    )
