"""The `nanolance` command line."""

import argparse
from pathlib import Path

from nanolance import __version__, row_layout
from nanolance.counting import CountingFile
from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH


def layouts(folder: Path) -> None:
    """Analogy: open the warehouse and pack the orders into crates.

    Store the orders table as rows, read it back, and print every step.
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
