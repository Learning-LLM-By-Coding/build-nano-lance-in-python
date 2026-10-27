# Day 4: Strings, lists, and missing values

> **Day 4** (of Days 0–17) · builds on `v1-day-03` · ≈ 2 h

| Section | Builds | Checkpoint |
|---------|--------|------------|
| A | What fixed widths cannot say: padding counted, a long name and a missing price refused | `v1-day-04a` |
| B | Strings as offsets and data — several buffers in one page, format version 3 | `v1-day-04b` |
| C | Lists: offsets into a column of strings | `v1-day-04c` |
| D | Missing values: a validity bitmap, and the whole table read back | `v1-day-04d` = `v1-day-04` |

**Pick your mode before starting** (explained fully in
[Setup](setup.md#4-choose-how-you-follow-along)):

```bash
# Build mode — type today's code yourself, on your own branch:
git switch -c my-course v1-day-03      # or keep going on yesterday's branch

# Inspect mode — read along with the finished code instead:
git switch --detach v1-day-04a         # then 04b, 04c, 04d as you pass each section
```

<div class="callout">

**Today's typing budget** — so nothing sneaks up on you:

| Section | The learning | Wiring & tests (copy-friendly) |
|---------|--------------|--------------------------------|
| A | the `shapes` demo's first half · ~30 lines | the shop's table (~20 lines), imports, 2 edits in `main`, 1 test |
| B | a new `shapes.py`: `offsets`, `spans`, `string_trays`, `strings_from`, `trays`, and helpers · ~125 lines with docstrings; in `page_file.py`: `Tray`, `Page.trays`, `pack_page`, the new `write`, `read_page`, `read_string`, version 3 · ~110 lines | `read_back`, `tray_bytes`, demo lines (~60), 17 tests |
| C | `list_trays` + `lists_from` · ~20 lines, and 5 one-line edits | `many_tagged_orders`, demo lines (~25), 8 tests |
| D | `roll_call` + `present` · ~20 lines; missing values in `fixed_tray`, `trays`, and `values_from` · ~25 lines | `TAGGED_COLUMNS`, `ask`, demo lines (~45), 11 tests |

Four sections are four natural sittings, and every checkpoint is a save
point — nothing says a "day" must fit in one. Still **no dependencies**.

</div>

> **Short on time?** Sections A–B are the core: the problem, the idea of
> offsets, and the format change it forces. C reuses B's idea one level
> up, and D adds missing values; each can be a second sitting.

## 1. What you will have running

By the end of today, `uv run nanolance shapes` stores the orders the way
a shop really sends them: names of **any length** — one with a two-byte
`Ø` in it — a **list of tags** on each order, some empty, and **prices
nobody has quoted yet** — and every value comes back exactly, counted
in bytes and reads along the way.

<div class="dl-concepts"><span>Lance concepts used here:</span>
<a href="https://arrow.apache.org/docs/format/Columnar.html#variable-size-binary-layout">Arrow's variable-size binary layout: an offsets buffer and a data buffer ↗</a>
<a href="https://arrow.apache.org/docs/format/Columnar.html#variable-size-list-layout">Arrow's variable-size list layout: offsets into a child array ↗</a>
<a href="https://arrow.apache.org/docs/format/Columnar.html#validity-bitmaps">Arrow's validity bitmaps: one bit per value ↗</a>
<a href="https://lance.org/format/file/">Lance's file format: every page lists its buffers ↗</a>
<a href="https://lance.org/format/file/encoding/">Lance's structural encodings: repetition and definition levels ↗</a>
<a href="https://en.wikipedia.org/wiki/UTF-8">UTF-8: how text becomes bytes, one to four per character (Wikipedia) ↗</a>
</div>

## 2. What you will be seeing in the output

A few lines from the end of the day (section 8 has all of them); if one
doesn't land yet, that's fine:

```text
names of Day 3's 1000 orders, in 12-byte slots: 12000 bytes, 6250 of them letters, 5750 padding
pack 'drill bits Ø6' as a name: refused, name needs 14 bytes; the slot holds 12
⋮
  strings.bin: 10290 bytes = offsets plain 4040 + data plain 6250
⋮
one name, row 4, from a box the picker already knows:
  padded.bin: 'drill bits' — tally: reads 1, bytes read 12, seeks 1
  strings.bin: 'drill bits' — tally: reads 2, bytes read 18, seeks 2
⋮
average price from shop.bin = 10.92, 250 missing
  tally: reads 12, bytes read 9702, seeks 12 (opening 7972, pages 1730)
```

- The first two lines — yesterday's names, each in a fixed 12 bytes:
  almost half of those bytes are padding, and a 14-byte name does not
  fit at all.

- `strings.bin: …` — the same names with no padding: the letters back to
  back, plus numbers saying where each name ends.

- `one name, row 4` and the two lines under it — the price: one read
  from fixed slots, two from back-to-back letters.

- `average price … 250 missing` — the table now *says* when a price is
  unknown, so an average leaves it out instead of counting it as zero.

## 3. Why we need it

Since Day 1, every value has had a fixed width: that is what made
"where is value *k*?" plain arithmetic. But a real shop's orders do not
fit fixed widths. Three things go wrong:

- **Names have any length.** A name slot is 12 bytes. Day 1 refused
  `screwdriver set` (15 bytes), and today's orders include `drill bits Ø6`:
  13 characters, but 14 bytes, because `Ø` takes two bytes in UTF-8.
  Making the slot wider only makes it worse for everyone else: the
  thousand names of Day 3 already spend 5750 of their 12000 bytes on
  padding.

- **Some values are lists.** An order may carry no tags, one, or two. No
  fixed width fits "any number of words, each of any length".

- **Some values are missing.** A price nobody has quoted yet has no bytes
  that say so: every 8-byte pattern is some float. Storing 0.0 instead
  is a lie the rest of the code believes — the cheapest order becomes
  `gloves at 0.0`, and the average price drops from 10.92 to 8.19.

Day 3 changed how values are packed; today changes what a page can
hold.

**The story so far — remember [the warehouse](story.md):** the orders
sit in [aisles](story.md#column-layout) cut into
[sealed boxes](story.md#pages); [box lists](story.md#box-list) and
[the wall card](story.md#wall-card) at the back tell a picker who knows
nothing where every box is, and [the tally](story.md#tally) counts every
trip; yesterday [the packer](story.md#encodings) learned to pack each
box tighter. Today's scene is **trays in the box**. The warehouse's
customer, a hardware shop, sends its orders as they really are, and at
the packer's bench they do not fit Day 1's
[packing rule](story.md#packing-rule) of fixed-size compartments. So the
packer puts **trays** in the box instead — a tray of letters, a tray of
marks saying where each name ends, and a tray of answers saying which
values are present at all.

## 4. Mental model

Walk the packer's bench, one station per section:

- **What does not fit (section A)** — counted, not guessed.

- **[The letter strip and its end marks](story.md#letter-strip)
  (section B)** — offsets and data. All the names' letters written back
  to back on one strip, no padding, and beside it a line of marks: where
  each name ends. Here are four names:

  ```text
  the names       bolts, hammer, washers, tape
  letter strip    boltshammerwasherstape     22 bytes, no padding
  end marks       0, 5, 11, 18, 22           where each name ends; the first is always 0
  ```

  Five marks for four names: name *k* is the strip from mark *k* up to
  mark *k* + 1, so name 2 (counting from 0, as Python does) runs from 11
  to 18 — `washers`.

- **[Trays](story.md#trays) (section B)** — several buffers in one page.
  A *buffer* is one run of bytes that a page stores in one piece; until
  today, every page was a single buffer. Now a box holds two trays back
  to back, the marks and the letters. Each tray is a run of fixed-width
  values — 4-byte marks, 1-byte letters. So each tray gets its own
  packing note, and Day 3's packing methods work on it unchanged.

- **Edition 3 (section B).** A box that needs one tray is packed as
  yesterday, but trays change what a file can mean, so the stamp moves
  to edition 3.

- **One name, two trips (section B).** In fixed slots, name *k* sits at
  12 × *k*: one trip. On a letter strip, its two end marks come first.

- **[Bundles](story.md#bundles) (section C)** — lists. Every tag of
  every bundle goes on a letter strip with its own end marks, and one
  more line of marks says where each order's bundle ends, counted in
  tags. An empty bundle is two equal marks.

- **[The roll call](story.md#roll-call) (section D)** — a validity
  bitmap: one answer per value, 1 for present, 0 for absent, eight to a
  byte. A missing value keeps its place in the other trays as an empty
  one, which the roll call hides. A box with nothing missing has no roll
  call. Here are ten prices, every other one missing —
  `[None, 4.25] * 5`:

  ```text
  value number      9 8 | 7 6 5 4 3 2 1 0
  present?          1 0 | 1 0 1 0 1 0 1 0      answers 1 at values 1, 3, 5, 7, 9
  byte 1            0b00000010                 values 8–15; only 8 and 9 are real
  byte 0            0b10101010                 values 0–7
  ```

  Each byte is read right to left: its lowest bit is the lowest value
  number. Byte 0 holds values 0–7, byte 1 values 8 and 9, and the six
  unused bits stay 0.

Here is how a picker who knows nothing reads the first box of prices
from section D's `shop.bin` — a box with a roll call — step by step down
the page:

```text
the wall card          where the box lists are; version 3; stamp NLNC
    │ read the box lists
    ▼
the price box list     box 0 starts at byte 1212: 173 bytes, 100 rows, packing note "trays":
                       a 13-byte roll call (plain), then 160 bytes of prices (dictionary)
    │ seek to 1212, read 173 bytes
    ▼
two trays              cut by their sizes: the first 13 bytes, then the next 160
    │ decode each tray by its own packing note
    ▼
plain trays            100 answers in 13 bytes; 100 prices at 8 bytes, 0.0 where missing
    │ cut the prices into values; set to None every value whose answer is 0
    ▼
the prices             100 of them: 75 known, 25 missing
```

Only two steps are new: cutting a box into its trays, and the roll call
at the end. Everything else is yesterday's reader.

## 5. Lance concepts introduced

- **Fixed-width and variable-width.** In Lance's words, "most types fall
  into two general paths. One for fixed-width data and one for
  variable-width data (where we recognize both 32-bit and 64-bit
  offsets)." Ours follow Apache Arrow's offsets and data buffers, and a
  list is offsets into a column of all its items.

- **A page holds several buffers.** "The number of buffers is variable
  and depends on the encoding." Our trays are those buffers.

- **A missing value is a 0 bit.** Arrow: "A 1 (set bit) for index j
  indicates that the value is not null, while a 0 (bit not set)
  indicates that it is null." And the order of the bits: "We use
  least-significant bit (LSB) numbering (also known as bit-endianness).
  This means that within a group of 8 bits, we read right-to-left".

- **No missing values, no bitmap.** "Arrays having a 0 null count may
  choose to not allocate the validity bitmap" — ours never has one on
  such a page.

<div class="callout">

**Where real Lance differs** — from its
[encoding strategy](https://lance.org/format/file/encoding/) page and
[file format](https://lance.org/format/file/):

1. **One buffer instead of several.** "Repetition and definition levels
   are an alternative to validity bitmaps and offset arrays for
   expressing struct and list information. They have a significant
   advantage in that they combine all of these buffers into a single
   buffer which allows us to avoid multiple IOPS." (An *IOP* is one trip.)

2. **Two trips for one value — as ours.** For large values, "To
   perform random access we require two IOPS. First we issue an IOP
   into the repetition index to determine the location and then a
   second IOP into the data buffer to load the data."

3. **Dictionaries of whole values.** "We've found the most convenient
   simple place to apply dictionary encoding is at the structural
   level": whole strings, not bytes inside a buffer. Lance also
   compresses string bytes with FSST, a compressor that replaces common
   byte sequences with one-byte codes, and has a layout "for pages where
   all (visible) values are the same scalar value or null".

4. **Metadata per column.** "there is no need to read all file metadata if
   you are only interested in a subset of the columns. However, in many
   cases, the column descriptors are small enough that it is cheaper to
   read the entire footer in a single read than split it into multiple
   reads." Ours always reads all of it; section D shows the cost.

</div>

## 6. Build it, section by section

### Section A — what fixed widths cannot say

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/constants.html#None"><code>None</code>: Python's value for "nothing here"</a>
<a href="https://docs.python.org/3.12/reference/expressions.html#is-not"><code>is not None</code>: the way to ask "is there a value?"</a>
<a href="https://docs.python.org/3.12/reference/expressions.html#conditional-expressions"><code>a if condition else b</code>: a choice inside one expression</a>
<a href="https://docs.python.org/3.12/library/struct.html#struct.error"><code>struct.error</code>: the error <code>struct</code> raises for a value it cannot pack</a>
<a href="https://docs.python.org/3.12/tutorial/errors.html#handling-exceptions"><code>except (A, B) as error</code>: catch either kind of error, and keep it</a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#comparing-sequences-and-other-types">comparing tuples: first elements first, then the next — so <code>min</code> works on pairs</a>
<a href="https://docs.python.org/3.12/library/string.html#format-specification-mini-language"><code>{x:.2f}</code> in an f-string: a number with two decimals</a>
</div>

First, the shop's orders, and what yesterday's packing rule makes of
them. The table is the same eight orders as Day 1 — the same ids and
quantities — as a shop really sends them. In `src/nanolance/orders.py`,
between the closing `]` of `ORDERS` (line 32) and `def pack_value`
(around line 35):

```python
# ──────── new code starts here (around line 35) ────────
# Analogy: the same eight orders as the shop really sends them — a name too
# long for its compartment, tags on most of them, and two prices nobody has
# quoted yet.
#
# Day 4's table: the same ids and quantities as ORDERS, but a price may be
# None (not known yet), a name may need more than NAME_WIDTH bytes, and tags
# is a list of words, possibly empty.
TaggedRow = tuple[int, float | None, int, str, list[str]]

TAGGED_ORDERS: list[TaggedRow] = [
    (101, 4.25, 3, "bolts", ["bulk"]),
    (102, 12.5, 1, "hammer", []),
    (103, None, 40, "washers", ["bulk", "small parts"]),
    (104, 7.0, 2, "tape", []),
    (105, 23.5, 1, "drill bits Ø6", ["fragile"]),
    (106, 3.25, 12, "nails", ["bulk"]),
    (107, None, 4, "gloves", []),
    (108, 15.0, 2, "padlock", ["gift", "fragile"]),
]


# ──────── new code ends here ────────
```

Orders 103 and 107 have no price yet: `None`. `TaggedRow` is the shape
of one row, a type alias like Day 1's `Row`.

Now the demo, in `src/nanolance/cli.py` — four edits:

1. Below `import argparse` (line 3), add

   ```python
   import struct
   ```

2. Replace the `from nanolance.orders import …` line (line 10) with this
   longer import — three more names than before, one per line, so it
   stays readable:

   ```python
   from nanolance.orders import (
       COLUMNS,
       NAME_WIDTH,
       ORDERS,
       ROW_WIDTH,
       TAGGED_ORDERS,
       Row,
       many_orders,
       pack_value,
   )
   ```

3. Between the end of `packing` and `def main` (around line 292), the
   demo:

   ```python
   # ──────── new code starts here (around line 292) ────────
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


   # ──────── new code ends here ────────
   ```

4. In `main`, register the subcommand after the `packing` one (around
   line 338), and run it after the `packing` branch (around line 348):

   ```python
       demo = demos.add_parser("packing", help="pack each page in fewer bytes")
       demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
       # ──────── new code starts here (around line 338) ────────
       demo = demos.add_parser("shapes", help="store values of any length, or none")
       demo.add_argument("folder", type=Path, nargs="?", default=Path("warehouse"))
       # ──────── new code ends here ────────
       args = parser.parse_args()
       ⋮
       elif args.demo == "packing":
           packing(args.folder)
       # ──────── new code starts here (around line 348) ────────
       elif args.demo == "shapes":
           shapes(args.folder)
       # ──────── new code ends here ────────
       else:
   ```

What `shapes` does so far:

- It counts the padding in Day 3's thousand names:
  `len(row[3].encode("utf-8"))` is how many bytes a name really uses.

- It asks Day 1's `pack_value` for a long name and a missing price. The
  two refusals are different errors — our `ValueError` and `struct`'s
  own `struct.error` — so `except` lists both.

- It tries the usual workaround, 0.0 for "unknown", on two honest
  questions: the cheapest order, and the average price.

Run it:

```bash
uv run nanolance shapes
```

```text
the orders as the shop sends them: 8 rows
  (101, 4.25, 3, 'bolts', ['bulk'])
  (102, 12.5, 1, 'hammer', [])
  (103, None, 40, 'washers', ['bulk', 'small parts'])
  (104, 7.0, 2, 'tape', [])
  (105, 23.5, 1, 'drill bits Ø6', ['fragile'])
  (106, 3.25, 12, 'nails', ['bulk'])
  (107, None, 4, 'gloves', [])
  (108, 15.0, 2, 'padlock', ['gift', 'fragile'])
names of Day 3's 1000 orders, in 12-byte slots: 12000 bytes, 6250 of them letters, 5750 padding
pack 'drill bits Ø6' as a name: refused, name needs 14 bytes; the slot holds 12
pack None as a price: refused, required argument is not a float
  stored as 0.0 instead: the cheapest order is gloves at 0.0
  and the average price is 8.19; the 6 known prices average 10.92
```

Read it line by line:

- `names of Day 3's 1000 orders, …` — 6250 letters in 12000 bytes: 5750
  bytes, almost half, are padding.

- `pack 'drill bits Ø6' as a name: refused, …` — `pack_value`: thirteen
  characters, but `Ø` is two bytes in UTF-8.

- `pack None as a price: refused, …` — `struct` itself refuses: an
  8-byte float has no pattern for "unknown".

- `stored as 0.0 instead: …` and the average line — the workaround fails
  twice: gloves look free, and two unknown prices drag the average from
  10.92 to 8.19.

Every problem here is the [packing rule](story.md#packing-rule) itself:
one fixed width per column.

Pin the demo with a test: at the bottom of `tests/test_cli.py`, a
`run_shapes` helper like Day 3's `run_packing`, and
`test_shapes_shows_what_fixed_widths_cannot_say`, which checks the lines
above word for word. Take the finished file rather than retyping a
transcript:

```bash
git checkout v1-day-04a -- tests/test_cli.py
```

```bash
uv run pytest -q
```

```text
........................................................................ [ 81%]
................                                                         [100%]
88 passed in 0.63s
```

Eighty-eight tests: yesterday's 87 and the new one.

**Section checkpoint:** `./scripts/compare.sh v1-day-04a`

### Section B — the letter strip and its end marks: strings, in trays

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/itertools.html#itertools.pairwise"><code>itertools.pairwise</code>: each element with the next one — (a, b), (b, c), …</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#dict"><code>list(d)</code> of a dict: its keys, in order</a>
<a href="https://docs.python.org/3.12/reference/expressions.html#dictionary-displays"><code>{**COLUMNS, "name": STRING}</code>: a copy of a dict, with one entry replaced</a>
<a href="https://docs.python.org/3.12/library/typing.html#annotating-tuples"><code>tuple[Tray, ...]</code>: a tuple of any length, all <code>Tray</code>s</a>
<a href="https://docs.python.org/3.12/library/dataclasses.html#dataclasses.dataclass">dataclass fields by position: <code>Page(offset, size, rows)</code>, in field order</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#dict.pop"><code>dict.pop(key, default)</code>: removes a key and returns its value, or <code>default</code></a>
<a href="https://docs.python.org/3.12/tutorial/datastructures.html#tuples-and-sequences">unpacking: <code>start, stop = …</code> takes exactly two values</a>
</div>

The fix for names comes from [Apache Arrow](https://arrow.apache.org/docs/format/Columnar.html#variable-size-binary-layout),
and Lance stores text the same way. Write every name's bytes back to
back, with no padding: that is the **data**. Then write where each name
ends: those are the **offsets**. §4 drew the idea; now the code. Create
`src/nanolance/shapes.py`, beginning with the constants and how a column
says what kind it is:

```python
"""Analogy: trays inside a box — values of any length kept in trays of
fixed-size compartments, so the packer's methods still work on every tray.

Variable-length values. A page that holds them is stored as several
buffers ("trays"), each one a run of fixed-width values that Day 3's
encodings can pack: OFFSET-wide positions, and BYTE-wide UTF-8 text. Strings
follow Apache Arrow's variable-size binary layout.
"""

import struct
from itertools import pairwise

# One offset: a position in a page's text, 4 bytes, so up to 4 GiB per page.
OFFSET = struct.Struct("<I")
# One byte of UTF-8 text.
BYTE = struct.Struct("<B")

# The name a variable-length text column records as its format.
STRING = "string"

# A column's kind: a fixed-width codec (Days 1–3), or the name of a
# variable-length kind.
Kind = struct.Struct | str
Value = int | float | str


def kind_of(format_name: str) -> Kind:
    """The column kind a metadata "format" names."""
    if format_name == STRING:
        return format_name
    return struct.Struct(format_name)


def format_of(kind: Kind) -> str:
    """The "format" the metadata records for a column kind."""
    return kind if isinstance(kind, str) else kind.format
```

A column's **kind** is either a fixed-width codec — the `struct.Struct`
every column has had since Day 1 — or the name `"string"`. `kind_of`
and `format_of` convert it to and from the metadata's "format" text.

Below `format_of`, the offsets, and strings built from them:

```python
def offsets(lengths: list[int]) -> bytes:
    """Analogy: the end marks — a mark beside the strip where each value ends.

    len(lengths) + 1 offsets: 0, then the running total of the lengths, so
    value k lies between offsets k and k + 1.
    """
    ends = [0]
    for length in lengths:
        ends.append(ends[-1] + length)
    return b"".join(OFFSET.pack(end) for end in ends)


def spans(raw: bytes) -> list[tuple[int, int]]:
    """Every value's (start, stop) from a tray of offsets."""
    return list(pairwise(end for (end,) in OFFSET.iter_unpack(raw)))


def string_trays(values: list[str]) -> dict[str, bytes]:
    """Analogy: the letter strip and its end marks — every name's letters
    written back to back, and a mark where each one ends.

    Two trays: "offsets" (len(values) + 1 of them), and "data" (every value's
    UTF-8 bytes back to back, no padding).
    """
    data = [value.encode("utf-8") for value in values]
    return {"offsets": offsets([len(text) for text in data]), "data": b"".join(data)}


def strings_from(trays: dict[str, bytes]) -> list[str]:
    """The strings back from their "offsets" and "data" trays."""
    data = trays["data"]
    return [data[start:stop].decode("utf-8") for start, stop in spans(trays["offsets"])]
```

- `offsets` turns lengths `[5, 6, 7, 4]` into `0, 5, 11, 18, 22`;
  `spans` reads them back as pairs, (0, 5), (5, 11), ….

- `string_trays` returns both buffers in a dict, by name. Offsets count
  **bytes**, not characters: `Ø6` is three bytes.

Last in the file, what the page file calls: `trays` to lay out one
page, `values_from` to rebuild it, and three helpers they lean on:

```python
def fixed_tray(codec: struct.Struct, values: list[Value]) -> bytes:
    """Analogy: Day 1's packing rule, for any compartment size.

    Values back to back at the codec's width. Text is UTF-8, zero-padded,
    and refused when it needs more bytes than the width.
    """
    parts = []
    for value in values:
        if isinstance(value, str):
            value = value.encode("utf-8")
            if len(value) > codec.size:
                raise ValueError(
                    f"text needs {len(value)} bytes; the slot holds {codec.size}"
                )
        parts.append(codec.pack(value))
    return b"".join(parts)


def fixed_values(codec: struct.Struct, plain: bytes) -> list[Value]:
    """Cut plain bytes into values; fixed-width text loses its zero padding."""
    values = []
    for (value,) in codec.iter_unpack(plain):
        if isinstance(value, bytes):
            value = value.rstrip(b"\0").decode("utf-8")
        values.append(value)
    return values


def trays(kind: Kind, values: list[Value]) -> dict[str, bytes]:
    """Analogy: lay out one box's trays before the packer packs each one.

    One page's values as plain trays, by name: a fixed-width column has one,
    "values"; a string column has "offsets" and "data".
    """
    if kind == STRING:
        return string_trays(values)
    return {"values": fixed_tray(kind, values)}


def tray_codec(kind: Kind, name: str) -> struct.Struct:
    """The fixed width of one tray's values, which its encoding works on."""
    if name == "offsets":
        return OFFSET
    if name == "data":
        return BYTE
    return kind  # "values": the column's own codec


def values_from(kind: Kind, trays: dict[str, bytes]) -> list[Value]:
    """One page's values back from its decoded (plain) trays."""
    if kind == STRING:
        return strings_from(trays)
    return fixed_values(kind, trays["values"])
```

- `fixed_tray` is Day 1's packing rule for any codec; `fixed_values`
  is yesterday's cutting loop from `read_page`, moved here.

- `trays` lays out one page as named buffers — `{"values": …}`, exactly
  yesterday's plain page, or `{"offsets": …, "data": …}`. Each buffer is
  a [tray](story.md#trays) of fixed-width values (`tray_codec` says which
  width), so **Day 3's encodings work on each tray unchanged**.

Now the page file has to store a page of several trays, and say where
each one is. Eight edits in `src/nanolance/page_file.py` (from here on,
docstring-only changes at a checkpoint are left out — `compare.sh`
ignores docstrings):

1. Replace the three `nanolance` imports (lines 16–18) with these four:

   ```python
   from nanolance import encodings, shapes
   from nanolance.counting import CountingFile
   from nanolance.orders import COLUMNS, Row, pack_value
   from nanolance.shapes import OFFSET, Kind, Value
   ```

2. Raise the format version (line 29):

   ```python
   VERSION = 3  # 3: a page may hold several trays
   ```

3. Replace the `Page` class (lines 32–45) with a new `Tray` class and a
   `Page` with a fifth field:

   ```python
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
   ```

4. In `Metadata`, a column's kind is no longer always a codec. Replace
   its `codecs` line (line 59, now around line 79) with

   ```python
       codecs: dict[str, Kind]
   ```

5. Replace the beginning of `write` — from `def write(` (around line
   101 now) down to the page loop's `out.write(data)` (around line 127) —
   with three new helpers and a new beginning for `write`. The
   metadata and footer code below the loop stays:

   ```python
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
           used, stored = pack(name, codec, plain)
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
   ```

6. Further down in `write`, three lines of the metadata change — a
   column's format comes from its kind, and each page's entry from
   `entry` (lines 114–117, now around line 169):

   ```python
   def write(
       ⋮
           metadata = {
               "rows": len(rows),
               "columns": [
                   {
                       "name": column,
                       # ──────── replacement starts here (around line 169) ────────
                       "format": shapes.format_of(kind),
                       "pages": [entry(page) for page in pages[column]],
                       # ──────── replacement ends here ────────
                   }
                   # ──────── replacement starts here (around line 172) ────────
                   for column, kind in columns.items()
                   # ──────── replacement ends here ────────
               ],
           }
   ```

7. Replace `read_page` (lines 127–142, now around line 182) with a new
   `read_page` and, below it, `read_string`:

   ```python
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
   ```

8. At the end of `read_metadata`, two lines read kinds and pages
   differently (lines 208–209, now around line 291), and a helper
   follows the function:

   ```python
   def read_metadata(f: CountingFile) -> Metadata:
       ⋮
       return Metadata(
           version=version,
           rows=metadata["rows"],
           # ──────── replacement starts here (around line 291) ────────
           codecs={c["name"]: shapes.kind_of(c["format"]) for c in columns},
           pages={c["name"]: [page_from(page) for page in c["pages"]] for c in columns},
           # ──────── replacement ends here ────────
       )


   # ──────── new code starts here (around line 296) ────────
   def page_from(fields: dict) -> Page:
       """A page from its metadata entry; entries without trays get none."""
       trays = tuple(Tray(**tray) for tray in fields.pop("trays", []))
       return Page(**fields, trays=trays)
   # ──────── new code ends here ────────
   ```

- **`Tray`** is one buffer: its name, size, `count` of fixed-width
  values (a bit-packed decoder needs it), and its own packing note.
  `pack_page` packs each tray on its own — `"smallest"` runs the
  [weigh-in](story.md#weigh-in) once per tray.

- **The version.** Trays change what a file means, so it is 3.
  `page_from` gives an entry without `trays` an empty tuple, so version 1
  and 2 files read as one-tray pages (a test below proves it). Sections
  C and D add trays to version 3 before the day ends.

Now the demo. In `src/nanolance/cli.py`, three edits:

1. Below the `from nanolance.page_file import …` line (line 21):

   ```python
   from nanolance.shapes import STRING, fixed_values
   ```

2. Between the end of `packing` and `def shapes` (around line 293), two
   helpers:

   ```python
   # ──────── new code starts here (around line 293) ────────
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
       "offsets plain 4040 + data plain 6250"."""
       totals = Counter()
       for page in boxes:
           for tray in page.trays:
               totals[f"{tray.name} {tray.encoding}"] += tray.size
       return " + ".join(f"{tray} {size}" for tray, size in totals.items())


   # ──────── new code ends here ────────
   ```

3. At the end of `shapes` (around line 352), after the average:

   ```python
       # ──────── new code starts here (around line 352) ────────
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
       # ──────── new code ends here ────────
   ```

`read_back` reads every column using only the file. `tray_bytes` adds
up a column's trays by name and note; `Counter` starts a new key at 0.
The demo stores Day 3's orders with `name` as a string —
`{**COLUMNS, "name": STRING}` — once plain and once weighed. Then it
stores the shop's own names, and fetches one name both ways. Both
one-name reads start from a page the picker already knows, so the tally
counts only the value.

Run it:

```bash
uv run nanolance shapes
```

```text
the orders as the shop sends them: 8 rows
  (101, 4.25, 3, 'bolts', ['bulk'])
  (102, 12.5, 1, 'hammer', [])
  (103, None, 40, 'washers', ['bulk', 'small parts'])
  (104, 7.0, 2, 'tape', [])
  (105, 23.5, 1, 'drill bits Ø6', ['fragile'])
  (106, 3.25, 12, 'nails', ['bulk'])
  (107, None, 4, 'gloves', [])
  (108, 15.0, 2, 'padlock', ['gift', 'fragile'])
names of Day 3's 1000 orders, in 12-byte slots: 12000 bytes, 6250 of them letters, 5750 padding
pack 'drill bits Ø6' as a name: refused, name needs 14 bytes; the slot holds 12
pack None as a price: refused, required argument is not a float
  stored as 0.0 instead: the cheapest order is gloves at 0.0
  and the average price is 8.19; the 6 known prices average 10.92
──── everything above: section A's output, unchanged ────
the same names as strings (in slots: plain 12000, smallest 2000):
  strings.bin: 10290 bytes = offsets plain 4040 + data plain 6250
    read back, told nothing: same as the table? True
  strings-smallest.bin: 6765 bytes = offsets bit-packed 1280 + data bit-packed 5485
    read back, told nothing: same as the table? True
the shop's names as strings, read back: ['bolts', 'hammer', 'washers', 'tape', 'drill bits Ø6', 'nails', 'gloves', 'padlock']
one name, row 4, from a box the picker already knows:
  padded.bin: 'drill bits' — tally: reads 1, bytes read 12, seeks 1
  strings.bin: 'drill bits' — tally: reads 2, bytes read 18, seeks 2
```

Read the new lines one by one:

- `the same names as strings (…)` — the yardstick: yesterday's slots,
  plain and weighed (the [lid legend](story.md#lid-legend) won).

- `strings.bin: 10290 bytes = …` — the [letter strip](story.md#letter-strip),
  6250 bytes, plus the end marks: 10 pages × 101 marks × 4 bytes = 4040.
  Plain against plain, 1710 bytes fewer than the slots.

- `strings-smallest.bin: 6765 bytes = …` — each tray weighed on its own:
  a page's end marks never pass 628, and 628 is under 1024 = 2¹⁰, so 10
  bits each instead of 32; every letter is below 128 = 2⁷, so 7 bits
  instead of 8.

- But 6765 is more than the slots' 2000: the lid legend wrote eight names
  once; the strip writes every name every time. A dictionary of *whole*
  strings would remove both padding and repetition — real Lance's (§5),
  not ours.

- `read back … True` (twice), and `drill bits Ø6` among the shop's
  names — every name back, the refused one included.

- `padded.bin: 'drill bits' — tally: reads 1, bytes read 12, seeks 1`
  against `strings.bin: … reads 2, bytes read 18, seeks 2` —
  one trip for two end marks (8 bytes), one for 10 letters. Fewer bytes,
  one more trip — and on a disk or in the cloud, the trip is what costs.

Now the other direction: yesterday's reader meeting a version 3 file.
Save Day 3's `page_file.py` next to the warehouse files and point it at
`strings.bin`:

```bash
git show v1-day-03:src/nanolance/page_file.py > warehouse/day3_page_file.py
uv run python - <<'EOF'
import sys
from pathlib import Path

sys.path.insert(0, "warehouse")
import day3_page_file
from nanolance.counting import CountingFile

day3_page_file.read_metadata(CountingFile(Path("warehouse/strings.bin")))
EOF
```

```text
Traceback (most recent call last):
  File "<stdin>", line 8, in <module>
  File "/…/build-nano-lance-in-python/warehouse/day3_page_file.py", line 192, in read_metadata
    raise ValueError(
ValueError: nanolance file version 3; this reader reads versions 1 to 2
```

Yesterday's reader saw edition 3 and [turned around](story.md#stamp),
instead of misreading a box of trays.

Pin it all with tests — six edits in three files, all made by one
checkout of the finished test files:

```bash
git checkout v1-day-04b -- tests/test_shapes.py tests/test_page_file.py tests/test_cli.py
```

<details>
<summary>Copy-friendly: what the six edits are, with two of the tests (click to open)</summary>

1. A new `tests/test_shapes.py`, twelve tests. Its heart is the round
   trip — six pages through the trays and back, from no values to a
   70,000-byte name, past what a 2-byte offset could reach:

   ```python
   STRING_PAGES = {
       "no values": [],
       "empty strings": ["", "tape", ""],
       "unicode": ["drill bits Ø6", "螺丝", "🔩 bolts", "café"],
       "a 12-byte name": ["washers 50mm"],
       "a 70000-byte name": ["x" * 70_000],
       "the shop's names": [row[3] for row in TAGGED_ORDERS],
   }


   @pytest.mark.parametrize("values", STRING_PAGES.values(), ids=STRING_PAGES.keys())
   def test_strings_give_back_exactly_what_went_in(values):
       trays = shapes.trays(STRING, values)
       assert list(trays) == ["offsets", "data"]
       assert shapes.values_from(STRING, trays) == values
   ```

2. In `tests/test_page_file.py`, the imports on lines 7–8 gain
   `TAGGED_ORDERS`, `Tray`, and `STRING`.

3. In `tests/test_page_file.py`, `test_another_version_is_refused` used
   version 3 as "another version" — now ours — so it uses version 4.

4. At the bottom of `tests/test_page_file.py`, four tests: a page's exact
   trays, a version 2 file made by rewriting today's footer, the refusal
   of packed trays, and the two trips of `read_string`:

   ```python
   def test_one_string_costs_two_reads_its_offsets_then_its_bytes(tmp_path):
       path = tmp_path / "names.bin"
       names = [(row[3],) for row in TAGGED_ORDERS]
       page = page_file.write(path, names, columns={"name": STRING})["name"][0]
       with CountingFile(path) as f:
           assert page_file.read_string(f, page, 4) == "drill bits Ø6"
           assert (f.reads, f.bytes_read, f.seeks) == (2, 8 + 14, 2)
   ```

5. In `tests/test_cli.py`, `test_pages_opens_the_file_from_its_footer`
   expects `version 2` twice (lines 100 and 103): now `version 3`. Day 2's
   demo writes the same bytes as before, apart from the version.

6. At the bottom of `tests/test_cli.py`,
   `test_shapes_stores_names_as_strings` pins the nine new lines of the
   run above, word for word.

</details>

```bash
uv run pytest -q
```

```text
........................................................................ [ 68%]
.................................                                        [100%]
105 passed in 0.64s
```

A hundred and five tests: seventeen more — twelve for the trays, four
for the page file, one for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-04b`

### Section C — bundles: lists, as offsets into strings

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/stdtypes.html#truth-value-testing"><code>not row[4]</code>: an empty list counts as false</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#boolean-type-bool"><code>sum(not x for …)</code>: <code>True</code> adds up as 1, so this counts</a>
</div>

A list of strings needs one more set of offsets on top of a string
column: where each order's list ends, counted in **items** — a
[bundle](story.md#bundles) per order. Seven edits in
`src/nanolance/shapes.py`:

1. Below `STRING = "string"` (line 19), the name of the new kind:

   ```python
   STRING_LIST = "list<string>"
   ```

2. Replace the `Value` line (line 24) — a value may now be a list:

   ```python
   Value = int | float | str | list[str]
   ```

3. In `kind_of`, replace `if format_name == STRING:` (line 29) with

   ```python
       if format_name in (STRING, STRING_LIST):
   ```

4. Between `strings_from` and `fixed_tray` (around line 75):

   ```python
   # ──────── new code starts here (around line 75) ────────
   def list_trays(values: list[list[str]]) -> dict[str, bytes]:
       """Analogy: bundles — each order's tags tied together, every bundle's
       tags on one letter strip, and a mark where each bundle ends.

       Three trays: "list offsets" (len(values) + 1 of them, counted in items),
       then every item of every list, stored as string_trays stores strings.
       """
       items = [item for value in values for item in value]
       return {
           "list offsets": offsets([len(value) for value in values]),
           **string_trays(items),
       }


   def lists_from(trays: dict[str, bytes]) -> list[list[str]]:
       """The lists back: the items first, then cut by the list offsets."""
       items = strings_from(trays)
       return [items[start:stop] for start, stop in spans(trays["list offsets"])]


   # ──────── new code ends here ────────
   ```

5. In `trays`, after the string branch (around line 132):

   ```python
   def trays(kind: Kind, values: list[Value]) -> dict[str, bytes]:
       ⋮
       if kind == STRING:
           return string_trays(values)
       # ──────── new code starts here (around line 132) ────────
       if kind == STRING_LIST:
           return list_trays(values)
       # ──────── new code ends here ────────
       return {"values": fixed_tray(kind, values)}
   ```

6. In `tray_codec`, list offsets are offsets too. Replace
   `if name == "offsets":` (line 114, now around line 139) with

   ```python
       if name in ("list offsets", "offsets"):
   ```

7. In `values_from`, after the string branch (around line 150):

   ```python
   def values_from(kind: Kind, trays: dict[str, bytes]) -> list[Value]:
       ⋮
       if kind == STRING:
           return strings_from(trays)
       # ──────── new code starts here (around line 150) ────────
       if kind == STRING_LIST:
           return lists_from(trays)
       # ──────── new code ends here ────────
       return fixed_values(kind, trays["values"])
   ```

`list_trays` puts one tray, the **list offsets**, in front of the
items' two string trays; `lists_from` cuts the items at those offsets.
An empty list is two equal offsets. `page_file.py` needs no change: it
already handles any number of trays.

The demo needs more orders. At the bottom of `src/nanolance/orders.py`
(around line 90):

```python
# ──────── new code starts here (around line 90) ────────
def many_tagged_orders(n_rows: int) -> list[TaggedRow]:
    """Analogy: a busy week of the shop's real orders.

    `n_rows` orders with ids 101, 102, 103, ...; order k repeats the price,
    quantity, name, and tags of TAGGED_ORDERS[k % 8].
    """
    return [
        (101 + k, *TAGGED_ORDERS[k % len(TAGGED_ORDERS)][1:]) for k in range(n_rows)
    ]


# ──────── new code ends here ────────
```

Then three edits in `src/nanolance/cli.py`:

1. Replace the `from nanolance.shapes import …` line (line 22) with

   ```python
   from nanolance.shapes import OFFSET, STRING, STRING_LIST, fixed_values, list_trays
   ```

2. In the `from nanolance.orders import (` block, below `many_orders,`
   (line 18):

   ```python
   from nanolance.orders import (
       ⋮
       many_orders,
       # ──────── new code starts here (around line 19) ────────
       many_tagged_orders,
       # ──────── new code ends here ────────
       pack_value,
   )
   ```

3. At the end of `shapes` (around line 390), after the one-name reads:

   ```python
       # ──────── new code starts here (around line 390) ────────
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
       # ──────── new code ends here ────────
   ```

The demo prints one box of tags tray by tray, then stores a thousand
orders' tags, plain and weighed. Run it:

```bash
uv run nanolance shapes
```

```text
⋮ (sections A and B print their 23 lines first, unchanged)
──── new: section C's lines ────
the shop's tags as one box of lists, tray by tray:
  list offsets: [0, 1, 1, 3, 3, 4, 5, 5, 7]
  offsets: [0, 4, 8, 19, 26, 30, 34, 41]
  data: b'bulkbulksmall partsfragilebulkgiftfragile'
tags of 1000 shop orders: 875 tags, 375 empty lists
  tags.bin: 12705 bytes = list offsets plain 4040 + offsets plain 3540 + data plain 5125
    read back, told nothing: same as the table? True
  tags-smallest.bin: 6465 bytes = list offsets bit-packed 900 + offsets bit-packed 1065 + data bit-packed 4500
    read back, told nothing: same as the table? True
```

Read it line by line:

- `list offsets: [0, 1, 1, 3, 3, 4, 5, 5, 7]` — the bundle marks, nine
  for eight orders, counted in tags: order 0's bundle is tags 0 to 1
  (`bulk`), order 1's is 1 to 1 — empty — and order 2's is 1 to 3
  (`bulk`, `small parts`).

- `offsets` and `data` — the seven tags as a string column, as in
  section B: tag 2, `small parts`, is bytes 8 to 19 of the
  [letter strip](story.md#letter-strip).

- `tags.bin: 12705 bytes = …` — 101 list offsets per page, one offset
  per tag plus one per page ((875 + 10) × 4 = 3540), and the letters;
  the 375 empty bundles cost only their list offsets.

- `tags-smallest.bin: 6465 bytes = …` — the list offsets never pass 88
  in a page, and 88 < 128 = 2⁷, so 7 bits each. Both files read back.

Pin it with tests — four edits in two files, all made by one checkout:

```bash
git checkout v1-day-04c -- tests/test_shapes.py tests/test_cli.py
```

<details>
<summary>Copy-friendly: what the four edits are, with one of the tests (click to open)</summary>

1. In `tests/test_shapes.py`, line 5 imports `STRING_LIST` too.

2. `test_a_kind_is_recorded_by_its_format` gains a line for
   `STRING_LIST`.

3. At the bottom of `tests/test_shapes.py`, seven tests: one exact
   layout — where `[]` and `[""]` must stay different — and six pages
   through the trays and back, including only empty lists and a list of
   a thousand tags. The layout test:

   ```python
   def test_a_list_is_offsets_into_its_items():
       trays = shapes.list_trays([["bulk"], [], ["a", ""]])
       assert trays == {
           "list offsets": offsets_of(0, 1, 1, 3),  # counted in items
           "offsets": offsets_of(0, 4, 5, 5),  # counted in bytes
           "data": b"bulka",
       }
   ```

4. At the bottom of `tests/test_cli.py`, `test_shapes_stores_tags_as_lists`
   pins the nine new lines of the run above.

</details>

```bash
uv run pytest -q
```

```text
........................................................................ [ 63%]
.........................................                                [100%]
113 passed in 0.72s
```

A hundred and thirteen tests: eight more — seven for the trays, one
for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-04c`

### Section D — the roll call: missing values, and the whole table

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/library/stdtypes.html#dict.update"><code>dict.update</code>: adds another dict's entries to this one</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#bytes"><code>bytes(n)</code>: n zero bytes</a>
<a href="https://docs.python.org/3.12/library/stdtypes.html#common-sequence-operations"><code>[None, 4.25] * 5</code>: a list repeated five times, end to end</a>
</div>

A page with a missing value gets one more tray in front, a
[roll call](story.md#roll-call) of one bit per value. Every other tray
keeps an empty place for the missing value, so value *k* stays value
*k* in every tray. Six edits
in `src/nanolance/shapes.py`:

1. Replace the `Value` line (line 26) — a value may now be missing:

   ```python
   Value = int | float | str | list[str] | None  # None: missing
   ```

2. Between `lists_from` and `fixed_tray` (around line 95), the roll call
   and its reader:

   ```python
   # ──────── new code starts here (around line 95) ────────
   def roll_call(values: list[Value]) -> bytes:
       """Analogy: the roll call — one answer per value: present, or absent.

       A validity bitmap: bit k is 1 when value k is present (not None), bit 0
       in the lowest bit of the first byte, as in Arrow; len(values) bits,
       rounded up to whole bytes.
       """
       bits = 0
       for position, value in enumerate(values):
           if value is not None:
               bits |= 1 << position
       return bits.to_bytes((len(values) + 7) // 8, "little")


   def present(raw: bytes, rows: int) -> list[bool]:
       """For each of `rows` values, whether the validity bitmap marks it present."""
       bits = int.from_bytes(raw, "little")
       return [(bits >> position) & 1 == 1 for position in range(rows)]


   # ──────── new code ends here ────────
   ```

3. In `fixed_tray`, a missing value takes its width in zero bytes. At the
   top of the loop (around line 125):

   ```python
   def fixed_tray(codec: struct.Struct, values: list[Value]) -> bytes:
       ⋮
       parts = []
       for value in values:
           # ──────── new code starts here (around line 125) ────────
           if value is None:
               parts.append(bytes(codec.size))
               continue
           # ──────── new code ends here ────────
           if isinstance(value, str):
   ```

4. In `trays`, replace the body below the docstring (lines 130–134, now
   around line 157) with one that builds the trays in a dict, roll call
   first:

   ```python
   def trays(kind: Kind, values: list[Value]) -> dict[str, bytes]:
       ⋮
       # ──────── replacement starts here (around line 157) ────────
       stored = {}
       if None in values:
           stored["validity"] = roll_call(values)
       if kind == STRING:
           stored.update(string_trays(["" if v is None else v for v in values]))
       elif kind == STRING_LIST:
           stored.update(list_trays([[] if v is None else v for v in values]))
       else:
           stored["values"] = fixed_tray(kind, values)
       return stored
       # ──────── replacement ends here ────────
   ```

5. In `tray_codec`, the roll call is made of bytes, like text. Replace
   `if name == "data":` (line 141, now around line 173) with

   ```python
       if name in ("data", "validity"):
   ```

6. In `values_from`, replace the body below the docstring (lines 148–152,
   now around line 181) with one that hides what the roll call marks
   missing:

   ```python
   def values_from(kind: Kind, trays: dict[str, bytes]) -> list[Value]:
       ⋮
       # ──────── replacement starts here (around line 181) ────────
       if kind == STRING:
           values = strings_from(trays)
       elif kind == STRING_LIST:
           values = lists_from(trays)
       else:
           values = fixed_values(kind, trays["values"])
       if "validity" in trays:
           here = present(trays["validity"], len(values))
           values = [
               v if is_here else None for v, is_here in zip(values, here, strict=True)
           ]
       return values
       # ──────── replacement ends here ────────
   ```

`roll_call` uses Day 3's bit-packing trick: one big whole number, bit
*k* set when value *k* is present, written lowest byte first — Arrow's
order. `trays` writes one only when `None in values`.

The roll call stays plain, whatever the column asks for. In
`src/nanolance/page_file.py`, in `pack_page`'s tray loop, replace the
`used, stored = pack(name, codec, plain)` line (line 125) with two:

```python
def pack_page(
    ⋮
    for tray_name, plain in plain_trays.items():
        codec = shapes.tray_codec(kind, tray_name)
        # ──────── replacement starts here (around line 125) ────────
        choice = "plain" if tray_name == "validity" else name  # bitmaps stay plain
        used, stored = pack(choice, codec, plain)
        # ──────── replacement ends here ────────
```

Why plain? It is one bit per value, next to a price's 64, and plain
keeps "is value *k* here?" arithmetic: bit *k* is in byte *k* ÷ 8.

Now the whole table. In `src/nanolance/orders.py`, two edits:

1. Below `import struct` (line 3):

   ```python
   from nanolance.shapes import STRING, STRING_LIST
   ```

2. Between the closing `]` of `TAGGED_ORDERS` (line 53, now around line
   55) and `def pack_value`:

   ```python
   # ──────── new code starts here (around line 57) ────────
   # Day 4's table as a page file stores it: the same id, price, and qty as
   # COLUMNS; name becomes a string of any length; tags a list of strings.
   TAGGED_COLUMNS = {**COLUMNS, "name": STRING, "tags": STRING_LIST}


   # ──────── new code ends here ────────
   ```

And the demo, in `src/nanolance/cli.py` — five edits:

1. In the `from nanolance.orders import (` block, above `TAGGED_ORDERS,`
   (line 16):

   ```python
   from nanolance.orders import (
       ⋮
       ROW_WIDTH,
       # ──────── new code starts here (around line 16) ────────
       TAGGED_COLUMNS,
       # ──────── new code ends here ────────
       TAGGED_ORDERS,
       ⋮
   )
   ```

2. Replace the `from nanolance.shapes import …` line (line 23) — one
   more name makes it too long for one line:

   ```python
   from nanolance.shapes import (
       OFFSET,
       STRING,
       STRING_LIST,
       Value,
       fixed_values,
       list_trays,
   )
   ```

3. In `tray_bytes`, a column whose pages have no trays — `id` and `qty`
   in the whole table — counts each page under its own packing note. At
   the top of the loop (around line 321):

   ```python
   def tray_bytes(boxes: list[Page]) -> str:
       ⋮
       totals = Counter()
       for page in boxes:
           # ──────── new code starts here (around line 321) ────────
           if not page.trays:
               totals[page.encoding] += page.size
           # ──────── new code ends here ────────
           for tray in page.trays:
   ```

4. Between `tray_bytes` and `shapes` (around line 329), a question asked
   of a fresh open:

   ```python
   # ──────── new code starts here (around line 329) ────────
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


   # ──────── new code ends here ────────
   ```

5. At the end of `shapes` (around line 438):

   ```python
       # ──────── new code starts here (around line 438) ────────
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
       # ──────── new code ends here ────────
   ```

`ask` is Day 3's `ask_qty` for any column. The demo writes the whole
table, every column weighed, and asks three questions. Run it:

```bash
uv run nanolance shapes
```

```text
⋮ (sections A to C print their 32 lines first, unchanged)
──── new: section D's lines ────
write shop.bin: 26169 bytes, every column packed smallest
  id: 1212 = bit-packed 1212
  price: 1730 = validity plain 130 + values dictionary 1600
  qty: 760 = bit-packed 760
  name: 8030 = offsets bit-packed 1280 + data plain 6750
  tags: 6465 = list offsets bit-packed 900 + offsets bit-packed 1065 + data bit-packed 4500
  read back, told nothing: same as the table? True
sum(qty) from shop.bin, told nothing = 8125
  tally: reads 12, bytes read 8732, seeks 12 (opening 7972, pages 760)
average price from shop.bin = 10.92, 250 missing
  tally: reads 12, bytes read 9702, seeks 12 (opening 7972, pages 1730)
names of rows 10–19 from shop.bin = ['washers', 'tape', 'drill bits Ø6', 'nails', 'gloves', 'padlock', 'bolts', 'hammer', 'washers', 'tape']
  tally: reads 3, bytes read 8770, seeks 3 (opening 7972, pages 798)
```

Read it line by line:

- `write shop.bin: …` — all five columns in one file. `id` and `qty`
  have nothing missing, so no trays: yesterday's pages exactly.

- `price: 1730 = validity plain 130 + …` — the
  [roll call](story.md#roll-call), 13 bytes a page; the dictionary's
  legend holds a 0.0 that the roll call hides.

- `name: … data plain 6750` — `Ø`'s two bytes are above 127, so letters
  need all 8 bits and stay plain. The whole table reads back `True`.

- `sum(qty) … = 8125` — the [stock count](story.md#stock-count): the
  same 760 bytes of pages as yesterday. But the opening is 7972 bytes,
  three times yesterday's 2668: partly the new tags column, mostly one
  box-list line per tray (in the two files' metadata, 2709 of the 5304
  extra bytes are the tags column's, 2594 are price's and name's new
  tray lines). With Lance's recommended 8 MB pages that would be a
  sliver; here it is most of a small question — the cost §5's
  per-column metadata avoids, left deliberately naive here.

- `average price from shop.bin = 10.92, 250 missing` — the honest
  answer section A could not give; 130 of its 1730 page bytes are the
  roll call, the whole cost of knowing. Ten names read 798 bytes: one
  page, its two trays in one trip.

Pin it with tests — four edits in three files, all made by one checkout:

```bash
git checkout v1-day-04d -- tests/test_shapes.py tests/test_page_file.py tests/test_cli.py
```

<details>
<summary>Copy-friendly: what the four edits are, with one of the tests (click to open)</summary>

1. At the bottom of `tests/test_shapes.py`, eight tests: all-missing
   pages of each kind, `None` next to `""` and `[]`, missing prices
   across a byte boundary, and the bitmap itself — with the example
   from Arrow's own documentation:

   ```python
   def test_the_validity_bitmap_has_one_bit_per_value_lowest_bit_first():
       values = [0, 1, None, 2, None, 3]  # the example in Arrow's documentation
       assert shapes.roll_call(values) == bytes([0b00101011])
       assert shapes.present(bytes([0b00101011]), 6) == [
           True,
           True,
           False,
           True,
           False,
           True,
       ]
   ```

2. In `tests/test_page_file.py`, the `from nanolance.orders import` line
   (line 7) gains `TAGGED_COLUMNS` and `many_tagged_orders`.

3. At the bottom of `tests/test_page_file.py`, two tests: a page of 100
   missing prices (its roll call plain, its 100 zeros one
   [stack](story.md#stacks)), and the whole table, plain and weighed.

4. At the bottom of `tests/test_cli.py`,
   `test_shapes_stores_the_shop_table_with_its_missing_prices` pins the
   thirteen new lines of the run above.

</details>

```bash
uv run pytest -q
```

```text
........................................................................ [ 58%]
....................................................                     [100%]
124 passed in 0.83s
```

A hundred and twenty-four tests: eleven more — eight for the trays, two
for the page file, and one for the demo.

**Section checkpoint:** `./scripts/compare.sh v1-day-04d` — which is
also the finished day.

## 7. Run it

```bash
uv run nanolance shapes
```

## 8. Expected result

```text
the orders as the shop sends them: 8 rows
  (101, 4.25, 3, 'bolts', ['bulk'])
  (102, 12.5, 1, 'hammer', [])
  (103, None, 40, 'washers', ['bulk', 'small parts'])
  (104, 7.0, 2, 'tape', [])
  (105, 23.5, 1, 'drill bits Ø6', ['fragile'])
  (106, 3.25, 12, 'nails', ['bulk'])
  (107, None, 4, 'gloves', [])
  (108, 15.0, 2, 'padlock', ['gift', 'fragile'])
names of Day 3's 1000 orders, in 12-byte slots: 12000 bytes, 6250 of them letters, 5750 padding
pack 'drill bits Ø6' as a name: refused, name needs 14 bytes; the slot holds 12
pack None as a price: refused, required argument is not a float
  stored as 0.0 instead: the cheapest order is gloves at 0.0
  and the average price is 8.19; the 6 known prices average 10.92
the same names as strings (in slots: plain 12000, smallest 2000):
  strings.bin: 10290 bytes = offsets plain 4040 + data plain 6250
    read back, told nothing: same as the table? True
  strings-smallest.bin: 6765 bytes = offsets bit-packed 1280 + data bit-packed 5485
    read back, told nothing: same as the table? True
the shop's names as strings, read back: ['bolts', 'hammer', 'washers', 'tape', 'drill bits Ø6', 'nails', 'gloves', 'padlock']
one name, row 4, from a box the picker already knows:
  padded.bin: 'drill bits' — tally: reads 1, bytes read 12, seeks 1
  strings.bin: 'drill bits' — tally: reads 2, bytes read 18, seeks 2
the shop's tags as one box of lists, tray by tray:
  list offsets: [0, 1, 1, 3, 3, 4, 5, 5, 7]
  offsets: [0, 4, 8, 19, 26, 30, 34, 41]
  data: b'bulkbulksmall partsfragilebulkgiftfragile'
tags of 1000 shop orders: 875 tags, 375 empty lists
  tags.bin: 12705 bytes = list offsets plain 4040 + offsets plain 3540 + data plain 5125
    read back, told nothing: same as the table? True
  tags-smallest.bin: 6465 bytes = list offsets bit-packed 900 + offsets bit-packed 1065 + data bit-packed 4500
    read back, told nothing: same as the table? True
write shop.bin: 26169 bytes, every column packed smallest
  id: 1212 = bit-packed 1212
  price: 1730 = validity plain 130 + values dictionary 1600
  qty: 760 = bit-packed 760
  name: 8030 = offsets bit-packed 1280 + data plain 6750
  tags: 6465 = list offsets bit-packed 900 + offsets bit-packed 1065 + data bit-packed 4500
  read back, told nothing: same as the table? True
sum(qty) from shop.bin, told nothing = 8125
  tally: reads 12, bytes read 8732, seeks 12 (opening 7972, pages 760)
average price from shop.bin = 10.92, 250 missing
  tally: reads 12, bytes read 9702, seeks 12 (opening 7972, pages 1730)
names of rows 10–19 from shop.bin = ['washers', 'tape', 'drill bits Ø6', 'nails', 'gloves', 'padlock', 'bolts', 'hammer', 'washers', 'tape']
  tally: reads 3, bytes read 8770, seeks 3 (opening 7972, pages 798)
```

Nothing here varies between runs: no randomness, no timing, only counts.

## 9. Test it

`uv run pytest -q` now runs a hundred and twenty-four tests — the
`124 passed` of section D. That is Day 3's 87 plus 37 new ones: the
felt problems (section A, 1 test), strings and trays (section B, 17),
lists (section C, 8), and missing values (section D, 11). A hundred and
seven are unit tests; the other seventeen (`test_cli_says_hello` and the
sixteen in `test_cli.py`) run the real command line.

## 10. Break it deliberately

Write the roll call's bytes in the wrong order. In `roll_call` in
`src/nanolance/shapes.py`, change one word:

```diff
@@ src/nanolance/shapes.py, around line 107 @@
         if value is not None:
             bits |= 1 << position
-    return bits.to_bytes((len(values) + 7) // 8, "little")
+    return bits.to_bytes((len(values) + 7) // 8, "big")
```

`present` still reads the bytes lowest first, so the writer and the
reader now disagree about which byte is which. Run the tests:

```bash
uv run pytest -q --tb=line
```

```text
E   AssertionError: assert ['write shop....ed 4500', ...] == ['write shop....ed 4500', ...]
E   AssertionError: assert [(101, 4.25, ...'bulk']), ...] == [(101, 4.25, ...'bulk']), ...]
E   assert [None, 4.25, ...ne, None, ...] == [None, 4.25, ...ne, 4.25, ...]
```

(Only the `E` lines are shown — one per failing test. Pytest's summary
line reads `3 failed, 121 passed`.)

The demo, the whole table, and the ten prices across a byte boundary
fail. The passing tests are the lesson: a page of eight values or fewer
is one byte, the same in either order, and an all-missing page is zeros
either way. Here are §4's ten prices — before the change, this command
printed the first output below:

```bash
uv run python -c 'from nanolance.shapes import roll_call; print(roll_call([None, 4.25] * 5).hex(" "))'
```

```text
aa 02
```

That is `"little"`: byte 0 is `aa` (`0b10101010`, values 0–7), byte 1
is `02` (values 8 and 9). With `"big"`, it prints:

```text
02 aa
```

The bytes swap: the reader takes `02` for values 0–7, so 3, 5, and 7
read as absent.

And how quietly the demo goes wrong — its `shop.bin` lines:

```bash
uv run nanolance shapes
```

```text
write shop.bin: 26169 bytes, every column packed smallest
  read back, told nothing: same as the table? False
average price from shop.bin = 10.92, 280 missing
  tally: reads 12, bytes read 9702, seeks 12 (opening 7972, pages 1730)
```

No error, and 280 prices missing instead of 250: thirty real prices
gone. By luck the average stays 10.92 — a wrong answer that looks
right. **A validity bitmap is correct only if
writer and reader agree on two orders: which byte holds values 0–7, and
which bit inside it is value 0.** Arrow writes both down.

Change `"big"` back and confirm `uv run pytest -q` is green again.

## 11. Checkpoint

Every checkpoint is done only when the full green bar passes:

```bash
./scripts/check.sh
```

```text
29 files already formatted
All checks passed!
........................................................................ [ 58%]
....................................................                     [100%]
124 passed in 0.83s
nanolance 0.1.0: scaffold is alive
⋮ (Day 1's `nanolance layouts` output, unchanged) ⋮
⋮ (Day 2's `nanolance pages` output: version 3 now) ⋮
⋮ (Day 3's `nanolance packing` output, unchanged) ⋮
⋮ (the §8 output, unchanged) ⋮
 INFO Book building has started
 INFO Running the html backend
 INFO HTML book written to `/…/build-nano-lance-in-python/book/book`
GREEN: all gates passed
```

Formatting, lints, the 124 tests, the smoke gate's four demos — now
including `nanolance shapes` — and the book build all pass.

The smoke gate gained one line today: `uv run --locked nanolance shapes
"$scratch"`. `scripts/check.sh` is course infrastructure, outside what
`compare.sh` checks; to pick up today's copy, take it from the
checkpoint:

```bash
git checkout v1-day-04 -- scripts/check.sh
```

Then close out the day in whichever mode you are following:

**Built along on your own branch?** Confirm your code matches the finished
day — the final ✓ line means it does:

```bash
./scripts/compare.sh v1-day-04
```

**Inspecting instead of typing?** Jump to today's exact finished state,
poke at it, and come back:

```bash
git switch --detach v1-day-04
uv run nanolance shapes
git switch -          # back to where you were
```

**Either way**, today's complete change set — docs included — reads as one
diff:

```bash
git diff v1-day-03 v1-day-04
```

## 12. Recap

**What changed today:** a new `shapes.py` (strings, lists, and the
roll call as trays of fixed-width values); in `page_file.py`, `Tray`,
`pack_page`, a `write` for any table's `columns`, `read_page` for trays,
`read_string`, and format `VERSION` 3; the shop's table in `orders.py`;
the `nanolance shapes` demo; and thirty-seven new tests (124 in all),
still with no dependencies.

**Deliberately naive:** 4-byte offsets only (a page's text stops at
4 GiB); dictionaries of tray bytes, never of whole strings; no single
value from a packed tray; full width for a missing number; a plain roll
call even on an all-missing page; lists of strings only; and every open
reads every column's box lists, tray by tray, in wordy JSON.

**Tomorrow, on Day 5:** today's one-name read began from a box the
picker already knew. Tomorrow the picker gets only a row number — order
7,342 — and finds the box, then the value, reading nothing else; and you
count how much less that reads than Parquet-style groups of whole rows. The boxes now hold trays of every shape — see [the
warehouse](story.md); next, the picker learns to go straight to one
order.
