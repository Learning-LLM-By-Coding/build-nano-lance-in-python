"""Analogy: every aisle cut into sealed boxes — a box holds up to
ROWS_PER_PAGE values, and a picker carries only the boxes a question needs.

The page file: each column is stored as a run of pages, one column after
another. A page is one read's worth of a single column's values. After the
pages come the column metadata (every column's format and page list, as
JSON), and last a fixed-size footer that says where the metadata is.
"""

import json
import struct
from bisect import bisect_right
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO

from nanolance import encodings, shapes
from nanolance.counting import CountingFile
from nanolance.orders import COLUMNS, Row, pack_value
from nanolance.shapes import OFFSET, Kind, Value

ROWS_PER_PAGE = 100

# Analogy: the wall card at the back — always the same size, always the
# last thing in the warehouse, so a picker knows where to find it.
#
# The footer: metadata offset (8 bytes), metadata size (8 bytes), format
# version (4 bytes), and the magic bytes that name the format (4 bytes).
FOOTER = struct.Struct("<QQI4s")
MAGIC = b"NLNC"
VERSION = 3  # 3: a page may hold several trays


@dataclass(frozen=True)
class Tray:
    """Analogy: one tray inside a box — what it holds, how many bytes it
    weighs, how many compartments it has, and its own packing note.

    One buffer of a page: `name` says what it holds ("offsets", "data", ...),
    `size` is its length in bytes as stored, `count` the number of
    fixed-width values in it, `encoding` how those values are stored.
    """

    name: str
    size: int
    count: int
    encoding: str = "plain"


@dataclass(frozen=True)
class Page:
    """Analogy: one line of a box list — where a box sits, how many bytes it
    weighs, how many values it holds, and the packing note: how it was packed.

    `offset` is the page's first byte in the file, `size` its length in
    bytes, `rows` the number of values in it, `encoding` the name of the
    encoding its bytes are stored in (version 1 files had only plain pages).
    A page of several buffers has encoding "trays" and lists them in `trays`,
    stored back to back from `offset`; a one-buffer page has no `trays`.
    """

    offset: int
    size: int
    rows: int
    encoding: str = "plain"
    trays: tuple[Tray, ...] = ()


@dataclass(frozen=True)
class Metadata:
    """Analogy: what the picker knows after reading the wall card and the
    box lists it points to.

    Everything a reader needs, taken from the file itself: the format
    version, the row count, each column's codec, and each column's pages.
    """

    version: int
    rows: int
    codecs: dict[str, Kind]
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


def pack(name: str, codec: struct.Struct, plain: bytes) -> tuple[str, bytes]:
    """Encode plain bytes with the encoding called `name`, or with the
    smallest one when `name` is "smallest"; returns the encoding used."""
    if name == "smallest":
        return encodings.smallest(codec, plain)
    return name, encodings.encode(name, codec, plain)


