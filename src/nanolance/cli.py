"""The `nanolance` command line."""

import argparse
from itertools import groupby
from pathlib import Path

from nanolance import __version__, column_layout, encodings, page_file, row_layout
from nanolance.counting import CountingFile
from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH, Row, many_orders
from nanolance.page_file import ROWS_PER_PAGE


def layouts(folder: Path) -> None:
    """Analogy: open the warehouse, pack the orders both ways, and ask each
    the same questions.

    Store the orders table as rows and as columns, query both, and print
    every step with its tally.
    """
    folder.mkdir(parents=True, exist_ok=True)
    n_rows = len(ORDERS)
    names = ", ".join(COLUMNS)
    print(f"the orders table: {n_rows} rows × {len(COLUMNS)} columns ({names})")
    for row in ORDERS:
        print(f"  {row}")

    rows_path = folder / "rows.bin"
    row_layout.write(rows_path, ORDERS)
    size = rows_path.stat().st_size
    print(f"write {rows_path.name}: {size} bytes = {n_rows} rows × {ROW_WIDTH} bytes")
    with CountingFile(rows_path) as f:
        same = row_layout.read_all(f, n_rows) == ORDERS
        print(f"read {rows_path.name} back: same as the table? {same}")
        print(f"  tally: {f.tally()}")

    needed = n_rows * COLUMNS["qty"].size
    with CountingFile(rows_path) as f:
        total = row_layout.sum_column(f, "qty", n_rows)
        print(f"sum(qty) from {rows_path.name} = {total}")
        print(f"  tally: {f.tally()} (qty needs only {needed} of them)")

    columns_path = folder / "columns.bin"
    column_layout.write(columns_path, ORDERS)
    size = columns_path.stat().st_size
    parts = " + ".join(f"{c} {n_rows * codec.size}" for c, codec in COLUMNS.items())
    print(f"write {columns_path.name}: {size} bytes = {parts}")
    with CountingFile(columns_path) as f:
        same = column_layout.read_all(f, n_rows) == ORDERS
        print(f"read {columns_path.name} back: same as the table? {same}")
        print(f"  tally: {f.tally()}")

    with CountingFile(columns_path) as f:
        total = column_layout.sum_column(f, "qty", n_rows)
        print(f"sum(qty) from {columns_path.name} = {total}")
        print(f"  tally: {f.tally()}")

    index = 5
    with CountingFile(rows_path) as f:
        row = row_layout.fetch_row(f, index)
        print(f"fetch row {index} from {rows_path.name} = {row}")
        print(f"  tally: {f.tally()}")
    with CountingFile(columns_path) as f:
        row = column_layout.fetch_row(f, index, n_rows)
        print(f"fetch row {index} from {columns_path.name} = {row}")
        print(f"  tally: {f.tally()}")


def pages(folder: Path) -> None:
    """Analogy: a busy week — a thousand orders sorted into aisles, and the
    questions the aisles cannot answer on their own.

    Store 1000 orders in Day 1's column layout and show what its reader has
    to be told, and what it has to read, to answer one column's questions.
    """
    folder.mkdir(parents=True, exist_ok=True)
    orders = many_orders(1000)
    n_rows = len(orders)
    names = ", ".join(COLUMNS)
    print(f"the orders table: {n_rows} rows × {len(COLUMNS)} columns ({names})")
    for row in orders[:3]:
        print(f"  {row}")
    print(f"  … and {n_rows - 3} more, repeating the same eight orders")

    columns_path = folder / "columns.bin"
    column_layout.write(columns_path, orders)
    size = columns_path.stat().st_size
    parts = " + ".join(f"{c} {n_rows * codec.size}" for c, codec in COLUMNS.items())
    print(f"write {columns_path.name}: {size} bytes = {parts}")
    for told in (n_rows, 8):
        with CountingFile(columns_path) as f:
            total = column_layout.sum_column(f, "qty", told)
            print(f"sum(qty) from {columns_path.name}, told {told} rows = {total}")
            print(f"  tally: {f.tally()}")

    needed = 10 * COLUMNS["qty"].size
    with CountingFile(columns_path) as f:
        values = column_layout.read_column(f, "qty", n_rows)[10:20]
        print(f"qty of rows 10–19 from {columns_path.name} = {values}")
        print(f"  tally: {f.tally()} (rows 10–19 need only {needed} of them)")

    pages_path = folder / "pages.bin"
    box_lists = page_file.write(pages_path, orders)
    size = pages_path.stat().st_size
    print(f"write {pages_path.name}: {size} bytes, each column cut into pages")
    for column, boxes in box_lists.items():
        at = f"{boxes[0].offset}, {boxes[1].offset}, …, {boxes[-1].offset}"
        print(f"  {column}: {len(boxes)} pages of {boxes[0].size} bytes, at {at}")

    codec = COLUMNS["qty"]
    with CountingFile(pages_path) as f:
        total = sum(page_file.read_column(f, codec, box_lists["qty"]))
        print(f"sum(qty) from {pages_path.name} = {total}")
        print(f"  tally: {f.tally()}")
    with CountingFile(pages_path) as f:
        values = page_file.read_rows(f, codec, box_lists["qty"], 10, 20)
        print(f"qty of rows 10–19 from {pages_path.name} = {values}")
        print(f"  tally: {f.tally()}")

    with CountingFile(pages_path) as f:
        metadata = page_file.read_metadata(f)
        names = ", ".join(metadata.codecs)
        n_pages = sum(len(boxes) for boxes in metadata.pages.values())
        print(
            f"open {pages_path.name}: version {metadata.version}, "
            f"{metadata.rows} rows, columns {names}, {n_pages} pages"
        )
        print(f"  tally: {f.tally()}")
    with CountingFile(pages_path) as f:
        metadata = page_file.read_metadata(f)
        codec, boxes = metadata.codecs["qty"], metadata.pages["qty"]
        total = sum(page_file.read_column(f, codec, boxes))
        print(f"sum(qty) from {pages_path.name}, told nothing = {total}")
        print(f"  tally: {f.tally()}")
    with CountingFile(pages_path) as f:
        metadata = page_file.read_metadata(f)
        codec, boxes = metadata.codecs["qty"], metadata.pages["qty"]
        values = page_file.read_rows(f, codec, boxes, 10, 20)
        print(f"qty of rows 10–19 from {pages_path.name}, told nothing = {values}")
        print(f"  tally: {f.tally()}")

    with CountingFile(columns_path) as f:
        try:
            page_file.read_metadata(f)
        except ValueError as error:
            print(f"open {columns_path.name} as a page file: refused, {error}")
        print(f"  tally: {f.tally()}")


