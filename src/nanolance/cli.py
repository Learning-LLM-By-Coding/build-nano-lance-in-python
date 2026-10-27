"""The `nanolance` command line."""

import argparse
from pathlib import Path

from nanolance import __version__, column_layout, row_layout
from nanolance.counting import CountingFile
from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH


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


def main() -> int:
    """Run one demo by name; with no name, print the hello line."""
    parser = argparse.ArgumentParser(prog="nanolance")
    demos = parser.add_subparsers(dest="demo")
    demo = demos.add_parser("layouts", help="store one table as rows and as columns")
    demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
    args = parser.parse_args()

    if args.demo == "layouts":
        layouts(args.folder)
    else:
        print(f"nanolance {__version__}: scaffold is alive")
    return 0
