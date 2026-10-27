# The warehouse: an analogy to help you build the right mental model

Every day of this book adds one scene to a single running story: **a
warehouse.** Each piece of the format you build is one thing in that story
— an aisle, a sealed box, the index card at the back. Keep the story in
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
