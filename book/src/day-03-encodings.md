# Day 3: Encodings

> **Day 3** (of Days 0–17) · builds on `v1-day-02` · ≈ 2 h

| Section | Builds | Checkpoint |
|---------|--------|------------|
| A | What a page holds: the same few values, every one full size | `v1-day-03a` |
| B | Dictionaries, and a page that names its encoding | `v1-day-03b` |
| C | Run-length, and where it backfires | `v1-day-03c` |
| D | Bit-packing, the smallest encoding per page, and bytes read | `v1-day-03d` = `v1-day-03` |

**Pick your mode before starting** (explained fully in
[Setup](setup.md#4-choose-how-you-follow-along)):

```bash
# Build mode — type today's code yourself, on your own branch:
git switch -c my-course v1-day-02      # or keep going on yesterday's branch

# Inspect mode — read along with the finished code instead:
git switch --detach v1-day-03a         # then 03b, 03c, 03d as you pass each section
```

<div class="callout">

**Today's typing budget** — so nothing sneaks up on you:

| Section | The learning | Wiring & tests (copy-friendly) |
|---------|--------------|--------------------------------|
| A | `describe` · ~12 lines | the `packing` demo (~22 lines), 2 imports, 2 edits in `main`, 1 test |
| B1 | a new `encodings.py`: `split`, `plain`, `dictionary`, their decoders, `ENCODINGS`, `encode`, `decode` · ~95 lines, docstrings included | — |
| B2 | in `page_file.py`: `Page.encoding`, `plain_pages`, the new `write` and `read_page`, version 2 · ~50 lines | `every_way`, `write_and_read_back` (~40 lines), 3 demo lines, a new test file and test edits — 20 tests |
| C | `run_length` + `from_run_length` · ~25 lines | 3 demo lines, 9 tests |
| D | `whole_numbers`, `bit_packed`, `from_bit_packed`, `smallest` · ~55 lines; the `"smallest"` choice in `write` · 4 lines | `packing_notes`, `ask_qty` (~25 lines), demo lines, 17 tests |

Four sections are four natural sittings, and every checkpoint is a save
point — nothing says a "day" must fit in one. Today still needs **no
dependencies**: `itertools` and `collections` come with Python.

</div>

> **Short on time?** Sections A–B are the core: the problem, the first
> encoding, and the format change it forces. C and D each add one
> encoding and can be a second sitting.

## 1. What you will have running

By the end of today, `uv run nanolance packing` stores the same thousand
orders as yesterday in **fewer bytes** — and proves that every value
comes back exactly. Yesterday's pages give every value its full fixed
width: a quantity of 3 takes four bytes, and a page of a hundred item
names holds the same eight names over and over, each one padded to 12
bytes. Today each page can be stored in one of four **encodings** —
plain (yesterday's way), dictionary, run-length, or bit-packed — and
records which one, so a reader decodes it correctly.

The demo prints, for every column, the bytes each encoding would take —
including the cases where an encoding makes a page *bigger* — and then
lets each page pick its smallest. Last, it asks yesterday's two
questions again and counts what fewer bytes on disk buys: fewer bytes
read.

<div class="dl-concepts"><span>Lance concepts used here:</span>
<a href="https://lance.org/format/file/encoding/">Lance's encoding strategy: dictionary, run-length, bitpacking, and more ↗</a>
<a href="https://parquet.apache.org/docs/file-format/data-pages/encodings/">Parquet's encodings: plain, dictionary, RLE/bit-packing ↗</a>
<a href="https://www.cs.umd.edu/~abadi/papers/abadisigmod06.pdf">Integrating Compression and Execution in Column-Oriented Database Systems (Abadi et al., SIGMOD 2006) ↗</a>
<a href="https://en.wikipedia.org/wiki/Run-length_encoding">run-length encoding (Wikipedia) ↗</a>
</div>

## 2. What you will be seeing in the output

A sneak peek at the end of the day — a few lines of it; section 8 has
all of it. If a note doesn't land yet, that's fine; the rest of the day
builds every piece:

```text
every column packed every way, orders as placed (bytes, all pages):
  id: plain 8000, dictionary 9040, run-length 12000, bit-packed 1212
  price: plain 8000, dictionary 1680, run-length 12000, bit-packed —
  qty: plain 4000, dictionary 1280, run-length 8000, bit-packed 760
  name: plain 12000, dictionary 2000, run-length 16000, bit-packed —
⋮
write smallest.bin: 8320 bytes, pages 5652 (plain: 32000)
  read back, told nothing: same as the table? True
  chosen: id bit-packed ×10, price dictionary ×10, qty bit-packed ×10, name dictionary ×10
⋮
sum(qty) from plain.bin, told nothing = 8125
  tally: reads 12, bytes read 6522, seeks 12 (opening 2522, pages 4000)
sum(qty) from smallest.bin, told nothing = 8125
  tally: reads 12, bytes read 3428, seeks 12 (opening 2668, pages 760)
```

- `every column packed every way` and the four lines under it — each
  column stored each of the four ways, in bytes. Names shrink from 12000
  bytes to 2000 with a dictionary; quantities from 4000 to 760 when
  bit-packed. Some ways make things worse: run-length *grows* every
  column here, and `—` means a way cannot store that kind of value.

- `write smallest.bin` and `chosen:` — a file where each page picked its
  own smallest way: 5652 bytes of pages instead of 32000.

- The last four lines — yesterday's first question, adding up every
  quantity, asked of a plain file and of the smallest one. The same
  answer, for 760 bytes of pages instead of 4000.

## 3. Why we need it

A quantity of 3 takes four bytes. A page of names spends 1200 bytes
saying eight names. That is yesterday's file: every value at its full
fixed width, as yesterday's recap promised we would fix. The largest
quantity, 40, fits in 6 bits and is stored in 32. The table is small and
predictable on purpose, but real columns look like this too: a status
with five possible values, a country code, a timestamp that grows
slowly, a label column sorted by label.

Fewer bytes matter twice. They are less to store, and — the part this
course measures — less to *read*. Every byte a page does not hold is a
byte no question ever has to read.

But encoding a page raises two questions the rest of the day answers:

- **How does a reader know how a page was encoded?** Different pages
  may be stored differently, so the file has to say which way each page
  went — and that changes the format.

- **How do you know nothing was lost?** An encoded page is only useful
  if decoding it gives back exactly the bytes that went in. Every
  encoding today gets a round-trip proof.

**The story so far — remember [the warehouse](story.md):** the orders
sit in [aisles](story.md#column-layout) cut into
[sealed boxes](story.md#pages); [box lists](story.md#box-list) and
[the wall card](story.md#wall-card) at the back tell a picker who knows
nothing where every box is, and [the tally](story.md#tally) counts every
trip. Today's scene is **the packer's bench**. The picker carries boxes
*out* to answer questions; **the packer** is the one who fills them in
the first place — until today by Day 1's
[packing rule](story.md#packing-rule), every value in a full-size
compartment. Today the packer learns new ways to pack a box, notes on the
box list how each box was packed, and weighs every packing to keep the
lightest. Section A looks inside the boxes; B, C, and D each bring one
new way of packing.

## 4. Mental model

Walk the packer's bench, one station per section:

- **Looking inside (section A).** The first box of each aisle, counted:
  how many different values, the longest run of equal neighbors, and how
  many bits the largest whole number needs. Every count says the box is
  emptier than its bytes.

- **[The lid legend](story.md#lid-legend) (section B)** — dictionary
  encoding. A box of 100 names, 8 of them different: the 8 names once on
  the lid (96 bytes), a count, and 100 one-byte legend numbers inside.
  200 bytes instead of 1200.

- **[The packing note](story.md#packing-note) (section B)** — each
  page's encoding, recorded. Each box's line on the box list now says
  how the box was packed. That is a new edition of the format, so the
  stamp's version goes from 1 to 2.

- **[Stacks](story.md#stacks) (section C)** — run-length encoding. A box
  of 100 identical names: one name and a count of 100. A box where no
  two neighbors match: every name gets a count of 1, and the box doubles.

- **[Snug compartments](story.md#snug-compartments) (section D)** —
  bit-packing. A box of quantities whose largest is 40: every quantity
  in 6 bits instead of 32.

- **[The weigh-in](story.md#weigh-in) (section D)** — the smallest
  encoding per page. The packer packs each box all four ways, weighs
  each packing, and keeps the lightest. `"smallest"` is not a fifth
  encoding: it is an instruction to the writer to run the weigh-in for
  every page of a column and record whichever encoding won, so pages of
  one column can be encoded differently.

Here is one box — the first 100 quantities, as placed — encoded each of
the four ways (every number is a byte count you will see the code
produce):

```text
plain        100 values × 4 bytes                         = 400 bytes
dictionary   4 (count) + 6 values × 4 + 100 codes × 1     = 128 bytes
run-length   100 runs × (4-byte value + 4-byte length)     = 800 bytes
bit-packed   1 (width = 6) + 100 values × 6 bits = 75     =  76 bytes
```

And here is how a picker who knows nothing reads that box from section
D's `smallest.bin`, where it is bit-packed, step by step down the page:

```text
the wall card          where the box lists are; version 2; stamp NLNC
    │ read the box lists
    ▼
the qty box list       box 0: offset 2892, size 76, 100 rows, encoding "bit-packed"
    │ seek to 2892, read 76 bytes
    ▼
the encoded box        1 byte saying "6 bits each", then 75 bytes of bits
    │ decode by the packing note
    ▼
the plain box          400 bytes: 100 quantities at 4 bytes each, exactly as written
    │ cut into values, as on Day 2
    ▼
the answer             100 quantities, for 76 bytes read instead of 400
```

The decode step is the only new one: everything after it is yesterday's
reader, unchanged.

## 5. Lance concepts introduced

- **Encodings.** An encoding is a reversible way to store a run of
  values in other bytes. Lance's documentation draws the same line we
  draw today: the *data type* says what the values mean, the *encoding*
  says how they sit in bytes — "An integer array might be encoded into
  two completely different layouts which represent the same data." Our
  encoders never look at what a value means; they see fixed-width pieces
  of bytes, except bit-packing, which needs whole numbers.

- **Plain is the fallback.** Parquet's documentation calls plain the
  encoding that "is used whenever a more efficient encoding cannot be
  used." Ours too: a column nobody asks to encode stays plain, and a
  tie goes to plain.

- **Each page records its encoding — and the format version moves.**
  Encodings are chosen per page, so the column metadata says, for every
  page, how to decode it; Lance's docs note that "the encoding strategy
  tends to evolve more quickly than the file format itself." Recording
  it changes what a file means, so the version goes up. Our reader reads
  both versions; a reader that only knows version 1 refuses a version 2
  file instead of misreading it. Section B runs both directions.

<div class="callout">

**Where real Lance does more.** Many more encodings — FSST for strings,
byte-stream-split and ALP for floats, delta and constant pages — and
general compression (LZ4, zstd) that "is applied on top of other
encoding techniques (RLE, BSS, bitpacking, etc.)". In Parquet, a
dictionary's codes are themselves stored with run-length/bit-packing.
And no trying of everything: Lance decides from cheap statistics. It
applies run-length encoding "if the number of runs is less than half the
number of values", and a dictionary only when the distinct values fit a
budget (by default half the number of values) and the estimated result
is under 80% of plain. When used in a mini-block context, its
bit-packing works on blocks of 1024 values with the bit width stored
inline in each block — like our one-byte width at the start of a page.
All of it is in the [encoding strategy](https://lance.org/format/file/encoding/)
page.

</div>

## 6. Build it, section by section

### Section A — what a page holds: the same few values, every one full size

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/itertools.html#itertools.groupby"><code>itertools.groupby</code>: groups equal neighbors into runs</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#sets"><code>set</code>: a collection that keeps each value once</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#int.bit_length"><code>int.bit_length</code>: how many bits a whole number needs</a>
<a href="https://docs.python.org/3.12/howto/sorting.html#key-functions"><code>sorted(…, key=…)</code>: sort by one part of each element</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#lambda-expressions"><code>lambda</code>: a one-line function without a name</a>
<a href="https://docs.python.org/3.12/library/functions.html#len"><code>len(list(run))</code>: count the elements a run yields</a>
</div>

Before encoding anything, count what the boxes hold. You need a small
measuring function and a new demo. In `src/nanolance/cli.py`, five
edits:

1. Below `import argparse` (line 3), add

   ```python
   from itertools import groupby
   ```

2. Below the `from nanolance.orders import …` line (line 8), add

   ```python
   from nanolance.page_file import ROWS_PER_PAGE
   ```

3. Between the end of `pages` and `def main` (around line 147), the
   measuring function and the demo:

   ```python
   # ──────── new code starts here (around line 147) ────────
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


   # ──────── new code ends here ────────
   ```

4. In `main`, register the new subcommand, after the `pages` one
   (around line 195):

   ```python
       demo = demos.add_parser("pages", help="store one table as pages with a footer")
       demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
       # ──────── new code starts here (around line 195) ────────
       demo = demos.add_parser("packing", help="pack each page in fewer bytes")
       demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
       # ──────── new code ends here ────────
       args = parser.parse_args()
   ```

5. And run it, after the `pages` branch (around line 203):

   ```python
       elif args.demo == "pages":
           pages(args.folder)
       # ──────── new code starts here (around line 203) ────────
       elif args.demo == "packing":
           packing(args.folder)
       # ──────── new code ends here ────────
       else:
   ```

What the new code does:

- `describe` measures one page three ways: `groupby` groups runs of
  equal neighbors (`[2, 2, 5]` is a run of two 2s, then one 5), a `set`
  keeps each value once, and `bit_length()` says how many bits a whole
  number needs — 40 is `101000`, so 6.

- `packing` describes the first page of every column twice: for the
  thousand orders, and for the same orders sorted by name
  (`key=lambda row: row[3]`). "Plain" is today's name for yesterday's
  way of storing a page: every value at its column's full width.

Run it:

```bash
uv run nanolance packing
```

```text
the orders table: 1000 rows × 4 columns (id, price, qty, name), 100 rows per page
the first page of each column, orders as placed:
  id: 800 bytes plain — 100 distinct, longest run 1, largest 200 needs 8 bits
  price: 800 bytes plain — 8 distinct, longest run 1
  qty: 400 bytes plain — 6 distinct, longest run 1, largest 40 needs 6 bits
  name: 1200 bytes plain — 8 distinct, longest run 1
the first page of each column, orders sorted by name:
  id: 800 bytes plain — 100 distinct, longest run 1, largest 893 needs 10 bits
  price: 800 bytes plain — 1 distinct, longest run 100
  qty: 400 bytes plain — 1 distinct, longest run 100, largest 3 needs 2 bits
  name: 1200 bytes plain — 1 distinct, longest run 100
```

Read it line by line:

- `the orders table: … 100 rows per page` — the header from `packing`:
  yesterday's thousand orders, in [boxes](story.md#pages) of 100.

- `id: 800 bytes plain — 100 distinct, longest run 1, largest 200 needs
  8 bits` — `describe` on the first id page. Every id is different, so
  there is nothing to share; but the largest, 200, needs 8 bits, and
  each id spends 64.

- `price: 800 bytes plain — 8 distinct` — a hundred prices, only 8
  different ones. `describe` prints no bit count for prices: they are
  not whole numbers.

- `qty: 400 bytes plain — 6 distinct, …, largest 40 needs 6 bits` — six
  different quantities (two of the eight orders share a quantity of 1,
  and two share 2), and none needs more than 6 of its 32 bits.

- `name: 1200 bytes plain — 8 distinct, longest run 1` — eight names,
  said a hundred times. Written once each, they would take 8 × 12 = 96
  bytes.

- The five lines for the orders sorted by name — the first page now
  holds only `bolts` orders: one price, one quantity, one name, each
  repeated 100 times in a single run. The ids stay all different, every
  eighth id from 101 up to 893.

Every line says the same thing: the box is much emptier than its bytes.
Sections B to D each turn one of these counts into saved bytes — the
distinct values, the runs, and the bits.

Pin the demo with a test. At the bottom of `tests/test_cli.py` (around
line 119), a helper that runs the new demo and a test of its first
eleven lines:

```python
# ──────── new code starts here (around line 119) ────────
def run_packing(folder):
    result = subprocess.run(
        [sys.executable, "-m", "nanolance", "packing", str(folder)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def test_packing_shows_what_each_first_page_holds(tmp_path):
    lines = run_packing(tmp_path)
    assert lines[:11] == [
        "the orders table: 1000 rows × 4 columns (id, price, qty, name), "
        "100 rows per page",
        "the first page of each column, orders as placed:",
        "  id: 800 bytes plain — 100 distinct, longest run 1, largest 200 needs 8 bits",
        "  price: 800 bytes plain — 8 distinct, longest run 1",
        "  qty: 400 bytes plain — 6 distinct, longest run 1, largest 40 needs 6 bits",
        "  name: 1200 bytes plain — 8 distinct, longest run 1",
        "the first page of each column, orders sorted by name:",
        "  id: 800 bytes plain — 100 distinct, longest run 1, "
        "largest 893 needs 10 bits",
        "  price: 800 bytes plain — 1 distinct, longest run 100",
        "  qty: 400 bytes plain — 1 distinct, longest run 100, largest 3 needs 2 bits",
        "  name: 1200 bytes plain — 1 distinct, longest run 100",
    ]


# ──────── new code ends here ────────
```

```bash
uv run pytest -q
```

```text
.........................................                                [100%]
41 passed in 0.36s
```

Forty-one tests: yesterday's 40 and the new one.

**Section checkpoint:** `./scripts/compare.sh v1-day-03a`

### Section B — the lid legend: a dictionary, and a page that names its encoding

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/stdtypes.html#dict.fromkeys"><code>dict.fromkeys</code>: a dict of a list's distinct values, in first-seen order</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#bytes-objects"><code>bytes(numbers)</code> and indexing <code>bytes</code>: a byte is a number from 0 to 255</a>
<a href="https://docs.python.org/3.12/library/collections.abc.html#collections.abc.Callable"><code>Callable</code>: the type of a function, by its arguments and result</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#defining-functions">functions are values: they can sit in a dict and be called from it</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#dict.get"><code>dict.get(key, default)</code>: the value, or <code>default</code> when the key is missing</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#iterator-types">iterating a dict: <code>for name in ENCODINGS</code> walks its keys</a>
<a href="https://docs.python.org/3.12/library/dataclasses.html#dataclasses.field">dataclass field defaults: <code>encoding: str = "plain"</code></a>
<a href="https://docs.python.org/3.12/reference/expressions.html#boolean-operations"><code>x or {}</code>: <code>x</code>, or <code>{}</code> when <code>x</code> is <code>None</code></a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#numeric-types-int-float-complex"><code>//</code>: division rounded down to a whole number</a>
<a href="https://docs.python.org/3.12/reference/expressions.html#comparisons">chained comparisons: <code>1 &lt;= version &lt;= VERSION</code></a>
<a href="https://docs.python.org/3.12/library/functions.html#zip"><code>zip(*columns, strict=True)</code>: columns into rows, refusing unequal lengths</a>
<a href="https://docs.python.org/3.12/library/sys.html#sys.path"><code>sys.path.insert</code>: one more folder Python imports from</a>
<a href="https://docs.pytest.org/en/stable/how-to/parametrize.html"><code>@pytest.mark.parametrize</code>: runs one test once per value; <code>ids=</code> names each run</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#the-del-statement"><code>del</code>: removes a key from a dict</a>
</div>

Start with the name column: eight names said a hundred times. A
dictionary stores each distinct value once and replaces every value with
a small code — its position in that list. Today's codes are one byte
each, so a page may hold up to 256 distinct values.

Every [encoding](story.md#encodings) needs two halves: an **encoder**,
which turns a page's plain bytes into stored bytes, and a **decoder**,
which turns them back. Create `src/nanolance/encodings.py`, beginning
with the plain encoding, which is yesterday's way given a name:

```python
"""Analogy: the ways a packer can fill one box — each turns the box's plain
contents into fewer bytes, and back again exactly.

Page encodings. Every encoder takes one page's PLAIN bytes (the values
packed back to back at the column's fixed width, as Day 2 stored them) and
returns encoded bytes; every decoder turns those bytes back into the very
same plain bytes. The encodings never need to know what the values mean.
"""

import struct
from collections.abc import Callable

# A 4-byte count, stored inside a page: how many distinct values a
# dictionary page holds.
COUNT = struct.Struct("<I")
# Dictionary codes are one byte each, so a dictionary holds at most 256 values.
MAX_DICTIONARY = 256


def split(codec: struct.Struct, data: bytes) -> list[bytes]:
    """Cut plain page bytes into one fixed-width piece per value."""
    return [data[k : k + codec.size] for k in range(0, len(data), codec.size)]


def plain(codec: struct.Struct, data: bytes) -> bytes:
    """Analogy: full-size compartments — the box packed as Day 2 packed it.

    The plain encoding stores the plain bytes unchanged.
    """
    return data


def from_plain(codec: struct.Struct, raw: bytes, rows: int) -> bytes:
    """Decode a plain page: its bytes already are the plain bytes."""
    return raw
```

- The module works on **plain bytes**: one page's values back to back at
  the column's width, the bytes Day 2 wrote. An encoder never sees
  Python values, only pieces of bytes, so every round-trip proof is byte
  for byte.

- Every decoder takes the same three arguments — the codec, the stored
  bytes, and the page's row count — so any decoder can be called the
  same way. The row count goes unused until section D's bit-packing.

Then the dictionary, below `from_plain` in the same file:

```python
def dictionary(codec: struct.Struct, data: bytes) -> bytes:
    """Analogy: the lid legend — every distinct value written once on the
    lid, and inside the box one small legend number per value.

    Layout: COUNT (how many distinct values), the distinct values at the
    column's width in first-seen order, then one 1-byte code per value.
    """
    values = split(codec, data)
    legend = list(dict.fromkeys(values))  # distinct, in first-seen order
    if len(legend) > MAX_DICTIONARY:
        raise ValueError(
            f"a dictionary holds at most {MAX_DICTIONARY} values; "
            f"this page has {len(legend)}"
        )
    code_of = {value: code for code, value in enumerate(legend)}
    codes = bytes(code_of[value] for value in values)
    return COUNT.pack(len(legend)) + b"".join(legend) + codes


def from_dictionary(codec: struct.Struct, raw: bytes, rows: int) -> bytes:
    """Decode a dictionary page: look every code up in the legend."""
    (count,) = COUNT.unpack(raw[: COUNT.size])
    codes_start = COUNT.size + count * codec.size
    legend = split(codec, raw[COUNT.size : codes_start])
    return b"".join(legend[code] for code in raw[codes_start:])
```

- `dict.fromkeys(values)` keeps the distinct values in first-seen order:
  the legend. `code_of` maps each to its position, and `bytes(…)` stores
  those positions — numbers from 0 to 255 — one byte each. More than 256
  distinct values cannot be numbered in a byte, so the encoder refuses.

- The page is three parts back to back: the count, the legend, the
  codes. For 100 names with 8 distinct: 4 + 96 + 100 = 200 bytes.
  Iterating over `bytes` gives numbers, so `from_dictionary` walks the
  codes and looks each one up.

Last in the file, the table of encodings and the two functions everyone
else calls:

```python
Encoder = Callable[[struct.Struct, bytes], bytes]
Decoder = Callable[[struct.Struct, bytes, int], bytes]

# Every encoding by the name the metadata records, in the order a packer
# tries them.
ENCODINGS: dict[str, tuple[Encoder, Decoder]] = {
    "plain": (plain, from_plain),
    "dictionary": (dictionary, from_dictionary),
}


def encode(name: str, codec: struct.Struct, data: bytes) -> bytes:
    """Encode one page's plain bytes with the encoding called `name`."""
    encoder, _ = ENCODINGS[name]
    return encoder(codec, data)


def decode(name: str, codec: struct.Struct, raw: bytes, rows: int) -> bytes:
    """Decode one page's stored bytes back to its plain bytes."""
    _, decoder = ENCODINGS[name]
    return decoder(codec, raw, rows)
```

`ENCODINGS` maps each name to its encoder and decoder — functions sit in
a dict like any other value. Sections C and D each add one line here.

Now the page file has to use them — and record which encoding each page
uses. Five edits in `src/nanolance/page_file.py`:

1. Import the new module, above the other `nanolance` imports (line 16):

   ```python
   from nanolance import encodings
   ```

2. Raise the format version (line 28):

   ```python
   VERSION = 2  # 2: every page records its encoding
   ```

3. Replace the `Page` class (lines 31–42) with this one — a fourth field,
   with a default:

   ```python
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
   ```

4. Replace `write` and `read_page` — lines 60–106, from `def write(`
   through `read_page`'s `return values` — with this block: a new
   `plain_pages`, then `write` with an `encoding` choice, and `read_page`
   with one decoding line. The metadata and footer code inside `write` is
   unchanged; `read_column` and `read_rows` below it stay as they are:

   ```python
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
       column it leaves out is stored plain). Returns every column's pages."""
       chosen = encoding or {}
       pages: dict[str, list[Page]] = {}
       with open(path, "wb") as out:
           for column, codec in COLUMNS.items():
               pages[column] = []
               name = chosen.get(column, "plain")
               for plain in plain_pages(rows, column, rows_per_page):
                   data = encodings.encode(name, codec, plain)
                   n_rows = len(plain) // codec.size
                   page = Page(
                       offset=out.tell(), size=len(data), rows=n_rows, encoding=name
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
   ```

5. In `read_metadata`, two replacements: its docstring (lines 136–143,
   now around line 168) says which versions it reads, and the version
   check (lines 154–157, now around line 187) accepts versions 1 to
   `VERSION`. The `def` line and the `⋮` are already in your file:

   ```python
   def read_metadata(f: CountingFile) -> Metadata:
       # ──────── replacement starts here (around line 168) ────────
       """Analogy: walk to the back wall, read the wall card, then the box
       lists it points to.

       Two seeks and two reads: the footer (the file's last FOOTER.size
       bytes), then the column metadata at the offset the footer gives. A file
       without the magic bytes, of a version this reader does not know, or whose
       footer points outside the file is refused with a ValueError before the
       second read. Version 1 files read as files whose pages are all plain.
       """
       # ──────── replacement ends here ────────
       ⋮
       # ──────── replacement starts here (around line 187) ────────
       if not 1 <= version <= VERSION:
           raise ValueError(
               f"nanolance file version {version}; "
               f"this reader reads versions 1 to {VERSION}"
           )
       # ──────── replacement ends here ────────
   ```

What changed, and why:

- `Page.encoding` is the [packing note](story.md#packing-note): the name
  of the encoding the page's bytes are stored in. `json.dumps` already
  writes every field of a `Page`, so the note lands in the metadata, and
  `Page(**page)` reads it back.

- `plain_pages` is yesterday's inner loop, moved out so the demo can use
  it too. `write` encodes each plain page with the column's chosen
  encoding; `chosen.get(column, "plain")` stores any column not named in
  plain.

- `read_page` reads the stored bytes as before, and `encodings.decode`
  turns them back into plain bytes; the rest is yesterday's code.

- **The version.** A version 1 file has no `encoding` in its metadata,
  so `Page`'s default, `"plain"`, reads it correctly: the default *is*
  the migration. The reader accepts versions 1 and 2; the writer always
  writes 2.

Prove that last claim before anything overwrites the evidence:
yesterday's demo left a version 1 `pages.bin` in `warehouse/`. Read it
with today's reader — `uv run python -` runs the lines that follow, up
to `EOF`:

```bash
uv run python - <<'EOF'
from pathlib import Path

from nanolance import page_file
from nanolance.counting import CountingFile

with CountingFile(Path("warehouse/pages.bin")) as f:
    metadata = page_file.read_metadata(f)
    qty = page_file.read_column(f, metadata.codecs["qty"], metadata.pages["qty"])
print(metadata.version)
print(sum(qty))
EOF
```

```text
1
8125
```

A version 1 file, read in full by today's reader: the same 8125 as
yesterday. Now re-run yesterday's demo, which rewrites `pages.bin` as
version 2:

```bash
uv run nanolance pages
```

```text
⋮ (the first twelve lines, unchanged)
write pages.bin: 34522 bytes, each column cut into pages
⋮ (the page lines and two questions, unchanged)
open pages.bin: version 2, 1000 rows, columns id, price, qty, name, 40 pages
  tally: reads 2, bytes read 2522, seeks 2
sum(qty) from pages.bin, told nothing = 8125
  tally: reads 12, bytes read 6522, seeks 12
qty of rows 10–19 from pages.bin, told nothing = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 3, bytes read 2922, seeks 3
⋮ (the refusal, unchanged)
```

The answers and the pages are the same; the version and four numbers
moved. `pages.bin` is 760 bytes bigger (34522 instead of 33762), because
each of the 40 lines of [box lists](story.md#box-list) now ends with
`,"encoding":"plain"` — 19 bytes, 40 times — and the opening reads them:
2522 instead of 1762. Yesterday's tests pin the old numbers; the test
edits below update them.

Now the demo. In `src/nanolance/cli.py`, four edits:

1. The `from nanolance import` line (line 7) gains `encodings`:

   ```python
   from nanolance import __version__, column_layout, encodings, page_file, row_layout
   ```

2. The `from nanolance.orders import` line (line 9) gains `Row`:

   ```python
   from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH, Row, many_orders
   ```

3. Between `describe` and `packing` (around line 162), two helpers:

   ```python
   # ──────── new code starts here (around line 162) ────────
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


   # ──────── new code ends here ────────
   ```

4. At the end of `packing` (around line 226), after the loop:

   ```python
       # ──────── new code starts here (around line 226) ────────
       every_way("as placed", orders)
       in_dictionaries = {"price": "dictionary", "qty": "dictionary", "name": "dictionary"}
       write_and_read_back(folder / "dictionary.bin", orders, in_dictionaries)
       # ──────── new code ends here ────────
   ```

- `every_way` encodes each column's pages with every encoding in
  `ENCODINGS` and prints the total bytes; an encoding that refuses
  (`ValueError`) prints `—`. Because it walks `ENCODINGS`, every encoding
  you register later shows up in this table on its own.

- `write_and_read_back` writes a real file, prints its size and its
  pages' share, then reads every column back through the metadata
  alone; `zip(*columns, strict=True)` turns the columns back into rows.
  The demo stores price, qty, and name as dictionaries and leaves id
  plain — the first table line says why.

Run it:

```bash
uv run nanolance packing
```

```text
⋮ (section A's eleven lines print first, unchanged)
──── new: section B's lines ────
every column packed every way, orders as placed (bytes, all pages):
  id: plain 8000, dictionary 9040
  price: plain 8000, dictionary 1680
  qty: plain 4000, dictionary 1280
  name: plain 12000, dictionary 2000
write dictionary.bin: 15612 bytes, pages 12960 (plain: 32000)
  read back, told nothing: same as the table? True
```

Read it line by line:

- `id: plain 8000, dictionary 9040` — `every_way` on the id column, and
  the first time an encoding makes things worse. Every id on a page is
  different, so the legend holds all 100 (800 bytes), plus the count and
  100 codes: 904 per page.

- `price: plain 8000, dictionary 1680` — 8 distinct prices: 4 + 64 +
  100 = 168 bytes per page, about a fifth of plain.

- `qty: plain 4000, dictionary 1280` — 6 distinct quantities: 4 + 24 +
  100 = 128 per page.

- `name: plain 12000, dictionary 2000` — the
  [lid legend](story.md#lid-legend)'s best case: 200 per page, a sixth
  of plain.

- `write dictionary.bin: 15612 bytes, pages 12960 (plain: 32000)` —
  `write_and_read_back`: 8000 + 1680 + 1280 + 2000 = 12960 bytes of
  pages, then the metadata and the 24-byte footer.

- `read back, told nothing: same as the table? True` — a reader that
  knew only the file decoded every page by its packing note and got all
  thousand orders back.

Now the other direction: a reader that only knows version 1 has no idea
pages can be dictionaries, and would read a legend and codes as if they
were quantities. Git can print a file as it was at any checkpoint, so
save Day 2's `page_file.py` next to the warehouse files and point it at
`dictionary.bin`:

```bash
git show v1-day-02:src/nanolance/page_file.py > warehouse/day2_page_file.py
uv run python - <<'EOF'
import sys
from pathlib import Path

sys.path.insert(0, "warehouse")
import day2_page_file
from nanolance.counting import CountingFile

day2_page_file.read_metadata(CountingFile(Path("warehouse/dictionary.bin")))
EOF
```

```text
Traceback (most recent call last):
  File "<stdin>", line 8, in <module>
  File "/…/build-nano-lance-in-python/warehouse/day2_page_file.py", line 155, in read_metadata
    raise ValueError(
ValueError: nanolance file version 2; this reader reads version 1
```

Yesterday's reader read the wall card, saw edition 2, and
[turned around](story.md#stamp) — exactly what Day 2's version check was
for. Compatibility runs one way: a new reader reads old files, and an
old reader refuses new ones instead of misreading them.

Pin it all with tests — six edits in three files:

<details>
<summary>Copy-friendly: the tests (click to open)</summary>

1. Create `tests/test_encodings.py`:

   ```python
   import pytest

   from nanolance import encodings
   from nanolance.encodings import COUNT
   from nanolance.orders import COLUMNS, many_orders, pack_value


   def plain_bytes(column, values):
       return b"".join(pack_value(column, value) for value in values)


   def round_trip(name, column, values):
       codec = COLUMNS[column]
       data = plain_bytes(column, values)
       raw = encodings.encode(name, codec, data)
       assert encodings.decode(name, codec, raw, len(values)) == data
       return raw


   QTY_PAGES = {
       "an empty page": [],
       "one value": [7],
       "all equal": [2] * 100,
       "the widest value": [0, 2**31 - 1, 5],
       "a page of orders": [row[2] for row in many_orders(100)],
   }


   @pytest.mark.parametrize("values", QTY_PAGES.values(), ids=QTY_PAGES.keys())
   @pytest.mark.parametrize("name", encodings.ENCODINGS)
   def test_every_encoding_gives_back_exactly_what_went_in(name, values):
       round_trip(name, "qty", values)


   @pytest.mark.parametrize("name", ["plain", "dictionary"])
   def test_text_and_floats_round_trip_too(name):
       orders = many_orders(100)
       round_trip(name, "name", [row[3] for row in orders])
       round_trip(name, "price", [row[1] for row in orders])


   def test_plain_stores_the_plain_bytes_unchanged():
       assert round_trip("plain", "qty", [3, 1, 40]) == plain_bytes("qty", [3, 1, 40])


   def test_a_dictionary_stores_each_distinct_value_once_and_one_byte_codes():
       raw = round_trip("dictionary", "name", ["tape", "bolts", "tape", "tape"])
       legend = plain_bytes("name", ["tape", "bolts"])
       assert raw == COUNT.pack(2) + legend + bytes([0, 1, 0, 0])


   def test_a_dictionary_of_all_distinct_values_is_larger_than_plain():
       ids = list(range(101, 201))
       assert len(round_trip("dictionary", "id", ids)) == 4 + 800 + 100  # plain: 800


   def test_a_dictionary_holds_at_most_256_distinct_values():
       round_trip("dictionary", "qty", list(range(256)))
       with pytest.raises(ValueError, match="at most 256 values; this page has 257"):
           round_trip("dictionary", "qty", list(range(257)))
   ```

2. In `tests/test_cli.py`, `test_pages_opens_the_file_from_its_footer`
   (lines 96–110) expects yesterday's numbers. Change `33762` to `34522`,
   `version 1` to `version 2` (twice), and the three tallies' bytes read
   from `1762`, `5762`, and `2162` to `2522`, `6522`, and `2922`.

3. In `tests/test_page_file.py`, the imports (lines 1–6) gain `json`:

   ```python
   import json

   import pytest
   ```

4. In `tests/test_page_file.py`, `test_another_version_is_refused`
   (lines 112–119) used version 2 as "another version" — which is now
   ours. Replace its last three lines (117–119) with version 3:

   ```python
   def test_another_version_is_refused(tmp_path):
       ⋮
       path.write_bytes(data[: -FOOTER.size] + FOOTER.pack(offset, size, 3, MAGIC))
       with pytest.raises(
           ValueError, match="version 3; this reader reads versions 1 to 2"
       ):
           open_metadata(path)
   ```

5. In `tests/test_page_file.py`, at the bottom (around line 129), three
   tests:

   ```python
   # ──────── new code starts here (around line 129) ────────
   def test_each_page_records_its_encoding(tmp_path):
       path = tmp_path / "pages.bin"
       pages = page_file.write(
           path, ORDERS, rows_per_page=3, encoding={"qty": "dictionary"}
       )
       assert pages["id"][0] == Page(offset=0, size=24, rows=3)  # plain by default
       assert pages["qty"][0] == Page(offset=128, size=19, rows=3, encoding="dictionary")
       with CountingFile(path) as f:
           assert page_file.read_metadata(f).pages == pages


   def test_a_reader_decodes_every_page_by_its_encoding(tmp_path):
       path = tmp_path / "pages.bin"
       orders = many_orders(1000)
       page_file.write(path, orders, encoding={c: "dictionary" for c in COLUMNS})
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
           for position, (column, codec) in enumerate(metadata.codecs.items()):
               values = page_file.read_column(f, codec, metadata.pages[column])
               assert values == [row[position] for row in orders]


   def test_a_version_1_file_still_reads_as_all_plain(tmp_path):
       path = tmp_path / "pages.bin"
       orders = many_orders(1000)
       page_file.write(path, orders)
       data = path.read_bytes()
       offset, size, _, _ = FOOTER.unpack(data[-FOOTER.size :])
       metadata = json.loads(data[offset : offset + size])
       for column in metadata["columns"]:
           for page in column["pages"]:
               del page["encoding"]  # version 1 box lists had no packing notes
       raw = json.dumps(metadata).encode("utf-8")
       path.write_bytes(data[:offset] + raw + FOOTER.pack(offset, len(raw), 1, MAGIC))
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
           assert metadata.version == 1
           qty = page_file.read_column(f, metadata.codecs["qty"], metadata.pages["qty"])
       assert qty == [row[2] for row in orders]


   # ──────── new code ends here ────────
   ```

6. In `tests/test_cli.py`, at the bottom (around line 149), a test of the
   new demo lines:

   ```python
   # ──────── new code starts here (around line 149) ────────
   def test_packing_packs_every_column_every_way(tmp_path):
       lines = run_packing(tmp_path)
       start = lines.index(
           "every column packed every way, orders as placed (bytes, all pages):"
       )
       assert lines[start : start + 7] == [
           "every column packed every way, orders as placed (bytes, all pages):",
           "  id: plain 8000, dictionary 9040",
           "  price: plain 8000, dictionary 1680",
           "  qty: plain 4000, dictionary 1280",
           "  name: plain 12000, dictionary 2000",
           "write dictionary.bin: 15612 bytes, pages 12960 (plain: 32000)",
           "  read back, told nothing: same as the table? True",
       ]


   # ──────── new code ends here ────────
   ```

</details>

What the tests prove:

- `round_trip`, the helper every test leans on, encodes, decodes, and
  checks the decoded bytes are *exactly* the plain bytes.

- Two stacked `parametrize` lines run
  `test_every_encoding_gives_back_exactly_what_went_in` for every
  encoding × every page in `QTY_PAGES` — an empty page, one value, all
  equal, the widest quantity, a real page — and pytest counts each run
  as its own test. Because it loops over `ENCODINGS`, the encodings of
  sections C and D are proven by this same test the moment you register
  them.

- `test_a_version_1_file_still_reads_as_all_plain` builds a version 1
  file by hand — today's file with every `encoding` deleted and a
  version 1 footer — and reads it.

```bash
uv run pytest -q
```

```text
.............................................................            [100%]
61 passed in 0.45s
```

Sixty-one tests: twenty more — sixteen in the new file (ten of them the
parametrized round trips), three for the page file, and one for the
demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-03b`

### Section C — stacks: run-length, and where it backfires

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/stdtypes.html#typesseq-common"><code>value * length</code>: a byte string repeated <code>length</code> times</a>
</div>

The first page of the sorted orders holds one name, a hundred times in
a row. A dictionary would still spend a byte per value, plus the name
once. **Run-length
encoding** stores each run once: the value and how many times it
repeats. Four edits in `src/nanolance/encodings.py`:

1. Below `from collections.abc import Callable` (line 11), import the
   tool that `describe` used in section A:

   ```python
   from itertools import groupby
   ```

2. The comment above `COUNT` (lines 13–14) gains a second use — `COUNT`
   now also holds a run's length:

   ```python
   # A 4-byte count, stored inside a page: how many distinct values a
   # dictionary page holds, or how long one run is.
   ```

3. Between `from_dictionary` and `Encoder = Callable` (around line 64),
   the encoder and its decoder:

   ```python
   # ──────── new code starts here (around line 64) ────────
   def run_length(codec: struct.Struct, data: bytes) -> bytes:
       """Analogy: stacks — equal values side by side stacked together, one
       value with a sticker saying how many.

       Layout: for each run of equal values, the value at the column's width
       followed by COUNT, the run's length.
       """
       runs = [
           value + COUNT.pack(len(list(run))) for value, run in groupby(split(codec, data))
       ]
       return b"".join(runs)


   def from_run_length(codec: struct.Struct, raw: bytes, rows: int) -> bytes:
       """Decode a run-length page: repeat every value as often as its run says."""
       step = codec.size + COUNT.size
       plain = []
       for start in range(0, len(raw), step):
           value = raw[start : start + codec.size]
           (length,) = COUNT.unpack(raw[start + codec.size : start + step])
           plain.append(value * length)
       return b"".join(plain)


   # ──────── new code ends here ────────
   ```

4. And in `ENCODINGS` (around line 97), register it after the
   dictionary:

   ```python
       "dictionary": (dictionary, from_dictionary),
       # ──────── new code starts here (around line 97) ────────
       "run-length": (run_length, from_run_length),
       # ──────── new code ends here ────────
   }
   ```

`groupby` finds the runs, as in section A's `describe`; a page of 100
identical names becomes one 12-byte name and one 4-byte count, 16 bytes.
The decoder steps through value-and-count pairs and repeats each value
(`value * length`).

At the end of `packing` in `src/nanolance/cli.py` (around line 231), the
sorted orders get the same treatment:

```python
    # ──────── new code starts here (around line 231) ────────
    every_way("sorted by name", by_name)
    in_runs = {"price": "run-length", "qty": "run-length", "name": "run-length"}
    write_and_read_back(folder / "sorted.bin", by_name, in_runs)
    # ──────── new code ends here ────────
```

Run it:

```bash
uv run nanolance packing
```

```text
⋮ (section A's eleven lines print first, unchanged)
every column packed every way, orders as placed (bytes, all pages):
  id: plain 8000, dictionary 9040, run-length 12000
  price: plain 8000, dictionary 1680, run-length 12000
  qty: plain 4000, dictionary 1280, run-length 8000
  name: plain 12000, dictionary 2000, run-length 16000
write dictionary.bin: 15612 bytes, pages 12960 (plain: 32000)
  read back, told nothing: same as the table? True
──── new: the run-length entries, and the sorted table ────
every column packed every way, orders sorted by name (bytes, all pages):
  id: plain 8000, dictionary 9040, run-length 12000
  price: plain 8000, dictionary 1168, run-length 192
  qty: plain 4000, dictionary 1100, run-length 120
  name: plain 12000, dictionary 1232, run-length 256
write sorted.bin: 11168 bytes, pages 8568 (plain: 32000)
  read back, told nothing: same as the table? True
```

Above the divider, each line of the first table gained a `run-length`
entry — `every_way` found the new encoding in `ENCODINGS` on its own.
Read the new parts line by line:

- `id: plain 8000, dictionary 9040, run-length 12000` and the three lines
  under it — run-length on the orders as placed is **worse than plain for
  every column**. As placed, no two neighbors are equal (section A's
  "longest run 1"), so every value becomes a [stack](story.md#stacks) of
  one, and pays for its count: 12000 instead of 8000 for ids, and 8000
  instead of 4000 for quantities — twice plain, because a 4-byte count
  joins every 4-byte quantity.

- `every column packed every way, orders sorted by name` and its four
  lines — the same encodings on the sorted table. The ids are still all
  different, so nothing changes for them. But the other three columns
  are long runs now: 192 bytes of prices instead of 8000, 120 of
  quantities instead of 4000, 256 of names instead of 12000.

- `qty: …, run-length 120` — 15 runs of 8 bytes. The names make 16 runs
  (every page boundary inside a name's 125 orders starts a new run), but
  the quantities make one fewer: `padlock` and `tape` orders both have a
  quantity of 2, so their runs join. Run-length only sees equal
  neighbors; it does not care which item they came from.

- `write sorted.bin: 11168 bytes, pages 8568 (plain: 32000)` and `read
  back … True` — the sorted orders stored with run-length for price,
  quantity, and name: 8000 + 192 + 120 + 256 = 8568 bytes of pages, read
  back exactly.

The same encoding shrinks the quantities 33-fold on one table and
doubles them on the other, and only the order of the rows changed. That
is the honest lesson of encodings: none of them is good in general. Each
one is good for a *shape* of data, and the writer has to look at the
data to choose.

Pin it with tests — four edits in two files:

1. In `tests/test_encodings.py`, the list in
   `test_text_and_floats_round_trip_too`'s decorator (line 35) gains
   `"run-length"`:

   ```python
   @pytest.mark.parametrize("name", ["plain", "dictionary", "run-length"])
   ```

2. In `tests/test_encodings.py`, at the bottom (around line 60), two
   tests — the exact layout and the backfire:

   ```python
   # ──────── new code starts here (around line 60) ────────
   def test_run_length_stores_each_run_once_with_its_length():
       raw = round_trip("run-length", "qty", [5, 5, 5, 9, 5])
       assert raw == b"".join(
           pack_value("qty", value) + COUNT.pack(length)
           for value, length in [(5, 3), (9, 1), (5, 1)]
       )


   def test_run_length_without_runs_is_twice_as_large_as_plain():
       qty = [row[2] for row in many_orders(100)]  # no two neighbors are equal
       assert len(round_trip("run-length", "qty", qty)) == 100 * (4 + 4)  # plain: 400


   # ──────── new code ends here ────────
   ```

3. In `tests/test_cli.py`, update the four table lines in
   `test_packing_packs_every_column_every_way` (around line 157) to the
   run's new lines — or take the finished file, step 4 included, with
   `git checkout v1-day-03c -- tests/test_cli.py`.

4. In `tests/test_cli.py`, at the bottom (around line 164), a test of the
   sorted lines:

   ```python
   # ──────── new code starts here (around line 164) ────────
   def test_packing_stacks_the_sorted_orders_in_runs(tmp_path):
       lines = run_packing(tmp_path)
       start = lines.index(
           "every column packed every way, orders sorted by name (bytes, all pages):"
       )
       assert lines[start : start + 7] == [
           "every column packed every way, orders sorted by name (bytes, all pages):",
           "  id: plain 8000, dictionary 9040, run-length 12000",
           "  price: plain 8000, dictionary 1168, run-length 192",
           "  qty: plain 4000, dictionary 1100, run-length 120",
           "  name: plain 12000, dictionary 1232, run-length 256",
           "write sorted.bin: 11168 bytes, pages 8568 (plain: 32000)",
           "  read back, told nothing: same as the table? True",
       ]


   # ──────── new code ends here ────────
   ```

```bash
uv run pytest -q
```

```text
......................................................................   [100%]
70 passed in 0.46s
```

Seventy tests: nine more. Five of them you did not write: the
parametrized round trip from section B ran its five pages through
run-length on its own. Then one more text-and-floats case, the two new
encoding tests, and one for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-03c`

### Section D — snug compartments, and the weigh-in

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/stdtypes.html#bitwise-operations-on-integer-types">bitwise operators: <code>&lt;&lt;</code>, <code>&gt;&gt;</code>, <code>&amp;</code>, <code>|</code> move and combine bits</a>
<a href="https://docs.python.org/3.12/reference/simple_stmts.html#augmented-assignment-statements"><code>packed |= x</code>: short for <code>packed = packed | x</code></a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#int.to_bytes"><code>int.to_bytes</code>: a whole number as exactly n bytes</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#int.from_bytes"><code>int.from_bytes</code>: bytes back to a whole number</a>
<a href="https://docs.python.org/3.12/library/functions.html#max"><code>max(…, default=0)</code>: 0 when there is nothing to compare</a>
<a href="https://docs.python.org/3.12/library/functions.html#all"><code>all</code>: is every element true?</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#break-and-continue-statements"><code>continue</code>: skip to the loop's next turn</a>
<a href="https://docs.python.org/3.12/library/collections.html#collections.Counter"><code>Counter</code>: counts how often each value appears</a>
<a href="https://docs.python.org/3.12/reference/lexical_analysis.html#integer-literals">binary literals: <code>0b10_01_11</code> is 39, written in bits</a>
<a href="https://docs.pytest.org/en/stable/how-to/parametrize.html">pytest: several parameters per case, <code>("column", "values")</code></a>
</div>

The quantities as placed have no runs, and a dictionary still spends a
byte per value. But section A said the largest quantity needs 6 bits.
**Bit-packing** stores every value of a page in exactly as many bits as
the page's largest value needs, and writes that width once, at the
start of the page.

Python makes this unusually short, because a Python `int` can be as
large as you like: the encoder builds the whole page as one big number,
value 0 in the lowest bits, value 1 in the next `width` bits, and so on,
then writes that number as bytes. Four edits in
`src/nanolance/encodings.py`:

1. Below `MAX_DICTIONARY` (around line 19), the width's one byte:

   ```python
   # ──────── new code starts here (around line 19) ────────
   # One byte at the start of a bit-packed page: how many bits each value takes.
   WIDTH = struct.Struct("<B")
   # ──────── new code ends here ────────
   ```

2. Between `from_run_length` and `Encoder = Callable` (around line 90),
   the encoder, its decoder, and the check they share:

   ```python
   # ──────── new code starts here (around line 90) ────────
   def whole_numbers(codec: struct.Struct, data: bytes) -> list[int]:
       """The page's values as whole numbers, refusing any other kind of value."""
       values = [value for (value,) in codec.iter_unpack(data)]
       if not all(isinstance(value, int) and value >= 0 for value in values):
           raise ValueError("bit-packing needs whole numbers that are not negative")
       return values


   def bit_packed(codec: struct.Struct, data: bytes) -> bytes:
       """Analogy: snug compartments — every compartment in the box cut down to
       the size its largest value needs.

       Layout: WIDTH (the bits per value: the largest value's bit length), then
       every value in exactly that many bits, value 0 in the lowest bits, the
       last byte filled up with zero bits.
       """
       values = whole_numbers(codec, data)
       width = max(values, default=0).bit_length()
       packed = 0
       for position, value in enumerate(values):
           packed |= value << (position * width)
       n_bytes = (len(values) * width + 7) // 8  # round up to whole bytes
       return WIDTH.pack(width) + packed.to_bytes(n_bytes, "little")


   def from_bit_packed(codec: struct.Struct, raw: bytes, rows: int) -> bytes:
       """Decode a bit-packed page: cut `rows` values of WIDTH bits each."""
       (width,) = WIDTH.unpack(raw[: WIDTH.size])
       packed = int.from_bytes(raw[WIDTH.size :], "little")
       mask = (1 << width) - 1  # `width` one-bits
       return b"".join(
           codec.pack((packed >> (position * width)) & mask) for position in range(rows)
       )


   # ──────── new code ends here ────────
   ```

3. In `ENCODINGS` (around line 135), register it last:

   ```python
       "run-length": (run_length, from_run_length),
       # ──────── new code starts here (around line 135) ────────
       "bit-packed": (bit_packed, from_bit_packed),
       # ──────── new code ends here ────────
   }
   ```

4. At the bottom of the file (around line 150), the weigh-in:

   ```python
   # ──────── new code starts here (around line 150) ────────
   def smallest(codec: struct.Struct, data: bytes) -> tuple[str, bytes]:
       """Analogy: the weigh-in — the box packed every way, each packing weighed,
       and the lightest kept.

       Encode the page with every encoding that accepts its values and return
       the name and bytes of the smallest result; a tie keeps the encoding that
       comes first in ENCODINGS, so plain wins a draw.
       """
       best_name, best = "plain", data
       for name in ENCODINGS:
           try:
               raw = encode(name, codec, data)
           except ValueError:
               continue  # this encoding refuses these values
           if len(raw) < len(best):
               best_name, best = name, raw
       return best_name, best


   # ──────── new code ends here ────────
   ```

How the bits move, on the page `[3, 1, 2]` (the largest, 3, needs 2
bits):

```text
value 0: 3 = 11      shifted left 0 bits  →  ......11
value 1: 1 = 01      shifted left 2 bits  →  ....01..
value 2: 2 = 10      shifted left 4 bits  →  ..10....
packed (| of all three)                    →  00100111  = 1 byte: 39
```

- **Encode:** `bit_packed` shifts each value left by `position * width`
  bits (`<<`) and ORs it into one number (`|=`), as the picture shows,
  then writes that number in whole bytes, lowest bits first.
  `whole_numbers` refuses anything else first: prices, names, and
  negative numbers.

- **Decode:** `from_bit_packed` shifts value `position` back down
  (`>>`) and keeps its lowest `width` bits with `& mask`, where the mask,
  `(1 << width) - 1`, is `width` one-bits — binary `11` for a width of 2.

- **Why `rows`:** the bytes alone cannot say whether the last zero bits
  are padding or values of 0, so here, at last, a decoder needs the
  page's row count.

`smallest` is [the weigh-in](story.md#weigh-in): encode the page every
way, skip any encoding that refuses, keep the fewest bytes — and since
it only replaces plain with something strictly smaller, plain wins a tie.

Then let `write` run the weigh-in. In `src/nanolance/page_file.py`, two
edits in `write`:

1. Its docstring (lines 87–89) mentions the new choice:

   ```python
       """Write `rows` column by column, each column cut into pages of up to
       `rows_per_page` values. `encoding` names an encoding per column (a
       column it leaves out is stored plain); "smallest" picks, page by page,
       whichever encoding gives the fewest bytes. Returns every column's pages."""
   ```

2. In the page loop, replace the lines from
   `data = encodings.encode(name, codec, plain)` down to the `)` that
   closes `Page(` (lines 97–101) with these — the `"smallest"`
   instruction from §4, and `encoding=used` instead of `encoding=name`:

   ```python
   def write(
       ⋮
               for plain in plain_pages(rows, column, rows_per_page):
                   if name == "smallest":
                       used, data = encodings.smallest(codec, plain)
                   else:
                       used, data = name, encodings.encode(name, codec, plain)
                   n_rows = len(plain) // codec.size
                   page = Page(
                       offset=out.tell(), size=len(data), rows=n_rows, encoding=used
                   )
   ```

Now the demo. Six edits in `src/nanolance/cli.py`:

1. Below `import argparse` (line 3):

   ```python
   from collections import Counter
   ```

2. The `from nanolance.page_file import` line (line 10) gains `Page`:

   ```python
   from nanolance.page_file import ROWS_PER_PAGE, Page
   ```

3. `write_and_read_back` returns the pages it wrote, so the demo can show
   each page's choice. Replace its first line (line 184) with

   ```python
   def write_and_read_back(
       path: Path, table: list[Row], encoding: dict[str, str]
   ) -> dict[str, list[Page]]:
   ```

4. … and add a last line to it, after the `print` of `read back` (around
   line 204), one indent in from that `print` — outside the `with`:

   ```python
           same = list(zip(*columns, strict=True)) == table
           print(f"  read back, told nothing: same as the table? {same}")
       return pages
   ```

   (The first two lines are already in your file.)

5. Between `write_and_read_back` and `packing` (around line 208), two
   helpers:

   ```python
   # ──────── new code starts here (around line 208) ────────
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


   # ──────── new code ends here ────────
   ```

6. At the end of `packing` (around line 266):

   ```python
       # ──────── new code starts here (around line 266) ────────
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
       # ──────── new code ends here ────────
   ```

`packing_notes` counts each column's packing notes (`Counter`), and
`ask_qty` asks yesterday's two questions of a freshly opened file,
splitting its tally into the opening and the pages. The demo writes a
plain baseline, the two `"smallest"` files, and asks both questions of
the plain file and the smallest one.

Run it:

```bash
uv run nanolance packing
```

```text
⋮ (sections A–C print first; each table line gains a bit-packed entry)
  id: plain 8000, dictionary 9040, run-length 12000, bit-packed 1212
  price: plain 8000, dictionary 1680, run-length 12000, bit-packed —
  qty: plain 4000, dictionary 1280, run-length 8000, bit-packed 760
  name: plain 12000, dictionary 2000, run-length 16000, bit-packed —
⋮
  id: plain 8000, dictionary 9040, run-length 12000, bit-packed 1364
  price: plain 8000, dictionary 1168, run-length 192, bit-packed —
  qty: plain 4000, dictionary 1100, run-length 120, bit-packed 424
  name: plain 12000, dictionary 1232, run-length 256, bit-packed —
──── new: a plain baseline, the smallest files, and the questions ────
write plain.bin: 34522 bytes, pages 32000 (plain: 32000)
  read back, told nothing: same as the table? True
write smallest.bin: 8320 bytes, pages 5652 (plain: 32000)
  read back, told nothing: same as the table? True
  chosen: id bit-packed ×10, price dictionary ×10, qty bit-packed ×10, name dictionary ×10
write sorted-smallest.bin: 4576 bytes, pages 1932 (plain: 32000)
  read back, told nothing: same as the table? True
  chosen: id bit-packed ×10, price run-length ×10, qty run-length ×10, name run-length ×10
sum(qty) from plain.bin, told nothing = 8125
  tally: reads 12, bytes read 6522, seeks 12 (opening 2522, pages 4000)
sum(qty) from smallest.bin, told nothing = 8125
  tally: reads 12, bytes read 3428, seeks 12 (opening 2668, pages 760)
qty of rows 10–19 from plain.bin, told nothing = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 3, bytes read 2922, seeks 3 (opening 2522, pages 400)
qty of rows 10–19 from smallest.bin, told nothing = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 3, bytes read 2744, seeks 3 (opening 2668, pages 76)
```

Read it line by line:

- `id: …, bit-packed 1212` — [snug compartments](story.md#snug-compartments)
  for the ids: the pages' largest ids need 8 to 11 bits (200 needs 8;
  1100 needs 11) instead of 64. The only encoding that shrinks the ids.

- `price: …, bit-packed —` and `name: …, bit-packed —` —
  `whole_numbers` refused: prices are floats and names are text.

- `qty: …, bit-packed 760` — 76 bytes per page: one byte of width, then
  100 values × 6 bits = 75 bytes. Sorted, `bit-packed 424` loses to
  run-length's 120: a hundred 2-bit values still take 25 bytes, and one
  run takes 8.

- `write plain.bin` — the baseline, every page plain: the same file
  `nanolance pages` writes as `pages.bin`. Then `write smallest.bin:
  8320 bytes, pages 5652` and its `chosen:` line — every page took the
  lightest of the four: 1212 + 1680 + 760 + 2000 =
  5652 bytes of pages, under a fifth of plain, read back exactly.

- `write sorted-smallest.bin: …, pages 1932` and its `chosen:` line — the
  same weigh-in on the sorted orders picks run-length for the three
  repetitive columns and still bit-packs the ids. Each page chose from
  its own bytes.

- `sum(qty)` and `qty of rows 10–19` from each file — the same answers.
  The [stock count](story.md#stock-count) reads 4000 bytes of pages from
  the plain file and 760 from the smallest, in the same 12 reads; ten
  quantities read 400 against 76. Fewer bytes on disk, fewer bytes read.

Two honest notes on these numbers. First, the opening — the footer and
metadata — is now most of what a small question reads: 2668 of the 2744
bytes. It even grew by 146 bytes, because `"bit-packed"` and
`"dictionary"` are longer to write than `"plain"`. With Lance's 8 MB
pages, the metadata is a sliver and the pages are everything. Second,
**the weigh-in has a price, paid when writing**. To keep 5652 bytes, the
writer encoded every entry of the first table: 22252 bytes of ids, 13680
of prices, 10040 of quantities, and 18000 of names besides the plain
bytes it started from — 63972 bytes made to keep 5652, more than eleven
for every one kept, plus twenty bit-packing attempts refused. That is
why real Lance decides from cheap counts (§5) instead of trying
everything.

Pin it with tests — five edits in three files:

1. In `tests/test_encodings.py`, line 4 imports `WIDTH` too:

   ```python
   from nanolance.encodings import COUNT, WIDTH
   ```

2. In `tests/test_encodings.py`, at the bottom (around line 73):

   ```python
   # ──────── new code starts here (around line 73) ────────
   def test_bit_packing_keeps_only_the_bits_the_largest_value_needs():
       raw = round_trip("bit-packed", "qty", [3, 1, 2])  # 2 bits each: 11, 01, 10
       assert raw == WIDTH.pack(2) + bytes([0b10_01_11])


   def test_bit_packing_a_page_of_zeros_takes_no_bits_per_value():
       assert round_trip("bit-packed", "qty", [0] * 100) == WIDTH.pack(0)


   def test_bit_packing_handles_the_widest_id():
       raw = round_trip("bit-packed", "id", [0, 2**63 - 1])
       assert raw[0] == 63


   @pytest.mark.parametrize(
       ("column", "values"),
       [("price", [4.25]), ("name", ["tape"]), ("qty", [-1, 5])],
   )
   def test_bit_packing_refuses_anything_but_whole_numbers_from_zero_up(column, values):
       with pytest.raises(ValueError, match="bit-packing needs whole numbers"):
           encodings.encode("bit-packed", COLUMNS[column], plain_bytes(column, values))


   @pytest.mark.parametrize(
       ("column", "values", "expected"),
       [
           ("qty", [], "plain"),  # plain and run-length both 0 bytes: plain wins a tie
           ("qty", [7], "bit-packed"),
           ("name", [row[3] for row in many_orders(100)], "dictionary"),
           ("price", [4.25] * 100, "run-length"),
       ],
   )
   def test_the_smallest_encoding_is_chosen_page_by_page(column, values, expected):
       codec = COLUMNS[column]
       data = plain_bytes(column, values)
       name, raw = encodings.smallest(codec, data)
       assert name == expected
       assert raw == encodings.encode(expected, codec, data)


   # ──────── new code ends here ────────
   ```

   `0b10_01_11` is the picture above, written in bits: underscores in a
   number are only for reading. The last test pins the weigh-in page by
   page — including the tie, where plain and run-length both store an
   empty page in 0 bytes, and plain wins.

3. In `tests/test_page_file.py`, at the bottom (around line 174), a
   column whose two pages choose differently:

   ```python
   # ──────── new code starts here (around line 174) ────────
   def test_smallest_can_pack_each_page_of_a_column_differently(tmp_path):
       path = tmp_path / "pages.bin"
       rows = many_orders(100) + [(1001 + k, 1.0, 5, "tape") for k in range(100)]
       pages = page_file.write(path, rows, encoding={"qty": "smallest"})
       assert [page.encoding for page in pages["qty"]] == ["bit-packed", "run-length"]
       with CountingFile(path) as f:
           metadata = page_file.read_metadata(f)
           qty = page_file.read_column(f, metadata.codecs["qty"], metadata.pages["qty"])
       assert qty == [row[2] for row in rows]


   # ──────── new code ends here ────────
   ```

4. In `tests/test_cli.py`, update the eight table lines in
   `test_packing_packs_every_column_every_way` and
   `test_packing_stacks_the_sorted_orders_in_runs` to the run's new
   lines — or take the finished file, step 5 included, with
   `git checkout v1-day-03d -- tests/test_cli.py`.

5. In `tests/test_cli.py`, at the bottom (around line 180):

   ```python
   # ──────── new code starts here (around line 180) ────────
   def test_packing_keeps_the_smallest_and_reads_fewer_bytes(tmp_path):
       lines = run_packing(tmp_path)
       start = lines.index("write smallest.bin: 8320 bytes, pages 5652 (plain: 32000)")
       assert lines[start : start + 3] == [
           "write smallest.bin: 8320 bytes, pages 5652 (plain: 32000)",
           "  read back, told nothing: same as the table? True",
           "  chosen: id bit-packed ×10, price dictionary ×10, "
           "qty bit-packed ×10, name dictionary ×10",
       ]
       assert lines[-8:] == [
           "sum(qty) from plain.bin, told nothing = 8125",
           "  tally: reads 12, bytes read 6522, seeks 12 (opening 2522, pages 4000)",
           "sum(qty) from smallest.bin, told nothing = 8125",
           "  tally: reads 12, bytes read 3428, seeks 12 (opening 2668, pages 760)",
           "qty of rows 10–19 from plain.bin, told nothing = "
           "[40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
           "  tally: reads 3, bytes read 2922, seeks 3 (opening 2522, pages 400)",
           "qty of rows 10–19 from smallest.bin, told nothing = "
           "[40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
           "  tally: reads 3, bytes read 2744, seeks 3 (opening 2668, pages 76)",
       ]


   # ──────── new code ends here ────────
   ```

```bash
uv run pytest -q
```

```text
........................................................................ [ 82%]
...............                                                          [100%]
87 passed in 0.59s
```

Eighty-seven tests: seventeen more — again five round trips you did not
write, run through bit-packing by section B's test; three tests of
bit-packing's layout, three refusals, four cases of the weigh-in, one for
the page file, and one for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-03d` — which is
also the finished day.

## 7. Run it

```bash
uv run nanolance packing
```

## 8. Expected result

```text
the orders table: 1000 rows × 4 columns (id, price, qty, name), 100 rows per page
the first page of each column, orders as placed:
  id: 800 bytes plain — 100 distinct, longest run 1, largest 200 needs 8 bits
  price: 800 bytes plain — 8 distinct, longest run 1
  qty: 400 bytes plain — 6 distinct, longest run 1, largest 40 needs 6 bits
  name: 1200 bytes plain — 8 distinct, longest run 1
the first page of each column, orders sorted by name:
  id: 800 bytes plain — 100 distinct, longest run 1, largest 893 needs 10 bits
  price: 800 bytes plain — 1 distinct, longest run 100
  qty: 400 bytes plain — 1 distinct, longest run 100, largest 3 needs 2 bits
  name: 1200 bytes plain — 1 distinct, longest run 100
every column packed every way, orders as placed (bytes, all pages):
  id: plain 8000, dictionary 9040, run-length 12000, bit-packed 1212
  price: plain 8000, dictionary 1680, run-length 12000, bit-packed —
  qty: plain 4000, dictionary 1280, run-length 8000, bit-packed 760
  name: plain 12000, dictionary 2000, run-length 16000, bit-packed —
write dictionary.bin: 15612 bytes, pages 12960 (plain: 32000)
  read back, told nothing: same as the table? True
every column packed every way, orders sorted by name (bytes, all pages):
  id: plain 8000, dictionary 9040, run-length 12000, bit-packed 1364
  price: plain 8000, dictionary 1168, run-length 192, bit-packed —
  qty: plain 4000, dictionary 1100, run-length 120, bit-packed 424
  name: plain 12000, dictionary 1232, run-length 256, bit-packed —
write sorted.bin: 11168 bytes, pages 8568 (plain: 32000)
  read back, told nothing: same as the table? True
write plain.bin: 34522 bytes, pages 32000 (plain: 32000)
  read back, told nothing: same as the table? True
write smallest.bin: 8320 bytes, pages 5652 (plain: 32000)
  read back, told nothing: same as the table? True
  chosen: id bit-packed ×10, price dictionary ×10, qty bit-packed ×10, name dictionary ×10
write sorted-smallest.bin: 4576 bytes, pages 1932 (plain: 32000)
  read back, told nothing: same as the table? True
  chosen: id bit-packed ×10, price run-length ×10, qty run-length ×10, name run-length ×10
sum(qty) from plain.bin, told nothing = 8125
  tally: reads 12, bytes read 6522, seeks 12 (opening 2522, pages 4000)
sum(qty) from smallest.bin, told nothing = 8125
  tally: reads 12, bytes read 3428, seeks 12 (opening 2668, pages 760)
qty of rows 10–19 from plain.bin, told nothing = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 3, bytes read 2922, seeks 3 (opening 2522, pages 400)
qty of rows 10–19 from smallest.bin, told nothing = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]
  tally: reads 3, bytes read 2744, seeks 3 (opening 2668, pages 76)
```

The whole day at the packer's bench, one stretch at a time:

- The first eleven lines — the packer looks inside the boxes: few
  distinct values, long runs once sorted, small numbers in wide
  compartments.

- The first table and `dictionary.bin` — every column encoded every
  way, where the [lid legend](story.md#lid-legend) wins on repeated
  values and loses on ids, and a real file decoded by its
  [packing notes](story.md#packing-note).

- The second table and `sorted.bin` — [stacks](story.md#stacks): a 2×
  loss on the orders as placed, a huge win once sorted.

- The `bit-packed` entries — [snug compartments](story.md#snug-compartments)
  for whole numbers.

- `plain.bin` through the second `chosen:` — [the weigh-in](story.md#weigh-in),
  page by page.

- The last eight lines — yesterday's questions: the same answers for a
  fraction of the page bytes.

Nothing here varies between runs: no randomness, no timing, only counts.

## 9. Test it

`uv run pytest -q` now runs eighty-seven tests — the `87 passed` of
section D. That is Day 2's 40 plus 47 new ones: the first-page counts
(section A, 1 test), the encodings module, packing notes, and version 2
(section B, 20), run-length (section C, 9), and bit-packing with the
weigh-in (section D, 17). Seventy-four are unit tests; the other
thirteen (`test_cli_says_hello` and the twelve in `test_cli.py`) run the
real command line.

Every encoding passes the same round-trip proof — an empty page, one
value, all values equal, the widest value, a real page — so "fewer bytes"
never means "different values".

## 10. Break it deliberately

Drop the `- 1` from the decoder's mask. In `from_bit_packed` in
`src/nanolance/encodings.py`, change one line:

```diff
@@ src/nanolance/encodings.py, around line 121 @@
     packed = int.from_bytes(raw[WIDTH.size :], "little")
-    mask = (1 << width) - 1  # `width` one-bits
+    mask = 1 << width  # `width` one-bits
     return b"".join(
```

For a width of 6, the mask should be binary `111111`; it is now
`1000000` — a single bit, the one *just above* each value. The encoder
is untouched, so every file is written exactly as before. Run the tests:

```bash
uv run pytest -q --tb=line
```

```text
E   AssertionError: assert ['write small...ctionary ×10'] == ['write small...ctionary ×10']
E   AssertionError: assert b'\x00\x00\x00\x00' == b'\x07\x00\x00\x00'
E   AssertionError: assert b'\x00\x00\x0...0\x00\x00\x00' == b'\x02\x00\x0...2\x00\x00\x00'
E   struct.error: 'i' format requires -2147483648 <= number <= 2147483647
E   AssertionError: assert b'@\x00\x00\x...0\x00\x00\x00' == b'\x03\x00\x0...2\x00\x00\x00'
E   AssertionError: assert b'\x04\x00\x0...0\x00\x00\x00' == b'\x03\x00\x0...2\x00\x00\x00'
E   struct.error: 'q' format requires -9223372036854775808 <= number <= 9223372036854775807
E   assert [64, 0, 0, 64, 0, 0, ...] == [3, 1, 40, 2, 1, 12, ...]
```

(Only the `E` lines are shown — one per failing test. Pytest's summary
line reads `8 failed, 79 passed`.)

Read it line by line:

- `['write small...'] == ['write small...']` — the demo test: the
  smallest file no longer reads back as the table.

- `b'\x00\x00\x00\x00' == b'\x07\x00\x00\x00'` and the next lines of
  bytes — the round trips: a one-value page of 7 came back as 0. Each
  decoded value is now only the single bit above it, which belongs to
  its neighbor.

- the two `struct.error` lines — the widest values: with a mask of
  `1 << 31` or `1 << 63`, the "value" is too big to pack back into its
  column's width, so these two fail loudly.

- `[64, 0, 0, 64, …] == [3, 1, 40, 2, …]` — the page-file test reading
  quantities back: real-looking numbers, all wrong.

- Two decoding tests still pass: an empty page and a page of zeros
  decode correctly with *any* mask, because every bit is 0. A bug that
  only touches nonzero bits hides from those two cases — which is why
  the round-trip test also uses real pages.

The demo shows how quietly the wrong answers arrive — here are only its
`smallest.bin` lines, picked out of the run:

```bash
uv run nanolance packing
```

```text
write smallest.bin: 8320 bytes, pages 5652 (plain: 32000)
  read back, told nothing: same as the table? False
sum(qty) from smallest.bin, told nothing = 23360
  tally: reads 12, bytes read 3428, seeks 12 (opening 2668, pages 760)
qty of rows 10–19 from smallest.bin, told nothing = [0, 64, 0, 0, 0, 64, 64, 0, 0, 64]
  tally: reads 3, bytes read 2744, seeks 3 (opening 2668, pages 76)
```

Every size is unchanged — the writer did nothing wrong. But the file
fails its read-back, and the stock count says 23360 — no error, a
confident wrong number, from the same 760 bytes. **An encoding is
correct only if its decoder gives back the exact plain bytes**, and only
a round-trip test proves that.

Put the `- 1` back and confirm `uv run pytest -q` is green again.

## 11. Checkpoint

Every checkpoint — each section and the day — is done only when the full
green bar passes:

```bash
./scripts/check.sh
```

```text
26 files already formatted
All checks passed!
........................................................................ [ 82%]
...............                                                          [100%]
87 passed in 0.61s
nanolance 0.1.0: scaffold is alive
⋮ (Day 1's `nanolance layouts` output, unchanged) ⋮
⋮ (Day 2's `nanolance pages` output, with today's sizes) ⋮
⋮ (the §8 output, unchanged) ⋮
 INFO Book building has started
 INFO Running the html backend
 INFO HTML book written to `/…/build-nano-lance-in-python/book/book`
GREEN: all gates passed
```

(Paths shortened, as everywhere in this book.)

- `26 files already formatted` through `87 passed` — formatting, lints
  (now over two new Python files and this chapter's code blocks), and the
  whole suite.

- the `⋮` lines through `GREEN: all gates passed` — the smoke gate's
  three demos, now including `nanolance packing` (section 8's output),
  then the book build.

The smoke gate gained one line today: `uv run --locked nanolance packing
"$scratch"`. `scripts/check.sh` is course infrastructure, outside what
`compare.sh` checks; to pick up today's copy, take it from the
checkpoint:

```bash
git checkout v1-day-03 -- scripts/check.sh
```

Then close out the day in whichever mode you are following:

**Built along on your own branch?** Confirm your code matches the finished
day — the final ✓ line means it does:

```bash
./scripts/compare.sh v1-day-03
```

**Inspecting instead of typing?** Jump to today's exact finished state,
poke at it, and come back:

```bash
git switch --detach v1-day-03
uv run nanolance packing
git switch -          # back to where you were
```

**Either way**, today's complete change set — docs included — reads as one
diff:

```bash
git diff v1-day-02 v1-day-03
```

## 12. Recap

**What changed today:**

- `encodings.py` (new) — encoders that turn a page's plain bytes into
  stored bytes and decoders that give them back exactly: `plain`,
  `dictionary`, `run_length`, and `bit_packed`, registered by name in
  `ENCODINGS`, plus `smallest`, the weigh-in.

- `page_file.py` — `plain_pages`; a `Page.encoding` packing note on every
  page; `write`'s per-column `encoding` choice, with `"smallest"` picking
  page by page; a `read_page` that decodes by the note; and format
  `VERSION` 2, whose reader still reads version 1 files.

- `cli.py` — the `nanolance packing` demo: `describe`, `every_way`,
  `write_and_read_back`, `packing_notes`, and `ask_qty`.

- Tests — forty-seven new ones (87 in all) across four section
  checkpoints (`v1-day-03a` to `v1-day-03d`), still with no
  dependencies.

**Deliberately naive:** the weigh-in tries every encoding on every page
instead of deciding from cheap counts; each page uses one encoding — no
layering, so a dictionary's codes are never bit-packed; dictionary codes
are always one byte; bit-packing stores values from 0, so ids around a
million would still need 20 bits each even when a page's ids differ by
less than 100 (storing each value's distance from the page's smallest —
*frame of reference* — would fix that); and decoding builds the whole
page in memory before cutting it into values.

**Tomorrow, on Day 4:** every value still has a fixed width — and for
names, that width is a lie: `tape` is padded to 12 bytes, and a name
longer than 12 bytes cannot be stored at all (Day 1's
`screwdriver set` was refused). Day 4 stores values of any length, with
a list of where each one starts, and values that are missing altogether.
The packer has learned to pack tight — see [the
warehouse](story.md); next, the boxes learn to hold things of every
size, and empty compartments.
