"""The `nanolance` command line."""

import argparse
import struct
from collections import Counter
from itertools import groupby
from pathlib import Path

from nanolance import __version__, column_layout, encodings, page_file, row_layout
from nanolance.counting import CountingFile
from nanolance.orders import (
    COLUMNS,
    NAME_WIDTH,
    ORDERS,
    ROW_WIDTH,
    TAGGED_COLUMNS,
    TAGGED_ORDERS,
    Row,
    many_orders,
    many_tagged_orders,
    pack_value,
)
from nanolance.page_file import ROWS_PER_PAGE, Page
from nanolance.shapes import (
    OFFSET,
    STRING,
    STRING_LIST,
    Value,
    fixed_values,
    list_trays,
)


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


def write_and_read_back(
    path: Path, table: list[Row], encoding: dict[str, str]
) -> dict[str, list[Page]]:
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
    return pages


def packing_notes(boxes: list[Page]) -> str:
    """How many of one column's pages each encoding packed, e.g. "dictionary ×10"."""
    counts = Counter(page.encoding for page in boxes)
    return " + ".join(f"{name} ×{n}" for name, n in counts.items())


def ask_qty(path: Path, start: int, stop: int) -> None:
    """Analogy: Day 2's two questions, asked by a picker who knows nothing —
    the stock count, or the quantities of a few orders.

    Read qty for rows `start` to `stop` from a fresh open, and split the
    tally's bytes into the opening (footer and metadata) and the pages.
    """
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        opening = f.bytes_read
        codec, boxes = metadata.codecs["qty"], metadata.pages["qty"]
        values = page_file.read_rows(f, codec, boxes, start, stop)
        if (start, stop) == (0, metadata.rows):
            print(f"sum(qty) from {path.name}, told nothing = {sum(values)}")
        else:
            rows = f"rows {start}–{stop - 1}"
            print(f"qty of {rows} from {path.name}, told nothing = {values}")
        pages = f.bytes_read - opening
        print(f"  tally: {f.tally()} (opening {opening}, pages {pages})")


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

    plain_path, smallest_path = folder / "plain.bin", folder / "smallest.bin"
    write_and_read_back(plain_path, orders, {})
    every_column = {column: "smallest" for column in COLUMNS}
    for path, table in (
        (smallest_path, orders),
        (folder / "sorted-smallest.bin", by_name),
    ):
        pages = write_and_read_back(path, table, every_column)
        chosen = ", ".join(f"{c} {packing_notes(boxes)}" for c, boxes in pages.items())
        print(f"  chosen: {chosen}")
    for start, stop in ((0, len(orders)), (10, 20)):
        for path in (plain_path, smallest_path):
            ask_qty(path, start, stop)


def read_back(path: Path) -> list[tuple]:
    """Analogy: a picker who knows nothing unpacks every box of every aisle.

    Every row of a page file, read using only the file.
    """
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        columns = [
            page_file.read_column(f, kind, metadata.pages[column])
            for column, kind in metadata.codecs.items()
        ]
    return list(zip(*columns, strict=True))


def tray_bytes(boxes: list[Page]) -> str:
    """The bytes of one column's trays, by tray and packing note, e.g.
    "offsets plain 4040 + data plain 6250"; a page without trays counts
    under its own packing note."""
    totals = Counter()
    for page in boxes:
        if not page.trays:
            totals[page.encoding] += page.size
        for tray in page.trays:
            totals[f"{tray.name} {tray.encoding}"] += tray.size
    return " + ".join(f"{tray} {size}" for tray, size in totals.items())


def ask(path: Path, column: str, start: int, stop: int) -> tuple[list[Value], str]:
    """Analogy: a picker who knows nothing fetches a stretch of one aisle.

    Rows `start` to `stop` of `column` from a fresh open, and the tally, its
    bytes split into the opening (footer and metadata) and the pages.
    """
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        opening = f.bytes_read
        kind, boxes = metadata.codecs[column], metadata.pages[column]
        values = page_file.read_rows(f, kind, boxes, start, stop)
        pages = f.bytes_read - opening
        return values, f"{f.tally()} (opening {opening}, pages {pages})"


