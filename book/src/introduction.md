# Introduction

You are going to build a columnar data format and a small vector database
in Python, from scratch, in 18 days — the kind of system that stores a
table so a question about one column reads only that column, keeps every
past version of the table one step away, and finds the rows most similar
to a query without looking at all of them.

By Day 17 your system will have:

- **a file format** — each column cut into pages, with a footer at the end
  that says where every page lives, so a reader jumps straight to the
  bytes it needs,

- **encodings** — ways to store the same values in fewer bytes, each one
  proven to give back exactly what went in,

- **a versioned table** — many files plus a small record of each version
  (Lance calls it a *manifest*), so you can append, delete, update, add a
  column, and still read the table as it was yesterday,

- **indexes** — sorted and bitmap indexes that let filters skip most of the
  table, and vector indexes that sort similar vectors into groups and
  shrink each vector to a few short codes, so a search reads a few groups
  instead of everything,

- **a small database on top** — tables in a folder, a query builder,
  full-text search, hybrid search, and a tiny built-in embedder, ending in
  a semantic-search app.

## Who this is for

You need some programming experience in any language. You do **not** need
to know Python, databases, or machine learning — each idea is introduced
when the code first needs it, with a plain-English analogy before any
code. Everything runs on one laptop, with no GPU and no network for the
tests.

## How we measure: bytes and reads, not milliseconds

Python is slower than Rust, the language real Lance is written in. If this
course timed everything with a stopwatch, the numbers would mostly measure
Python. So every "this reads less" claim is a **count**: how many bytes a
query read, how many separate reads it issued, how many pages it touched.
From Day 1 on, a small wrapper around the file does the counting for you.
A count tells the same story in any language — it is the layout talking,
not the interpreter. Wall-clock time shows up only as a second, clearly
caveated number.

## Real Lance is the referee

From Part 1 on, tests run your code and the real `pylance` and `lancedb`
packages on the same data, and the results must match: the same rows from
a scan, a filter, or a fetch by row id, the same table at the same
version. Vector search is judged differently — by *recall*, the share of
the true nearest neighbors your index finds. One honest limit: your files
will not be readable by real Lance. The course rebuilds Lance's ideas, not
its exact bytes.

## One story holds it all together

Every day adds a scene to one running story — a warehouse — and each
piece of the format is one thing in it: an aisle, a sealed box, the wall
card at the back.
[The warehouse: an analogy to help you build the right mental model](story.md)
keeps the whole story on one page. Come back to it whenever an earlier
idea gets fuzzy. In the chapters, a concept name with a dotted underline
links there: click it, and a short reminder of what the concept is, what
it is in the story, and which day introduced it opens right where you are
reading. In the code, the story rides along too: every docstring that
starts with `Analogy:` has that paragraph highlighted, so you can spot
where a scene from the story meets the code that builds it.

## How the course works

Each day is one chapter and one theme, built as **two to four related
sections** — each section is one focused capability with its own runnable
finish, and a day's sections always tell a single story. Every section is
one git commit with its own checkpoint tag (`v1-day-03a`, `v1-day-03b`, …),
and the day's last section doubles as the day tag (`v1-day-03`). After
finishing a section, `./scripts/compare.sh <tag>` checks your code — and
only your code (`src/`, `tests/`, `pyproject.toml`; never chapters or
README) — against that checkpoint. It ignores comments, docstrings,
formatting, and the order of top-level definitions, so its ✓ means the
section is done.

The Python language itself is taught by reference instead of by detour:
every code section opens with a small **Python used here** strip linking
exactly the constructs its code leans on (functions, `bytes`, `struct`, …)
to the matching page of the official
[Python documentation](https://docs.python.org/3.12/). No prior Python is
assumed; read only the strips you need.

Every chapter has the same shape: what you will have running, what its
output will show, why yesterday's code is not enough, a mental model, the
code section by section, the exact commands to run, the output you should
see, tests, one deliberate way to break it, and a checkpoint.

## The 18 days

The sections below are the plan; day boundaries will be refined as the
book is written.

| Day | Theme | Sections | ≈ Time |
|-----|-------|----------|--------|
| 0 | Setup | uv, pytest, ruff, mdBook · the empty tested scaffold | 0.5 h |
| **Part 1** | **The Lance format** | | |
| 1 | Rows vs columns | One table stored row by row · a counting file: bytes read for a one-column question · the same table stored column by column · fetching one whole row: where rows win | 2 h |
| 2 | A file of pages | Day 1's file at a thousand rows · columns cut into pages · metadata and a footer, read from the end · refusing a file by name | 2 h |
| 3 | Encodings | What a page holds · plain & dictionary, each page naming its encoding · run-length · bit-packing & the smallest per page — bytes saved, bytes read, round-trip proofs | 2 h |
| 4 | Strings, lists, and missing values | What fixed widths cannot say · strings as offsets and data, in trays · lists as offsets into strings · validity bitmaps — bytes saved, one value in two reads | 2 h |
| 5 | Random access | Row id → page · a Parquet-style row-group layout to compare · bytes and seeks counted | 2 h |
| 6 | The table | Fragments · a manifest per version · time travel | 2 h |
| 7 | Changing data | Appends · deletion files · updates · optimistic commits & conflict detection | 2.5 h |
| 8 | Schema evolution | Add a column without rewriting · drop a column | 1.5 h |
| 9 | Compaction and cleanup | Compaction · cleaning up old versions | 2 h |
| **Part 2** | **Indexes** | | |
| 10 | Scalar indexes | A sorted (B-tree) index · a bitmap index · filters that read less | 2 h |
| 11 | Vector search | Brute force · k-means & IVF · recall vs reads | 2.5 h |
| 12 | Product quantization | PQ codes · IVF-PQ · refine | 2.5 h |
| **Part 3** | **nano-LanceDB** | | |
| 13 | The database | `connect` & the table list · add, delete, update · merge-insert (upsert) | 2 h |
| 14 | The query builder | `search().where().limit().select()` · prefilter vs postfilter · `nprobes` & `refine_factor` | 2.5 h |
| 15 | Full-text search | A tokenizer · an inverted index · BM25 ranking | 2 h |
| 16 | Hybrid search | Vector + keyword results · reciprocal rank fusion | 1.5 h |
| 17 | The payoff: semantic search | A tiny offline embedder · embedding on insert and query · a search app refereed against LanceDB | 3 h |

Roughly 35 hours end to end. Days 0–5 are the free public preview; Days
6–17 are the Pro edition.

Two rules keep the course honest:

1. **Every day ends green.** At every tag, formatting, lints, tests, the
   day's smoke command, and the book build all pass.

2. **Naive before optimized.** Every optimization arrives after a slow,
   clearly correct version you already understand — so you can count, in
   bytes and reads, exactly what the optimization buys.

Head to [Setup](setup.md) to get your tools ready.
