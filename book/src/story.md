# The warehouse: an analogy to help you build the right mental model

Every day of this book adds one scene to a single running story: **a
warehouse.** Each piece of the format you build is one thing in that story
— an aisle, a sealed box, the wall card at the back. Keep the story in
your head, and you can always picture what the code is doing, even on the
days it gets dense.

This page keeps the whole story in one place:

- **Before you start**, read it through once. A few minutes here give you
  a map of where the course is going, and every later chapter will feel
  like a place you have already visited.

- **While you work**, come back whenever a name from an earlier day stops
  making sense. You rarely need to leave the chapter to do that: in the
  chapters, a concept name with a dotted underline is a link to this page,
  and clicking it opens that concept's reminder right where you are
  reading. (Press Esc or click anywhere else to close it.)

- **The page grows with the book.** Every new day adds its scene here, so
  it always covers exactly the days you can read. Day 0 only installs the
  tools, so the warehouse is still empty: its first scene arrives with
  Day 1.

Each reminder has the same three parts: *what it is* in plain words, *in
the story* — the thing it is in the warehouse — and the day that
introduced it, if you want the full explanation again.

| Day | Scene | Concepts it adds |
|-----|-------|------------------|
| 1 | [Crates or aisles](#day-1--crates-or-aisles) | the packing rule, crates, the tally, the stock count, aisles, a customer pickup |
| 2 | [The wall card at the back](#day-2--the-wall-card-at-the-back) | sealed boxes, the box list, the wall card at the back, the stamp |
| 3 | [The packer's bench](#day-3--the-packers-bench) | the packer and packing methods, the lid legend, stacks, snug compartments, the packing note, the weigh-in |
| 4 | [Trays in the box](#day-4--trays-in-the-box) | trays, the letter strip and its end marks, bundles, the roll call |
| 5 | [The pick list](#day-5--the-pick-list) | the pick list, start numbers, pallets, the box size |

## Day 1 — crates or aisles

The warehouse opens, and it stores orders. Each order has four values —
its id, price, quantity, and the item's name — and there are two ways to
shelve them. **Packed in crates**: one crate per order, every
compartment a fixed size, crate after crate along one long shelf. Or
**sorted into aisles**: an aisle of ids, an aisle of prices, an aisle of
quantities, an aisle of names, with spot *k* of every aisle belonging to
order *k*. The picker fetches things for every question and keeps a
tally of every request. The manager's stock count — how many items are on
order? — sends the picker into every crate, but only into one aisle. A
customer collecting one whole order needs one crate, but a stop in every
aisle. Neither shelving wins everything.

<div class="concept" id="packing-rule">

**The packing rule — every value a fixed size** · [Day 1, section A](day-01-rows-vs-columns.md#section-a--the-orders-table-stored-row-by-row)

*What it is:* the list of a table's columns, each with a fixed width in bytes (`COLUMNS`: id 8, price 8, qty 4, name 12 — 32 bytes per row). Because every value of a column has the same size, where any value sits in the file is arithmetic, not a search. Short text is padded to fill its width.

*In the story:* every crate has the same four compartments, each one a fixed size, so "the sixth crate starts five crate-lengths in" is all the picker needs to know.

</div>

<div class="concept" id="row-layout">

**Crates — the row layout** · [Day 1, section A](day-01-rows-vs-columns.md#section-a--the-orders-table-stored-row-by-row)

*What it is:* storing a table row after row: all of row 0's values, then all of row 1's, and so on. One row's values sit together on disk. Most transactional databases store tables this way.

*In the story:* one crate per order, holding all four of that order's values, crates standing in one long line on the shelf.

</div>

<div class="concept" id="tally">

**The tally — counting what a question reads** · [Day 1, section B](day-01-rows-vs-columns.md#section-b--the-tally-what-one-question-reads)

*What it is:* `CountingFile`, a wrapper around a file opened for reading that counts every read, every byte read, and every seek — each time the reader tells the file where to go next, even to the spot it is already at. Every "this reads less" claim in the course is one of these counts, never a stopwatch time.

*In the story:* the picker's clipboard: each armful carried back (a read), how much it weighed (bytes), and each time the picker is told where to go next (a seek) — counted even when the picker happens to be standing there already.

</div>

<div class="concept" id="stock-count">

**The stock count — a scan of one column** · [Day 1, section B](day-01-rows-vs-columns.md#section-b--the-tally-what-one-question-reads)

*What it is:* a question about one column across every row, such as `sum(qty)`. Reading one or more columns for every row is called a *scan*.

*In the story:* the manager asks how many items are on order in all. With crates, the picker opens every crate to reach one compartment; with aisles, the picker walks one aisle.

</div>

<div class="concept" id="column-layout">

**Aisles — the column layout** · [Day 1, section C](day-01-rows-vs-columns.md#section-c--the-same-table-stored-column-by-column)

*What it is:* storing a table column after column: every row's value of column 0, then every row's value of column 1, and so on. Value *k* of each column belongs to row *k*. A question about one column reads only that column. Parquet, ORC, and Lance store data this way.

*In the story:* the same orders unpacked and sorted, one aisle per column: all the ids, then all the prices, the quantities, the names.

</div>

<div class="concept" id="pickup">

**A customer pickup — fetching one whole row** · [Day 1, section D](day-01-rows-vs-columns.md#section-d--fetching-one-whole-row-both-ways)

*What it is:* fetching one row, all its columns, by its position. The row layout does it in one seek and one read; the column layout needs one seek and one read per column. Lance calls fetching rows by position a *take*.

*In the story:* a customer comes to collect one whole order: one crate, or a stop in every aisle.

</div>

## Day 2 — the wall card at the back

A busy week: a thousand orders arrive, and every aisle grows long. A
picker told the wrong number of orders walks to the wrong spot and
carries back the wrong bytes without noticing, and ten orders' worth of
quantities still means carrying the whole aisle. So the warehouse cuts
every aisle into **sealed boxes** of up to 100 values, and for each aisle
keeps a **box list**: where each box sits, how much it weighs, how many
values it holds. The box lists are stored after the last box, and on the
back wall hangs **the wall card** — always the same size, always last —
which says where the box lists are. A picker who knows nothing walks to
the back wall, reads the card, reads the box lists, and carries only the
boxes the question needs. The card carries **the stamp**, the
warehouse's name and edition, so a picker sent to the wrong building
turns around after reading one card.

<div class="concept" id="pages">

**Sealed boxes — pages** · [Day 2, section B](day-02-a-file-of-pages.md#section-b--sealed-boxes-each-column-cut-into-pages)

*What it is:* a run of one column's values — here up to `ROWS_PER_PAGE` = 100 — stored back to back and read in one piece. A question reads only the pages that overlap the rows it asks for. Lance recommends pages of about 8 MB.

*In the story:* each aisle cut into sealed boxes of up to 100 values; the picker carries whole boxes, never half of one, and only the boxes a question needs.

</div>

<div class="concept" id="box-list">

**The box list — column metadata** · [Day 2, section B](day-02-a-file-of-pages.md#section-b--sealed-boxes-each-column-cut-into-pages)

*What it is:* for each column, its value format and one `Page` per page: its offset (first byte), size in bytes, and row count. Section B hands it from the writer to the reader in memory; from section C on it is stored in the file, as JSON, right after the pages. Lance stores it as Protocol Buffers.

*In the story:* one list per aisle — where each box sits, how much it weighs, how many values it holds — kept in the warehouse after the last box.

</div>

<div class="concept" id="wall-card">

**The wall card at the back — the footer** · [Day 2, section C](day-02-a-file-of-pages.md#section-c--the-wall-card-at-the-back)

*What it is:* a fixed-size record (24 bytes, `FOOTER`) at the very end of the file: where the metadata starts, how long it is, the format version, and the magic bytes. Because its size never changes, a reader finds it at the file's size minus 24, and reads it first. It goes last because a writer only knows where everything landed once it is written.

*In the story:* a card of one fixed size on the back wall, the last thing in the warehouse, saying where the box lists are.

</div>

<div class="concept" id="stamp">

**The stamp — magic bytes and a version** · [Day 2, section D](day-02-a-file-of-pages.md#section-d--the-stamp-refusing-a-file-by-name)

*What it is:* the footer's last four bytes, `NLNC`, name the format, and its version field says which edition wrote it. The reader checks both before trusting the footer, and refuses a file that is too short, not ours, of another version, or whose footer points outside it. A file whose writing was interrupted has no footer, so it is refused too. The stamp proves whose file it is — not that its box lists are true.

*In the story:* the warehouse's name and edition, printed on the wall card; a picker at the wrong building turns around after reading one card.

</div>

## Day 3 — the packer's bench

The picker carries boxes out; the packer is the one who fills them in
the first place — and today the packer looks inside and sees waste. Every value sits in a full-size compartment — the
[packing rule](#packing-rule) — so a quantity of 3 takes four bytes, and
a box of a hundred names holds the same eight names over and over, each
with its padding. So the packer learns three new **packing methods**.
**The lid legend**: write each distinct value once on the lid, and put a
one-byte legend number in the box for every value. **Stacks**: equal
values side by side become one value with a sticker saying how many.
**Snug compartments**: cut every compartment down to the size the box's
largest value needs. Each method can make a box *bigger* as easily as
smaller — stacks of one, a legend as long as the box — so every box goes
through **the weigh-in**: the packer packs it every way, weighs each
packing, and keeps the lightest. Each line of
the [box list](#box-list) gains **a packing note** saying how that box
was packed, so the picker unpacks it the same way; the warehouse's
[stamp](#stamp) moves to edition 2, so a picker trained on edition 1
turns around instead of misreading a box.

<div class="concept" id="encodings">

**The packer and packing methods — page encodings** · [Day 3, section B](day-03-encodings.md#section-b--the-lid-legend-a-dictionary-and-a-page-that-names-its-encoding)

*What it is:* an encoding turns one page's *plain* bytes — every value at its column's fixed width, as Day 2 stored them — into other bytes, and a matching decoder turns them back into exactly the same plain bytes. Today's four: plain, dictionary, run-length, and bit-packed (`ENCODINGS` in `encodings.py`). Fewer bytes on disk means fewer bytes read.

*In the story:* the packer at the bench, who fills each box. The plain method is Day 1's packing rule — full-size compartments; the others pack the same values tighter, and a picker can always unpack them back.

</div>

<div class="concept" id="lid-legend">

**The lid legend — dictionary encoding** · [Day 3, section B](day-03-encodings.md#section-b--the-lid-legend-a-dictionary-and-a-page-that-names-its-encoding)

*What it is:* a page stores each distinct value once (the dictionary), then one small code per value — here one byte, so up to 256 distinct values. It wins when a page repeats a few values many times; on a page where every value is different it is larger than plain.

*In the story:* the box's distinct values written once on its lid; inside, each compartment holds only a one-byte legend number pointing at a line of the lid.

</div>

<div class="concept" id="stacks">

**Stacks — run-length encoding** · [Day 3, section C](day-03-encodings.md#section-c--stacks-run-length-and-where-it-backfires)

*What it is:* each *run* — equal values side by side — is stored as one value plus its length. It wins on sorted or slowly changing columns; on a page with no repeats next to each other it doubles the size, because every value gains a length.

*In the story:* equal values side by side stacked together, one value with a sticker saying how many; a stack of one still needs its sticker.

</div>

<div class="concept" id="snug-compartments">

**Snug compartments — bit-packing** · [Day 3, section D](day-03-encodings.md#section-d--snug-compartments-and-the-weigh-in)

*What it is:* whole numbers from 0 up stored in only as many bits as the page's largest value needs (its *bit width*), written once at the start of the page. Forty fits in 6 bits instead of 32. It does not apply to prices, names, or negative numbers.

*In the story:* every compartment in a box cut down to the size its largest value needs.

</div>

<div class="concept" id="packing-note">

**The packing note — each page's encoding, recorded** · [Day 3, section B](day-03-encodings.md#section-b--the-lid-legend-a-dictionary-and-a-page-that-names-its-encoding)

*What it is:* every page's entry in the column metadata now names its encoding (`Page.encoding`), so a reader decodes each page the way it was written. Adding it changed the format, so the version became 2: the new reader still reads version 1 files (all plain), and an old reader refuses version 2 files instead of misreading them.

*In the story:* a note on each line of the box list saying how that box was packed; the stamp moves to edition 2, so a picker trained on edition 1 turns around.

</div>

<div class="concept" id="weigh-in">

**The weigh-in — keep the smallest** · [Day 3, section D](day-03-encodings.md#section-d--snug-compartments-and-the-weigh-in)

*What it is:* for every page, encode with every encoding that accepts its values and store the smallest (`smallest`; a tie keeps plain). Each page of a column may choose differently. The cost is paid when writing: every page is encoded several times to keep one result. Real Lance chooses from cheap statistics instead, such as the number of runs.

*In the story:* the packer packs each box every way at the bench, weighs each packing, keeps the lightest, and throws the rest away.

</div>

## Day 4 — trays in the box

The warehouse's customer, a hardware shop, sends its orders as they
really are, and they reach the packer's bench — where Day 1's
[packing rule](#packing-rule) no longer fits: a name too long for
its compartment, short names rattling in theirs, a bundle of tags on
most orders, and prices nobody has quoted yet. So the packer stops
cutting a box into equal compartments and puts **trays** in it instead —
each tray holding equal compartments, with its own
[packing note](#packing-note), so the lid legend, stacks, and snug
compartments still work on every tray. Names go on **a letter strip**,
every letter back to back, with **end marks** saying where each name
ends; fetching one name now takes the picker two trips — the marks, then
the letters. An order's tags are tied into a **bundle**: every tag on a
letter strip of its own, and one more line of marks saying where each
bundle ends. And a box with something missing gets **a roll call**: one
answer per order, present or absent, while each missing one keeps an empty
place in the other trays. The [stamp](#stamp) moves to edition 3, so a
picker trained on edition 2 turns around.

<div class="concept" id="trays">

**Trays — several buffers in one page** · [Day 4, section B](day-04-strings-lists-nulls.md#section-b--the-letter-strip-and-its-end-marks-strings-in-trays)

*What it is:* a page stored as several buffers back to back, each a run of fixed-width values with its own name, size, value count, and encoding (`Tray`, `Page.trays`), so Day 3's encodings pack every buffer unchanged. A page with a single buffer is stored exactly as on Day 3. Adding trays made the format version 3; the reader still reads versions 1 and 2. A Lance page lists its buffers the same way.

*In the story:* trays inside a box, each holding equal compartments, with its own packing note.

</div>

<div class="concept" id="letter-strip">

**The letter strip and its end marks — offsets and data** · [Day 4, section B](day-04-strings-lists-nulls.md#section-b--the-letter-strip-and-its-end-marks-strings-in-trays)

*What it is:* a variable-length column stored as two buffers: *data*, every value's UTF-8 bytes back to back with no padding, and *offsets*, one more 4-byte offset than there are values — 0, then where each value ends. Value *k* is the data from offset *k* up to offset *k* + 1. Fetching one value takes two reads: its two offsets, then its bytes. This is Apache Arrow's variable-size binary layout.

*In the story:* every name's letters written on one strip, and a line of marks saying where each name ends; one name costs two trips.

</div>

<div class="concept" id="bundles">

**Bundles — list columns** · [Day 4, section C](day-04-strings-lists-nulls.md#section-c--bundles-lists-as-offsets-into-strings)

*What it is:* a list column stored as *list offsets*, counted in items, into one child column of all the items — here a string column, so three buffers in all. An empty list is two equal offsets and takes no item bytes. This is Arrow's variable-size list layout.

*In the story:* an order's tags tied into a bundle; every tag goes on a letter strip, and one more line of marks says where each order's bundle ends.

</div>

<div class="concept" id="roll-call">

**The roll call — a validity bitmap** · [Day 4, section D](day-04-strings-lists-nulls.md#section-d--the-roll-call-missing-values-and-the-whole-table)

*What it is:* one bit per value — 1 when present, 0 when missing (`None`) — with bit 0 in the lowest bit of the first byte, as in Arrow. A missing value keeps an empty place in the page's other buffers, which the bitmap hides. Only a page with a missing value has one, and it is always stored plain. Real Lance expresses the same facts with definition levels instead.

*In the story:* one answer per order — present, or absent; a box with nothing missing has no roll call.

</div>

## Day 5 — the pick list

The shop's orders now fill 10,000 rows, and a customer hands the picker
**a pick list**: ten orders, scattered across the warehouse, in the
customer's own order. The slow way to fill it is a stock count of every
aisle, with every box carried back for ten orders. So the picker learns
**start numbers**. The [box list](#box-list) already says how many orders
each box holds, and adding them up gives the number each box starts at.
Now one look tells the picker which box holds order 7,342, and where in
it. Each box the list needs is carried back once, even when two orders
share it. Across the street, a second warehouse ships its orders on
**pallets**. Each pallet carries a few thousand whole orders, with every
aisle's share wrapped as one piece that must be unwrapped whole. There,
the same ten orders mean unwrapping every pallet. Last, the picker
weighs **the box size**: small boxes suit pick lists, big ones suit
stock counts, and a pallet behaves like any big box.

<div class="concept" id="pick-list">

**The pick list — a take** · [Day 5, section A](day-05-random-access.md#section-a--a-pick-list-filled-by-scanning)

*What it is:* fetching rows by their row numbers — positions in the table, from 0 — in the order asked, repeats allowed, with the columns asked for (`take`). Scanning every column first (`take_by_scan`) reads the whole table for any list. Reading only the pages that hold the rows reads a fraction. Training jobs that sample rows and searches that return row numbers both ask this question.

*In the story:* a customer's list of orders to collect, scattered across the warehouse; a [customer pickup](#pickup) is a pick list of one.

</div>

<div class="concept" id="start-numbers">

**Start numbers — row id to page** · [Day 5, section B](day-05-random-access.md#section-b--start-numbers-only-the-boxes-on-the-list)

*What it is:* the row number of each page's first value, a running total of the pages' row counts (`page_starts`). A row's page is the last one starting at or before it, found by binary search (`locate`, with `bisect_right`), and its place in the page is the row number minus that start. A take reads each page it needs once, and unpacks it on its own.

*In the story:* the number of the first order in every box, added up from the box list; one look says which box holds an order, and where in it.

</div>

<div class="concept" id="pallets">

**Pallets — Parquet-style row groups** · [Day 5, section C](day-05-random-access.md#section-c--pallets-a-parquet-style-row-group-file)

*What it is:* rows cut into groups (here 2,500 rows). Inside a group, each column's values form one *column chunk*, and the chunks are stored group after group (`row_groups.write`). Here each chunk is packed as one unit, so one value costs the whole chunk: Parquet's worst case. Real Parquet can cut chunks into pages, and its optional page index lets a reader reach one page. Lance has no row groups at all.

*In the story:* the warehouse across the street, which ships a few thousand whole orders per pallet, each aisle's share wrapped as one piece that must be unwrapped whole.

</div>

<div class="concept" id="box-size">

**The box size — scan against take** · [Day 5, section D](day-05-random-access.md#section-d--the-box-size-scan-against-take)

*What it is:* rows per page decides what a take and a scan each cost. Small pages make a take read little, but a scan needs many reads and the metadata grows. Big pages are the other way round. For a take, a row group behaves exactly like a page of the same size. Real Lance keeps pages big (about 8 MB) and reads small mini-blocks inside them, to have both.

*In the story:* small boxes for pick lists, big ones for stock counts; a pallet is one more big box.

</div>
