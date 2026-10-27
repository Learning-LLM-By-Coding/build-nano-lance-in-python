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

from nanolance import encodings
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
VERSION = 2  # 2: every page records its encoding


@dataclass(frozen=True)
class Page:
    """Analogy: one line of a box list — where a box sits, how many bytes it
    weighs, how many values it holds, and the packing note: how it was packed.

    `offset` is the page's first byte in the file, `size` its length in
    bytes, `rows` the number of values in it, `encoding` the name of the
    encoding its bytes are stored in (version 1 files had only plain pages).
    """

    offset: int
    size: int
    rows: int
    encoding: str = "plain"


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


def plain_pages(
    rows: list[Row], column: str, rows_per_page: int = ROWS_PER_PAGE
) -> list[bytes]:
    """Analogy: fill one aisle's boxes with full-size compartments.

    One column's values cut into pages of up to `rows_per_page` values, each
    page packed plain: its values back to back at the column's fixed width.
    """
    position = list(COLUMNS).index(column)
    return [
        b"".join(
            pack_value(column, row[position])
            for row in rows[first : first + rows_per_page]
        )
        for first in range(0, len(rows), rows_per_page)
    ]


def write(
    path: Path,
    rows: list[Row],
    rows_per_page: int = ROWS_PER_PAGE,
    encoding: dict[str, str] | None = None,
) -> dict[str, list[Page]]:
    """Write `rows` column by column, each column cut into pages of up to
    `rows_per_page` values. `encoding` names an encoding per column (a
    column it leaves out is stored plain); "smallest" picks, page by page,
    whichever encoding gives the fewest bytes. Returns every column's pages."""
    chosen = encoding or {}
    pages: dict[str, list[Page]] = {}
    with open(path, "wb") as out:
        for column, codec in COLUMNS.items():
            pages[column] = []
            name = chosen.get(column, "plain")
            for plain in plain_pages(rows, column, rows_per_page):
                if name == "smallest":
                    used, data = encodings.smallest(codec, plain)
                else:
                    used, data = name, encodings.encode(name, codec, plain)
                n_rows = len(plain) // codec.size
                page = Page(
                    offset=out.tell(), size=len(data), rows=n_rows, encoding=used
                )
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
    """Analogy: walk to one box, carry it back whole, and unpack it the way
    its packing note says.

    One seek, one read of `page.size` bytes, decoded by the page's encoding
    back to plain bytes, then cut into values by `codec`.
    """
    f.seek(page.offset)
    raw = f.read(page.size)
    plain = encodings.decode(page.encoding, codec, raw, page.rows)
    values = []
    for (value,) in codec.iter_unpack(plain):
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
    bytes), then the column metadata at the offset the footer gives. A file
    without the magic bytes, of a version this reader does not know, or whose
    footer points outside the file is refused with a ValueError before the
    second read. Version 1 files read as files whose pages are all plain.
    """
    if f.size < FOOTER.size:
        raise ValueError(
            f"not a nanolance file: {f.size} bytes is shorter than the "
            f"{FOOTER.size}-byte footer"
        )
    f.seek(f.size - FOOTER.size)
    footer = f.read(FOOTER.size)
    metadata_offset, metadata_size, version, magic = FOOTER.unpack(footer)
    if magic != MAGIC:
        raise ValueError(f"not a nanolance file: it ends with {magic!r}, not {MAGIC!r}")
    if not 1 <= version <= VERSION:
        raise ValueError(
            f"nanolance file version {version}; "
            f"this reader reads versions 1 to {VERSION}"
        )
    footer_start = f.size - FOOTER.size
    if metadata_offset + metadata_size > footer_start:
        raise ValueError(
            f"damaged nanolance file: its metadata would end at byte "
            f"{metadata_offset + metadata_size}, past the footer at {footer_start}"
        )
    f.seek(metadata_offset)
    metadata = json.loads(f.read(metadata_size))
    columns = metadata["columns"]
    return Metadata(
        version=version,
        rows=metadata["rows"],
        codecs={c["name"]: struct.Struct(c["format"]) for c in columns},
        pages={c["name"]: [Page(**page) for page in c["pages"]] for c in columns},
    )