def describe(values: list[int | float | str]) -> str:
    """Analogy: the packer looks inside one box before sealing it.

    How many distinct values the box holds, its longest run of equal values
    side by side, and for whole numbers the largest one and how many bits
    it needs.
    """
    longest = max(len(list(run)) for _, run in groupby(values))
    facts = f"{len(set(values))} distinct, longest run {longest}"
    if isinstance(values[0], int):
        largest = max(values)
        facts += f", largest {largest} needs {largest.bit_length()} bits"
    return facts


def every_way(title: str, table: list[Row]) -> None:
    """Analogy: the packer packs every aisle's boxes every way it knows, and
    weighs each result.

    For each column, the bytes of all its pages in every encoding of
    ENCODINGS — or "—" where an encoding refuses the column's values.
    """
    print(f"every column packed every way, orders {title} (bytes, all pages):")
    for column, codec in COLUMNS.items():
        pages = page_file.plain_pages(table, column)
        sizes = []
        for name in encodings.ENCODINGS:
            try:
                size = sum(len(encodings.encode(name, codec, page)) for page in pages)
                sizes.append(f"{name} {size}")
            except ValueError:
                sizes.append(f"{name} —")
        print(f"  {column}: {', '.join(sizes)}")


def write_and_read_back(path: Path, table: list[Row], encoding: dict[str, str]) -> None:
    """Analogy: pack a whole warehouse, then send a picker who knows nothing
    to unpack every box by its packing note.

    Write `table` with the chosen encodings, print the file's size and its
    pages' share, then read every column back using only the file.
    """
    pages = page_file.write(path, table, encoding=encoding)
    size = path.stat().st_size
    stored = sum(page.size for boxes in pages.values() for page in boxes)
    plain = len(table) * ROW_WIDTH
    print(f"write {path.name}: {size} bytes, pages {stored} (plain: {plain})")
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        columns = [
            page_file.read_column(f, metadata.codecs[c], metadata.pages[c])
            for c in COLUMNS
        ]
        same = list(zip(*columns, strict=True)) == table
        print(f"  read back, told nothing: same as the table? {same}")


def packing(folder: Path) -> None:
    """Analogy: the packer looks inside the boxes — the same few values said
    again and again, each in a full-size compartment.

    For the first page of every column, print its plain size and what it
    holds, for the orders as placed and for the same orders sorted by name.
    """
    folder.mkdir(parents=True, exist_ok=True)
    orders = many_orders(1000)
    by_name = sorted(orders, key=lambda row: row[3])
    names = ", ".join(COLUMNS)
    print(
        f"the orders table: {len(orders)} rows × {len(COLUMNS)} columns ({names}), "
        f"{ROWS_PER_PAGE} rows per page"
    )
    for title, table in (("as placed", orders), ("sorted by name", by_name)):
        print(f"the first page of each column, orders {title}:")
        for position, (column, codec) in enumerate(COLUMNS.items()):
            values = [row[position] for row in table[:ROWS_PER_PAGE]]
            plain = len(values) * codec.size
            print(f"  {column}: {plain} bytes plain — {describe(values)}")

    every_way("as placed", orders)
    in_dictionaries = {"price": "dictionary", "qty": "dictionary", "name": "dictionary"}
    write_and_read_back(folder / "dictionary.bin", orders, in_dictionaries)

    every_way("sorted by name", by_name)
    in_runs = {"price": "run-length", "qty": "run-length", "name": "run-length"}
    write_and_read_back(folder / "sorted.bin", by_name, in_runs)


def main() -> int:
    """Run one demo by name; with no name, print the hello line."""
    parser = argparse.ArgumentParser(prog="nanolance")
    demos = parser.add_subparsers(dest="demo")
    demo = demos.add_parser("layouts", help="store one table as rows and as columns")
    demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
    demo = demos.add_parser("pages", help="store one table as pages with a footer")
    demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
    demo = demos.add_parser("packing", help="pack each page in fewer bytes")
    demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
    args = parser.parse_args()

    if args.demo == "layouts":
        layouts(args.folder)
    elif args.demo == "pages":
        pages(args.folder)
    elif args.demo == "packing":
        packing(args.folder)
    else:
        print(f"nanolance {__version__}: scaffold is alive")
    return 0
