# Build nano-Lance in Python

Build a tiny columnar data format and a small vector database on top of it —
a nano-[Lance](https://github.com/lance-format/lance) and a
nano-[LanceDB](https://github.com/lancedb/lancedb) — from an empty folder,
in Python, one tested day at a time.

This is the **public preview**: Days 0–5 — the file format, from rows and
columns to random access — are free here, with every checkpoint tag. Days
6–17 (tables and versions, indexes, the database layer) are the Pro
edition. **Status: the free preview is complete — Days 0 to 5 are done.**

## Prerequisites

Some programming experience, in any language — that is the whole list.
${\color{red}\textbf{Python is not a prerequisite}}$: each Python construct
gets a small "Python used here" chip at its first use, linking straight to
the matching page of the official Python docs.
${\color{red}\textbf{Databases and file formats are not a prerequisite}}$:
every idea arrives with a plain-English analogy before any code.
${\color{red}\textbf{Machine learning is not a prerequisite}}$: the vector
days explain what an embedding is when they need one, and the math is never
required to progress. No GPU is needed, ever, and the tests never touch the
network.

## Why Lance?

[Lance](https://github.com/lance-format/lance) is an open-source columnar
format built for machine-learning data: tables of text, images, and
embeddings that a training job reads in random order and a search service
queries by similarity. [LanceDB](https://github.com/lancedb/lancedb) is the
embedded vector database built on top of it. Both are Apache-2.0.

- **Data layout is the quiet half of ML performance.** A training job that
  waits on its data loader, a search that reads ten times the bytes it
  needs, a table that grows slower with every small append — these are
  layout problems, not model problems. Lance is a clear, modern answer to
  them, and its ideas (columns, pages, footers, versioned manifests,
  vector indexes) are the same ones inside Parquet, Delta Lake, Iceberg,
  and every vector database.

- **Lance's answers are small enough to build.** A file of column pages with
  an index at the end; a table that is a list of files plus a manifest per
  version; an index that reads a few clusters instead of everything. Each
  one fits in your head once you have typed it yourself.

- **Using a format teaches its options; building one teaches its
  physics.** After you have written the footer, the deletion file, and the
  vector index with your own hands, "why is this query slow?" stops being
  a guess: you can say how many bytes it should read, and why.

## Why Python?

Fair question — Lance itself is written mostly in Rust (about four-fifths
of its code by GitHub's language count when this course began). Three
honest reasons this course uses Python anyway:

- **The lessons are about layout and I/O, not language.** Which bytes sit
  next to which, how many reads a query needs, what a version records —
  those answers are the same in any language. Python keeps the code short
  enough that the layout stays visible.

- **This is where Lance's users already live.** Most people meet Lance
  through its Python packages (`pylance`, `lancedb`) in a notebook or a
  data pipeline. Building it in the same language means the course ends
  next to the tools you already use — and lets the real packages referee
  your results.

- **We measure bytes and reads, not milliseconds.** Python is slower than
  Rust, so wall-clock timings would mostly measure the interpreter. Instead,
  every "faster" claim in this course is a count: bytes read, reads issued,
  pages touched — taken by a small file wrapper that counts every read. A
  count is honest in any language. Timings appear only as a secondary,
  clearly caveated number.

And where Rust really wins, the book says so: real Lance reads data without
copying it, computes vector distances with SIMD instructions, and talks to
cloud object stores with asynchronous I/O. Those are speed wins on top of
the same layout ideas — this course teaches the ideas.

## Why this course?

Knowing what each part of a data format does is not the same as knowing
how the parts behave *together* — and the second kind of knowledge is the
one you need when a table gets slow, a query reads too much, or a
version you need is gone. There are three common ways to learn Lance, and
each one stops short of it:

- **Using Lance shows you the outside.** You learn `write_dataset`,
  `to_table`, and which options are safe. But when a scan reads far more
  than expected, the result only shows the symptom. The cause lives in how
  pages, fragments, deletions, and indexes affect each other.

- **Reading the format spec teaches one part at a time.** The public
  [format documentation](https://lance.org/format/) is precise about each
  piece. But the hard questions sit *between* the pieces. Why does a delete
  make later scans slower until compaction? Why can a vector search with a
  filter return fewer results than you asked for? No single section of a
  spec can show you those answers.

- **Reading the real source is a second job.** Lance is a large Rust
  codebase built for production: cloud storage, many encodings, many index
  types. The core ideas are all in there, surrounded by everything
  production needs.

This course takes a fourth path: **build a nano version from scratch**,
keeping only the load-bearing parts. You write every one of them, one day
at a time, and each new part lands in a format that already works. So you
watch every new part change how the old ones behave.

**And one story carries you through the hard parts.** Every concept arrives
as part of one running story: a warehouse. A table stored by rows is
shelving where each customer's order sits together; stored by columns,
each aisle holds one column's values. Values arrive in sealed boxes, and
a wall card at the back says which aisle and shelf holds each box. So you
meet each idea first as something you can picture, and only then as code.
[The warehouse: an analogy to help you build the right mental model](book/src/story.md)
keeps the whole story on one page, one scene per finished day: come back
whenever an idea gets fuzzy.

## What you build

One small format and one small database, built in three parts:

- **Part 1 — the Lance format (Days 1–9):** the same table stored as rows
  and as columns; a file of pages with a footer; encodings that shrink
  bytes; strings, lists, and missing values; random access by row id; then
  a table of many files with a manifest per version — time travel,
  appends, deletes, updates, schema changes, and compaction.

- **Part 2 — indexes (Days 10–12):** scalar indexes that let filters read
  less, then vector search — exact brute force first, then IVF clustering
  and product quantization, always measured as recall against reads.

- **Part 3 — nano-LanceDB (Days 13–17):** a database with tables, a query
  builder (`search(...).where(...).limit(...)`), full-text search with
  BM25, hybrid search, and a tiny built-in embedder — ending in a small
  semantic-search app.

**The referee is real — at the finale.** Day 17 runs a small
semantic-search app on your code and on the real `lancedb` package, on the
same data, and compares the results. Before that, every day is its own
referee: tests check each result against the data that went in, and every
cost is counted. One honest limit: your files will *not* be
readable by real Lance — the course rebuilds the ideas, not its exact byte
format.

## What this course is — and isn't — about

This is a course about **how a columnar format and a vector database work
inside**: layout, I/O, versioning, and indexes. It is *not* a course about
Python, or about machine learning.

Some days necessarily carry other material — the Python language itself,
`numpy` once vectors arrive, and the math of k-means and product
quantization — because the code has to run. The contract for those parts:
every concept gets a plain-English analogy and a link to a fuller
explanation, but **understanding the math is never required to progress**.
What you will never be asked to do is type *blindly*: every block comes
with a plain statement of **what it is and why the format needs it**.
Copying those blocks straight from the chapter is a completely legitimate
choice.

It is also not a performance race. Real Lance is engineered for cloud
storage and huge tables; nano-Lance is engineered to be read. The numbers
this course cares about are the ones that do not depend on the language:
bytes, reads, and recall.

## The 18 days

About 39½ hours end to end. Day boundaries will be refined as the book is
written. Each day is one theme built as two to four related sections, and
every section ends at a runnable, tagged checkpoint — the per-section plan
lives in the book's [introduction](book/src/introduction.md).

| Day | Theme | In plain words | ≈&nbsp;Time |
|-----|-------|----------------|--------|
| 0&nbsp;✅ | Setup: tools and the empty tested scaffold | Install the tools and end with a tested, running (if empty) program. | 0.5&nbsp;h |
| 1&nbsp;✅ | Rows vs columns | Store one table both ways, and count what a one-column question and a one-row fetch each have to read. | 2&nbsp;h |
| 2&nbsp;✅ | A file of pages | Cut each column into pages, write a footer of where everything is, and read one column by jumping straight to it. | 2&nbsp;h |
| 3&nbsp;✅ | Encodings | Store the same values in fewer bytes — dictionaries, runs, packed bits — and prove every value comes back. | 2&nbsp;h |
| 4&nbsp;✅ | Strings, lists, and missing values | Values of different lengths, and values that are not there at all. | 2&nbsp;h |
| 5&nbsp;✅ | Random access | Fetch row 7,342 without reading the rest — and count how much less that reads than a Parquet-style layout. | 2&nbsp;h |
| 6&nbsp;✅&#8288;🔒 | The table | Many files plus a record of each version: read the table as it was yesterday. | 2&nbsp;h |
| 7&nbsp;✅&#8288;🔒 | Changing data | Delete without rewriting, update — and catch two writers colliding. | 2.5&nbsp;h |
| 8&nbsp;✅&#8288;🔒 | Schema evolution | Add a column to a big table without rewriting it; drop one. | 2.5&nbsp;h |
| 9&nbsp;✅&#8288;🔒 | Compaction and cleanup | Merge many small files into a few, and delete versions nobody needs. | 2.5&nbsp;h |
| 10&nbsp;✅&#8288;🔒 | Scalar indexes | A sorted index and a bitmap index let filters skip most of the table. | 2.5&nbsp;h |
| 11&nbsp;✅&#8288;🔒 | Vector search | Find the nearest vectors: check every one, then only the few closest clusters — and measure what that costs in recall. | 2.5&nbsp;h |
| 12&nbsp;✅&#8288;🔒 | Product quantization | Store each vector as a few short codes: far less memory, a little less recall, and a refine step to win it back. | 2.5&nbsp;h |
| 13&nbsp;✅&#8288;🔒 | The database | Connect to a folder, create and open tables, add, upsert, delete. | 2.5&nbsp;h |
| 14&nbsp;✅&#8288;🔒 | The query builder | `search().where().limit()` — and why filtering after the search can quietly return too few results. | 2.5&nbsp;h |
| 15&nbsp;✅&#8288;🔒 | Full-text search | Split text into words, build an inverted index, and rank matches with BM25. | 2.5&nbsp;h |
| 16&nbsp;🔒 | Hybrid search | Combine vector and keyword results into one ranking. | 1.5&nbsp;h |
| 17&nbsp;🔒 | The payoff: semantic search | A tiny built-in embedder, automatic embedding on insert and query, and a small search app checked against real LanceDB. | 3&nbsp;h |

✅ = finished — the day's chapter and checkpoint tags are in this repository.

✅&#8288;🔒 = finished, in the Pro edition (launching soon — star or watch this repository to catch it).

🔒 = Pro edition, still being written.

## How to follow the course

Read the book chapters in `book/` (rendered with
[mdBook](https://rust-lang.github.io/mdBook/)):

```bash
mdbook serve book --open
```

`main` always holds the most recently finished day; every day's exact state
lives forever under its tag. Then pick one of two modes:

```bash
# Mode 1 — inspect the exact completed state of any day
git switch --detach v1-day-02
uv run pytest -q

# Mode 2 — build it yourself: start from yesterday, follow today's chapter
git switch -c my-course v1-day-01
# ...write the code from the Day 2 chapter, section by section...
./scripts/compare.sh v1-day-02a   # code-only diff after section A
./scripts/compare.sh v1-day-02    # the finished day
```

Every *section* of a day is one commit with its own checkpoint tag
(`v1-day-02a`, `v1-day-02b`, …), and the day's last section doubles as the
day tag. The compare script checks only the code you write (`src/`,
`tests/`, `pyproject.toml`) — never chapters, README, or course
infrastructure. It parses your Python and prints it back in a standard
form, so comments, docstrings, blank lines, formatting, and the order of
top-level definitions are all ignored: its ✓ means the section is done.

## The green bar

A checkpoint is not done until this passes at its tag:

```bash
./scripts/check.sh
```

The script runs, in order: `uv run ruff format --check`, `uv run ruff
check`, `uv run pytest -q`, the day's smoke command, and `mdbook build
book`. Every run uses the exact versions pinned in `uv.lock`, and the
formatting gate also checks the Python code blocks inside the book's
chapters.

## Credits & further learning

This course stands on excellent public work, and it is built only from
public material — Lance's open-source code and public documentation. No
code is copied from either project; the course rebuilds the ideas.

- [Lance](https://github.com/lance-format/lance) and its
  [format documentation](https://lance.org/format/) (Apache-2.0) — the
  format this course rebuilds in miniature.

- [LanceDB](https://github.com/lancedb/lancedb) and its
  [docs](https://docs.lancedb.com/) (Apache-2.0) — the database Part 3
  rebuilds, and its referee.

- The [Python documentation](https://docs.python.org/3.12/) — every
  "Python used here" chip links into it.

- [uv](https://docs.astral.sh/uv/), [Ruff](https://docs.astral.sh/ruff/),
  [pytest](https://docs.pytest.org/), and
  [mdBook](https://github.com/rust-lang/mdBook) — the tools behind the
  green bar and this book.

None of these projects are affiliated with this course; all of them deserve
your time.

## License

MIT — see [LICENSE](LICENSE). This license covers the public preview.