def shapes(folder: Path) -> None:
    """Analogy: the shop's real orders reach the packer's bench — a name too
    long for its compartment, short names rattling in theirs, and prices
    nobody has quoted yet.

    Print Day 4's table, then what Day 1's fixed widths make of it: the
    padding they spend, and the values they refuse.
    """
    folder.mkdir(parents=True, exist_ok=True)
    print(f"the orders as the shop sends them: {len(TAGGED_ORDERS)} rows")
    for row in TAGGED_ORDERS:
        print(f"  {row}")

    orders = many_orders(1000)
    slots = len(orders) * NAME_WIDTH
    letters = sum(len(row[3].encode("utf-8")) for row in orders)
    print(
        f"names of Day 3's {len(orders)} orders, in {NAME_WIDTH}-byte slots: "
        f"{slots} bytes, {letters} of them letters, {slots - letters} padding"
    )
    for column, value in (("name", "drill bits Ø6"), ("price", None)):
        try:
            pack_value(column, value)
        except (ValueError, struct.error) as error:
            print(f"pack {value!r} as a {column}: refused, {error}")
    zeros = [(0.0 if row[1] is None else row[1], row[3]) for row in TAGGED_ORDERS]
    known = [row[1] for row in TAGGED_ORDERS if row[1] is not None]
    price, name = min(zeros)
    average = sum(p for p, _ in zeros) / len(zeros)
    print(f"  stored as 0.0 instead: the cheapest order is {name} at {price}")
    print(
        f"  and the average price is {average:.2f}; "
        f"the {len(known)} known prices average {sum(known) / len(known):.2f}"
    )

    every_column = {column: "smallest" for column in COLUMNS}
    in_slots = sum(
        len(encodings.smallest(COLUMNS["name"], page)[1])
        for page in page_file.plain_pages(orders, "name")
    )
    print(f"the same names as strings (in slots: plain {slots}, smallest {in_slots}):")
    as_strings = {**COLUMNS, "name": STRING}
    strings_path, smallest_path = (
        folder / "strings.bin",
        folder / "strings-smallest.bin",
    )
    strings = page_file.write(strings_path, orders, columns=as_strings)
    smallest = page_file.write(
        smallest_path, orders, encoding=every_column, columns=as_strings
    )
    for path, boxes in ((strings_path, strings), (smallest_path, smallest)):
        stored = sum(page.size for page in boxes["name"])
        print(f"  {path.name}: {stored} bytes = {tray_bytes(boxes['name'])}")
        same = read_back(path) == orders
        print(f"    read back, told nothing: same as the table? {same}")

    shop = [(row[3],) for row in TAGGED_ORDERS]
    page_file.write(folder / "shop-names.bin", shop, columns={"name": STRING})
    names = [name for (name,) in read_back(folder / "shop-names.bin")]
    print(f"the shop's names as strings, read back: {names}")

    k = 4
    print(f"one name, row {k}, from a box the picker already knows:")
    padded_path = folder / "padded.bin"
    page = page_file.write(padded_path, orders)["name"][0]
    with CountingFile(padded_path) as f:
        f.seek(page.offset + k * NAME_WIDTH)  # a fixed width makes this arithmetic
        (name,) = fixed_values(COLUMNS["name"], f.read(NAME_WIDTH))
        print(f"  {padded_path.name}: {name!r} — tally: {f.tally()}")
    with CountingFile(strings_path) as f:
        name = page_file.read_string(f, strings["name"][0], k)
        print(f"  {strings_path.name}: {name!r} — tally: {f.tally()}")

    print("the shop's tags as one box of lists, tray by tray:")
    trays = list_trays([row[4] for row in TAGGED_ORDERS])
    for tray in ("list offsets", "offsets"):
        print(f"  {tray}: {[end for (end,) in OFFSET.iter_unpack(trays[tray])]}")
    print(f"  data: {trays['data']}")
    tagged = many_tagged_orders(1000)
    tags = [(row[4],) for row in tagged]
    n_tags = sum(len(row[4]) for row in tagged)
    n_empty = sum(not row[4] for row in tagged)
    print(f"tags of {len(tagged)} shop orders: {n_tags} tags, {n_empty} empty lists")
    for path, encoding in (
        (folder / "tags.bin", {}),
        (folder / "tags-smallest.bin", {"tags": "smallest"}),
    ):
        boxes = page_file.write(
            path, tags, encoding=encoding, columns={"tags": STRING_LIST}
        )
        stored = sum(page.size for page in boxes["tags"])
        print(f"  {path.name}: {stored} bytes = {tray_bytes(boxes['tags'])}")
        same = read_back(path) == tags
        print(f"    read back, told nothing: same as the table? {same}")

    shop_path = folder / "shop.bin"
    every_column = {column: "smallest" for column in TAGGED_COLUMNS}
    boxes = page_file.write(
        shop_path, tagged, encoding=every_column, columns=TAGGED_COLUMNS
    )
    size = shop_path.stat().st_size
    print(f"write {shop_path.name}: {size} bytes, every column packed smallest")
    for column, pages in boxes.items():
        stored = sum(page.size for page in pages)
        print(f"  {column}: {stored} = {tray_bytes(pages)}")
    same = read_back(shop_path) == tagged
    print(f"  read back, told nothing: same as the table? {same}")

    qty, tally = ask(shop_path, "qty", 0, len(tagged))
    print(f"sum(qty) from {shop_path.name}, told nothing = {sum(qty)}")
    print(f"  tally: {tally}")
    prices, tally = ask(shop_path, "price", 0, len(tagged))
    known = [price for price in prices if price is not None]
    average = sum(known) / len(known)
    missing = len(prices) - len(known)
    print(f"average price from {shop_path.name} = {average:.2f}, {missing} missing")
    print(f"  tally: {tally}")
    names, tally = ask(shop_path, "name", 10, 20)
    print(f"names of rows 10–19 from {shop_path.name} = {names}")
    print(f"  tally: {tally}")


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
    demo = demos.add_parser("shapes", help="store values of any length, or none")
    demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
    args = parser.parse_args()

    if args.demo == "layouts":
        layouts(args.folder)
    elif args.demo == "pages":
        pages(args.folder)
    elif args.demo == "packing":
        packing(args.folder)
    elif args.demo == "shapes":
        shapes(args.folder)
    else:
        print(f"nanolance {__version__}: scaffold is alive")
    return 0