def pack_page(
    kind: Kind, name: str, values: list[Value], offset: int
) -> tuple[Page, bytes]:
    """Analogy: the packer fills one box — tray by tray, when it has trays.

    One page's values as stored bytes, and its Page for the metadata. A page
    with one buffer is stored as on Day 3; a page with several trays stores
    them back to back, each packed by `name` on its own.
    """
    plain_trays = shapes.trays(kind, values)
    if list(plain_trays) == ["values"]:  # one buffer: a page as on Day 3
        used, data = pack(name, kind, plain_trays["values"])
        return Page(offset, len(data), len(values), used), data
    trays, parts = [], []
    for tray_name, plain in plain_trays.items():
        codec = shapes.tray_codec(kind, tray_name)
        choice = "plain" if tray_name == "validity" else name  # bitmaps stay plain
        used, stored = pack(choice, codec, plain)
        trays.append(Tray(tray_name, len(stored), len(plain) // codec.size, used))
        parts.append(stored)
    data = b"".join(parts)
    return Page(offset, len(data), len(values), "trays", tuple(trays)), data


def entry(page: Page) -> dict:
    """A page as its metadata records it; a one-buffer page as on Day 3."""
    fields = asdict(page)
    if not page.trays:
        del fields["trays"]
    return fields


def write(
    path: Path,
    rows: list[tuple],
    rows_per_page: int = ROWS_PER_PAGE,
    encoding: dict[str, str] | None = None,
    columns: dict[str, Kind] = COLUMNS,
) -> dict[str, list[Page]]:
    """Write `rows` column by column, each column cut into pages of up to
    `rows_per_page` values; `columns` gives each column's kind, in row order.
    `encoding` names an encoding per column (a column it leaves out is stored
    plain); "smallest" picks, page by page, whichever encoding gives the
    fewest bytes. Returns every column's pages."""
    chosen = encoding or {}
    pages: dict[str, list[Page]] = {}
    with open(path, "wb") as out:
        for position, (column, kind) in enumerate(columns.items()):
            pages[column] = []
            name = chosen.get(column, "plain")
            for first in range(0, len(rows), rows_per_page):
                values = [row[position] for row in rows[first : first + rows_per_page]]
                page, data = pack_page(kind, name, values, out.tell())
                pages[column].append(page)
                out.write(data)
        finish(out, len(rows), columns, pages)
    return pages


def finish(
    out: BinaryIO, n_rows: int, columns: dict[str, Kind], pages: dict[str, list[Page]]
) -> None:
    """Analogy: write the box lists after the last box, then hang the wall card.

    Write the column metadata (as JSON) at the current position, then the
    footer that says where it is.
    """
    metadata = {
        "rows": n_rows,
        "columns": [
            {
                "name": column,
                "format": shapes.format_of(kind),
                "pages": [entry(page) for page in pages[column]],
            }
            for column, kind in columns.items()
        ],
    }
    raw = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
    metadata_offset = out.tell()
    out.write(raw)
    out.write(FOOTER.pack(metadata_offset, len(raw), VERSION, MAGIC))


def read_page(f: BinaryIO, codec: Kind, page: Page) -> list[Value]:
    """Analogy: walk to one box, carry it back whole, and unpack it the way
    its packing note says — tray by tray, when it has trays.

    One seek, one read of `page.size` bytes. A one-buffer page is decoded by
    the page's encoding and cut into values by `codec`; a page of trays has
    each tray decoded by its own encoding, then its values rebuilt.
    """
    f.seek(page.offset)
    raw = f.read(page.size)
    if not page.trays:
        plain = encodings.decode(page.encoding, codec, raw, page.rows)
        return shapes.fixed_values(codec, plain)
    trays = {}
    start = 0
    for tray in page.trays:
        stored = raw[start : start + tray.size]
        start += tray.size
        tray_codec = shapes.tray_codec(codec, tray.name)
        trays[tray.name] = encodings.decode(
            tray.encoding, tray_codec, stored, tray.count
        )
    return shapes.values_from(codec, trays)


def read_string(f: BinaryIO, page: Page, k: int) -> str:
    """Analogy: fetch one name without carrying the box — read its two end
    marks first, then only its letters.

    Two seeks and two reads: offsets k and k + 1 from the page's "offsets"
    tray, then the bytes between them from its "data" tray. Both trays must
    be stored plain, so where offset k sits is arithmetic.
    """
    starts, at = {}, page.offset
    for tray in page.trays:
        if tray.name in ("offsets", "data") and tray.encoding != "plain":
            raise ValueError(f"the {tray.name} tray is {tray.encoding}, not plain")
        starts[tray.name] = at
        at += tray.size
    f.seek(starts["offsets"] + k * OFFSET.size)
    start, stop = (end for (end,) in OFFSET.iter_unpack(f.read(2 * OFFSET.size)))
    f.seek(starts["data"] + start)
    return f.read(stop - start).decode("utf-8")


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


def check_row_ids(metadata: Metadata, row_ids: list[int]) -> None:
    """Refuse any row id the file does not hold, negative ones included."""
    for row_id in row_ids:
        if not 0 <= row_id < metadata.rows:
            raise IndexError(
                f"row id {row_id}: the file holds rows 0 to {metadata.rows - 1}"
            )


def take_by_scan(
    f: BinaryIO, metadata: Metadata, row_ids: list[int], columns: list[str]
) -> list[tuple]:
    """Analogy: a pick list, the slow way — carry back every box of every
    aisle the list asks about, then pick the orders out at the bench.

    The rows at `row_ids` (positions, from 0), in that order, each with the
    `columns` asked for, in that order. Every asked-for column is read whole.
    """
    check_row_ids(metadata, row_ids)
    values = {c: read_column(f, metadata.codecs[c], metadata.pages[c]) for c in columns}
    return [tuple(values[c][row_id] for c in columns) for row_id in row_ids]


def page_starts(pages: list[Page]) -> list[int]:
    """Analogy: start numbers — the number of the first order in every box,
    added up from the box list's row counts.

    The row number of every page's first value: 0, then a running total of
    the pages' row counts.
    """
    starts, first = [], 0
    for page in pages:
        starts.append(first)
        first += page.rows
    return starts


def locate(starts: list[int], row_id: int) -> tuple[int, int]:
    """Analogy: find an order's box by the start numbers, and its place in it.

    The number of the page holding `row_id` — the last page that starts at or
    before it, found by binary search — and the row's position in that page.
    """
    n = bisect_right(starts, row_id) - 1
    return n, row_id - starts[n]


def take(
    f: BinaryIO, metadata: Metadata, row_ids: list[int], columns: list[str]
) -> list[tuple]:
    """Analogy: a pick list, box by box — find each order's box by the start
    numbers and carry back only that box, each box once.

    The rows at `row_ids` (positions, from 0), in that order, repeats allowed,
    each with the `columns` asked for, in that order. Only the pages holding a
    requested row are read, each with one seek and one read however many of
    its rows are asked for, and each is decoded on its own.
    """
    check_row_ids(metadata, row_ids)
    picked = []
    for column in columns:
        kind, pages = metadata.codecs[column], metadata.pages[column]
        starts = page_starts(pages)
        opened = {}  # page number -> its values, so no page is read twice
        values = []
        for row_id in row_ids:
            n, k = locate(starts, row_id)
            if n not in opened:
                opened[n] = read_page(f, kind, pages[n])
            values.append(opened[n][k])
        picked.append(values)
    return list(zip(*picked, strict=True))


def read_metadata(f: CountingFile) -> Metadata:
    """Analogy: walk to the back wall, read the wall card, then the box
    lists it points to.

    Two seeks and two reads: the footer (the file's last FOOTER.size
    bytes), then the column metadata at the offset the footer gives. A file
    without the magic bytes, of a version this reader does not know, or whose
    footer points outside the file is refused with a ValueError before the
    second read. Version 1 files read as files whose pages are all plain, and
    versions 1 and 2 as files without trays.
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
        codecs={c["name"]: shapes.kind_of(c["format"]) for c in columns},
        pages={c["name"]: [page_from(page) for page in c["pages"]] for c in columns},
    )


def page_from(fields: dict) -> Page:
    """A page from its metadata entry; entries without trays get none."""
    trays = tuple(Tray(**tray) for tray in fields.pop("trays", []))
    return Page(**fields, trays=trays)
