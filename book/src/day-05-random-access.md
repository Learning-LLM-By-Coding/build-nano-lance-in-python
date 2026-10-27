# Day 5: Random access

> **Day 5** (of Days 0–17) · builds on `v1-day-04` · ≈ 2 h · the last day of the free preview

| Section | Builds | Checkpoint |
|---------|--------|------------|
| A | A take by scanning: ten scattered rows, every page read | `v1-day-05a` |
| B | Row id → page: only the pages that hold a requested row, each once | `v1-day-05b` |
| C | A Parquet-style row-group file, and the same take against it | `v1-day-05c` |
| D | Page size: what a scan and a take each read, from 10 to 10,000 rows per page | `v1-day-05d` = `v1-day-05` |

**Pick your mode before starting** (explained fully in
[Setup](setup.md#4-choose-how-you-follow-along)):

```bash
# Build mode — type today's code yourself, on your own branch:
git switch -c my-course v1-day-04      # or keep going on yesterday's branch

# Inspect mode — read along with the finished code instead:
git switch --detach v1-day-05a         # then 05b, 05c, 05d as you pass each section
```

<div class="callout">

**Today's typing budget** — so nothing sneaks up on you:

| Section | The learning | Wiring & tests (copy-friendly) |
|---------|--------------|--------------------------------|
| A | in `page_file.py`: `check_row_ids` + `take_by_scan` · ~25 lines | `PICK_LIST` and the `take` demo (~35 lines), 2 edits in `main`, 2 tests |
| B | in `page_file.py`: `page_starts`, `locate`, `take` · ~60 lines with docstrings | 1 import, demo lines (~12), 17 tests |
| C | a new `row_groups.py`: `write` · ~55 lines with docstrings; in `page_file.py`, the end of `write` moved into `finish` | 1 import, demo lines (~25), 8 tests |
| D | `costs` · ~20 lines | demo lines (~10), 3 tests |

Four sections are four natural sittings, and every checkpoint is a save
point — nothing says a "day" must fit in one. Still **no dependencies**.

</div>

> **Short on time?** Sections A–B are the core: the problem, and the
> take that solves it. C builds the Parquet-style file to compare
> against, and D the table that sums up the day; each can be a second
> sitting.

## 1. What you will have running

By the end of today, `uv run nanolance take` stores 10,000 of the shop's
orders and fetches ten of them, scattered all over the table, by their
row numbers: row 7342, row 15, row 9999, and seven more. Fetching rows
by number is what Lance calls a **take**. The demo does it three ways,
and counts every read:

- by **scanning**: reading every value of every column, then picking
  out the ten rows;

- by **looking up the page** that holds each row, and reading only
  those pages;

- from a **Parquet-style file**, where rows are grouped into large
  blocks that must be read whole.

Last, it writes the same table with pages of 10, 100, 2,500, and 10,000
rows, and prints one table: what a full scan and the ten-row take each
read from every one. Small pages make the take read few bytes; big pages
let the scan finish in few reads. You will see both, in bytes and reads.

<div class="dl-concepts"><span>Lance concepts used here:</span>
<a href="https://lance.org/format/file/">Lance's file format: "No Row Groups", and pages built for random access ↗</a>
<a href="https://lance.org/format/file/encoding/">Lance's encodings: mini-blocks and full-zip, for reading one value ↗</a>
<a href="https://parquet.apache.org/docs/file-format/configurations/">Parquet's row group and page sizes ↗</a>
<a href="https://parquet.apache.org/docs/file-format/pageindex/">Parquet's page index: skipping to one page ↗</a>
<a href="https://en.wikipedia.org/wiki/Binary_search">binary search (Wikipedia) ↗</a>
</div>

## 2. What you will be seeing in the output

A few lines from the end of the day (section 8 has all of them); if one
doesn't land yet, that's fine:

```text
the pick list, 10 row ids: [7342, 15, 9999, 2718, 404, 6001, 8123, 3141, 0, 5050]
⋮
  tally: reads 500, bytes read 185577, seeks 500
⋮
take box by box: the same rows? True
  tally: reads 45, bytes read 16672, seeks 45
⋮
take from the row groups: the same rows? True
  tally: reads 20, bytes read 196701, seeks 20
box size: what a scan and the pick list read, every column (reads, bytes)
    rows per box | box lists |         scan |    pick list
              10 |    753278 | 5000, 238534 |     50, 2355
             100 |     77910 |  500, 185577 |    45, 16672
            2500 |      3496 |   20, 196701 |   20, 196701
           10000 |      1084 |    5, 204917 |    5, 204917
  2500 in groups |      3500 |   20, 196701 |   20, 196701
```

- `the pick list, 10 row ids: …` — the ten rows to fetch. A row's number
  is its position in the table, counting from 0.

- The first `tally` line — fetching those ten rows by scanning: 500
  reads and 185,577 bytes, every byte of every column.

- `take box by box` and its tally — the same ten rows from only the
  pages that hold them: 45 reads, 16,672 bytes, about an eleventh.

- `take from the row groups` and its tally — the Parquet-style file:
  fewer reads, but more bytes than even the scan.

- The table — five ways to store the same table. The first number in
  each row is the size of the file's map of its pages; then the scan,
  and the ten-row take, as reads and bytes. Read the last two columns
  side by side: as the pages grow, the scan needs fewer reads
  and the take needs more bytes.

## 3. Why we need it

Since Day 2, the reader answers two kinds of question: a **scan** —
every value of a column — and a **stretch** of neighboring rows, such as
rows 10 to 19. Real programs often ask a third kind:

- **A training job** shuffles its table every pass and asks for a batch
  of rows in random order — row 7342, then row 15, then row 9999.

- **A search** returns the numbers of the ten best matches, and the
  program then fetches those ten rows' text and images.

Both ask for *scattered* rows, in an order they choose, sometimes the
same row twice. That is a **take**.

Lance's file format names random access as a design goal. Its pages are
built to be read "with a small and predictable number of I/O
operations", and: "This is important for selective filters, point
lookups, vector-search follow-up reads, and ML training workloads that
sample rows non-sequentially."

Yesterday's code has no way to ask for a list of rows. The simplest way
to get one is to scan and pick — and section A counts what that costs.

On Day 1 you saw that one row costs a stop in every column. Today you
count what a *list* of rows costs, and compare it with the other famous
columnar format, Parquet, which groups rows into large blocks first.

**The story so far — remember [the warehouse](story.md):** orders in
[aisles](story.md#column-layout), cut into [sealed boxes](story.md#pages),
found by [box lists](story.md#box-list), every trip
[tallied](story.md#tally).

Today's scene is **the pick list**. On Day 1, a
[customer pickup](story.md#pickup) was one whole order; now a customer
hands the picker a list of ten orders, scattered across a warehouse of
10,000, and the picker learns to walk straight to the right box for each
one. Across the street stands a second warehouse, built the Parquet way:
it ships its orders on **pallets** — a few thousand whole orders each,
every aisle's share wrapped as one piece — and today the picker fills
the same list there.

## 4. Mental model

Walk the picker's route, one stop per section:

- **[The pick list](story.md#pick-list) (section A)** — ten row numbers.
  A row's number is its place in the table, from 0 — not the order's
  `id`, which starts at 101. The slow way to fill the list: carry back
  every box of every aisle, then pick the ten orders out at the bench.

- **[Start numbers](story.md#start-numbers) (section B)** — which box
  holds row 7342? The box list already says how many rows each box
  holds. Add them up, and you get the number each box starts at:

  ```text
  rows in each box   100, 100, 100, …, 100      the box list's row counts, 100 boxes
  start numbers      0, 100, 200, …, 9900       a running total: box n starts at row 100 × n
  row 7342           box 73, place 42           the last start at or below 7342 is 7300
  ```

  Finding "the last start at or below 7342" in a sorted list is a
  *binary search*: look at the middle start, keep the half that can
  hold the answer, repeat. A hundred starts take seven looks.

- **Each box once, the list's order kept (section B).** Rows 15 and 0
  share box 0. The picker carries box 0 back once and takes both orders
  from it, then hands the rows over in the order the list asked.

- **[Pallets](story.md#pallets) (section C)** — the warehouse across the
  street. A pallet carries 2,500 whole orders, and on it each aisle's
  share is wrapped as one piece: to get one price, the picker unwraps
  all 2,500 prices. That is Parquet's *row group*, in miniature.

- **[The box size](story.md#box-size) (section D)** — small boxes let a
  pick list carry few bytes, but a stock count must make many trips to
  carry them all; big boxes let the stock count finish in a few trips,
  but a pick list carries far more. Section D counts both.

Here is the whole take of section B, as data flowing down the page:

```text
the pick list          10 row numbers: 7342, 15, 9999, …, 5050
    │ for each column: add up the box list's row counts
    ▼
start numbers          0, 100, 200, …, 9900: where each of the 100 boxes begins
    │ for each row number: binary-search the start numbers
    ▼
a box and a place      row 7342: box 73, place 42 — row 15: box 0, place 15
    │ carry back every box the list needs, once; unpack it by its packing note
    ▼
9 boxes per column     rows 15 and 0 share box 0
    │ take each row's value from its place, in the list's order
    ▼
10 rows                (7443, None, 4, 'gloves', []), …
```

Only the first two steps are new. Carrying a box back and unpacking it
by its [packing note](story.md#packing-note) is Day 4's `read_page`,
unchanged.

## 5. Lance concepts introduced

- **A take.** Fetching rows by their positions, in a given order. It
  is the question behind Lance's "Random-Access-Friendly Encoding" design
  goal (§3).

- **Read the metadata once, keep it.** "Random access requires that we
  locate the physical location of the data in the file," and Lance's
  reader keeps what it needs for that — page locations, encodings — in
  a *search cache*: "The cost of initialization is assumed to be
  amortized over the lifetime of the reader." Today's demo does the
  same: it opens a file once, keeps the box lists, and counts each take
  without them.

- **Row groups.** A Parquet file first cuts its rows into *row groups*;
  inside each group, every column's values form one *column chunk*.
  Parquet's documentation recommends them large: "We recommend large row
  groups (512MB - 1GB). Since an entire row group might need to be read,
  we want it to completely fit on one HDFS block."

- **The unit you must read whole.** Parquet again: "Data pages should be
  considered indivisible so smaller data pages allow for more fine
  grained reading (e.g. single row lookup)." Whatever a format's smallest
  unit is, one value costs that whole unit. Section D measures it.

- **No row groups in Lance.** "Lance does not use Parquet-style row
  groups. Each column may have its own number of pages". Its reasons: "If
  the row group size is too small then columns will be split into "runt
  pages" which yield poor read performance on cloud storage. If the row
  group size is too large then a file writer will need a large amount of
  RAM since an entire row group must be buffered in memory before it can
  be written."

<div class="callout">

Fine to skip on a first read — section D's table makes the same point
with numbers.

**Be fair to both formats** — what today's code leaves out, from Lance's
[file format](https://lance.org/format/file/) and
[encoding](https://lance.org/format/file/encoding/) pages, and Parquet's
[page index](https://parquet.apache.org/docs/file-format/pageindex/) page:

1. **Real Parquet cuts each column chunk into pages.** Today's pallets
   store each chunk as one unit — Parquet's worst case for a take. Real
   writers cut chunks into data pages (the documentation recommends
   "8KB for page sizes"), and an optional *page index* says where each
   page sits: its OffsetIndex "allows navigation by row index". Without
   it, "a reader had to process the page header to determine whether the
   page could be skipped", which "means the reader had to access all
   pages in a column, thus likely reading most of the column data from
   disk." With it, a reader can jump straight to the one page holding a
   row — a take much like section B's.

2. **Real Lance pages are big, but not opaque.** Lance recommends
   "a default of 8MB" per page — far bigger than our boxes. "Disk pages
   should not generally be opaque. It is possible to read a portion of a
   disk page when a subset of the rows are required." Small values are
   stored in *mini-blocks*: "We have to read an entire mini-block to get a
   single value so we want to keep the mini-block size small" — "less than
   32KiB of compressed data". So a real Lance page is big for a scan, yet
   a take can read only part of it.

3. **One value, not one box, for large values.** For values of 256 bytes
   and up, Lance's *full-zip* layout finds one value directly: "To perform
   random access we require two IOPS" — the same two trips as Day 4's
   `read_string`. Today's take always carries a whole box.

</div>

## 6. Build it, section by section

### Section A — a pick list, filled by scanning

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/exceptions.html#IndexError"><code>IndexError</code>: Python's error for a position a sequence does not have</a>
<a href="https://docs.python.org/3.12/reference/lexical_analysis.html#integer-literals"><code>10_000</code>: underscores group a number's digits; it is 10000</a>
</div>

First, the question itself, asked the obvious way. In
`src/nanolance/page_file.py`, between the end of `read_rows` (its
`return values`, line 251) and `def read_metadata` (around line 253):

```python
# ──────── new code starts here (around line 253) ────────
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


# ──────── new code ends here ────────
```

- `check_row_ids` refuses a row the file does not hold. Python would
  quietly read `values[-1]` as the *last* value, so a negative row number
  is refused too.

- `take_by_scan` reads every column the list asks about whole, with
  Day 2's `read_column`, then picks the asked rows out, in the list's
  order. A `row_id` can repeat; it is only an index.

- Both take the file's `Metadata`, already read. The picker reads the
  wall card and the box lists once, and keeps them in hand for every
  question that follows.

Now the demo. The demo function is named `take`, after its subcommand.
Section B adds `page_file.take`, a different function the demo will
call. In `src/nanolance/cli.py`, two edits:

1. Between the end of `shapes` and `def main` (around line 466), the
   pick list and the demo:

   ```python
   # ──────── new code starts here (around line 466) ────────
   # Analogy: a customer's pick list — ten orders, scattered across the warehouse.
   #
   # Ten row ids of a 10,000-row table: positions counted from 0 (row k holds the
   # order with id 101 + k), out of order, and rows 0 and 15 in the same page.
   PICK_LIST = [7342, 15, 9999, 2718, 404, 6001, 8123, 3141, 0, 5050]


   def take(folder: Path) -> None:
       """Analogy: a customer hands the picker a pick list of ten orders.

       Store 10,000 shop orders, read the file's metadata once, and fetch the
       PICK_LIST rows, every column, counting what each way of fetching reads.
       """
       folder.mkdir(parents=True, exist_ok=True)
       tagged = many_tagged_orders(10_000)
       shop_path = folder / "shop.bin"
       every_column = {column: "smallest" for column in TAGGED_COLUMNS}
       page_file.write(shop_path, tagged, encoding=every_column, columns=TAGGED_COLUMNS)
       size = shop_path.stat().st_size
       print(
           f"write {shop_path.name}: {len(tagged)} shop orders, "
           f"{ROWS_PER_PAGE} rows per page, {size} bytes"
       )
       with CountingFile(shop_path) as f:
           metadata = page_file.read_metadata(f)
           print(f"open it once and keep the box lists — tally: {f.tally()}")
       columns = list(metadata.codecs)
       print(f"the pick list, {len(PICK_LIST)} row ids: {PICK_LIST}")

       with CountingFile(shop_path) as f:
           scanned = page_file.take_by_scan(f, metadata, PICK_LIST, columns)
           print("take by scanning every column:")
           for row_id, row in zip(PICK_LIST, scanned, strict=True):
               print(f"  row {row_id}: {row}")
           print(f"  tally: {f.tally()}")


   # ──────── new code ends here ────────
   ```

2. In `main`, register the subcommand after the `shapes` one (around
   line 515), and run it after the `shapes` branch (around line 527):

   ```python
       demo = demos.add_parser("shapes", help="store values of any length, or none")
       demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
       # ──────── new code starts here (around line 515) ────────
       demo = demos.add_parser("take", help="fetch scattered rows by their row ids")
       demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
       # ──────── new code ends here ────────
       args = parser.parse_args()
       ⋮
       elif args.demo == "shapes":
           shapes(args.folder)
       # ──────── new code starts here (around line 527) ────────
       elif args.demo == "take":
           take(args.folder)
       # ──────── new code ends here ────────
       else:
   ```

What `take` does so far:

- It writes 10,000 of the shop's orders, every box through the
  [weigh-in](story.md#weigh-in), with Day 4's `write` — 100 orders per
  box, as always.

- It opens the file once, and keeps its `metadata`.

- It fills `PICK_LIST` by scanning, with a fresh `CountingFile`, so the
  tally counts the take alone.

Run it:

```bash
uv run nanolance take
```

```text
write shop.bin: 10000 shop orders, 100 rows per page, 263487 bytes
open it once and keep the box lists — tally: reads 2, bytes read 77910, seeks 2
the pick list, 10 row ids: [7342, 15, 9999, 2718, 404, 6001, 8123, 3141, 0, 5050]
take by scanning every column:
  row 7342: (7443, None, 4, 'gloves', [])
  row 15: (116, 15.0, 2, 'padlock', ['gift', 'fragile'])
  row 9999: (10100, 15.0, 2, 'padlock', ['gift', 'fragile'])
  row 2718: (2819, None, 4, 'gloves', [])
  row 404: (505, 23.5, 1, 'drill bits Ø6', ['fragile'])
  row 6001: (6102, 12.5, 1, 'hammer', [])
  row 8123: (8224, 7.0, 2, 'tape', [])
  row 3141: (3242, 3.25, 12, 'nails', ['bulk'])
  row 0: (101, 4.25, 3, 'bolts', ['bulk'])
  row 5050: (5151, None, 40, 'washers', ['bulk', 'small parts'])
  tally: reads 500, bytes read 185577, seeks 500
```

Read it line by line:

- `write shop.bin: … 263487 bytes` — the shop's table at ten times
  Day 4's size, written by `page_file.write`.

- `open it once … bytes read 77910` — the wall card and the
  [box lists](story.md#box-list), read once by `read_metadata`. They are
  big: 100 boxes per aisle, each with its trays, in wordy JSON. The
  demo keeps them, so none of today's takes pays for them again.

- `the pick list, 10 row ids: …` — out of order, and spread from the
  first row (0) to the last (9999).

- The ten `row …` lines — each order, every column, from
  `take_by_scan`. Row 7342 is the order with id 7443; its price is
  `None`, because Day 4's [roll call](story.md#roll-call) came along;
  its name and its empty tags list came from their trays.

- `tally: reads 500, bytes read 185577, seeks 500` — five aisles of 100
  boxes: every box in the warehouse, 185,577 bytes, for ten orders.

That is the felt problem: a list of ten rows cost exactly as much as
reading the whole table. And on cloud storage, each of those 500 reads
is a separate request.

Pin it with two tests — one edit in each file, made by one checkout:

```bash
git checkout v1-day-05a -- tests/test_page_file.py tests/test_cli.py
```

<details>
<summary>Copy-friendly: what the two edits are, with one of the tests (click to open)</summary>

1. At the bottom of `tests/test_page_file.py`, a take by scanning that
   asks for two columns, in reverse order, with a repeated row — rows 6
   and 2 are the shop's two orders without a price:

   ```python
   def test_a_take_by_scanning_reads_every_page_of_every_column_asked(tmp_path):
       path = tmp_path / "shop.bin"
       tagged = many_tagged_orders(1000)
       pages = page_file.write(path, tagged, columns=TAGGED_COLUMNS)
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
       with CountingFile(path) as f:
           rows = page_file.take_by_scan(f, metadata, [6, 2, 6], ["name", "price"])
           assert rows == [("gloves", None), ("washers", None), ("gloves", None)]
           every_page = pages["name"] + pages["price"]
           assert (f.reads, f.bytes_read) == (20, sum(p.size for p in every_page))
   ```

2. At the bottom of `tests/test_cli.py`, a `run_take` helper like Day
   4's `run_shapes`, and `test_take_by_scanning_reads_every_page_for_ten_rows`,
   which pins the fifteen lines above, word for word.

</details>

```bash
uv run pytest -q
```

```text
........................................................................ [ 57%]
......................................................                   [100%]
126 passed in 0.93s
```

A hundred and twenty-six tests: yesterday's 124 and the two new ones.

**Section checkpoint:** `./scripts/compare.sh v1-day-05a`

### Section B — start numbers: only the boxes on the list

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/bisect.html#bisect.bisect_right"><code>bisect.bisect_right</code>: where a value would go in a sorted list, after any equal ones — a binary search</a>
<a href="https://docs.python.org/3.12/reference/expressions.html#membership-test-operations"><code>n not in opened</code>: for a dict, asks whether <code>n</code> is one of its keys</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#sets">set comprehensions: <code>{f(x) for x in …}</code> builds a set, each value once</a>
</div>

The box list already knows how many rows each box holds — Day 2's
`read_rows` used those counts to skip boxes outside one stretch of rows.
A pick list needs the same idea for every row on it, in any order. Three
new functions in `src/nanolance/page_file.py`:

1. Below `import struct` (line 11), the binary search from Python's
   standard library:

   ```python
   from bisect import bisect_right
   ```

2. Between the end of `take_by_scan` and `def read_metadata` (around
   line 277):

   ```python
   # ──────── new code starts here (around line 277) ────────
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


   # ──────── new code ends here ────────
   ```

- **`page_starts`** turns the box list's row counts into
  [start numbers](story.md#start-numbers): `[0, 100, 200, …]`. Uneven
  boxes work too; the last box of a table often holds fewer rows.

- **`locate`** finds a row's box: `bisect_right(starts, row_id)` counts
  the starts at or below the row, so one less is the last of them — the
  box. Row 7342: 74 starts (0 to 7300) are at or below it, so box 73,
  place 7342 − 7300 = 42.

- **`take`** walks the pick list once per column. `opened` remembers the
  values of every box already carried back, so a box two rows share is
  read once. Each value goes into `values` in the list's order, so
  repeats and any order come out right. Each box is unpacked by
  `read_page` on its own: a box packed with the
  [lid legend](story.md#lid-legend) needs only its own lid.

Now the demo, at the end of `take` in `src/nanolance/cli.py` (around
line 502). It prints each new step before the take itself:

```python
def take(folder: Path) -> None:
    ⋮
        print(f"  tally: {f.tally()}")

    # ──────── new code starts here (around line 502) ────────
    starts = page_file.page_starts(metadata.pages["qty"])
    print(f"start numbers of the qty boxes: {starts[:3]} … {starts[-1]}")
    for row_id in PICK_LIST[:2]:
        n, k = page_file.locate(starts, row_id)
        print(f"  row {row_id}: box {n}, place {k}")
    boxes = sorted({page_file.locate(starts, row_id)[0] for row_id in PICK_LIST})
    print(f"  the whole list: {len(boxes)} boxes per column, {boxes}")
    with CountingFile(shop_path) as f:
        rows = page_file.take(f, metadata, PICK_LIST, columns)
        print(f"take box by box: the same rows? {rows == scanned}")
        print(f"  tally: {f.tally()}")
    # ──────── new code ends here ────────
```

Run it:

```bash
uv run nanolance take
```

```text
write shop.bin: 10000 shop orders, 100 rows per page, 263487 bytes
open it once and keep the box lists — tally: reads 2, bytes read 77910, seeks 2
the pick list, 10 row ids: [7342, 15, 9999, 2718, 404, 6001, 8123, 3141, 0, 5050]
take by scanning every column:
  row 7342: (7443, None, 4, 'gloves', [])
  row 15: (116, 15.0, 2, 'padlock', ['gift', 'fragile'])
  row 9999: (10100, 15.0, 2, 'padlock', ['gift', 'fragile'])
  row 2718: (2819, None, 4, 'gloves', [])
  row 404: (505, 23.5, 1, 'drill bits Ø6', ['fragile'])
  row 6001: (6102, 12.5, 1, 'hammer', [])
  row 8123: (8224, 7.0, 2, 'tape', [])
  row 3141: (3242, 3.25, 12, 'nails', ['bulk'])
  row 0: (101, 4.25, 3, 'bolts', ['bulk'])
  row 5050: (5151, None, 40, 'washers', ['bulk', 'small parts'])
  tally: reads 500, bytes read 185577, seeks 500
──── everything above: section A's output, unchanged ────
start numbers of the qty boxes: [0, 100, 200] … 9900
  row 7342: box 73, place 42
  row 15: box 0, place 15
  the whole list: 9 boxes per column, [0, 4, 27, 31, 50, 60, 73, 81, 99]
take box by box: the same rows? True
  tally: reads 45, bytes read 16672, seeks 45
```

Read the new lines one by one:

- `start numbers of the qty boxes: [0, 100, 200] … 9900` — from
  `page_starts`: a hundred boxes of 100 rows each. Every aisle has the
  same boxes here, so the qty aisle stands for all five.

- `row 7342: box 73, place 42` and `row 15: box 0, place 15` — from
  `locate`.

- `the whole list: 9 boxes per column, […]` — ten rows, nine boxes:
  rows 15 and 0 share box 0.

- `take box by box: the same rows? True` — `take` gives exactly
  `take_by_scan`'s ten rows, in the same order.

- `tally: reads 45, bytes read 16672, seeks 45` — nine boxes in each of
  five aisles: 45 reads instead of 500, and 16,672 bytes instead of
  185,577 — about an eleventh.

Calling Day 2's `read_rows` once per row would have found the right
boxes too, but carried box 0 back twice: 50 reads, 18,459 bytes. Remembering opened
boxes is what turns ten fetches into one take.

Pin it with tests — four edits in two files, all made by one checkout:

```bash
git checkout v1-day-05b -- tests/test_page_file.py tests/test_cli.py
```

<details>
<summary>Copy-friendly: what the four edits are, with the main test (click to open)</summary>

1. At the bottom of `tests/test_page_file.py`,
   `test_start_numbers_find_the_page_and_the_place_of_a_row`: the very
   first row, the last row of a box, the first of the next, and the very
   last row.

2. Below it, the heart of the day: six pick lists, each taken from a
   plain file and a weighed one, with uneven pages of 70 rows. Each take
   must equal the scan's answer and the table itself — repeats, any
   order, box edges, missing prices, strings, lists, and an empty list:

   ```python
   TAKES = {
       "first and last": [0, 999],
       "out of order": [512, 3, 998, 40],
       "repeats": [7, 7, 2, 7],
       "page edges": [99, 100, 199, 200],
       "missing prices": [2, 6, 10, 14],
       "nothing": [],
   }


   @pytest.mark.parametrize("encoding", ["plain", "smallest"])
   @pytest.mark.parametrize("row_ids", TAKES.values(), ids=TAKES.keys())
   def test_take_returns_exactly_the_rows_asked_in_the_order_asked(
       tmp_path, row_ids, encoding
   ):
       path = tmp_path / "shop.bin"
       tagged = many_tagged_orders(1000)
       every_column = {column: encoding for column in TAGGED_COLUMNS}
       page_file.write(path, tagged, 70, every_column, TAGGED_COLUMNS)  # 70: uneven pages
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
           columns = ["tags", "id", "price", "name"]  # any columns, in any order
           rows = page_file.take(f, metadata, row_ids, columns)
           assert rows == page_file.take_by_scan(f, metadata, row_ids, columns)
       assert rows == [
           (tagged[r][4], tagged[r][0], tagged[r][1], tagged[r][3]) for r in row_ids
       ]
   ```

3. Below that, two tests of exact counts: rows 999, 0, 5, 100, 99, and 5
   cost three reads — boxes 9, 0, and 1 — and an empty list costs
   nothing; and row −1 or 1000 is refused before any read.

4. At the bottom of `tests/test_cli.py`,
   `test_take_box_by_box_reads_only_the_boxes_on_the_list` pins the six
   new lines of the run above.

</details>

```bash
uv run pytest -q
```

```text
........................................................................ [ 50%]
.......................................................................  [100%]
143 passed in 1.40s
```

A hundred and forty-three tests: seventeen more — twelve runs of the
pick-list test, four more for the page file, and one for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-05b`

### Section C — pallets: a Parquet-style row-group file

Section C needs no new Python.

Now the warehouse across the street. A Parquet file stores its rows in
**row groups**: the first few thousand rows, then the next few thousand.
Inside a group, each column's values form one **column chunk**, stored
one after another — every column of group 0, then every column of group
1. Here, each chunk is packed as one unit, so one value costs the whole
chunk.

First, a small move, so both files can share their ending. In
`src/nanolance/page_file.py`, two edits:

1. In `write`, replace the metadata and footer lines (lines 166–180,
   from `metadata = {` to the `out.write(FOOTER.pack(…))` line, and the
   blank line above them) with one call:

   ```python
   def write(
       ⋮
                   out.write(data)
           # ──────── replacement starts here (around line 165) ────────
           finish(out, len(rows), columns, pages)
           # ──────── replacement ends here ────────
       return pages
   ```

2. Below `write` (around line 168), the lines you removed, as a function
   of their own — the same lines, one level less indented, except that
   `len(rows)` becomes the new parameter `n_rows`:

   ```python
   # ──────── new code starts here (around line 168) ────────
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


   # ──────── new code ends here ────────
   ```

Then create `src/nanolance/row_groups.py`:

```python
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
```

- **The loops are swapped.** `page_file.write` loops over columns, then
  pages; `row_groups.write` loops over groups, then columns. So group 0's
  five chunks lie side by side, then group 1's.

- **A chunk is one page.** `pack_page` packs the whole group's values of
  a column as one unit: one packing note, one lid legend, one set of
  trays. That is what makes a chunk a
  [pallet's](story.md#pallets) wrapped piece.

- **The same box lists.** `finish` writes each column's chunks as its
  pages, so the page file's reader reads a pallet file unchanged —
  `read_metadata`, `take`, and all. Parquet's own footer lists the row
  groups first, then their chunks; ours lists the same facts the other
  way round.

Now the demo. In `src/nanolance/cli.py`, two edits:

1. Replace the `from nanolance import …` line (line 9) — one more module
   makes it too long for one line:

   ```python
   from nanolance import (
       __version__,
       column_layout,
       encodings,
       page_file,
       row_groups,
       row_layout,
   )
   ```

2. At the end of `take` (around line 521):

   ```python
   def take(folder: Path) -> None:
       ⋮
           print(f"take box by box: the same rows? {rows == scanned}")
           print(f"  tally: {f.tally()}")

       # ──────── new code starts here (around line 521) ────────
       groups_path = folder / "groups.bin"
       pallets = row_groups.write(
           groups_path, tagged, encoding=every_column, columns=TAGGED_COLUMNS
       )
       size = groups_path.stat().st_size
       print(
           f"write {groups_path.name}: {len(pallets['id'])} row groups of "
           f"{row_groups.ROWS_PER_GROUP} orders, {size} bytes"
       )
       for n in range(2):
           at = ", ".join(f"{c} {chunks[n].offset}" for c, chunks in pallets.items())
           print(f"  group {n}: {at}")
       with CountingFile(groups_path) as f:
           grouped = page_file.read_metadata(f)
           print(f"open it once and keep the box lists — tally: {f.tally()}")
       starts = page_file.page_starts(grouped.pages["qty"])
       boxes = sorted({page_file.locate(starts, row_id)[0] for row_id in PICK_LIST})
       print(f"  the pick list: {len(boxes)} groups, {boxes}")
       with CountingFile(groups_path) as f:
           rows = page_file.take(f, grouped, PICK_LIST, columns)
           print(f"take from the row groups: the same rows? {rows == scanned}")
           print(f"  tally: {f.tally()}")
       # ──────── new code ends here ────────
   ```

The demo writes the same 10,000 orders in groups of
`ROWS_PER_GROUP` = 2,500, prints where the first two pallets' chunks
start, and fills the same pick list. Run it:

```bash
uv run nanolance take
```

```text
⋮ (sections A and B print their 21 lines first, unchanged)
──── new: section C's lines ────
write groups.bin: 4 row groups of 2500 orders, 200201 bytes
  group 0: id 0, price 3751, qty 6624, name 8500, tags 30061
  group 1: id 48855, price 52919, qty 55792, name 57668, tags 79239
open it once and keep the box lists — tally: reads 2, bytes read 3500, seeks 2
  the pick list: 4 groups, [0, 1, 2, 3]
take from the row groups: the same rows? True
  tally: reads 20, bytes read 196701, seeks 20
```

Read it line by line:

- `write groups.bin: 4 row groups of 2500 orders, 200201 bytes` —
  `row_groups.write`: four pallets.

- `group 0: id 0, price 3751, …` and `group 1: id 48855, …` — the swapped
  loops, in offsets: group 0's five chunks, then group 1's.

- `open it once … bytes read 3500` — four chunks per aisle instead of a
  hundred boxes: box lists 22 times smaller than `shop.bin`'s 77,910.

- `the pick list: 4 groups, [0, 1, 2, 3]` — `locate`, unchanged: ten
  scattered rows land on every pallet.

- `take from the row groups: the same rows? True` — the same `take`, the
  same answer.

- `tally: reads 20, bytes read 196701, seeks 20` — four groups times
  five columns: fewer trips than section B's 45, but 196,701 bytes: every
  chunk in the file, about twelve times section B's 16,672.

That is even more than the scan of `shop.bin` (185,577), because bigger
units pack differently.

<details>
<summary>Why more bytes than the scan? (click to open)</summary>

A price chunk writes its [lid legend](story.md#lid-legend) once instead
of 25 times (11,492 bytes against 17,300), but the
[end marks](story.md#letter-strip) of a 2,500-row chunk run to bigger
numbers and need more bits (the names' end marks: 18,764 against 12,800).
Here the second effect wins.

</details>

A pallet is the right shape for a [stock count](story.md#stock-count) of a
few columns — and the wrong one for a pick list.

Pin it with tests — two files, made by one checkout:

```bash
git checkout v1-day-05c -- tests/test_row_groups.py tests/test_cli.py
```

<details>
<summary>Copy-friendly: what the two edits are, with one of the tests (click to open)</summary>

1. A new `tests/test_row_groups.py`, seven tests: the exact offsets of
   eight orders in groups of three, a weighed table read back through
   the page file's reader, four pick lists that must match a page file's
   answer, and the cost of one value:

   ```python
   def test_one_value_from_a_row_group_reads_its_whole_chunk(tmp_path):
       path = tmp_path / "groups.bin"
       row_groups.write(path, many_orders(1000), rows_per_group=250)
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
       with CountingFile(path) as f:
           assert page_file.take(f, metadata, [260], ["qty"]) == [(1,)]
           assert (f.reads, f.bytes_read, f.seeks) == (1, 250 * 4, 1)  # one whole chunk
   ```

2. At the bottom of `tests/test_cli.py`,
   `test_take_from_row_groups_reads_every_chunk` pins the seven new lines
   of the run above.

</details>

```bash
uv run pytest -q
```

```text
........................................................................ [ 47%]
........................................................................ [ 95%]
.......                                                                  [100%]
151 passed in 1.75s
```

A hundred and fifty-one tests: eight more — seven for the pallets, one
for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-05c`

### Section D — the box size: scan against take

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/string.html#format-specification-mini-language"><code>{x:>9}</code> in an f-string: <code>x</code> right-aligned in 9 characters, so columns line up</a>
</div>

Sections B and C differ in one thing: the size of the unit a take must
carry whole — 100 rows, or 2,500. So try every size. In
`src/nanolance/cli.py`, two edits:

1. Between the end of `shapes` and the `# Analogy: a customer's pick
   list` comment (around line 473), one row of the table:

   ```python
   # ──────── new code starts here (around line 473) ────────
   def costs(path: Path, row_ids: list[int]) -> str:
       """Analogy: what one warehouse costs to open, to stock-count, and to fill
       a pick list from.

       One row of the box-size table: the bytes of the metadata, then the reads
       and bytes of a scan of every column and of a take of `row_ids`, both with
       the metadata already in hand.
       """
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
           opening = f.bytes_read
       columns = list(metadata.codecs)
       with CountingFile(path) as f:
           for column in columns:
               page_file.read_column(f, metadata.codecs[column], metadata.pages[column])
           scan = f"{f.reads}, {f.bytes_read}"
       with CountingFile(path) as f:
           page_file.take(f, metadata, row_ids, columns)
           taken = f"{f.reads}, {f.bytes_read}"
       return f"{opening:>9} | {scan:>12} | {taken:>12}"


   # ──────── new code ends here ────────
   ```

2. At the end of `take` (around line 565):

   ```python
   def take(folder: Path) -> None:
       ⋮
           print(f"take from the row groups: the same rows? {rows == scanned}")
           print(f"  tally: {f.tally()}")

       # ──────── new code starts here (around line 565) ────────
       print("box size: what a scan and the pick list read, every column (reads, bytes)")
       print(f"  {'rows per box':>14} | box lists | {'scan':>12} | {'pick list':>12}")
       for rows_per_page in (10, 100, 2500, 10_000):
           path = folder / f"shop-{rows_per_page}.bin"
           page_file.write(path, tagged, rows_per_page, every_column, TAGGED_COLUMNS)
           print(f"  {rows_per_page:>14} | {costs(path, PICK_LIST)}")
       row_groups_size = f"{row_groups.ROWS_PER_GROUP} in groups"
       print(f"  {row_groups_size:>14} | {costs(groups_path, PICK_LIST)}")
       # ──────── new code ends here ────────
   ```

`costs` opens a file once for its box lists, then counts two questions
with them in hand: a scan of every column, with `read_column`, and the
pick list, with `take`. The demo writes the same table with four
[box sizes](story.md#box-size), then adds `groups.bin` as a last row.
Run it:

```bash
uv run nanolance take
```

```text
⋮ (sections A to C print their 28 lines first, unchanged)
──── new: section D's lines ────
box size: what a scan and the pick list read, every column (reads, bytes)
    rows per box | box lists |         scan |    pick list
              10 |    753278 | 5000, 238534 |     50, 2355
             100 |     77910 |  500, 185577 |    45, 16672
            2500 |      3496 |   20, 196701 |   20, 196701
           10000 |      1084 |    5, 204917 |    5, 204917
  2500 in groups |      3500 |   20, 196701 |   20, 196701
```

Read it line by line:

- `10 | 753278 | 5000, 238534 | 50, 2355` — tiny boxes: the pick list
  costs 2,355 bytes, the least of any row. But the scan takes 5,000
  reads, and the box lists weigh 753,278 bytes — three times the data
  itself. Every box packs its own lid legend and its own bit widths, so
  even the data grows, to 238,534 bytes.

- `100 | 77910 | 500, 185577 | 45, 16672` — sections A and B.

- `2500 | 3496 | 20, 196701 | 20, 196701` — boxes as big as a pallet:
  now the pick list carries every box, the same as the scan.

- `10000 | 1084 | 5, 204917 | 5, 204917` — one box per aisle: the scan
  in five reads, and the pick list in the same five.

- `2500 in groups | 3500 | 20, 196701 | 20, 196701` — the pallets,
  matching the page file of 2,500-row boxes read for read and byte for
  byte. (Their box lists differ by 4 bytes: the chunks sit at other
  offsets, and those numbers take four more digits to write.)

The last two rows hold the day's main result. **For a take, the order on
disk did not matter; the size of the unit read whole did.** A pallet is
a 2,500-row box — and so is any big box. Row groups still shape other
things a byte count cannot show here, such as how much memory a writer
needs, which is one of Lance's reasons to drop them (§5). Real Lance
keeps big pages yet escapes this cost by reading one small mini-block
inside them ([§5](#5-lance-concepts-introduced), item 2 of the "Be fair"
callout).

Pin it with tests — three edits in two files, all made by one checkout:

```bash
git checkout v1-day-05d -- tests/test_page_file.py tests/test_cli.py
```

<details>
<summary>Copy-friendly: what the three edits are, with one of the tests (click to open)</summary>

1. At the bottom of `tests/test_page_file.py`, the trade-off at the
   smallest scale — one column of 1,000 quantities, in boxes of 10 rows
   or of 1,000:

   ```python
   @pytest.mark.parametrize(
       ("rows_per_page", "scan", "take"),
       [(10, (100, 4000), (2, 2 * 40)), (1000, (1, 4000), (1, 4000))],
   )
   def test_smaller_pages_make_a_take_cheaper_and_a_scan_take_more_reads(
       tmp_path, rows_per_page, scan, take
   ):
       path = tmp_path / "pages.bin"
       page_file.write(path, many_orders(1000), rows_per_page)
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
       codec, pages = metadata.codecs["qty"], metadata.pages["qty"]
       with CountingFile(path) as f:
           page_file.read_column(f, codec, pages)
           assert (f.reads, f.bytes_read) == scan
       with CountingFile(path) as f:
           assert page_file.take(f, metadata, [5, 500], ["qty"]) == [(12,), (1,)]
           assert (f.reads, f.bytes_read) == take
   ```

2. In `tests/test_cli.py`, section C's test compared everything from
   `write groups.bin` to the end of the output; now the table follows,
   so it pins its seven lines only: `lines[start:]` becomes
   `lines[start : start + 7]`.

3. At the bottom of `tests/test_cli.py`,
   `test_take_counts_scan_and_pick_list_for_every_box_size` pins the
   seven new lines of the run above.

</details>

```bash
uv run pytest -q
```

```text
........................................................................ [ 46%]
........................................................................ [ 93%]
..........                                                               [100%]
154 passed in 7.29s
```

A hundred and fifty-four tests: three more — two for the page file, one
for the demo. The suite now takes a few seconds, not one: each of the
four `take` tests in `test_cli.py` runs the whole demo, and writing the
10-row boxes, with their 753,278 bytes of JSON, is the slow part.

**Section checkpoint:** `./scripts/compare.sh v1-day-05d` — which is
also the finished day.

## 7. Run it

```bash
uv run nanolance take
```

## 8. Expected result

```text
write shop.bin: 10000 shop orders, 100 rows per page, 263487 bytes
open it once and keep the box lists — tally: reads 2, bytes read 77910, seeks 2
the pick list, 10 row ids: [7342, 15, 9999, 2718, 404, 6001, 8123, 3141, 0, 5050]
take by scanning every column:
  row 7342: (7443, None, 4, 'gloves', [])
  row 15: (116, 15.0, 2, 'padlock', ['gift', 'fragile'])
  row 9999: (10100, 15.0, 2, 'padlock', ['gift', 'fragile'])
  row 2718: (2819, None, 4, 'gloves', [])
  row 404: (505, 23.5, 1, 'drill bits Ø6', ['fragile'])
  row 6001: (6102, 12.5, 1, 'hammer', [])
  row 8123: (8224, 7.0, 2, 'tape', [])
  row 3141: (3242, 3.25, 12, 'nails', ['bulk'])
  row 0: (101, 4.25, 3, 'bolts', ['bulk'])
  row 5050: (5151, None, 40, 'washers', ['bulk', 'small parts'])
  tally: reads 500, bytes read 185577, seeks 500
start numbers of the qty boxes: [0, 100, 200] … 9900
  row 7342: box 73, place 42
  row 15: box 0, place 15
  the whole list: 9 boxes per column, [0, 4, 27, 31, 50, 60, 73, 81, 99]
take box by box: the same rows? True
  tally: reads 45, bytes read 16672, seeks 45
write groups.bin: 4 row groups of 2500 orders, 200201 bytes
  group 0: id 0, price 3751, qty 6624, name 8500, tags 30061
  group 1: id 48855, price 52919, qty 55792, name 57668, tags 79239
open it once and keep the box lists — tally: reads 2, bytes read 3500, seeks 2
  the pick list: 4 groups, [0, 1, 2, 3]
take from the row groups: the same rows? True
  tally: reads 20, bytes read 196701, seeks 20
box size: what a scan and the pick list read, every column (reads, bytes)
    rows per box | box lists |         scan |    pick list
              10 |    753278 | 5000, 238534 |     50, 2355
             100 |     77910 |  500, 185577 |    45, 16672
            2500 |      3496 |   20, 196701 |   20, 196701
           10000 |      1084 |    5, 204917 |    5, 204917
  2500 in groups |      3500 |   20, 196701 |   20, 196701
```

The whole day in the warehouse, one stretch at a time:

- The first three lines — the shop's 10,000 orders stored, the wall card
  and box lists read once, and the pick list. (`page_file.write`,
  `read_metadata`, `PICK_LIST`.)

- `take by scanning` down to its tally — every box of every aisle,
  carried for ten orders. (`take_by_scan`.)

- The start numbers down to `take box by box` — each order's box found,
  each box carried once. (`page_starts`, `locate`, `take`.)

- `write groups.bin` down to its tally — the same pick list from the
  pallets across the street: every wrapped piece unwrapped.
  (`row_groups.write`, then `take` again.)

- The table — every box size counted twice: a stock count of every aisle,
  and the pick list. (`costs`.)

Nothing here varies between runs: no randomness, no timing, only counts.

## 9. Test it

`uv run pytest -q` now runs a hundred and fifty-four tests — the
`154 passed` of section D. That is Day 4's 124 plus 30 new ones: the
take by scanning (section A, 2 tests), start numbers and the take
(section B, 17), the pallets (section C, 8), and the box size
(section D, 3). A hundred and thirty-three are unit tests; the other
twenty-one (`test_cli_says_hello` and the twenty in `test_cli.py`) run
the real command line.

## 10. Break it deliberately

Swap one binary search for its twin. In `locate` in
`src/nanolance/page_file.py`, change one word — and import the new name
next to the old one:

```diff
@@ src/nanolance/page_file.py, around line 12 and line 308 @@
-from bisect import bisect_right
+from bisect import bisect_left, bisect_right
 ⋮
-    n = bisect_right(starts, row_id) - 1
+    n = bisect_left(starts, row_id) - 1
```

`bisect_left` counts the starts *below* a row, not at or below it. For
most rows that is the same count. For a row that is the first of its box
— row 0, 100, 200, … — it is one less. Run the tests:

```bash
uv run pytest -q --tb=line
```

```text
E   assert (-1, -200) == (0, 0)
E   IndexError: list index out of range
E   IndexError: list index out of range
E   IndexError: list index out of range
E   IndexError: list index out of range
E   IndexError: list index out of range
E   IndexError: list index out of range
```

(Only the `E` lines are shown, and four more are left out: the four demo
tests in `test_cli.py`, which fail because the demo crashed. Pytest's
summary line reads `11 failed, 143 passed`.)

- `assert (-1, -200) == (0, 0)` — the start-numbers test asks for row 0,
  the very first row, and `locate` answers box −1, place −200.

- The `IndexError` lines — every pick list that holds the first row of
  a box.

The demo shows where the −1 goes:

```bash
uv run nanolance take
```

Section A's fifteen lines print unchanged; then the new code stops
with an error:

```text
write shop.bin: 10000 shop orders, 100 rows per page, 263487 bytes
open it once and keep the box lists — tally: reads 2, bytes read 77910, seeks 2
the pick list, 10 row ids: [7342, 15, 9999, 2718, 404, 6001, 8123, 3141, 0, 5050]
take by scanning every column:
  row 7342: (7443, None, 4, 'gloves', [])
  row 15: (116, 15.0, 2, 'padlock', ['gift', 'fragile'])
  row 9999: (10100, 15.0, 2, 'padlock', ['gift', 'fragile'])
  row 2718: (2819, None, 4, 'gloves', [])
  row 404: (505, 23.5, 1, 'drill bits Ø6', ['fragile'])
  row 6001: (6102, 12.5, 1, 'hammer', [])
  row 8123: (8224, 7.0, 2, 'tape', [])
  row 3141: (3242, 3.25, 12, 'nails', ['bulk'])
  row 0: (101, 4.25, 3, 'bolts', ['bulk'])
  row 5050: (5151, None, 40, 'washers', ['bulk', 'small parts'])
  tally: reads 500, bytes read 185577, seeks 500
──── everything above: section A's output, unchanged ────
start numbers of the qty boxes: [0, 100, 200] … 9900
  row 7342: box 73, place 42
  row 15: box 0, place 15
  the whole list: 10 boxes per column, [-1, 0, 4, 27, 31, 50, 60, 73, 81, 99]
Traceback (most recent call last):
  ⋮
  File "/…/build-nano-lance-in-python/src/nanolance/page_file.py", line 334, in take
    values.append(opened[n][k])
                  ~~~~~~~~~^^^
IndexError: list index out of range
```

Box `-1` sits in the list of boxes, and Python reads `pages[-1]` as *the
last box*: the picker walks to box 99 for row 0. Only the place, −9900,
is too far for any box to hold, and that is where the error comes from.
With one box per aisle, the place would be 0, `pages[-1]` would be the
only box, and the wrong code would give the right answer. **A row that
starts a box is the edge every lookup must get right** — which is why
the start-numbers test checks the first row, the last row of a box, and
the first of the next.

Then undo the break:

1. In `locate`, change `bisect_left` back to `bisect_right`.

2. Restore the import line to `from bisect import bisect_right`.

3. Run `uv run pytest -q` and confirm it is green again.

## 11. Checkpoint

Every checkpoint is done only when the full green bar passes:

```bash
./scripts/check.sh
```

```text
32 files already formatted
All checks passed!
........................................................................ [ 46%]
........................................................................ [ 93%]
..........                                                               [100%]
154 passed in 9.28s
nanolance 0.1.0: scaffold is alive
⋮ (Day 1's `nanolance layouts` output, unchanged) ⋮
⋮ (Day 2's `nanolance pages` output, unchanged) ⋮
⋮ (Day 3's `nanolance packing` output, unchanged) ⋮
⋮ (Day 4's `nanolance shapes` output, unchanged) ⋮
⋮ (the §8 output, unchanged) ⋮
 INFO Book building has started
 INFO Running the html backend
 INFO HTML book written to `/…/build-nano-lance-in-python/book/book`
GREEN: all gates passed
```

Formatting, lints, the 154 tests, the smoke gate's five demos — now
including `nanolance take` — and the book build all pass.

The smoke gate gained one line today: `uv run --locked nanolance take
"$scratch"`. `scripts/check.sh` is course infrastructure, outside what
`compare.sh` checks; to pick up today's copy, take it from the
checkpoint:

```bash
git checkout v1-day-05 -- scripts/check.sh
```

Then close out the day in whichever mode you are following:

**Built along on your own branch?** Confirm your code matches the finished
day — the final ✓ line means it does:

```bash
./scripts/compare.sh v1-day-05
```

**Inspecting instead of typing?** Jump to today's exact finished state,
poke at it, and come back:

```bash
git switch --detach v1-day-05
uv run nanolance take
git switch -          # back to where you were
```

**Either way**, today's complete change set — docs included — reads as one
diff:

```bash
git diff v1-day-04 v1-day-05
```

## 12. Recap

**What changed today:** in `page_file.py`, a take — `take_by_scan` first,
then `page_starts`, `locate`, and `take`, which reads only the pages that
hold a requested row, each once, and returns the rows in the order
asked; `write`'s ending moved into `finish`; a new `row_groups.py` that
writes a Parquet-style file the same reader reads; the `nanolance take`
demo; and thirty new tests (154 in all), still with no dependencies.

**Deliberately naive:**

- a take always carries whole boxes, even plain ones where Day 4's
  `read_string` could fetch one value in two trips;

- boxes are read one request each, in the order the list first needs
  them, where a reader could sort them and merge neighbors into fewer
  requests;

- the box lists are read whole, and at 10 rows per box they outweigh the
  data three times over;

- and our pallets hold each chunk as one unit, without the pages and
  page index real Parquet can have.

**Five days of Part 1 (Days 1–9) are done.** Look at what the warehouse
can do now:

- **Crates or aisles (Day 1):** the same table stored both ways, with a
  tally that counts every read.

- **The wall card at the back (Day 2):** sealed boxes, box lists, and a
  file that describes itself.

- **The packer's bench (Day 3):** four packing methods, and a weigh-in
  per box.

- **Trays in the box (Day 4):** names of any length, lists, and missing
  values.

- **The pick list (Day 5):** any rows, in any order, reading only the
  boxes that hold them — and a count of what pallets would cost instead.

That is the heart of a columnar file format — layout, encodings,
variable-length values, missing values, and random access — in about
1,070 lines of format code, comments included, with 154 tests
and no dependencies. Tonight the picker leaves with a pick list filled,
nine boxes per aisle carried and not one more — see
[the warehouse](story.md).

**This is where the free book ends.** Days 6 to 17 — tables and their
versions, indexes, and the database on top — are the Pro edition. The
free book ends on something real: a working file format you built by
hand, every cost in it counted. If you would like to keep going — a
table of many files that remembers every version, indexes that let
filters and vector searches read less, and a small LanceDB-style
database — that is the Pro edition. The Pro edition is still being
written; star or watch the repository to hear when it launches — the
README will say. Either way, thank you for building this far.

**What the Pro edition does next (Day 6):** everything still lives in
one file, written once. A real table grows: new rows arrive while
readers are reading, and yesterday's version must stay readable. Day 6,
*The table*, stores a table as many files plus a small record of each
version — Lance calls it a *manifest* — so a reader can open the table
as it was yesterday. In the warehouse, each new file arrives as a
**delivery**, and a **ledger** — Lance's manifest — records which
deliveries made up the stock at every version.
