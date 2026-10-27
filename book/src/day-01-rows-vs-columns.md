# Day 1: Rows vs columns

> **Day 1** (of Days 0–17) · builds on `v1-day-00` · ≈ 2 h

| Section | Builds | Checkpoint |
|---------|--------|------------|
| A | The orders table, stored row by row | `v1-day-01a` |
| B | A counting file: what one question reads | `v1-day-01b` |
| C | The same table, stored column by column | `v1-day-01c` |
| D | Fetching one whole row, both ways | `v1-day-01d` = `v1-day-01` |

**Pick your mode before starting** (explained fully in
[Setup](setup.md#4-choose-how-you-follow-along)):

```bash
# Build mode — type today's code yourself, on your own branch:
git switch -c my-course v1-day-00      # branch off the Day 0 scaffold

# Inspect mode — read along with the finished code instead:
git switch --detach v1-day-01a         # then 01b, 01c, 01d as you pass each section
```

<div class="callout">

**Today's typing budget** — so nothing sneaks up on you:

| Section | The learning | Wiring & tests (copy-friendly) |
|---------|--------------|--------------------------------|
| A | `pack_value` + `unpack_value` · ~25 lines; the row file's `write`, `read_row`, `read_all` · ~35 lines | the table itself (~30 lines), a new `cli.py`, 7 tests |
| B | `CountingFile` · ~45 lines; the row file's `sum_column` · ~8 lines | 2 demo edits, 5 tests |
| C | the column file's `write`, `column_start`, `read_column`, `read_all`, `sum_column` · ~60 lines | 3 demo edits, 5 tests |
| D | two `fetch_row` functions · ~20 lines | demo lines, 3 tests |

Four sections are four natural sittings, and every checkpoint is a save
point — nothing says a "day" must fit in one. Today needs **no
dependencies**: everything comes from Python's standard library.

</div>

## 1. What you will have running

By the end of today, `uv run nanolance layouts` takes a tiny table — eight
orders, each with an id, a price, a quantity, and an item name — and
writes it to disk **twice**: once with each order's values side by side,
once with each column's values side by side. Then it asks both files the
same two questions and prints what each answer cost:

- **"How many items are on order, in all?"** — a question about one
  column, across every row.

- **"Show me the sixth order."** — a question about one row, across every
  column.

The cost is not a stopwatch time. It is a **count**: how many separate
reads the question issued, how many bytes came back, and how many times
the reader told the file where to go next (a *seek*). You build the small
wrapper that counts those today, and every later day reuses it.

The two layouts are the oldest trade-off in data storage, and you will
see it in plain numbers: one layout wins the first question by a factor
of eight, and the other wins the second.

<div class="dl-concepts"><span>Lance concepts used here:</span>
<a href="https://en.wikipedia.org/wiki/Column-oriented_DBMS">row vs column storage (Wikipedia) ↗</a>
<a href="https://lance.org/format/file/">the Lance file format: "a columnar container" ↗</a>
<a href="https://www.cs.umd.edu/~abadi/papers/abadi-sigmod08.pdf">Column-Stores vs. Row-Stores (Abadi et al., SIGMOD 2008) ↗</a>
</div>

## 2. What you will be seeing in the output

A sneak peek at the end of the day — the exact output you will produce,
with a plain-English note under each group of lines. If a note doesn't
fully land yet, that's fine; the rest of the day builds every piece:

```text
the orders table: 8 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  (104, 7.0, 2, 'tape')
  (105, 23.5, 1, 'drill bits')
  (106, 3.25, 12, 'nails')
  (107, 9.75, 4, 'gloves')
  (108, 15.0, 2, 'padlock')
write rows.bin: 256 bytes = 8 rows × 32 bytes
read rows.bin back: same as the table? True
  tally: reads 8, bytes read 256, seeks 0
sum(qty) from rows.bin = 65
  tally: reads 8, bytes read 256, seeks 0 (qty needs only 32 of them)
write columns.bin: 256 bytes = id 64 + price 64 + qty 32 + name 96
read columns.bin back: same as the table? True
  tally: reads 4, bytes read 256, seeks 4
sum(qty) from columns.bin = 65
  tally: reads 1, bytes read 32, seeks 1
fetch row 5 from rows.bin = (106, 3.25, 12, 'nails')
  tally: reads 1, bytes read 32, seeks 1
fetch row 5 from columns.bin = (106, 3.25, 12, 'nails')
  tally: reads 4, bytes read 32, seeks 4
```

- The first nine lines — the table: eight orders, four values each. This
  is all the data there is today.

- `write rows.bin: 256 bytes = 8 rows × 32 bytes` — the first file keeps
  each order's four values together. Every value has a fixed size, so
  every order takes exactly 32 bytes, and eight orders take 256.

- `read rows.bin back: same as the table? True` and the `tally` line under
  it — reading the whole file back gives exactly the table again. The
  tally line counts the work: eight reads (one per order), all 256 bytes,
  and no seeks.

- `sum(qty) from rows.bin = 65` and its tally — the first question: add
  up the quantities. The answer is right, but the reader had to read all
  256 bytes, although the quantities themselves are only 32 of them.

- `write columns.bin` down to `sum(qty) from columns.bin = 65` — the
  second file holds the same 256 bytes, arranged by column: all eight ids,
  then all eight prices, then the quantities, then the names. It also
  reads back to exactly the table. The same question now costs one seek
  and one read of 32 bytes: an eighth of what the first file needed.

- The last four lines — the second question: fetch the sixth order
  (counting from zero, it is row 5). Both files give the same order and
  read the same 32 bytes. But the first file needs one seek and one read;
  the second needs four of each, one per column.

## 3. Why we need it

The Day 0 scaffold stores nothing. Every data format, though — a CSV
file, a database, Parquet, Lance — has to answer one question before any
other: **which bytes go next to which?** A table is a grid, and a file
is a single line of bytes. Laying a grid out on a line leaves two obvious
choices: row after row, or column after column.

The choice matters because the two common questions are opposite shapes.
A report, a filter, or a training job's statistics ask about **a few
columns across many rows**. A search result or a single training sample
asks for **one row with all its columns**. Whichever layout you pick,
one of those questions has to read around the bytes it does not need.
Lance is a *columnar* format — it picks columns — and much of its design
is about making the other question cheap as well. Before any of that
design makes sense, you need to feel the trade-off yourself, in bytes.

**The story starts here — meet [the warehouse](story.md).** Every day of
this book adds one scene to a single running story, and today the
warehouse opens. It stores orders. Each order has four values — its id,
price, quantity, and the item's name — and every value goes into a
compartment of a fixed size: that is **the packing rule**. The warehouse
can shelve the orders two ways: **packed in crates**, one crate per
order, or **sorted into aisles**, one aisle per column (ids, prices,
quantities, names). Someone has to fetch things for every question —
call them **the picker** — and the picker carries a clipboard, **the
tally**, that records every request. Two people ask the questions.
**The manager** wants the **stock count**: how many items are on order
in all — one column, across every row. **A customer** comes for a
**pickup**: one whole order — one row, with all its columns. Section A
writes the packing rule and packs the crates, section B hands the
picker the tally and runs the stock count, section C sorts the same
orders into aisles, and section D sends the customer to collect one
order from each. The whole story, scene by scene, lives on one page —
[The warehouse: an analogy to help you build the right mental model](story.md)
— which grows by one scene every day.

## 4. Mental model

Walk the warehouse, one station per section:

- **[The packing rule](story.md#packing-rule) (section A).** Every crate
  has the same four compartments, and every compartment has a fixed size:
  8 bytes for the id, 8 for the price, 4 for the quantity, 12 for the
  name. Short names get padding to fill their 12 bytes. Fixed sizes make
  position plain arithmetic: every order is 32 bytes, so order number *k*
  (counting from zero) starts at byte *k* × 32.

- **[Crates](story.md#row-layout) (section A).** The row layout: crate
  after crate along one long shelf. Order 101's 32 bytes, then order
  102's, and so on.

- **[The tally](story.md#tally) (section B).** The picker's clipboard. It
  counts three things: every **read** (one armful carried back), every
  **byte** in those armfuls, and every **seek** — each time the reader
  tells the file where to go next. The tally counts the request, even
  when the picker happens to be standing there already.

- **[The stock count](story.md#stock-count) (sections B and C).** The
  manager asks how many items are on order in all. With crates, the
  picker has to open every crate to reach its quantity compartment, and
  carries the whole crate to do it.

- **[Aisles](story.md#column-layout) (section C).** The column layout:
  the same orders, unpacked. The id aisle holds all eight ids in order,
  then the price aisle, the quantity aisle, and the name aisle. Spot *k*
  in every aisle belongs to order *k*. The stock count is now one walk to
  one aisle and one armful.

- **[A customer pickup](story.md#pickup) (section D).** A customer comes
  for one whole order. With crates, that is one walk and one crate. With
  aisles, it is a stop in every aisle — four walks, four small armfuls.

Here are the two files, byte by byte, as the picker sees them (each box
is one value; the numbers under each file are byte positions):

```text
rows.bin     │101│4.25│3│bolts│102│12.5│1│hammer│ … │108│15.0│2│padlock│
             0                32                    224                256

columns.bin  │101│102│ … │108│4.25│12.5│ … │15.0│3│1│ … │2│bolts│ … │padlock│
             0               64                 128       160               256
```

And the whole day as data flowing down the page:

```text
the orders table          8 orders × 4 values (id, price, qty, name)
    │ pack each value into its fixed-size compartment
    ▼
32 bytes per order        8 (id) + 8 (price) + 4 (qty) + 12 (name)
    │ lay the orders out two ways
    ▼
rows.bin     256 bytes    crates: order 101's 32 bytes, then 102's, …
columns.bin  256 bytes    aisles: 8 ids, 8 prices, 8 quantities, 8 names
    │ the stock count — sum(qty) — through the tally
    ▼
rows.bin     256 bytes    every crate carried back, for 32 bytes of answers
columns.bin   32 bytes    one walk to the qty aisle, one armful
    │ a customer pickup — row 5 — through the tally
    ▼
rows.bin     1 seek       one walk, one crate
columns.bin  4 seeks      a stop in each of the four aisles
```

## 5. Lance concepts introduced

- **Row-oriented vs column-oriented storage.** Storing a table row by row
  is how most transactional databases (PostgreSQL, MySQL) keep their
  tables: a whole record is together, so reading or updating one record
  is cheap. Storing it column by column is how analytics formats work —
  Parquet, ORC, and Lance among them: a question about a few columns
  reads only those columns. The SIGMOD paper linked above measures the
  gap on real queries.

- **Fixed-width values.** When every value of a column has the same size,
  the position of value *k* is arithmetic, with no lookup needed. Today
  every column is fixed-width, even the names (12 bytes, padded).
  Variable-length text needs an extra list of where each value starts —
  that arrives on Day 4.

- **Scans and takes.** A *scan* reads some columns for every row (the
  stock count). Fetching rows by position (the pickup) is what Lance
  calls a **take**; its file format is built to keep takes cheap, and
  Day 5 measures how.

- **Reads and seeks are what storage charges for.** Every read is a
  separate request to the storage — on cloud object storage, a separate
  network request. Counting reads, bytes, and seeks is how this course
  measures every layout, in any language.

- **Byte order.** A number bigger than one byte has to be stored in some
  byte order. Today's files use *little-endian* order — the smallest byte
  first — the order most current processors use.

## 6. Build it, section by section

Each section opens with a **Python used here** strip: the language
features its code leans on, each linked to the matching page of the
official Python documentation. Read only the ones you need.

### Section A — the orders table, stored row by row

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/struct.html"><code>struct</code>: turns a number into exact bytes and back</a>
<a href="https://docs.python.org/3.12/library/struct.html#format-characters"><code>struct</code> format characters: <code>q</code>, <code>d</code>, <code>i</code>, <code>12s</code> name the byte layout</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#bytes"><code>bytes</code>: an unchangeable run of raw bytes</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#dictionaries">dictionaries: names mapped to values, kept in insertion order</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#tuples-and-sequences">tuples: a fixed group of values, like one row</a>
<a href="https://docs.python.org/3.12/tutorial/introduction.html#lists">lists: an ordered, growable sequence</a>
<a href="https://docs.python.org/3.12/library/functions.html#sum"><code>sum</code>: adds up a sequence of numbers</a>
<a href="https://docs.python.org/3.12/glossary.html#term-generator-expression">generator expressions: <code>(x for x in …)</code>, values made one at a time</a>
<a href="https://docs.python.org/3.12/library/typing.html#type-aliases">type aliases: a short name for a type, like <code>Row</code></a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#types-union">union types: <code>int | str</code> means "an int or a str"</a>
<a href="https://docs.python.org/3.12/library/functions.html#isinstance"><code>isinstance</code>: is this value of that type?</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#str.encode"><code>str.encode</code>: text to bytes</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#bytes.decode"><code>bytes.decode</code>: bytes back to text</a>
<a href="https://docs.python.org/3.12/tutorial/errors.html#raising-exceptions"><code>raise</code>: stop with an error</a>
</div>

First, the table itself. A table needs two things before it can be
stored: its rows, and a rule for turning each value into bytes. Create
`src/nanolance/orders.py`:

```python
"""The orders table: its columns, its eight rows, and how one value becomes bytes."""

import struct

NAME_WIDTH = 12

# Analogy: the packing rule — every crate has the same four compartments,
# each one a fixed size, so where anything sits is plain arithmetic.
#
# Each column's values are packed with one `struct` format: "<" means
# little-endian with values back to back, no gaps; q = 8-byte int,
# d = 8-byte float, i = 4-byte int, 12s = 12 raw bytes.
COLUMNS = {
    "id": struct.Struct("<q"),
    "price": struct.Struct("<d"),
    "qty": struct.Struct("<i"),
    "name": struct.Struct(f"<{NAME_WIDTH}s"),
}
ROW_WIDTH = sum(codec.size for codec in COLUMNS.values())

Row = tuple[int, float, int, str]

ORDERS: list[Row] = [
    (101, 4.25, 3, "bolts"),
    (102, 12.5, 1, "hammer"),
    (103, 0.75, 40, "washers"),
    (104, 7.0, 2, "tape"),
    (105, 23.5, 1, "drill bits"),
    (106, 3.25, 12, "nails"),
    (107, 9.75, 4, "gloves"),
    (108, 15.0, 2, "padlock"),
]
```

- `COLUMNS` is the packing rule, one entry per column, in table order.
  Each entry is a `struct.Struct`, Python's tool for turning a value
  into an exact run of bytes and back; the code calls one a `codec`,
  short for coder-decoder. Its format string says how: `"<q"` is an
  8-byte whole number, `"<d"` an 8-byte number with a fractional part
  (a *float*), `"<i"` a 4-byte whole number, and `"<12s"` twelve raw
  bytes. The `<` picks little-endian byte order and packs values back
  to back with no gaps.

- `ROW_WIDTH` adds the four widths with `sum`: 8 + 8 + 4 + 12 = 32 bytes
  per order.
  It is computed, not typed, so it can never disagree with `COLUMNS`.

- `Row` is a name for the shape of one row: a tuple of an int, a float,
  an int, and a string. Writing `list[Row]` reads better than spelling
  that out each time.

- `ORDERS` is the data: eight orders. The prices are all multiples of a
  quarter, which a float stores exactly — so "same as the table?" can be
  answered with a plain `==`.

Then, at the bottom of the same file, the two functions that move one
value in and out of its compartment:

```python
# ──────── new code starts here (around line 35) ────────
def pack_value(column: str, value: int | float | str) -> bytes:
    """Analogy: put one value into its compartment.

    Turns one value of `column` into exactly that column's width in bytes.
    Text is encoded as UTF-8 and padded with zero bytes up to NAME_WIDTH.
    """
    if isinstance(value, str):
        value = value.encode("utf-8")
        if len(value) > NAME_WIDTH:
            raise ValueError(
                f"{column} needs {len(value)} bytes; the slot holds {NAME_WIDTH}"
            )
    return COLUMNS[column].pack(value)


def unpack_value(column: str, raw: bytes) -> int | float | str:
    """Analogy: take one value out of its compartment.

    The reverse of `pack_value`: `raw` must be exactly the column's width.
    """
    (value,) = COLUMNS[column].unpack(raw)
    if isinstance(value, bytes):
        value = value.rstrip(b"\0").decode("utf-8")
    return value


# ──────── new code ends here ────────
```

- `pack_value` handles text first: `str.encode("utf-8")` turns the name
  into bytes, and a name longer than its 12-byte slot raises an error.
  That check matters. Without it, `struct` would cut the name short
  without a word, and the table you read back would quietly differ from
  the one you wrote. Shorter names are fine: `struct` pads them with zero
  bytes up to 12.

- `unpack_value` is the mirror image. `struct` always hands back a tuple,
  even for one value, and `(value,) = …` unpacks that one-value tuple.
  Text comes back as 12 bytes, so the padding zeros are stripped
  (`rstrip(b"\0")`) before decoding.

One idea before the first layout. An open file keeps a **current
position** — think of it as a bookmark. Every read starts at the bookmark
and moves it forward past the bytes it returned, so two reads of 32 bytes
give you the first 32 bytes, then the next 32. Reading never needs to be
told where to go as long as you want the next bytes. (Section B adds the
way to move the bookmark on purpose: a *seek*.)

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/functions.html#open"><code>open</code>: opens a file; <code>"wb"</code> / <code>"rb"</code> mean write / read bytes</a>
<a href="https://docs.python.org/3.12/reference/compound_stmts.html#the-with-statement"><code>with</code>: closes the file when the block ends</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#for-statements"><code>for</code> loops: run the body once per element</a>
<a href="https://docs.python.org/3.12/library/functions.html#zip"><code>zip</code>: walks several sequences in step</a>
<a href="https://docs.python.org/3.12/reference/expressions.html#slicings">slicing: <code>raw[a : b]</code> is the bytes from a up to b</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#list-comprehensions">list comprehensions: <code>[f(x) for x in …]</code> builds a list</a>
<a href="https://docs.python.org/3.12/library/functions.html#func-range"><code>range</code>: the numbers 0, 1, 2, … up to n</a>
<a href="https://docs.python.org/3.12/library/typing.html#typing.BinaryIO"><code>typing.BinaryIO</code>: "something you can read bytes from"</a>
</div>

Now the first layout. Create `src/nanolance/row_layout.py`:

```python
"""Analogy: one crate per order — all of an order's values packed together.

The row layout: the file is row 0's bytes, then row 1's, then row 2's, ...
Each row is ROW_WIDTH bytes, its values in column order.
"""

from pathlib import Path
from typing import BinaryIO

from nanolance.orders import COLUMNS, ROW_WIDTH, Row, pack_value, unpack_value


def write(path: Path, rows: list[Row]) -> None:
    """Write `rows` to `path` one whole row after another."""
    with open(path, "wb") as out:
        for row in rows:
            for column, value in zip(COLUMNS, row, strict=True):
                out.write(pack_value(column, value))


def read_row(f: BinaryIO) -> Row:
    """Read the row that starts at the file's current position."""
    raw = f.read(ROW_WIDTH)
    values = []
    start = 0
    for column, codec in COLUMNS.items():
        values.append(unpack_value(column, raw[start : start + codec.size]))
        start += codec.size
    return tuple(values)


def read_all(f: BinaryIO, n_rows: int) -> list[Row]:
    """Read every row, front to back. The file does not record how many
    rows it holds, so the caller has to say."""
    return [read_row(f) for _ in range(n_rows)]
```

- `write` opens the file in `"wb"` mode (write, binary) and packs each
  row's values in column order — the inner loop runs across one row, so
  each order's four values land next to each other: a crate. The `with`
  block closes the file when it ends. `zip(COLUMNS, row, strict=True)`
  walks the column names and the row's values in step, and
  `strict=True` makes it complain if a row has the wrong number of
  values.

- `read_row` reads one 32-byte crate from the bookmark, then cuts it
  apart by the same widths, front to back.

- `read_all` calls `read_row` once per row. Notice its second parameter:
  **the file does not say how many rows it holds**, so the caller has to.
  Remember that; it comes back on Day 2.

- `f: BinaryIO` means "something you can read bytes from". Today that is
  a file from `open`; from section B on, it will be a file that counts.

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/argparse.html#sub-commands"><code>argparse</code> subcommands: <code>nanolance layouts</code>-style commands</a>
<a href="https://docs.python.org/3.12/library/argparse.html#dest"><code>dest</code>: where the chosen subcommand's name is stored</a>
<a href="https://docs.python.org/3.12/library/argparse.html#type"><code>type=</code>: converts an argument from text</a>
<a href="https://docs.python.org/3.12/library/argparse.html#nargs"><code>nargs="?"</code>: an argument you may leave out</a>
<a href="https://docs.python.org/3.12/library/pathlib.html#operators"><code>pathlib.Path</code>: a file path; <code>/</code> joins parts</a>
<a href="https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.mkdir"><code>Path.mkdir</code>: creates a folder</a>
<a href="https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.stat"><code>Path.stat</code>: file facts, such as its size</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#str.join"><code>str.join</code>: glues strings with a separator</a>
</div>

Last, the command line. The demo needs a name you can ask for, so
`nanolance` learns its first subcommand. Replace all nine lines of Day
0's `src/nanolance/cli.py` with this file — Day 0's hello line survives,
in the `else` branch at the end:

```python
"""The `nanolance` command line."""

import argparse
from pathlib import Path

from nanolance import __version__, row_layout
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
    with open(rows_path, "rb") as f:
        same = row_layout.read_all(f, n_rows) == ORDERS
    print(f"read {rows_path.name} back: same as the table? {same}")


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
```

- `main` now reads the command line with `argparse`. `dest="demo"`
  stores the chosen subcommand's name in `args.demo` — `"layouts"`, or
  `None` when you typed no subcommand, which prints Day 0's hello line.

- The `folder` argument is optional (`nargs="?"`) and defaults to a
  folder called `warehouse`. `type=Path` turns the text you typed into a
  `Path`, so the code can join it with file names.

- `layouts` starts with `folder.mkdir(parents=True, exist_ok=True)`:
  create the folder, and any missing folders above it, and carry on
  quietly if it already exists. Then it prints the table, writes
  `rows.bin`, and reads it back — one printed line per step, so you can
  watch the data move. `folder / "rows.bin"` is how `pathlib` joins a
  folder and a file name.

One small housekeeping step: the demo writes into `warehouse/`, and those
files should never be committed. Add this line to `.gitignore`:

```text
/warehouse
```

Run it:

```bash
uv run nanolance layouts
```

```text
the orders table: 8 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  (104, 7.0, 2, 'tape')
  (105, 23.5, 1, 'drill bits')
  (106, 3.25, 12, 'nails')
  (107, 9.75, 4, 'gloves')
  (108, 15.0, 2, 'padlock')
write rows.bin: 256 bytes = 8 rows × 32 bytes
read rows.bin back: same as the table? True
```

Read it line by line:

- `the orders table: 8 rows × 4 columns (id, price, qty, name)` and the
  eight lines under it — `ORDERS`, printed by the loop at the top of
  `layouts`. Each line is one order, in the order it will be packed.

- `write rows.bin: 256 bytes = 8 rows × 32 bytes` — `row_layout.write`
  packed eight crates of `ROW_WIDTH` bytes; the size comes from the file
  on disk (`stat().st_size`), so it is a measurement, not a promise.

- `read rows.bin back: same as the table? True` — `read_all` unpacked
  every crate, and the result compares equal to `ORDERS`, value for value.

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.read_bytes"><code>Path.read_bytes</code>: a whole file as bytes</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#bytes.hex"><code>bytes.hex</code>: bytes as two hex digits each</a>
</div>

You can look at the bytes themselves. This one-line Python command prints
the first 32 bytes of `rows.bin` — one crate — as hexadecimal, two digits
per byte:

```bash
uv run python -c "from pathlib import Path; print(Path('warehouse/rows.bin').read_bytes()[:32].hex(' '))"
```

```text
65 00 00 00 00 00 00 00 00 00 00 00 00 00 11 40 03 00 00 00 62 6f 6c 74 73 00 00 00 00 00 00 00
```

That is order 101, all of it, in compartment order:

- `65 00 00 00 00 00 00 00` — the id. Hex `65` is 6 × 16 + 5 = 101, and
  little-endian puts that smallest byte first; the other seven bytes are
  zero.

- `00 00 00 00 00 00 11 40` — the price, 4.25. Floats have their own bit
  recipe, so this one is not readable by eye; `struct` handles it.

- `03 00 00 00` — the quantity, 3, in four bytes.

- `62 6f 6c 74 73` and seven `00`s — the letters `b o l t s` as UTF-8
  bytes, then the zero padding that fills the 12-byte name slot.

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.pytest.org/en/stable/how-to/tmp_path.html">pytest's <code>tmp_path</code>: a fresh temporary folder per test</a>
<a href="https://docs.pytest.org/en/stable/how-to/assert.html#assertions-about-expected-exceptions"><code>pytest.raises</code>: the test passes only if this error happens</a>
</div>

Now pin it with tests. Create `tests/test_orders.py` for the packing
rule:

```python
import pytest

from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH, pack_value, unpack_value


def test_every_column_has_a_fixed_width():
    widths = {column: codec.size for column, codec in COLUMNS.items()}
    assert widths == {"id": 8, "price": 8, "qty": 4, "name": 12}
    assert ROW_WIDTH == 32


def test_every_value_round_trips_through_its_bytes():
    for row in ORDERS:
        for column, value in zip(COLUMNS, row, strict=True):
            raw = pack_value(column, value)
            assert len(raw) == COLUMNS[column].size
            assert unpack_value(column, raw) == value


def test_short_names_are_padded_with_zero_bytes():
    assert pack_value("name", "tape") == b"tape" + bytes(8)


def test_names_longer_than_their_slot_are_refused():
    with pytest.raises(ValueError, match="needs 15 bytes"):
        pack_value("name", "screwdriver set")
```

`bytes(8)` is eight zero bytes: `tape` fills 4 bytes of its 12-byte
slot, and the other 8 are padding.

Create `tests/test_row_layout.py` for the crates — the first test checks
that the first 32 bytes on disk are exactly order 101, packed:

```python
from nanolance import row_layout
from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH, pack_value


def test_each_row_is_stored_in_one_piece(tmp_path):
    path = tmp_path / "rows.bin"
    row_layout.write(path, ORDERS)
    data = path.read_bytes()
    assert len(data) == len(ORDERS) * ROW_WIDTH
    first_row = b"".join(
        pack_value(column, value)
        for column, value in zip(COLUMNS, ORDERS[0], strict=True)
    )
    assert data[:ROW_WIDTH] == first_row


def test_rows_round_trip_exactly(tmp_path):
    path = tmp_path / "rows.bin"
    row_layout.write(path, ORDERS)
    with open(path, "rb") as f:
        assert row_layout.read_all(f, len(ORDERS)) == ORDERS
```

And `tests/test_cli.py` runs the real command, the way Day 0's hello test
does, into a fresh temporary folder (`tmp_path`, which pytest creates for
each test and cleans up later):

```python
import subprocess
import sys


def run_layouts(folder):
    result = subprocess.run(
        [sys.executable, "-m", "nanolance", "layouts", str(folder)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def test_layouts_stores_the_table_as_rows(tmp_path):
    lines = run_layouts(tmp_path)
    assert lines[0] == "the orders table: 8 rows × 4 columns (id, price, qty, name)"
    assert "write rows.bin: 256 bytes = 8 rows × 32 bytes" in lines
    assert "read rows.bin back: same as the table? True" in lines
```

```bash
uv run pytest -q
```

```text
.........                                                                [100%]
9 passed in 0.07s
```

Nine tests: Day 0's two and today's seven.

**Section checkpoint:** `./scripts/compare.sh v1-day-01a` — its ✓ line
means your code matches the official section state.

### Section B — the tally: what one question reads

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/tutorial/classes.html#a-first-look-at-classes">classes, <code>__init__</code>, <code>self</code>: your own type, with data and methods</a>
<a href="https://docs.python.org/3.12/reference/datamodel.html#context-managers"><code>__enter__</code> / <code>__exit__</code>: what makes a type work with <code>with</code></a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#arbitrary-argument-lists"><code>*args</code>: accept any number of arguments</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#more-on-lists"><code>list.index</code>: the position of a value in a list</a>
</div>

Your row file works: it holds the table and gives it back exactly. So ask
it a question — the manager's stock count, *how many items are on order
in all?* The quantities are inside the crates, so the reader opens every
crate and adds up one compartment from each.

But how much did that cost? Right now nobody can say. `read_all` reads
from a plain file, and a plain file keeps no record. To measure, the
reader needs a file that keeps count — the picker's tally. Create
`src/nanolance/counting.py`:

```python
"""Analogy: the tally — the picker's clipboard, marked on every trip.

A file you read through a CountingFile counts its own work: how many reads
were issued, how many bytes came back, and how many times the reader told
the file where to go next (every seek request counts, even one to the
current position). Every "this reads less" claim in the course is one of
these counts.
"""

from pathlib import Path


class CountingFile:
    """A binary file opened for reading that counts reads, bytes, and seeks."""

    def __init__(self, path: Path) -> None:
        self._file = open(path, "rb")
        self.reads = 0
        self.bytes_read = 0
        self.seeks = 0

    def read(self, size: int) -> bytes:
        """Read up to `size` bytes from the current position."""
        data = self._file.read(size)
        self.reads += 1
        self.bytes_read += len(data)
        return data

    def seek(self, offset: int) -> None:
        """Jump to byte `offset`, counted from the start of the file."""
        self._file.seek(offset)
        self.seeks += 1

    def tally(self) -> str:
        return f"reads {self.reads}, bytes read {self.bytes_read}, seeks {self.seeks}"

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "CountingFile":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
```

- `CountingFile` *wraps* a real file: it opens one in `__init__`, keeps it
  in `self._file` (the leading underscore says "internal — use the
  methods"), and starts three counters at zero.

- `read` and `seek` do the real work through `self._file`, then add to
  the counters. `bytes_read` adds `len(data)` — what really came back,
  which can be less than asked for at the end of the file.

- `seek(offset)` moves the bookmark to byte `offset`, counted from the
  start. The tally counts every seek request — even one to the spot the
  bookmark is already at — because it counts what the reader asks for.
  Reading straight through a file needs no seeks at all.

- `__enter__` and `__exit__` let a `CountingFile` sit in a `with` block,
  the same way a file from `open` does: the file is closed when the block
  ends, even if the code inside it fails.

`CountingFile` has `read` and `seek`, so the row reader accepts it as it
is — nothing in `read_all` changes. The stock count gets its own small
function, at the bottom of `src/nanolance/row_layout.py`:

```python
# ──────── new code starts here (around line 38) ────────
def sum_column(f: BinaryIO, column: str, n_rows: int) -> int | float:
    """Analogy: the stock count, done crate by crate.

    Add up one column's values. In this layout the values sit inside every
    row, so every row is read whole.
    """
    position = list(COLUMNS).index(column)
    return sum(row[position] for row in read_all(f, n_rows))


# ──────── new code ends here ────────
```

`list(COLUMNS).index(column)` finds the column's position in a row (`qty`
is position 2). Then `sum` adds that position from every row that
`read_all` hands back. There is no way to reach the quantities without
reading the crates they sit in.

Now let the demo use the tally. Two edits in `src/nanolance/cli.py`:

1. Import the new class, on a new line right under
   `from nanolance import __version__, row_layout` (around line 7):

   ```python
   from nanolance.counting import CountingFile
   ```

2. In `layouts`, replace the last three lines — the
   `with open(rows_path, "rb") as f:` block and the `print` after it —
   with a read-back through the tally, followed by the stock count:

   ```python
       # ──────── replacement starts here (around line 27) ────────
       with CountingFile(rows_path) as f:
           same = row_layout.read_all(f, n_rows) == ORDERS
           print(f"read {rows_path.name} back: same as the table? {same}")
           print(f"  tally: {f.tally()}")

       needed = n_rows * COLUMNS["qty"].size
       with CountingFile(rows_path) as f:
           total = row_layout.sum_column(f, "qty", n_rows)
           print(f"sum(qty) from {rows_path.name} = {total}")
           print(f"  tally: {f.tally()} (qty needs only {needed} of them)")
       # ──────── replacement ends here ────────
   ```

   Each question gets a fresh `CountingFile`, so each tally counts one
   question only. `needed` is how many bytes the quantities really
   occupy: 8 rows × 4 bytes.

Run it again:

```bash
uv run nanolance layouts
```

```text
the orders table: 8 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  (104, 7.0, 2, 'tape')
  (105, 23.5, 1, 'drill bits')
  (106, 3.25, 12, 'nails')
  (107, 9.75, 4, 'gloves')
  (108, 15.0, 2, 'padlock')
write rows.bin: 256 bytes = 8 rows × 32 bytes
read rows.bin back: same as the table? True
──── everything above: section A's output, unchanged ────
  tally: reads 8, bytes read 256, seeks 0
sum(qty) from rows.bin = 65
  tally: reads 8, bytes read 256, seeks 0 (qty needs only 32 of them)
```

Read the new lines one by one:

- `tally: reads 8, bytes read 256, seeks 0` — reading the table back:
  `read_all` called `read_row` eight times, and each call made one read
  of 32 bytes. No seeks: each read started where the last one ended.

- `sum(qty) from rows.bin = 65` — the stock count, from `sum_column`:
  3 + 1 + 40 + 2 + 1 + 12 + 4 + 2 = 65. The answer is right.

- `tally: reads 8, bytes read 256, seeks 0 (qty needs only 32 of them)` —
  and here is the problem, in numbers. To add up 32 bytes of quantities,
  the picker carried all 256 bytes: every id, every price, every name.
  Seven of every eight bytes were carried for nothing.

You might wonder: why not jump over the other compartments and read only
the four quantity bytes of each crate? That would be 8 seeks and 8 reads
of 4 bytes. It looks smaller, but storage does not work that way. A disk
or a cloud store hands out data in blocks — commonly 4,096 bytes at a
time on a disk — so the bytes you skip come along anyway, and every
extra seek is another trip. Our file is smaller than one block, so
today's tally counts what the layout asks for. At gigabyte scale, asking
is paying. The waste is not in the reader. It is in the
**layout**: the quantities are scattered across every crate. Section C
moves them next to each other.

Pin the tally with tests. Create `tests/test_counting.py`:

```python
from nanolance.counting import CountingFile


def test_a_fresh_file_has_an_empty_tally(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(bytes(range(10)))
    with CountingFile(path) as f:
        assert f.tally() == "reads 0, bytes read 0, seeks 0"


def test_reads_and_their_bytes_are_counted(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(bytes(range(10)))
    with CountingFile(path) as f:
        assert f.read(4) == bytes([0, 1, 2, 3])
        assert f.read(4) == bytes([4, 5, 6, 7])
        assert f.read(4) == bytes([8, 9])  # only two bytes were left
        assert (f.reads, f.bytes_read, f.seeks) == (3, 10, 0)


def test_seeks_are_counted_and_move_the_position(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(bytes(range(10)))
    with CountingFile(path) as f:
        f.seek(7)
        assert f.read(2) == bytes([7, 8])
        f.seek(0)
        assert f.read(1) == bytes([0])
        assert (f.reads, f.bytes_read, f.seeks) == (2, 3, 2)
```

The middle test reads past the end on purpose: the third `read(4)` gets
only two bytes, and `bytes_read` counts what came back — 10, not 12.

In `tests/test_row_layout.py`, add the import under the first line, and
the new test at the bottom (around line 25):

```python
from nanolance import row_layout
from nanolance.counting import CountingFile
from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH, pack_value
⋮
# ──────── new code starts here (around line 25) ────────
def test_summing_one_column_reads_every_byte(tmp_path):
    path = tmp_path / "rows.bin"
    row_layout.write(path, ORDERS)
    with CountingFile(path) as f:
        assert row_layout.sum_column(f, "qty", len(ORDERS)) == 65
        assert (f.reads, f.bytes_read, f.seeks) == (8, 256, 0)


# ──────── new code ends here ────────
```

And at the bottom of `tests/test_cli.py` (around line 22), one test that
checks the four lines from the read-back on, exactly:

```python
# ──────── new code starts here (around line 22) ────────
def test_layouts_tallies_what_each_question_reads(tmp_path):
    lines = run_layouts(tmp_path)
    start = lines.index("read rows.bin back: same as the table? True")
    assert lines[start : start + 4] == [
        "read rows.bin back: same as the table? True",
        "  tally: reads 8, bytes read 256, seeks 0",
        "sum(qty) from rows.bin = 65",
        "  tally: reads 8, bytes read 256, seeks 0 (qty needs only 32 of them)",
    ]


# ──────── new code ends here ────────
```

```bash
uv run pytest -q
```

```text
..............                                                           [100%]
14 passed in 0.12s
```

Fourteen tests: section A's nine, plus three for the tally, one for the
crate stock count, and one for the demo's new lines.

**Section checkpoint:** `./scripts/compare.sh v1-day-01b`

### Section C — the same table, stored column by column

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/functions.html#enumerate"><code>enumerate</code>: each element with its position</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#unpacking-argument-lists">unpacking with <code>*</code>: a list's elements as separate arguments</a>
</div>

The tally put a number on the problem: the quantities are spread over
every crate. So unpack the crates and sort the same orders into aisles —
all the ids together, then all the prices, then the quantities, then the
names. Create `src/nanolance/column_layout.py`, starting with the writer
and one helper:

```python
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
```

- Put `write` next to section A's `row_layout.write`. They are the same
  two loops, **swapped**. There, the outer loop walks rows and the inner
  loop walks columns, so one row's values land together. Here, the outer
  loop walks columns and the inner loop walks rows, so one column's
  values land together. `enumerate` hands out each column's position
  alongside its name.

- `column_start` answers "where does this aisle begin?" Every column
  before it takes `n_rows` values of its own width: the ids take
  8 × 8 = 64 bytes, so prices start at 64; prices take 64 more, so
  quantities start at 128; quantities take 8 × 4 = 32, so names start at
  160.

The readers go below it, in the same file:

```python
# ──────── new code starts here (around line 36) ────────
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


# ──────── new code ends here ────────
```

- `read_column` is the heart of the column layout: **one seek** to the
  aisle's start, **one read** of the whole aisle, then cut the bytes into
  `n_rows` values of the column's width.

- `read_all` reads all four columns, then `zip(*columns, strict=True)`
  turns four lists of eight values into eight tuples of four values — it
  takes the first value of every column, then the second, and so on. The
  `*` hands the four lists to `zip` as four separate arguments.

- `sum_column` reads one column and adds it up. Nothing else is touched.

Now the demo. Three edits in `src/nanolance/cli.py`:

1. Import the new module: replace the line
   `from nanolance import __version__, row_layout` (line 6) with

   ```python
   from nanolance import __version__, column_layout, row_layout
   ```

2. Replace the docstring of `layouts` (lines 12–15), which still talks
   about crates only:

   ```python
   def layouts(folder: Path) -> None:
       # ──────── replacement starts here (around line 12) ────────
       """Analogy: open the warehouse, pack the orders both ways, and ask each
       the same questions.

       Store the orders table as rows and as columns, query both, and print
       every step with its tally.
       """
       # ──────── replacement ends here ────────
   ```

3. At the end of `layouts`, after the stock-count block and before
   `def main` (around line 40), write the aisles, read them back, and run
   the same stock count:

   ```python
       # ──────── new code starts here (around line 40) ────────
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
       # ──────── new code ends here ────────
   ```

   `parts` builds the size breakdown, one `name bytes` piece per column,
   joined with `" + "`.

Run it:

```bash
uv run nanolance layouts
```

```text
the orders table: 8 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  (104, 7.0, 2, 'tape')
  (105, 23.5, 1, 'drill bits')
  (106, 3.25, 12, 'nails')
  (107, 9.75, 4, 'gloves')
  (108, 15.0, 2, 'padlock')
write rows.bin: 256 bytes = 8 rows × 32 bytes
read rows.bin back: same as the table? True
  tally: reads 8, bytes read 256, seeks 0
sum(qty) from rows.bin = 65
  tally: reads 8, bytes read 256, seeks 0 (qty needs only 32 of them)
──── everything above: sections A and B's output, unchanged ────
write columns.bin: 256 bytes = id 64 + price 64 + qty 32 + name 96
read columns.bin back: same as the table? True
  tally: reads 4, bytes read 256, seeks 4
sum(qty) from columns.bin = 65
  tally: reads 1, bytes read 32, seeks 1
```

Read the new lines one by one:

- `write columns.bin: 256 bytes = id 64 + price 64 + qty 32 + name 96` —
  `column_layout.write` laid out four aisles. Same 256 bytes as the
  crates, the same values — only the order on disk differs.

- `read columns.bin back: same as the table? True` — the aisles hold
  the whole table: `read_all` zipped them back into exactly `ORDERS`.

- `tally: reads 4, bytes read 256, seeks 4` — reading everything costs
  one seek and one armful per aisle: `read_column`, four times. Three of
  those four seeks ask for the spot the picker is already standing at —
  each aisle begins where the last read ended — and the tally counts
  them anyway, because it counts requests.

- `sum(qty) from columns.bin = 65` — the same stock count, the same
  answer.

- `tally: reads 1, bytes read 32, seeks 1` — and the payoff. One walk to
  the quantity aisle, one armful of exactly the 32 bytes the question
  needs. Compare it with the crates' tally for the same question, above
  the divider: 256 bytes in 8 reads. The question did not change; the layout
  did, and the bytes read went down eight-fold.

Look at the first 32 bytes of the new file, as you did for the crates:

```bash
uv run python -c "from pathlib import Path; print(Path('warehouse/columns.bin').read_bytes()[:32].hex(' '))"
```

```text
65 00 00 00 00 00 00 00 66 00 00 00 00 00 00 00 67 00 00 00 00 00 00 00 68 00 00 00 00 00 00 00
```

Four ids in a row: hex `65`, `66`, `67`, `68` — orders 101, 102, 103,
and 104, eight bytes each. The first 32 bytes of `rows.bin` held one
whole order; the first 32 bytes of `columns.bin` hold half of one aisle.

Pin the aisles with tests. Create `tests/test_column_layout.py`:

```python
from nanolance import column_layout
from nanolance.counting import CountingFile
from nanolance.orders import ORDERS, pack_value


def test_each_column_is_stored_in_one_piece(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, ORDERS)
    data = path.read_bytes()
    assert len(data) == 256
    ids = b"".join(pack_value("id", row[0]) for row in ORDERS)
    assert data[: len(ids)] == ids


def test_columns_start_where_the_earlier_columns_end():
    starts = [column_layout.column_start(c, 8) for c in ("id", "price", "qty", "name")]
    assert starts == [0, 64, 128, 160]


def test_columns_round_trip_exactly(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, ORDERS)
    with CountingFile(path) as f:
        assert column_layout.read_all(f, len(ORDERS)) == ORDERS
        assert (f.reads, f.bytes_read, f.seeks) == (4, 256, 4)


def test_summing_one_column_reads_only_that_column(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, ORDERS)
    with CountingFile(path) as f:
        assert column_layout.sum_column(f, "qty", len(ORDERS)) == 65
        assert (f.reads, f.bytes_read, f.seeks) == (1, 32, 1)
```

`test_columns_start_where_the_earlier_columns_end` checks the arithmetic
you did by hand above: 0, 64, 128, 160. The last two tests pin the
tallies exactly, so a change that makes a question read more fails a
test.

And at the bottom of `tests/test_cli.py` (around line 33):

```python
# ──────── new code starts here (around line 33) ────────
def test_layouts_stores_the_table_as_columns_too(tmp_path):
    lines = run_layouts(tmp_path)
    start = lines.index(
        "write columns.bin: 256 bytes = id 64 + price 64 + qty 32 + name 96"
    )
    assert lines[start : start + 5] == [
        "write columns.bin: 256 bytes = id 64 + price 64 + qty 32 + name 96",
        "read columns.bin back: same as the table? True",
        "  tally: reads 4, bytes read 256, seeks 4",
        "sum(qty) from columns.bin = 65",
        "  tally: reads 1, bytes read 32, seeks 1",
    ]


# ──────── new code ends here ────────
```

```bash
uv run pytest -q
```

```text
...................                                                      [100%]
19 passed in 0.13s
```

Nineteen tests: five more, four for the aisles and one for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-01c`

### Section D — fetching one whole row, both ways

Section D needs no new Python — only new arithmetic.

Columns won the stock count by a factor of eight. So is the column
layout better at everything? Ask the opposite question: a customer comes
for one whole order. Positions are plain arithmetic in both files, so
both layouts can seek straight to it. The question is how many seeks.

At the bottom of `src/nanolance/row_layout.py` (around line 48):

```python
# ──────── new code starts here (around line 48) ────────
def fetch_row(f: BinaryIO, index: int) -> Row:
    """Analogy: a customer collects one order — walk to its crate, lift it.

    Row `index` starts index × ROW_WIDTH bytes in: one seek, one read.
    """
    f.seek(index * ROW_WIDTH)
    return read_row(f)


# ──────── new code ends here ────────
```

One seek to `index × 32`, then section A's `read_row` lifts the crate.

At the bottom of `src/nanolance/column_layout.py` (around line 63):

```python
# ──────── new code starts here (around line 63) ────────
def fetch_row(f: BinaryIO, index: int, n_rows: int) -> Row:
    """Analogy: a customer collects one order — one stop in every aisle.

    Value `index` of each column sits `index` values into that column, so
    one row costs one seek and one small read per column.
    """
    values = []
    for column, codec in COLUMNS.items():
        f.seek(column_start(column, n_rows) + index * codec.size)
        values.append(unpack_value(column, f.read(codec.size)))
    return tuple(values)


# ──────── new code ends here ────────
```

One stop per aisle: value `index` of a column sits `index` values past
the aisle's start, so the picker seeks there and reads one value's width.

Then, in `src/nanolance/cli.py`, at the end of `layouts` — after the
column stock count and before `def main` (around line 55):

```python
    # ──────── new code starts here (around line 55) ────────
    index = 5
    with CountingFile(rows_path) as f:
        row = row_layout.fetch_row(f, index)
        print(f"fetch row {index} from {rows_path.name} = {row}")
        print(f"  tally: {f.tally()}")
    with CountingFile(columns_path) as f:
        row = column_layout.fetch_row(f, index, n_rows)
        print(f"fetch row {index} from {columns_path.name} = {row}")
        print(f"  tally: {f.tally()}")
    # ──────── new code ends here ────────
```

Run it:

```bash
uv run nanolance layouts
```

```text
the orders table: 8 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  (104, 7.0, 2, 'tape')
  (105, 23.5, 1, 'drill bits')
  (106, 3.25, 12, 'nails')
  (107, 9.75, 4, 'gloves')
  (108, 15.0, 2, 'padlock')
write rows.bin: 256 bytes = 8 rows × 32 bytes
read rows.bin back: same as the table? True
  tally: reads 8, bytes read 256, seeks 0
sum(qty) from rows.bin = 65
  tally: reads 8, bytes read 256, seeks 0 (qty needs only 32 of them)
write columns.bin: 256 bytes = id 64 + price 64 + qty 32 + name 96
read columns.bin back: same as the table? True
  tally: reads 4, bytes read 256, seeks 4
sum(qty) from columns.bin = 65
  tally: reads 1, bytes read 32, seeks 1
──── everything above: sections A, B, and C's output, unchanged ────
fetch row 5 from rows.bin = (106, 3.25, 12, 'nails')
  tally: reads 1, bytes read 32, seeks 1
fetch row 5 from columns.bin = (106, 3.25, 12, 'nails')
  tally: reads 4, bytes read 32, seeks 4
```

Read the new lines one by one:

- `fetch row 5 from rows.bin = (106, 3.25, 12, 'nails')` — row 5 counts
  from zero, so it is the sixth order: id 106. `row_layout.fetch_row`
  found it at byte 5 × 32 = 160.

- `tally: reads 1, bytes read 32, seeks 1` — one walk, one crate. A row
  question is what crates are made for.

- `fetch row 5 from columns.bin = (106, 3.25, 12, 'nails')` — the same
  order, rebuilt by `column_layout.fetch_row` from one spot in each aisle.

- `tally: reads 4, bytes read 32, seeks 4` — the same 32 bytes, but in
  four requests instead of one. Against cloud storage each request is a
  separate network round trip — Day 5 counts what that does to a take.

So neither layout wins everything. Here is the scoreboard, from your own
tallies:

| Question | rows.bin | columns.bin |
|----------|----------|-------------|
| stock count, `sum(qty)` | 256 bytes, 8 reads, 0 seeks | **32 bytes, 1 read, 1 seek** |
| customer pickup, row 5 | **32 bytes, 1 read, 1 seek** | 32 bytes, 4 reads, 4 seeks |

Columns win the scan; rows win the single-row fetch. Lance stores
columns, because so many questions about data scan a few columns at a
time — and then works hard to make the take cheap too, because training
jobs and search results fetch rows one at a time. That is the story of
Day 5.

Three more tests. At the bottom of `tests/test_row_layout.py`
(around line 33):

```python
# ──────── new code starts here (around line 33) ────────
def test_fetching_one_row_is_one_seek_and_one_read(tmp_path):
    path = tmp_path / "rows.bin"
    row_layout.write(path, ORDERS)
    for index, expected in enumerate(ORDERS):
        with CountingFile(path) as f:
            assert row_layout.fetch_row(f, index) == expected
            assert (f.reads, f.bytes_read, f.seeks) == (1, 32, 1)


# ──────── new code ends here ────────
```

At the bottom of `tests/test_column_layout.py` (around line 36):

```python
# ──────── new code starts here (around line 36) ────────
def test_fetching_one_row_visits_every_column(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, ORDERS)
    for index, expected in enumerate(ORDERS):
        with CountingFile(path) as f:
            assert column_layout.fetch_row(f, index, len(ORDERS)) == expected
            assert (f.reads, f.bytes_read, f.seeks) == (4, 32, 4)


# ──────── new code ends here ────────
```

Both loop over all eight rows, with a fresh `CountingFile` for each, so
the counts are pinned for every position, not only row 5.

And at the bottom of `tests/test_cli.py` (around line 47):

```python
# ──────── new code starts here (around line 47) ────────
def test_layouts_fetches_one_row_both_ways(tmp_path):
    lines = run_layouts(tmp_path)
    assert lines[-4:] == [
        "fetch row 5 from rows.bin = (106, 3.25, 12, 'nails')",
        "  tally: reads 1, bytes read 32, seeks 1",
        "fetch row 5 from columns.bin = (106, 3.25, 12, 'nails')",
        "  tally: reads 4, bytes read 32, seeks 4",
    ]


# ──────── new code ends here ────────
```

```bash
uv run pytest -q
```

```text
......................                                                   [100%]
22 passed in 0.16s
```

Twenty-two tests, all green — section 9 lists what they cover.

**Section checkpoint:** `./scripts/compare.sh v1-day-01d` — which is also
the finished day.

## 7. Run it

```bash
uv run nanolance layouts
```

## 8. Expected result

```text
the orders table: 8 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  (104, 7.0, 2, 'tape')
  (105, 23.5, 1, 'drill bits')
  (106, 3.25, 12, 'nails')
  (107, 9.75, 4, 'gloves')
  (108, 15.0, 2, 'padlock')
write rows.bin: 256 bytes = 8 rows × 32 bytes
read rows.bin back: same as the table? True
  tally: reads 8, bytes read 256, seeks 0
sum(qty) from rows.bin = 65
  tally: reads 8, bytes read 256, seeks 0 (qty needs only 32 of them)
write columns.bin: 256 bytes = id 64 + price 64 + qty 32 + name 96
read columns.bin back: same as the table? True
  tally: reads 4, bytes read 256, seeks 4
sum(qty) from columns.bin = 65
  tally: reads 1, bytes read 32, seeks 1
fetch row 5 from rows.bin = (106, 3.25, 12, 'nails')
  tally: reads 1, bytes read 32, seeks 1
fetch row 5 from columns.bin = (106, 3.25, 12, 'nails')
  tally: reads 4, bytes read 32, seeks 4
```

The whole day in the warehouse, one stretch at a time:

- The table lines — the eight orders, before anything is packed.
  (`ORDERS`, printed by `layouts`.)

- `write rows.bin` through the first stock count — the orders packed in
  crates by the packing rule, read back exactly, then counted crate by
  crate: every byte carried for a 32-byte answer.
  (`row_layout.write`, `read_all`, `sum_column`, through a
  `CountingFile`.)

- `write columns.bin` through the second stock count — the same orders
  sorted into aisles, read back exactly, then counted in one aisle: one
  walk, one armful, 32 bytes.
  (`column_layout.write`, `read_all`, `sum_column`.)

- The two `fetch row 5` stretches — a customer collects order 106: one
  crate, or one stop in each of four aisles.
  (The two `fetch_row` functions.)

Nothing here varies between runs: there is no randomness and no timing,
only counts, and the counts are the same on every machine.

## 9. Test it

Twenty-two tests now pin the day — Day 0's two, plus 20 new ones: the
packing rule and the crates (section A, 7 tests), the tally and the
crate stock count (section B, 5), the aisles and their stock count
(section C, 5), and the two pickups (section D, 3). Seventeen are unit
tests; the other five (`test_cli_says_hello` and the four in
`test_cli.py`) run the real command line.

```bash
uv run pytest -q
```

```text
......................                                                   [100%]
22 passed in 0.16s
```

Every layout round-trips exactly, and every tally is pinned to the exact
reads, bytes, and seeks shown above, so a change that makes a question
read more fails a test.

## 10. Break it deliberately

Make the picker lose track of where aisles begin. In `column_start` in
`src/nanolance/column_layout.py`, delete one line:

```diff
@@ src/nanolance/column_layout.py, around line 32 @@
     for name, codec in COLUMNS.items():
         if name == column:
             return start
-        start += n_rows * codec.size
     raise KeyError(column)
```

Now every column "starts" at byte 0. Nothing complains when the file is
written — the writer never calls `column_start`. Run the column tests:

```bash
uv run pytest -q --tb=line tests/test_column_layout.py
```

```text
E   assert [0, 0, 0, 0] == [0, 64, 128, 160]
E   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe8 in position 2: invalid continuation byte
E   AssertionError: assert 410 == 65
E   AssertionError: assert (101, 5e-322,...x00\x00\x00f') == (101, 4.25, 3, 'bolts')
```

(Only the `E` lines are shown — one per failing test. Pytest's summary
line reads `4 failed, 1 passed`.)

Read the wreckage:

- The one test that passes is `test_each_column_is_stored_in_one_piece`:
  the file on disk is still perfect. Only the reading went wrong.

- `assert [0, 0, 0, 0] == [0, 64, 128, 160]` — the arithmetic test
  catches it directly: every aisle claims to start at the very front of
  the warehouse.

- `UnicodeDecodeError` — reading everything back, the name column read
  the first 96 bytes of the file — all the ids and some prices — as eight
  12-byte names. The first seven turned into nonsense text without a
  complaint; the eighth landed on price bytes that are not valid UTF-8
  (`0xe8`), and the decoder refused. It is the only part that noticed.

- `assert 410 == 65` — the stock count read the first 32 bytes as eight
  4-byte quantities. Those bytes are the first four ids, 8 bytes each, so
  each id became two "quantities": 101 and 0, 102 and 0, 103 and 0, 104
  and 0. Their sum is 410 — a confident, wrong answer.

- `(101, 5e-322, …) == (101, 4.25, 3, 'bolts')` — fetching row 0, the
  price came from the id aisle:
  the bytes of 101, read as a float, mean a tiny number close to zero.

The lesson: **bytes carry no labels.** The file is 256 anonymous bytes;
only the reader's arithmetic — the packing rule, the row count, where
each aisle starts — says what they mean. Today all of that lives in the
code, and one wrong line turns the warehouse into nonsense without a
single error from the storage. On Day 2, the file starts carrying its own
map. (`uv run nanolance layouts` fails the same way: it crashes with the
`UnicodeDecodeError` right after `write columns.bin`.)

Put the line back and confirm `uv run pytest -q` is green again.

## 11. Checkpoint

Every checkpoint — each section and the day — is done only when the full
green bar passes:

```bash
./scripts/check.sh
```

```text
20 files already formatted
All checks passed!
......................                                                   [100%]
22 passed in 0.15s
nanolance 0.1.0: scaffold is alive
⋮ (the §8 output, unchanged) ⋮
 INFO Book building has started
 INFO Running the html backend
 INFO HTML book written to `/…/build-nano-lance-in-python/book/book`
GREEN: all gates passed
```

(Paths shortened, as everywhere in this book.)

Read it line by line:

- `20 files already formatted` and `All checks passed!` — Ruff's
  formatting and lint gates, now over today's new files and this
  chapter's Python blocks too.

- the dots and `22 passed` — the whole suite, as in section 9.

- `nanolance 0.1.0: scaffold is alive` — the Day 0 smoke command, still
  there: with no subcommand, `main` prints the hello line.

- `⋮ (the §8 output, unchanged) ⋮` — the new smoke command,
  `nanolance layouts`, writing into a throwaway folder. It prints the
  same 23 lines as your run in section 8, shortened here.

- the three `INFO` lines and `GREEN: all gates passed` — the book built,
  and every gate passed.

The smoke gate now runs `nanolance layouts` as well, into a throwaway
folder. `scripts/check.sh` and `.gitignore` are course infrastructure,
outside what `compare.sh` checks; to pick up today's versions, copy them
from the checkpoint:

```bash
git checkout v1-day-01 -- scripts/check.sh .gitignore
```

Then close out the day in whichever mode you are following:

**Built along on your own branch?** Confirm your code matches the finished
day — the final ✓ line means it does:

```bash
./scripts/compare.sh v1-day-01
```

**Inspecting instead of typing?** Jump to today's exact finished state,
poke at it, and come back:

```bash
git switch --detach v1-day-01
uv run nanolance layouts
git switch -          # back to where you were
```

**Either way**, today's complete change set — docs included — reads as one
diff:

```bash
git diff v1-day-00 v1-day-01
```

## 12. Recap

**What changed today:** the project gained an orders table with a packing
rule (`COLUMNS`: four fixed-width `struct` formats, 32 bytes per row),
two layouts of the same table — `row_layout` (crates) and
`column_layout` (aisles) — each with a writer, a reader that round-trips
exactly, a one-column `sum_column`, and a one-row `fetch_row`; a
`CountingFile` that tallies reads, bytes read, and seeks, which every
later day reuses; and a `nanolance layouts` demo that prints each step
with its tally. Twenty new tests (22 in all) pin it across four section
checkpoints (`v1-day-01a` to `v1-day-01d`), with no dependencies.

**Deliberately naive:** every value has a fixed width, so names are
capped at 12 bytes and short ones waste their padding; each column is
read in one piece, which is fine for 32 bytes and hopeless for 32
gigabytes; the tally counts seeks but does not model what they cost; and
the file is 256 bytes with no description of itself at all — the reader
must already know the packing rule, the row count, and where each aisle
starts.

**Tomorrow's limitation, resolved on Day 2:** that last point is the one
you broke in section 10. On Day 2 the aisles are cut into **sealed
boxes** — Lance calls them *pages* — and the warehouse gets **the index
card at the back**: a small record at the very end of the file that says
where every box lives. A
reader opens the card first, then walks straight to the boxes it needs,
and never has to be told the layout. The scene grows from two ways of
shelving into a warehouse that describes itself — see
[the warehouse](story.md).
