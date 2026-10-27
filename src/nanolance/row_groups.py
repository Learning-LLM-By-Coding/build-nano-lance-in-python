"""Analogy: pallets — the warehouse across the street ships orders on
pallets: each pallet carries a few thousand whole orders, every column's
share of them wrapped as one piece that must be unwrapped whole.

A Parquet-style row-group file, in miniature. The rows are cut into groups;
inside a group, each column's values form one chunk, packed as one unit; the
chunks are stored group after group. The metadata lists each column's chunks
as its pages, and the footer and stamp are the page file's own, so
page_file.read_metadata and page_file.take read this file unchanged.
"""

from pathlib import Path

from nanolance import page_file
from nanolance.orders import COLUMNS
from nanolance.page_file import Page
from nanolance.shapes import Kind

ROWS_PER_GROUP = 2500


def write(
    path: Path,
    rows: list[tuple],
    rows_per_group: int = ROWS_PER_GROUP,
    encoding: dict[str, str] | None = None,
    columns: dict[str, Kind] = COLUMNS,
) -> dict[str, list[Page]]:
    """Analogy: load the pallets — a group of whole orders at a time, every
    column's share wrapped as one piece, pallet after pallet.

    Write `rows` group by group, `rows_per_group` rows each; within a group,
    each column's values are one chunk, encoded as one page by `encoding` (as
    in page_file.write). Returns every column's chunks, group by group.
    """
    chosen = encoding or {}
    chunks: dict[str, list[Page]] = {column: [] for column in columns}
    with open(path, "wb") as out:
        for first in range(0, len(rows), rows_per_group):
            group = rows[first : first + rows_per_group]
            for position, (column, kind) in enumerate(columns.items()):
                values = [row[position] for row in group]
                name = chosen.get(column, "plain")
                chunk, data = page_file.pack_page(kind, name, values, out.tell())
                chunks[column].append(chunk)
                out.write(data)
        page_file.finish(out, len(rows), columns, chunks)
    return chunks
