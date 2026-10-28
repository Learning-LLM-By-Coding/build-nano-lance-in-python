# Day 2: A file of pages

> **Day 2** (of Days 0–17) · builds on `v1-day-01` · ≈ 2 h

| Section | Builds | Checkpoint |
|---------|--------|------------|
| A | A thousand orders, and what Day 1's file cannot say | `v1-day-02a` |
| B | Each column cut into pages | `v1-day-02b` |
| C | The metadata and the footer, read from the end | `v1-day-02c` |
| D | Refusing a file that is not ours | `v1-day-02d` = `v1-day-02` |

**Pick your mode before starting** (explained fully in
[Setup](setup.md#4-choose-how-you-follow-along)):

```bash
# Build mode — type today's code yourself, on your own branch:
git switch -c my-course v1-day-01      # or keep going on yesterday's branch

# Inspect mode — read along with the finished code instead:
git switch --detach v1-day-02a         # then 02b, 02c, 02d as you pass each section
```

<div class="callout">

**Today's typing budget** — so nothing sneaks up on you:

| Section | The learning | Wiring & tests (copy-friendly) |
|---------|--------------|--------------------------------|
| A | `many_orders` · ~8 lines | the `pages` demo (~30 lines, all Day 1 calls), an import, 2 edits in `main`, 3 tests |
| B | `Page`, the page file's `write`, `read_page`, `read_column`, `read_rows` · ~90 lines, docstrings included | 2 demo edits, 4 tests |
| C | `FOOTER`, `Metadata`, the metadata and footer in `write`, `read_metadata` · ~65 lines; `CountingFile.size` · 2 lines | demo lines, 5 tests |
| D | four checks in `read_metadata` · ~20 lines | demo lines, 6 tests |

Four sections are four natural sittings, and every checkpoint is a save
point — nothing says a "day" must fit in one. Today still needs **no
dependencies**: `json` and `dataclasses` come with Python.

</div>

> **Short on time?** Sections A–B are the core; C–D can be a second
> sitting.

## 1. What you will have running

By the end of today, `uv run nanolance pages` stores a bigger table, a
thousand orders, in a new kind of file: one that **describes itself**.
Yesterday's files were anonymous bytes. To read one, the reader had to
know from outside how many rows it held and how wide each value was. And
a question about a few rows still read a whole column. Today's file fixes
both problems:

- **Each column is cut into pages**, runs of 100 values each. A question
  about ten rows reads the one page that holds them, not the whole
  column.

- **A small description of every page is stored after the data**, and a
  fixed-size **footer** at the very end of the file says where that
  description is. A reader that knows nothing about the file starts at
  the end, reads the footer, reads the description, and then reads only
  the pages its question needs.

- **The footer ends with a name.** Its last four bytes spell the format's
  name, and a format version number sits next to them. So the reader
  refuses a file that is not ours, by name, after one small read.

Every claim is a count again: reads, bytes read, and seeks, from
yesterday's counting file.

<div class="dl-concepts"><span>Lance concepts used here:</span>
<a href="https://lance.org/format/file/">the Lance file format: data pages, column metadata, a fixed-size footer ↗</a>
<a href="https://parquet.apache.org/docs/file-format/">the Parquet file layout: metadata at the end, "for single pass writing" ↗</a>
<a href="https://en.wikipedia.org/wiki/Magic_number_(programming)">magic numbers: a file naming its own format (Wikipedia) ↗</a>
</div>

## 2. What you will be seeing in the output

Here is a sneak peek at the end of the day, with a plain-English note
under each group of lines. If a note doesn't land yet, that's fine. The
rest of the day builds every piece:

```text
the orders table: 1000 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  … and 997 more, repeating the same eight orders
write columns.bin: 32000 bytes = id 8000 + price 8000 + qty 4000 + name 12000
sum(qty) from columns.bin, told 1000 rows = 8125
  tally: reads 1, bytes read 4000, seeks 1
sum(qty) from columns.bin, told 8 rows = 474
  tally: reads 1, bytes read 32, seeks 1
qty of rows 10–19 from columns.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 1, bytes read 4000, seeks 1 (rows 10–19 need only 40 of them)
write pages.bin: 33762 bytes, each column cut into pages
  id: 10 pages of 800 bytes, at 0, 800, …, 7200
  price: 10 pages of 800 bytes, at 8000, 8800, …, 15200
  qty: 10 pages of 400 bytes, at 16000, 16400, …, 19600
  name: 10 pages of 1200 bytes, at 20000, 21200, …, 30800
sum(qty) from pages.bin = 8125
  tally: reads 10, bytes read 4000, seeks 10
qty of rows 10–19 from pages.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 1, bytes read 400, seeks 1
open pages.bin: version 1, 1000 rows, columns id, price, qty, name, 40 pages
  tally: reads 2, bytes read 1762, seeks 2
sum(qty) from pages.bin, told nothing = 8125
  tally: reads 12, bytes read 5762, seeks 12
qty of rows 10–19 from pages.bin, told nothing = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 3, bytes read 2162, seeks 3
open columns.bin as a page file: refused, not a nanolance file: it ends with b'\x00\x00\x00\x00', not b'NLNC'
  tally: reads 1, bytes read 24, seeks 1
```

- The first five lines — the table: a thousand orders. They are
  yesterday's eight orders, repeated, each with a fresh id, so every value
  is predictable.

- `write columns.bin` down to the first `qty of rows 10–19` — yesterday's
  file, holding the bigger table. When you ask it for the total quantity,
  it gives the right answer only if the reader knows the right row count.
  Tell the reader "8 rows" instead, and it gives 474: a wrong answer, and
  no error. And ten quantities cost all 4000 bytes of the quantity column.

- `write pages.bin` and the four lines under it — the new file. Each
  column is cut into 10 pages of 100 values, and each line says where
  that column's pages start in the file.

- The next four lines — the same two questions, answered from the pages.
  The code that wrote the file hands over the page list. Ten rows now
  cost one read of 400 bytes.

- `open pages.bin` and its count — a reader that knows nothing starts at
  the end of the file. It reads two small pieces: the footer, then the
  description the footer points to. Those 1762 bytes tell it the format
  version, the row count, the columns, and where all 40 pages are.

- The two `told nothing` questions — the same answers, with no outside
  help. Each costs the 1762 bytes of the opening, plus the pages it needs.

- The last two lines — yesterday's file, opened as a new one. The reader
  refuses it by name after reading only its last 24 bytes.

## 3. Why we need it

Yesterday ended with a broken line of arithmetic and a lesson: **bytes
carry no labels.** The column file was 256 anonymous bytes, and only the
reader's code knew what they meant. Two problems hide in that lesson,
and both grow with the table:

- **The reader must be told.** Yesterday's column reader takes the row
  count as an argument, and the column widths live in the code, not in
  the file. Hand the file to a reader with the wrong count, or to another
  program, and nothing in the file warns it.

- **A column is one piece.** The column reader has one move: read the
  whole column. A question about ten rows of a million-row column
  reads a million values.

You might object to the second problem. Every value has a fixed width, so
value 10 of a column sits at a spot you can compute. Today, yes. But that
works only while the reader knows the widths and the row count, and only
while every value has the same width. On Day 3 the values get squeezed
into fewer bytes, with a different number of bytes per stretch of the
column, and that arithmetic stops working. So real formats do not compute
where data is. They **cut each column into pages and write down where
every page is**, inside the file.

That raises a question of its own: where in the file does the list go?
A writer only knows where a page landed after writing it, so the list
can only be complete at the very end. Parquet and Lance both put it
there, after the data. That means a reader has to find the end first.

**The story so far — remember [the warehouse](story.md):** orders
shelved two ways, in [crates](story.md#row-layout) or in
[aisles](story.md#column-layout), a picker who fetches things and keeps
[a tally](story.md#tally) of every trip, the manager's
[stock count](story.md#stock-count) and a customer's
[pickup](story.md#pickup). Today's scene is **the wall card at the
back.** The week gets busy: a thousand orders arrive, and each aisle
grows long. So the warehouse cuts every aisle into **sealed boxes** of
100 values. These are not Day 1's [crates](story.md#row-layout), which
held one whole order. A box holds 100 values of a single aisle. For each
aisle the warehouse keeps a **box list**: where each box sits, how much
it weighs, and how many values it holds. The box lists are stored in the
warehouse after the last box. On the back wall hangs **the wall card**.
It is always the same size and always the last thing in the building, so
a picker who knows nothing walks straight to it. The card says where the
box lists are. It also carries **the stamp**, the warehouse's name and
its edition, so a picker sent to the wrong building turns around after
reading it. Section A shows what the aisles cannot tell on their own.
Section B cuts them into boxes, section C writes the box lists and the
card, and section D checks the stamp.

## 4. Mental model

Walk the warehouse, one station per section:

- **A busy week (section A).** A thousand orders sit in
  [aisles](story.md#column-layout). The quantity aisle alone is 4000
  bytes, and a picker told the wrong row count reads the wrong spot.

- **[Sealed boxes](story.md#pages) (section B).** Up to 100 values per
  box, back to back along the aisle. Orders 10 to 19 are one box, not the
  whole aisle.

- **[The box list](story.md#box-list) (sections B and C).** One line per
  box: its *offset* (the byte where it starts), its *size* in bytes, and
  its row count. In section B the writer hands it over in memory. In
  section C it is stored after the last box.

- **[The wall card at the back](story.md#wall-card) (section C).**
  Exactly 24 bytes and always last, so it starts at the file's size
  minus 24. It says where the box lists start and how long they are.

- **[The stamp](story.md#stamp) (section D).** The card's last bytes,
  `NLNC`, and its format version, `1`. The picker checks them before
  believing anything else on the card.

Here is the new file, laid out from its first byte to its last. The
numbers under it are byte positions:

```text
pages.bin
│ id: 10 boxes │ price: 10 boxes │ qty: 10 boxes │ name: 10 boxes │ box lists │ card │
0              8000              16000           20000            32000       33738  33762
```

And here is how a picker who knows nothing answers "the quantities of
rows 10 to 19", step by step down the page:

```text
the file's size        33762 bytes — the file system says so, no read needed
    │ seek to 33762 − 24, read 24 bytes
    ▼
the wall card          box lists at byte 32000, 1738 bytes long; version 1; stamp NLNC
    │ seek to 32000, read 1738 bytes
    ▼
the box lists          4 aisles, each with its value format and 10 boxes
    │ find the qty box that holds rows 10 to 19: box 0, rows 0 to 99
    ▼
one box                seek to 16000, read 400 bytes: 100 quantities
    │ keep values 10 to 19
    ▼
the answer             10 quantities, for 3 reads in all
```

## 5. Lance concepts introduced

- **Pages.** A page is a run of one column's values, sized to be one
  good read. Lance recommends pages of about 8 MB. Ours hold 100 values
  (400 to 1200 bytes) so the counts stay readable. A question reads only
  the pages that overlap it. Parquet calls its pages *pages* too, and
  keeps them inside larger *column chunks*.

- **Column metadata.** Each column gets a description of its pages:
  where each starts, how big it is, and how many rows it holds. It also
  says how to decode the values. Lance writes this as
  [Protocol Buffers](https://protobuf.dev/), a compact binary encoding.
  Ours is [JSON](https://docs.python.org/3.12/library/json.html) text,
  so you can read it with your own eyes.

- **A footer read first, from the end.** The metadata is written after
  the data, because a writer only knows where pages landed once they are
  written. Parquet's documentation says it is "written after the data to
  allow for single pass writing". So the reader starts at the end. The
  footer has a fixed size, and that is what makes the end a findable
  place.
  Lance's footer is 40 bytes (three 8-byte offsets, two 4-byte counts,
  two 2-byte version numbers, and `LANC`: 40 bytes —
  [the public spec](https://lance.org/format/file/)); ours is 24.

- **Magic numbers and format versions.** A magic number is a few fixed
  bytes that name a format. Lance's files end with `LANC`, Parquet's start
  *and* end with `PAR1`, and ours end with `NLNC`. Putting the name at the
  end has a bonus. A file whose writing was interrupted has no ending, so
  the reader refuses it instead of misreading it. The format version lets
  a reader refuse a file written by a newer (or older) format than it
  understands.

- **Where real Lance does more.** Its footer also points to a small
  table of where *each column's* metadata sits, so a reader can fetch
  only the columns it wants. Ours reads all four box lists every time.
  And instead of two exact reads for the footer and metadata, a Lance
  reader asks for one whole block from the end of the file (4 KiB on a
  local disk, more on cloud storage). So opening a file costs one or two
  requests: one when the metadata is small enough to arrive with the
  footer.

## 6. Build it, section by section

### Section A — a busy week: what Day 1's file cannot say

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/reference/expressions.html#expression-lists"><code>*</code> inside a tuple: spreads a sequence's elements into it</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#numeric-types-int-float-complex"><code>%</code>: the remainder after division</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#if-statements"><code>elif</code>: "otherwise, if"</a>
</div>

Eight orders were enough to see rows and columns. Pages need a longer
column, so first you grow the table. At the bottom of
`src/nanolance/orders.py` (around line 59):

```python
# ──────── new code starts here (around line 59) ────────
def many_orders(n_rows: int) -> list[Row]:
    """Analogy: a busy week — the same eight orders, placed again and again.

    `n_rows` orders with ids 101, 102, 103, ...; order k repeats the price,
    quantity, and name of ORDERS[k % 8], so every value is predictable.
    """
    return [(101 + k, *ORDERS[k % len(ORDERS)][1:]) for k in range(n_rows)]


# ──────── new code ends here ────────
```

- Order `k` copies the price, quantity, and name of `ORDERS[k % 8]`, and
  gets the id `101 + k`. `k % 8` is the remainder of `k` divided by 8, so
  it cycles through the eight orders.

- `ORDERS[...][1:]` is that order without its id, and the `*` spreads
  those three values into the new tuple, after the new id.

- The first eight are exactly `ORDERS`, so you can check every number
  today by hand. The quantities of eight orders add up to 65, so a
  thousand orders hold 125 × 65 = 8125.

Now a demo that puts yesterday's column file to work on the bigger
table. In `src/nanolance/cli.py`, three edits:

1. Import the new function: replace the line
   `from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH` (line 8) with

   ```python
   from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH, many_orders
   ```

2. Add the demo between the end of `layouts` and `def main` (around line
   64). Every call in it is one you wrote yesterday:

   ```python
   # ──────── new code starts here (around line 64) ────────
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


   # ──────── new code ends here ────────
   ```

3. In `main`, register the new subcommand and run it. There are two
   insertions, and the framing lines are already in your file:

   ```python
       demo = demos.add_parser("layouts", help="store one table as rows and as columns")
       demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
       # ──────── new code starts here (around line 106) ────────
       demo = demos.add_parser("pages", help="store one table as pages with a footer")
       demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
       # ──────── new code ends here ────────
       args = parser.parse_args()

       if args.demo == "layouts":
           layouts(args.folder)
       # ──────── new code starts here (around line 112) ────────
       elif args.demo == "pages":
           pages(args.folder)
       # ──────── new code ends here ────────
       else:
   ```

What the demo does, in order:

- It prints the first three orders and a count of the rest. A thousand
  lines would bury everything else.

- It writes the orders with yesterday's `column_layout.write`, then asks
  for `sum(qty)` twice. The first time it tells the reader the true row
  count. The second time it says 8, the count that was right yesterday.

- Last, it asks for the quantities of rows 10 to 19. The column reader
  can only read a whole column, so the demo reads it all and keeps
  `[10:20]`: the slice from position 10 up to, but not including, 20.

Run it:

```bash
uv run nanolance pages
```

```text
the orders table: 1000 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  … and 997 more, repeating the same eight orders
write columns.bin: 32000 bytes = id 8000 + price 8000 + qty 4000 + name 12000
sum(qty) from columns.bin, told 1000 rows = 8125
  tally: reads 1, bytes read 4000, seeks 1
sum(qty) from columns.bin, told 8 rows = 474
  tally: reads 1, bytes read 32, seeks 1
qty of rows 10–19 from columns.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 1, bytes read 4000, seeks 1 (rows 10–19 need only 40 of them)
```

Read it line by line:

- The first five lines — the table, from `many_orders(1000)`. Three
  orders are printed, and the other 997 are only counted.

- `write columns.bin: 32000 bytes = …` — `column_layout.write`, unchanged
  since yesterday, laid out four [aisles](story.md#column-layout) of a
  thousand values each.

- `sum(qty) from columns.bin, told 1000 rows = 8125` and its tally — the
  [stock count](story.md#stock-count) is right, and it cost one read of
  the 4000 bytes of the quantity aisle.

- `sum(qty) from columns.bin, told 8 rows = 474` and its tally — the same
  file and the same function, told the wrong row count. `column_start`
  computed where quantities would begin in an 8-row file, byte 128, and
  `read_column` read 32 bytes there. In this file, those bytes are
  the ids of orders 117 to 120. Each 8-byte id was read as two 4-byte
  quantities: 117 and 0, 118 and 0, 119 and 0, 120 and 0. Their sum,
  474, came back with no error at all.

- `qty of rows 10–19 … = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]` and its tally
  — the right ten values. But [the tally](story.md#tally) shows the cost:
  4000 bytes carried for 40 bytes of answer.

You have now counted both problems. Nothing in `columns.bin` records its
own row count, and nothing lets a reader carry less than a whole aisle.
The rest of the day fixes both.

Pin the problem with tests. There are five edits in three files:

1. In `tests/test_orders.py`, the `from nanolance.orders import` line
   (line 3) grows by one name, `many_orders`. Once the line is too long,
   Ruff's formatter splits it over several lines:

   ```python
   from nanolance.orders import (
       COLUMNS,
       ORDERS,
       ROW_WIDTH,
       many_orders,
       pack_value,
       unpack_value,
   )
   ```

2. In `tests/test_orders.py`, at the bottom (around line 36), add a test
   of the bigger table:

   ```python
   # ──────── new code starts here (around line 36) ────────
   def test_many_orders_repeats_the_eight_orders_with_fresh_ids():
       orders = many_orders(20)
       assert orders[:8] == ORDERS
       assert orders[8] == (109, 4.25, 3, "bolts")
       assert [row[0] for row in orders] == list(range(101, 121))


   # ──────── new code ends here ────────
   ```

3. In `tests/test_column_layout.py`, line 3: add `many_orders` to the
   import, so it reads
   `from nanolance.orders import ORDERS, many_orders, pack_value`.

4. In `tests/test_column_layout.py`, at the bottom (around line 45), add
   a test that pins the silent wrong answer:

   ```python
   # ──────── new code starts here (around line 45) ────────
   def test_a_wrong_row_count_reads_the_wrong_bytes_without_error(tmp_path):
       path = tmp_path / "columns.bin"
       column_layout.write(path, many_orders(1000))
       with CountingFile(path) as f:
           assert column_layout.sum_column(f, "qty", 1000) == 8125
       with CountingFile(path) as f:
           assert column_layout.sum_column(f, "qty", 8) == 474  # four ids, not qty


   # ──────── new code ends here ────────
   ```

5. In `tests/test_cli.py`, at the bottom (around line 57), add a helper
   that runs the new demo, like yesterday's `run_layouts`, and a test of
   its lines:

   ```python
   # ──────── new code starts here (around line 57) ────────
   def run_pages(folder):
       result = subprocess.run(
           [sys.executable, "-m", "nanolance", "pages", str(folder)],
           capture_output=True,
           text=True,
           check=True,
       )
       return result.stdout.splitlines()


   def test_pages_shows_what_the_column_file_must_be_told(tmp_path):
       lines = run_pages(tmp_path)
       assert lines[0] == "the orders table: 1000 rows × 4 columns (id, price, qty, name)"
       start = lines.index("sum(qty) from columns.bin, told 1000 rows = 8125")
       assert lines[start : start + 6] == [
           "sum(qty) from columns.bin, told 1000 rows = 8125",
           "  tally: reads 1, bytes read 4000, seeks 1",
           "sum(qty) from columns.bin, told 8 rows = 474",
           "  tally: reads 1, bytes read 32, seeks 1",
           "qty of rows 10–19 from columns.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
           "  tally: reads 1, bytes read 4000, seeks 1 (rows 10–19 need only 40 of them)",
       ]


   # ──────── new code ends here ────────
   ```

```bash
uv run pytest -q
```

```text
.........................                                                [100%]
25 passed in 0.20s
```

That makes twenty-five tests: Day 1's 22, plus one for the bigger table,
one for the wrong row count, and one for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-02a`

### Section B — sealed boxes: each column cut into pages

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/dataclasses.html#dataclasses.dataclass"><code>@dataclass</code>: a class that only holds named fields, written for you</a>
<a href="https://docs.python.org/3.12/library/dataclasses.html#frozen-instances"><code>frozen=True</code>: fields cannot change after creation</a>
<a href="https://docs.python.org/3.12/glossary.html#term-decorator">decorators: the <code>@name</code> line above a class or function</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#default-argument-values">default argument values: <code>rows_per_page: int = ROWS_PER_PAGE</code></a>
<a href="https://docs.python.org/3.12/glossary.html#term-variable-annotation">variable annotations: <code>pages: dict[str, list[Page]] = {}</code></a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#typesseq-range"><code>range(start, stop, step)</code>: counts in steps</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#bytes.join"><code>b"".join</code>: glues byte strings together</a>
<a href="https://docs.python.org/3.12/library/io.html#io.IOBase.tell"><code>tell</code>: the file's current position</a>
<a href="https://docs.python.org/3.12/library/struct.html#struct.Struct.iter_unpack"><code>Struct.iter_unpack</code>: unpacks value after value</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#more-on-lists"><code>list.extend</code>: appends every element of another list</a>
<a href="https://docs.python.org/3.12/library/functions.html#max"><code>max</code>: the larger of its arguments</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#nested-list-comprehensions">nested comprehensions: two <code>for</code>s in one list</a>
<a href="https://docs.python.org/3.12/tutorial/introduction.html#text">negative indexes: <code>boxes[-1]</code> is the last element, <code>[-24:]</code> the last 24</a>
</div>

Start with the second problem: a column is one piece. Your fix is to cut
every aisle into boxes. Create `src/nanolance/page_file.py`, beginning
with the page's description and the writer:

```python
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
```

- `Page` holds the three facts about one box: `offset` (the byte where it
  starts), `size` (its length in bytes), and `rows` (how many values it
  holds). `@dataclass` writes the class's `__init__` for you. It also
  writes an `==` that compares field by field, which the tests use.
  `frozen=True` forbids changing a `Page` later, because a box does not
  move once it is shelved.

- `write` has the same outer loop as yesterday's `column_layout.write`:
  one column after another. But the inner loop now steps through the rows
  `rows_per_page` at a time, so `range(0, 1000, 100)` gives 0, 100, 200,
  …, 900. Each step packs one page's values, `chunk`, into `data`.

- Before writing a page, `out.tell()` asks the file where its bookmark
  is, which is where the page is about to land. The writer records that
  offset, with the page's size and row count, *before* writing the bytes.

- `write` returns `pages`: for each column name, its list of `Page`s, in
  file order. That return value is the box list. Today it lives in the
  program's memory, and the writer hands it to whoever called it.

Then the readers, below `write` in the same file:

```python
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
```

- `read_page` is the picker carrying one box: one seek to
  `page.offset`, one read of `page.size` bytes. `codec.iter_unpack` cuts
  those bytes into values of the codec's width, one tuple per value.
  `for (value,) in …` unpacks each one-element tuple straight into
  `value`, as Day 1's `(value,) = …` did. Text loses its padding and is
  decoded, as in yesterday's `unpack_value`.

- `read_page` takes the codec as an argument instead of looking it up in
  `COLUMNS` by name. Today the caller passes `COLUMNS["qty"]`. In section
  C, the codec will come from the file itself.

- `read_column` carries every box of one aisle, in order, and joins their
  values into one list. The two `for`s read left to right: for each page,
  for each value in that page.

- `read_rows` is the new move. It walks the box list, keeping `first`,
  the row number of the current page's first value. A page holds rows
  `first` up to `first + page.rows`. If that range overlaps the range you
  asked for, `read_rows` reads the page and keeps the overlapping slice.
  It skips every other page: no seek, no read.

- The slice `page_values[max(start - first, 0) : stop - first]` turns
  file-wide row numbers into positions inside the page. For rows 10 to
  19 and the first page (`first` = 0), that is `[10:20]`. For a range
  that starts in an earlier page, `start - first` is negative, and
  `max(…, 0)` starts the slice at the page's beginning instead.

Now the demo. Two edits in `src/nanolance/cli.py`:

1. Import the new module: replace the line
   `from nanolance import __version__, column_layout, row_layout` (line 6)
   with

   ```python
   from nanolance import __version__, column_layout, page_file, row_layout
   ```

2. At the end of `pages`, after the rows 10–19 block and before
   `def main` (around line 98), write the same orders as pages and ask
   the same two questions:

   ```python
       # ──────── new code starts here (around line 98) ────────
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
       # ──────── new code ends here ────────
   ```

   The loop prints one line per column: how many pages, how big each
   one is, and where the first two and the last begin. `box_lists["qty"]`
   is the quantity column's list of pages. The demo hands it to the
   readers along with the codec.

Run it:

```bash
uv run nanolance pages
```

```text
the orders table: 1000 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  … and 997 more, repeating the same eight orders
write columns.bin: 32000 bytes = id 8000 + price 8000 + qty 4000 + name 12000
sum(qty) from columns.bin, told 1000 rows = 8125
  tally: reads 1, bytes read 4000, seeks 1
sum(qty) from columns.bin, told 8 rows = 474
  tally: reads 1, bytes read 32, seeks 1
qty of rows 10–19 from columns.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 1, bytes read 4000, seeks 1 (rows 10–19 need only 40 of them)
──── everything above: section A's output, unchanged ────
write pages.bin: 32000 bytes, each column cut into pages
  id: 10 pages of 800 bytes, at 0, 800, …, 7200
  price: 10 pages of 800 bytes, at 8000, 8800, …, 15200
  qty: 10 pages of 400 bytes, at 16000, 16400, …, 19600
  name: 10 pages of 1200 bytes, at 20000, 21200, …, 30800
sum(qty) from pages.bin = 8125
  tally: reads 10, bytes read 4000, seeks 10
qty of rows 10–19 from pages.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 1, bytes read 400, seeks 1
```

Read it line by line:

- `write pages.bin: 32000 bytes, each column cut into pages` — the same
  32000 bytes as `columns.bin`. Cutting an aisle into
  [boxes](story.md#pages) adds no bytes, because a page boundary is a line
  on a list, not something stored between the values.

- `id: 10 pages of 800 bytes, at 0, 800, …, 7200` and the three lines
  under it — the box list, from `write`'s return value. Each column is cut
  into ten pages of 100 values. The pages of one column sit back to back,
  and each column starts where the one before it ends.

- `sum(qty) from pages.bin = 8125` and `reads 10, bytes read 4000,
  seeks 10` — `read_column` carried all ten quantity boxes. That is the
  same 4000 bytes as yesterday's single read, now in ten reads.

- `qty of rows 10–19 from pages.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]`
  and `reads 1, bytes read 400, seeks 1` — the payoff. `read_rows` found
  that rows 10 to 19 live in the first quantity page. It carried that one
  box and skipped the other nine: 400 bytes instead of 4000.

You can confirm the "no bytes added" claim yourself. `cmp` compares two
files and prints nothing when they match:

```bash
cmp warehouse/columns.bin warehouse/pages.bin && echo identical
```

```text
identical
```

Byte for byte, `pages.bin` is yesterday's column file. Everything new is
in the box list, and the box list is not in the file. It exists only in
the memory of the program that wrote the file. Close the program, and a
reader is back to being told things from outside. Section C writes the
list down.

Pin the pages with tests. Create `tests/test_page_file.py`:

```python
from nanolance import page_file
from nanolance.counting import CountingFile
from nanolance.orders import COLUMNS, ORDERS, many_orders
from nanolance.page_file import Page


def test_each_column_is_cut_into_pages(tmp_path):
    pages = page_file.write(tmp_path / "pages.bin", ORDERS, rows_per_page=3)
    assert pages["id"] == [
        Page(offset=0, size=24, rows=3),
        Page(offset=24, size=24, rows=3),
        Page(offset=48, size=16, rows=2),
    ]
    assert pages["price"][0].offset == 64  # right after the id column


def test_every_column_round_trips_through_its_pages(tmp_path):
    path = tmp_path / "pages.bin"
    orders = many_orders(1000)
    pages = page_file.write(path, orders)
    with CountingFile(path) as f:
        for position, (column, codec) in enumerate(COLUMNS.items()):
            values = page_file.read_column(f, codec, pages[column])
            assert values == [row[position] for row in orders]


def test_reading_some_rows_reads_only_the_pages_that_hold_them(tmp_path):
    path = tmp_path / "pages.bin"
    orders = many_orders(1000)
    pages = page_file.write(path, orders)
    codec, qty_pages = COLUMNS["qty"], pages["qty"]
    qty = [row[2] for row in orders]
    with CountingFile(path) as f:
        assert page_file.read_rows(f, codec, qty_pages, 10, 20) == qty[10:20]
        assert (f.reads, f.bytes_read, f.seeks) == (1, 400, 1)
    with CountingFile(path) as f:  # rows 95-104 straddle pages 0 and 1
        assert page_file.read_rows(f, codec, qty_pages, 95, 105) == qty[95:105]
        assert (f.reads, f.bytes_read, f.seeks) == (2, 800, 2)
```

- `test_each_column_is_cut_into_pages` writes the eight `ORDERS` in pages
  of 3 rows, so the last page is short: 3 + 3 + 2. Its exact `Page`
  values check that the pages sit back to back, and that the writer
  records a page's row count instead of assuming it.

- `test_every_column_round_trips_through_its_pages` reads all four
  columns of the thousand orders back, page by page.

- `test_reading_some_rows_reads_only_the_pages_that_hold_them` pins two
  tallies: rows 10 to 19 read one page, and rows 95 to 104, which
  straddle the first two pages, read exactly those two.

At the bottom of `tests/test_cli.py` (around line 81):

```python
# ──────── new code starts here (around line 81) ────────
def test_pages_reads_only_the_pages_it_needs(tmp_path):
    lines = run_pages(tmp_path)
    start = lines.index("  id: 10 pages of 800 bytes, at 0, 800, …, 7200")
    assert lines[start : start + 8] == [
        "  id: 10 pages of 800 bytes, at 0, 800, …, 7200",
        "  price: 10 pages of 800 bytes, at 8000, 8800, …, 15200",
        "  qty: 10 pages of 400 bytes, at 16000, 16400, …, 19600",
        "  name: 10 pages of 1200 bytes, at 20000, 21200, …, 30800",
        "sum(qty) from pages.bin = 8125",
        "  tally: reads 10, bytes read 4000, seeks 10",
        "qty of rows 10–19 from pages.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
        "  tally: reads 1, bytes read 400, seeks 1",
    ]


# ──────── new code ends here ────────
```

The test starts at the `id:` line rather than at `write pages.bin`,
because the file's size changes in section C.

```bash
uv run pytest -q
```

```text
.............................                                            [100%]
29 passed in 0.31s
```

That makes twenty-nine tests: three more for the pages and one for the
demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-02b`

### Section C — the wall card at the back

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/json.html#json.dumps"><code>json.dumps</code>: Python lists and dicts to JSON text</a>
<a href="https://docs.python.org/3.12/library/json.html#json.loads"><code>json.loads</code>: JSON text back to lists and dicts</a>
<a href="https://docs.python.org/3.12/library/dataclasses.html#dataclasses.asdict"><code>dataclasses.asdict</code>: a dataclass's fields as a dict</a>
<a href="https://docs.python.org/3.12/library/struct.html#struct.Struct.format"><code>Struct.format</code>: the format string a codec was made from</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#unpacking-argument-lists"><code>**</code>: a dict's entries as named arguments</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#dictionaries">dict comprehensions: <code>{k: v for …}</code> builds a dict</a>
<a href="https://docs.python.org/3.12/reference/lexical_analysis.html#string-literal-concatenation">adjacent strings are joined: <code>"ab" "cd"</code> is <code>"abcd"</code></a>
<a href="https://docs.python.org/3.12/reference/expressions.html#membership-test-operations"><code>in</code>: is this value somewhere in that list?</a>
</div>

Your box list works, but it lives only in memory. It has to travel with
the file. It goes after the last page, because the writer only knows
where the pages landed once they are written. A fixed-size footer goes
after the list, so a reader can find the list from the end. Make six
edits in `src/nanolance/page_file.py`, top to bottom:

1. Replace the module docstring (lines 1–6), because the file now holds
   more than pages:

   ```python
   """Analogy: every aisle cut into sealed boxes — a box holds up to
   ROWS_PER_PAGE values, and a picker carries only the boxes a question needs.

   The page file: each column is stored as a run of pages, one column after
   another. A page is one read's worth of a single column's values. After the
   pages come the column metadata (every column's format and page list, as
   JSON), and last a fixed-size footer that says where the metadata is.
   """
   ```

2. Replace the imports (lines 8–13). `json` and `asdict` are new, and so
   is `CountingFile`, which the reader in step 6 needs:

   ```python
   import json
   import struct
   from dataclasses import asdict, dataclass
   from pathlib import Path
   from typing import BinaryIO

   from nanolance.counting import CountingFile
   from nanolance.orders import COLUMNS, Row, pack_value
   ```

3. Below `ROWS_PER_PAGE = 100` (around line 19), add the footer's shape,
   its magic bytes, and its format version:

   ```python
   # ──────── new code starts here (around line 21) ────────
   # Analogy: the wall card at the back — always the same size, always the
   # last thing in the warehouse, so a picker knows where to find it.
   #
   # The footer: metadata offset (8 bytes), metadata size (8 bytes), format
   # version (4 bytes), and the magic bytes that name the format (4 bytes).
   FOOTER = struct.Struct("<QQI4s")
   MAGIC = b"NLNC"
   VERSION = 1
   # ──────── new code ends here ────────
   ```

   `FOOTER` is a `struct` codec, like yesterday's column codecs. `Q` is
   an 8-byte whole number that is never negative, `I` a 4-byte one, and
   `4s` four raw bytes: 8 + 8 + 4 + 4 = 24 bytes, always.

4. Below the `Page` class (around line 45), add a class for everything a
   reader learns from the file:

   ```python
   # ──────── new code starts here (around line 45) ────────
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


   # ──────── new code ends here ────────
   ```

5. In `write`, between the end of the page loop and `return pages`
   (around line 76), write the box lists and then the card. The framing
   lines are already in your file. Notice that the new code sits inside
   the `with` block, one indent deeper than `return`:

   ```python
                   pages[column].append(page)
                   out.write(data)

           # ──────── new code starts here (around line 76) ────────
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
           # ──────── new code ends here ────────
       return pages
   ```

6. At the bottom of the file (around line 133), add the reader that
   opens a file from its end:

   ```python
   # ──────── new code starts here (around line 133) ────────
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


   # ──────── new code ends here ────────
   ```

What the new code does:

- `metadata` is the box lists as plain Python. It holds the row count,
  then for each column its name, its codec's format string (`"<i"` for
  `qty`), and its pages, each one turned into a dict by `asdict`.
  `json.dumps` writes that as JSON text. `separators=(",", ":")` leaves
  out the spaces it would otherwise add after each comma and colon.

- The writer notes `metadata_offset = out.tell()` before writing the
  JSON, the same move as for every page. Then `FOOTER.pack` writes the
  card: where the metadata starts, how long it is, the format version, and the
  magic bytes.

- `read_metadata` does the reverse, from the end. It seeks to `f.size -
  FOOTER.size`, reads the 24-byte card, and unpacks its four fields. Then
  it seeks to the metadata and reads exactly `metadata_size` bytes.
  `struct.Struct(c["format"])` rebuilds each column's codec from the
  file. `Page(**page)` turns each `{"offset": …, "size": …, "rows":
  …}` dict back into a `Page`; the `**` passes the dict's entries as
  named arguments.

- `read_metadata` unpacks `magic` but does not check it yet. Hold that
  thought until section D.

The reader needs one more fact: where the end is. The file system can
tell it. In `src/nanolance/counting.py`, in `CountingFile.__init__`, add
this right after the file is opened (around line 18):

```python
        self._file = open(path, "rb")
        # ──────── new code starts here (around line 18) ────────
        # The file's length comes from the file system, not from a read.
        self.size = path.stat().st_size
        # ──────── new code ends here ────────
```

Knowing the size costs no read, so the tally does not count it. (On a
cloud store, asking for the size is a small request of its own.)

Now the demo. At the end of `pages` in `src/nanolance/cli.py` (around
line 116), add three fresh `CountingFile`s. One only opens the file, and
two answer the same questions as before, told nothing:

```python
    # ──────── new code starts here (around line 116) ────────
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
    # ──────── new code ends here ────────
```

Each question opens the file itself, so each tally includes the
opening. That is the honest price of a reader that starts from nothing.

Run it:

```bash
uv run nanolance pages
```

```text
the orders table: 1000 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  … and 997 more, repeating the same eight orders
write columns.bin: 32000 bytes = id 8000 + price 8000 + qty 4000 + name 12000
sum(qty) from columns.bin, told 1000 rows = 8125
  tally: reads 1, bytes read 4000, seeks 1
sum(qty) from columns.bin, told 8 rows = 474
  tally: reads 1, bytes read 32, seeks 1
qty of rows 10–19 from columns.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 1, bytes read 4000, seeks 1 (rows 10–19 need only 40 of them)
write pages.bin: 33762 bytes, each column cut into pages
  id: 10 pages of 800 bytes, at 0, 800, …, 7200
  price: 10 pages of 800 bytes, at 8000, 8800, …, 15200
  qty: 10 pages of 400 bytes, at 16000, 16400, …, 19600
  name: 10 pages of 1200 bytes, at 20000, 21200, …, 30800
sum(qty) from pages.bin = 8125
  tally: reads 10, bytes read 4000, seeks 10
qty of rows 10–19 from pages.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 1, bytes read 400, seeks 1
──── everything above: sections A and B's output, unchanged but for one size ────
open pages.bin: version 1, 1000 rows, columns id, price, qty, name, 40 pages
  tally: reads 2, bytes read 1762, seeks 2
sum(qty) from pages.bin, told nothing = 8125
  tally: reads 12, bytes read 5762, seeks 12
qty of rows 10–19 from pages.bin, told nothing = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 3, bytes read 2162, seeks 3
```

One line above the divider changed: `pages.bin` is now 33762 bytes, not
32000. Read it line by line:

- `write pages.bin: 33762 bytes, …` — the 32000 bytes of pages come
  first, then 1738 bytes of box lists, then the 24-byte card.

- `open pages.bin: version 1, 1000 rows, columns id, price, qty, name,
  40 pages` and `reads 2, bytes read 1762, seeks 2` — `read_metadata`
  walked to [the wall card](story.md#wall-card) and then to the
  [box lists](story.md#box-list). That took two seeks and two reads, of
  24 + 1738 = 1762 bytes. Every fact on that line came from the file.

- `sum(qty) from pages.bin, told nothing = 8125` and `reads 12, bytes
  read 5762, seeks 12` — the opening costs 2 reads and 1762 bytes. Then
  come the ten quantity boxes: 10 reads, 4000 bytes.

- `qty of rows 10–19 …, told nothing = […]` and `reads 3, bytes read
  2162, seeks 3` — the opening, then one box of 400 bytes. Compare that
  with section A's 4000 bytes, which also needed the row count from
  outside.

The opening's 1762 bytes look large next to a 400-byte box because our
boxes are tiny. With Lance's 8 MB pages, the metadata is a sliver of one
page. And a reader that asks many questions opens the file once and
keeps the metadata.

<div class="callout">

**Optional — look inside the file.** You can read the card and the start
of the box lists yourself. The last 24 bytes, in hex:

```bash
uv run python -c "from pathlib import Path; print(Path('warehouse/pages.bin').read_bytes()[-24:].hex(' '))"
```

```text
00 7d 00 00 00 00 00 00 ca 06 00 00 00 00 00 00 01 00 00 00 4e 4c 4e 43
```

- `00 7d 00 00 00 00 00 00` — where the metadata starts. The bytes are
  little-endian, so read them backward: hex `7d00` is 32000.

- `ca 06 00 00 00 00 00 00` — its size: hex `06ca` is 1738.

- `01 00 00 00` — the format version, 1.

- `4e 4c 4e 43` — the letters `N L N C` as bytes: the stamp.

And the first 170 bytes of the metadata, which is plain text:

```bash
uv run python -c "from pathlib import Path; print(Path('warehouse/pages.bin').read_bytes()[32000:32170].decode())"
```

```text
{"rows":1000,"columns":[{"name":"id","format":"<q","pages":[{"offset":0,"size":800,"rows":100},{"offset":800,"size":800,"rows":100},{"offset":1600,"size":800,"rows":100},
```

You see the row count, then the `id` column: its format, `<q`, and its
first three boxes. They have the same offsets the demo printed in
section B.

</div>

Pin the card with tests. There are four edits in three files:

1. In `tests/test_counting.py`, at the bottom (around line 32), add a
   test of the new `size`:

   ```python
   # ──────── new code starts here (around line 32) ────────
   def test_the_file_size_is_known_without_a_read(tmp_path):
       path = tmp_path / "data.bin"
       path.write_bytes(bytes(range(10)))
       with CountingFile(path) as f:
           assert f.size == 10
           assert (f.reads, f.bytes_read, f.seeks) == (0, 0, 0)


   # ──────── new code ends here ────────
   ```

2. In `tests/test_page_file.py`, line 6: the last import line grows to
   `from nanolance.page_file import FOOTER, MAGIC, VERSION, Page`.

3. In `tests/test_page_file.py`, at the bottom (around line 41), add
   three tests:

   ```python
   # ──────── new code starts here (around line 41) ────────
   def test_the_file_ends_with_a_fixed_size_footer(tmp_path):
       path = tmp_path / "pages.bin"
       page_file.write(path, many_orders(1000))
       data = path.read_bytes()
       offset, size, version, magic = FOOTER.unpack(data[-FOOTER.size :])
       assert (version, magic) == (VERSION, MAGIC)
       assert offset == 32000  # the metadata starts right after the pages
       assert offset + size + FOOTER.size == len(data)


   def test_the_metadata_tells_a_reader_everything(tmp_path):
       path = tmp_path / "pages.bin"
       orders = many_orders(1000)
       pages = page_file.write(path, orders)
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
           assert (f.reads, f.seeks) == (2, 2)
           assert f.bytes_read == f.size - 32000  # the metadata plus the footer
       assert metadata.version == VERSION
       assert metadata.rows == 1000
       assert {name: codec.format for name, codec in metadata.codecs.items()} == {
           "id": "<q",
           "price": "<d",
           "qty": "<i",
           "name": "<12s",
       }
       assert metadata.pages == pages


   def test_a_reader_told_nothing_reads_back_every_column(tmp_path):
       path = tmp_path / "pages.bin"
       orders = many_orders(1000)
       page_file.write(path, orders)
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
           for position, (column, codec) in enumerate(metadata.codecs.items()):
               values = page_file.read_column(f, codec, metadata.pages[column])
               assert values == [row[position] for row in orders]


   # ──────── new code ends here ────────
   ```

   `test_the_file_ends_with_a_fixed_size_footer` unpacks the last 24
   bytes and checks that the pieces add up: metadata from byte 32000,
   then the footer, then nothing.
   `test_the_metadata_tells_a_reader_everything` pins the opening's
   cost: two reads, two seeks, and every byte after the pages. It also
   checks that what the reader learns equals what the writer recorded.
   `test_a_reader_told_nothing_reads_back_every_column` reads all four
   columns using only what the file says.

4. In `tests/test_cli.py`, at the bottom (around line 96), add a test of
   the demo's new lines. The long expected line is split in two, and
   Python joins adjacent string literals into one.

   ```python
   # ──────── new code starts here (around line 96) ────────
   def test_pages_opens_the_file_from_its_footer(tmp_path):
       lines = run_pages(tmp_path)
       assert "write pages.bin: 33762 bytes, each column cut into pages" in lines
       start = lines.index(
           "open pages.bin: version 1, 1000 rows, columns id, price, qty, name, 40 pages"
       )
       assert lines[start : start + 6] == [
           "open pages.bin: version 1, 1000 rows, columns id, price, qty, name, 40 pages",
           "  tally: reads 2, bytes read 1762, seeks 2",
           "sum(qty) from pages.bin, told nothing = 8125",
           "  tally: reads 12, bytes read 5762, seeks 12",
           "qty of rows 10–19 from pages.bin, told nothing = "
           "[40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
           "  tally: reads 3, bytes read 2162, seeks 3",
       ]


   # ──────── new code ends here ────────
   ```

```bash
uv run pytest -q
```

```text
..................................                                       [100%]
34 passed in 0.31s
```

That makes thirty-four tests. The five new ones cover the file size
(one), the card and the box lists (three), and the demo (one).

**Section checkpoint:** `./scripts/compare.sh v1-day-02c`

### Section D — the stamp: refusing a file by name

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/tutorial/errors.html#handling-exceptions"><code>try</code> / <code>except … as error</code>: catch an error and keep going</a>
<a href="https://docs.python.org/3.12/library/functions.html#repr"><code>!r</code> in an f-string: the value as Python would write it, e.g. <code>b'NLNC'</code></a>
<a href="https://docs.python.org/3.12/reference/expressions.html#the-power-operator"><code>**</code> between numbers: a power, <code>10**6</code> is a million</a>
<a href="https://docs.python.org/3.12/reference/lexical_analysis.html#string-and-bytes-literals">raw strings: <code>r"\x00"</code> keeps the backslash as typed</a>
<a href="https://docs.python.org/3.12/reference/lexical_analysis.html#reserved-classes-of-identifiers"><code>_</code>: a name for a value you will not use</a>
</div>

Your reader now opens a file with no outside help. But it trusts the
last 24 bytes of any file it is given. So give it the wrong file:
yesterday's `columns.bin`, still sitting in `warehouse/`:

```bash
uv run python -c "from pathlib import Path; from nanolance import page_file; from nanolance.counting import CountingFile; page_file.read_metadata(CountingFile(Path('warehouse/columns.bin')))"
```

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/…/build-nano-lance-in-python/src/nanolance/page_file.py", line 146, in read_metadata
    metadata = json.loads(f.read(metadata_size))
                          ^^^^^^^^^^^^^^^^^^^^^
  File "/…/build-nano-lance-in-python/src/nanolance/counting.py", line 26, in read
    data = self._file.read(size)
           ^^^^^^^^^^^^^^^^^^^^^
MemoryError
```

(Paths shortened, as everywhere in this book.) The last 24 bytes of
`columns.bin` are the names `gloves` and `padlock` with their padding.
Read as a card, those letters say the metadata is about
7,810,474,787,431,514,112 bytes long, and `read` tried to make room for
that many. Python ran out of memory before it ran out of trust. A
smaller accident is worse. With a few plausible-looking numbers, the
reader carries back garbage without a word, like section A's 474.

The fix is to check the card before believing it. In
`src/nanolance/page_file.py`, replace the whole `read_metadata` function,
from line 135 to the end of the file, with this one. The docstring gains
a sentence, and four checks arrive around the first read:

```python
def read_metadata(f: CountingFile) -> Metadata:
    """Analogy: walk to the back wall, read the wall card, then the box
    lists it points to.

    Two seeks and two reads: the footer (the file's last FOOTER.size
    bytes), then the column metadata at the offset the footer gives. A file
    without the magic bytes, of another version, or whose footer points
    outside the file is refused with a ValueError before the second read.
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
    if version != VERSION:
        raise ValueError(
            f"nanolance file version {version}; this reader reads version {VERSION}"
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
```

- **Too short.** A file smaller than the card cannot hold one. This check
  comes before any seek, because otherwise `f.size - FOOTER.size` would be
  negative.

- **The wrong name.** If the last four bytes are not `NLNC`, this is not
  our file. Whatever it is, the reader refuses it by name. A file whose
  writer was interrupted also lands here. Its last bytes are page data,
  because the card is the last thing written.

- **The wrong format version.** The file is ours, but written by a format
  version this reader does not know. Refusing is safer than guessing.

- **A card that points outside the file.** The metadata must end before
  the footer starts. This catches a damaged card before the reader tries
  to read past the end.

Each error is a `ValueError` whose message says which check failed.
`{magic!r}` prints the bytes the way Python writes them, so an
unprintable byte shows as `\x00` instead of vanishing.

At the end of `pages` in `src/nanolance/cli.py` (around line 138), open
yesterday's file as a page file, and catch the refusal:

```python
    # ──────── new code starts here (around line 138) ────────
    with CountingFile(columns_path) as f:
        try:
            page_file.read_metadata(f)
        except ValueError as error:
            print(f"open {columns_path.name} as a page file: refused, {error}")
        print(f"  tally: {f.tally()}")
    # ──────── new code ends here ────────
```

If `read_metadata` raises a `ValueError`, the `except` block runs and
prints its message. Either way, the demo carries on to print the tally.

Run it:

```bash
uv run nanolance pages
```

```text
⋮ (sections A, B, and C's output prints first, unchanged)
──── everything above: sections A, B, and C's output, unchanged ────
open columns.bin as a page file: refused, not a nanolance file: it ends with b'\x00\x00\x00\x00', not b'NLNC'
  tally: reads 1, bytes read 24, seeks 1
```

Read it line by line:

- `open columns.bin as a page file: refused, not a nanolance file: it
  ends with b'\x00\x00\x00\x00', not b'NLNC'` — [the stamp](story.md#stamp)
  check. The last four bytes of `columns.bin` are the padding after
  `padlock`: four zero bytes, not `NLNC`.

- `reads 1, bytes read 24, seeks 1` — the reader refused the file after
  one read of the card, before it carried anything else.

Pin every refusal. There are three edits in two files:

1. In `tests/test_page_file.py`, lines 1–6, the imports gain `pytest`
   and `column_layout`:

   ```python
   import pytest

   from nanolance import column_layout, page_file
   from nanolance.counting import CountingFile
   from nanolance.orders import COLUMNS, ORDERS, many_orders
   from nanolance.page_file import FOOTER, MAGIC, VERSION, Page
   ```

2. In `tests/test_page_file.py`, at the bottom (around line 81), add a
   small helper and five tests:

   ```python
   # ──────── new code starts here (around line 81) ────────
   def open_metadata(path):
       with CountingFile(path) as f:
           return page_file.read_metadata(f)


   def test_a_day_1_column_file_is_refused_by_name(tmp_path):
       path = tmp_path / "columns.bin"
       column_layout.write(path, ORDERS)
       with pytest.raises(ValueError, match="not a nanolance file: it ends with"):
           open_metadata(path)


   def test_a_file_cut_short_by_an_interrupted_write_is_refused(tmp_path):
       path = tmp_path / "pages.bin"
       page_file.write(path, many_orders(1000))
       path.write_bytes(path.read_bytes()[:32000])  # the pages, but no footer
       with pytest.raises(ValueError, match="not a nanolance file: it ends with"):
           open_metadata(path)


   def test_a_file_shorter_than_the_footer_is_refused_without_a_read(tmp_path):
       path = tmp_path / "tiny.bin"
       path.write_bytes(b"NLNC")
       with CountingFile(path) as f:
           with pytest.raises(ValueError, match="4 bytes is shorter than the 24-byte"):
               page_file.read_metadata(f)
           assert (f.reads, f.seeks) == (0, 0)


   def test_another_version_is_refused(tmp_path):
       path = tmp_path / "pages.bin"
       page_file.write(path, ORDERS)
       data = path.read_bytes()
       offset, size, _, _ = FOOTER.unpack(data[-FOOTER.size :])
       path.write_bytes(data[: -FOOTER.size] + FOOTER.pack(offset, size, 2, MAGIC))
       with pytest.raises(ValueError, match="version 2; this reader reads version 1"):
           open_metadata(path)


   def test_a_footer_pointing_outside_the_file_is_refused(tmp_path):
       path = tmp_path / "pages.bin"
       page_file.write(path, ORDERS)
       data = path.read_bytes()
       offset, _, _, _ = FOOTER.unpack(data[-FOOTER.size :])
       path.write_bytes(data[: -FOOTER.size] + FOOTER.pack(offset, 10**6, VERSION, MAGIC))
       with pytest.raises(ValueError, match="damaged nanolance file"):
           open_metadata(path)


   # ──────── new code ends here ────────
   ```

   `test_a_day_1_column_file_is_refused_by_name` gets the same refusal
   the demo shows. `test_a_file_cut_short_by_an_interrupted_write_is_refused`
   keeps only the first 32000 bytes: every page, but no box lists and no
   card, as if the writer had stopped there.
   `test_a_file_shorter_than_the_footer_is_refused_without_a_read` gives
   the reader four bytes that do spell `NLNC`. The size check refuses
   them before a single seek. The last two tests rewrite a good file's
   card, once with format version 2 and once pointing a million bytes
   past the end. Each expects its refusal by its message. `_` names the
   footer fields they do not need.

3. In `tests/test_cli.py`, at the bottom (around line 113), add a test
   of the refusal line. The `r` before the second string keeps `\x00` as
   the four characters the demo prints, instead of turning it into a
   zero byte.

   ```python
   # ──────── new code starts here (around line 113) ────────
   def test_pages_refuses_a_file_that_is_not_a_page_file(tmp_path):
       lines = run_pages(tmp_path)
       assert lines[-2:] == [
           "open columns.bin as a page file: refused, not a nanolance file: "
           r"it ends with b'\x00\x00\x00\x00', not b'NLNC'",
           "  tally: reads 1, bytes read 24, seeks 1",
       ]


   # ──────── new code ends here ────────
   ```

```bash
uv run pytest -q
```

```text
........................................                                 [100%]
40 passed in 0.37s
```

That makes forty tests: five more for the refusals and one for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-02d`. This one is
also the finished day.

## 7. Run it

```bash
uv run nanolance pages
```

## 8. Expected result

```text
the orders table: 1000 rows × 4 columns (id, price, qty, name)
  (101, 4.25, 3, 'bolts')
  (102, 12.5, 1, 'hammer')
  (103, 0.75, 40, 'washers')
  … and 997 more, repeating the same eight orders
write columns.bin: 32000 bytes = id 8000 + price 8000 + qty 4000 + name 12000
sum(qty) from columns.bin, told 1000 rows = 8125
  tally: reads 1, bytes read 4000, seeks 1
sum(qty) from columns.bin, told 8 rows = 474
  tally: reads 1, bytes read 32, seeks 1
qty of rows 10–19 from columns.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 1, bytes read 4000, seeks 1 (rows 10–19 need only 40 of them)
write pages.bin: 33762 bytes, each column cut into pages
  id: 10 pages of 800 bytes, at 0, 800, …, 7200
  price: 10 pages of 800 bytes, at 8000, 8800, …, 15200
  qty: 10 pages of 400 bytes, at 16000, 16400, …, 19600
  name: 10 pages of 1200 bytes, at 20000, 21200, …, 30800
sum(qty) from pages.bin = 8125
  tally: reads 10, bytes read 4000, seeks 10
qty of rows 10–19 from pages.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 1, bytes read 400, seeks 1
open pages.bin: version 1, 1000 rows, columns id, price, qty, name, 40 pages
  tally: reads 2, bytes read 1762, seeks 2
sum(qty) from pages.bin, told nothing = 8125
  tally: reads 12, bytes read 5762, seeks 12
qty of rows 10–19 from pages.bin, told nothing = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 3, bytes read 2162, seeks 3
open columns.bin as a page file: refused, not a nanolance file: it ends with b'\x00\x00\x00\x00', not b'NLNC'
  tally: reads 1, bytes read 24, seeks 1
```

The whole day in the warehouse, one stretch at a time:

- The table lines — a busy week: a thousand orders, the same eight over
  and over. (`many_orders`, printed by `pages`.)

- `write columns.bin` through the first `qty of rows 10–19` — yesterday's
  aisles. They are right when told the right count and confidently wrong
  when told the wrong one, and they carry a whole aisle for ten values.
  (`column_layout`, unchanged.)

- `write pages.bin` through the second `qty of rows 10–19` — every aisle
  is cut into sealed boxes, and the writer hands over a box list. Ten
  values now cost one box. (`page_file.write`, `read_column`,
  `read_rows`.)

- `open pages.bin` through the `told nothing` lines — the box lists and
  the wall card are stored in the file. A picker who knows nothing reads
  the card, then the lists, then only the boxes it needs.
  (`read_metadata`, then the same readers.)

- The last two lines — the stamp check turns a stranger's file away
  after one 24-byte read. (`read_metadata`'s checks.)

Nothing here varies between runs. There is no randomness and no timing,
only counts.

## 9. Test it

Forty tests now pin the day: Day 1's 22, plus 18 new ones. They cover the
bigger table and what Day 1's file cannot say (section A, 3 tests), the
pages (section B, 4), the box lists and the card (section C, 5), and the
refusals (section D, 6). Thirty-one are unit tests. The other nine
(`test_cli_says_hello` and the eight in `test_cli.py`) run the real
command line.

```bash
uv run pytest -q
```

```text
........................................                                 [100%]
40 passed in 0.37s
```

Every round trip is exact, every tally is pinned to its reads, bytes,
and seeks, and every refusal is pinned by its message.

## 10. Break it deliberately

Now make the writer note where each box *ends* instead of where it
begins. In `write` in `src/nanolance/page_file.py`, change one line:

```diff
@@ src/nanolance/page_file.py, around line 72 @@
                 data = b"".join(pack_value(column, row[position]) for row in chunk)
-                page = Page(offset=out.tell(), size=len(data), rows=len(chunk))
+                page = Page(offset=out.tell() + len(data), size=len(data), rows=len(chunk))
                 pages[column].append(page)
```

Every page's bytes still land in exactly the same place. Only the box
list lies, because each entry points one box further along. Run the page
tests:

```bash
uv run pytest -q --tb=line tests/test_page_file.py
```

```text
E   assert [Page(offset=...e=16, rows=2)] == [Page(offset=...e=16, rows=2)]
E   assert [201, 202, 20...205, 206, ...] == [101, 102, 10...105, 106, ...]
E   assert [4, 2, 3, 1, 40, 2, ...] == [40, 2, 1, 12, 4, 2, ...]
E   assert [201, 202, 20...205, 206, ...] == [101, 102, 10...105, 106, ...]
```

(Only the `E` lines are shown, one per failing test. Pytest's summary
line reads `4 failed, 7 passed`.)

Read it line by line:

- `[Page(offset=...)] == [Page(offset=...)]` — the exact-pages test sees
  the lie directly. The first page now claims to start at byte 24, where
  the second one starts.

- `[201, 202, …] == [101, 102, …]` (twice) — when reading the id column
  back, the first box on the list is really the second box, rows 100 to
  199. So every id comes back 100 too high.

- `[4, 2, 3, 1, 40, 2, …] == [40, 2, 1, 12, 4, 2, …]` — rows 10 to 19,
  read from the box the list names, are really rows 110 to 119. They are
  real quantities from the wrong rows, with no error.

- The seven tests that pass are the instructive part. The card is
  perfect. It points at the box lists, and the stamp and the format
  version are right, so every refusal test still passes. And the box
  lists the reader loads equal the ones the writer recorded, because both
  are wrong in the same way.

The demo shows how far the lie travels:

```bash
uv run nanolance pages
```

```text
write pages.bin: 33766 bytes, each column cut into pages
  id: 10 pages of 800 bytes, at 800, 1600, …, 8000
  price: 10 pages of 800 bytes, at 8800, 9600, …, 16000
  qty: 10 pages of 400 bytes, at 16400, 16800, …, 20000
  name: 10 pages of 1200 bytes, at 21200, 22400, …, 32000
sum(qty) from pages.bin = 69666604232
  tally: reads 10, bytes read 4000, seeks 10
qty of rows 10–19 from pages.bin = [4, 2, 3, 1, 40, 2, 1, 12, 4, 2]
  tally: reads 1, bytes read 400, seeks 1
open pages.bin: version 1, 1000 rows, columns id, price, qty, name, 40 pages
  tally: reads 2, bytes read 1766, seeks 2
sum(qty) from pages.bin, told nothing = 69666604232
  tally: reads 12, bytes read 5766, seeks 12
qty of rows 10–19 from pages.bin, told nothing = [4, 2, 3, 1, 40, 2, 1, 12, 4, 2]
  tally: reads 3, bytes read 2166, seeks 3
open columns.bin as a page file: refused, not a nanolance file: it ends with b'\x00\x00\x00\x00', not b'NLNC'
  tally: reads 1, bytes read 24, seeks 1
```

(The first twelve lines are left out. They are section A's, which never
touch `pages.bin`.) The sum is 69666604232. The last quantity box on the
list points at byte 20000, where the name column begins, so its
"quantities" are letters read as numbers. The last name box on the list
points at byte 32000, where the box lists themselves begin. So its first
four "names" are 12-byte slices of the metadata's own JSON text, starting
`'{"rows":1000'`. (The file is also 4 bytes longer, 33766, because the
larger offsets take more digits to write.)

The lesson: **the stamp proves whose file this is; it does not prove the
box lists are true.** A reader has no way to check where a box really
starts, because the list is the only map. That is why `write` records
`out.tell()` *before* writing each page, and why the exact-pages test
exists.

Put the line back and confirm `uv run pytest -q` is green again.

## 11. Checkpoint

Every checkpoint, each section and the day alike, is done only when the
full green bar passes:

```bash
./scripts/check.sh
```

```text
23 files already formatted
All checks passed!
........................................                                 [100%]
40 passed in 0.38s
nanolance 0.1.0: scaffold is alive
⋮ (Day 1's `nanolance layouts` output, unchanged) ⋮
⋮ (the §8 output, unchanged) ⋮
 INFO Book building has started
 INFO Running the html backend
 INFO HTML book written to `/…/build-nano-lance-in-python/book/book`
GREEN: all gates passed
```

(Paths shortened, as everywhere in this book.)

Read it line by line:

- `23 files already formatted` and `All checks passed!` — Ruff's
  formatting and lint gates, now over today's new files and this
  chapter's Python blocks too.

- The dots and `40 passed` — the whole suite, as in section 9.

- `nanolance 0.1.0: scaffold is alive` — the Day 0 smoke command.

- The two `⋮` lines — the smoke gate's two demos, shortened here:
  `nanolance layouts` (Day 1's 23 lines) and the new `nanolance pages`
  (the 29 lines of section 8).

- The three `INFO` lines and `GREEN: all gates passed` — the book built,
  and every gate passed.

The smoke gate gained one line today: `uv run --locked nanolance pages
"$scratch"`. `scripts/check.sh` is course infrastructure, outside what
`compare.sh` checks. To pick up today's copy, take it from the
checkpoint:

```bash
git checkout v1-day-02 -- scripts/check.sh
```

Then close out the day in whichever mode you are following:

**Built along on your own branch?** Confirm your code matches the finished
day. The final ✓ line means it does:

```bash
./scripts/compare.sh v1-day-02
```

**Inspecting instead of typing?** Jump to today's exact finished state,
poke at it, and come back:

```bash
git switch --detach v1-day-02
uv run nanolance pages
git switch -          # back to where you were
```

**Either way**, today's complete change set, docs included, reads as one
diff:

```bash
git diff v1-day-01 v1-day-02
```

## 12. Recap

**What changed today:** you added `many_orders`, a thousand predictable
orders. You built a page file, `page_file`, whose `write` cuts each
column into pages of up to 100 values and records each one as a `Page`
(offset, size, rows). `read_page`, `read_column`, and `read_rows` read
only the pages a question needs. The column metadata is written as JSON
after the pages, and a 24-byte `FOOTER` follows it, carrying the
metadata's position, the format `VERSION`, and the `MAGIC` bytes `NLNC`.
`read_metadata` opens a file from its end. It refuses a file that is too
short, not ours, of another format version, or pointing outside itself.
You also added `CountingFile.size`, and a `nanolance pages` demo that
counts every step. Eighteen new tests (40 in all) pin it across four
section checkpoints (`v1-day-02a` to `v1-day-02d`), still with no
dependencies.

**Deliberately naive:** pages hold a fixed number of rows. Opening a
file reads every column's box list, in two separate reads (§5's "Where
real Lance does more" says how Lance does better). And the reader trusts
the box list completely; section 10 showed what that costs.

**Tomorrow, on Day 3:** every value still takes its full fixed width. A
quantity of 3 spends four bytes, and `tape` drags eight bytes of
padding. Day 3 packs the boxes tighter: the same values in fewer bytes,
with dictionaries, runs, and packed bits, each proven to give back
exactly what went in. Then a page's size can no longer be computed from
its row count, and you will see why the box list had to record each
box's size rather than work it out. The warehouse now describes itself
(see [the warehouse](story.md)). Next, it learns to pack.
