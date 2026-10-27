# Setup

This is Day 0. By the end of this page you have the course repository on
your machine, its tests passing, and its one command printing a hello
line. That empty-but-working scaffold is checkpoint `v1-day-00`, and every
later day builds on it.

You need two tools: **uv**, which installs Python and runs the code, and
**mdBook**, which builds this book. Nothing else — no system Python, no
virtual environment to create by hand, no GPU.

## 1. Install uv

[uv](https://docs.astral.sh/uv/) is a Python project manager. In this
course it does three jobs for you: it installs the exact Python version the
course was built with, it installs the exact versions of the tools the
course uses, and it runs commands inside that setup with `uv run`.

Install it with the official installer
([other ways to install](https://docs.astral.sh/uv/getting-started/installation/)):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then open a new terminal so your shell finds `uv`, and check it:

```bash
uv --version
```

The course was written with `uv 0.11.3`, and the project asks for at least
that version; later versions should work too. You do
not need to install Python yourself. The repository pins its Python version
in a file called `.python-version` (it says `3.12`), and uv downloads that
version the first time you run a command in the repository.

## 2. Install mdBook

The book you are reading is built with
[mdBook](https://rust-lang.github.io/mdBook/), and the course's checks
(section 5) build it at every checkpoint, so you need it installed. Pick whichever of
these fits your machine:

1. **macOS or Linux with Homebrew:**

   ```bash
   brew install mdbook
   ```

2. **Any system:** download a ready-made binary from the
   [mdBook releases page](https://github.com/rust-lang/mdBook/releases),
   unpack it, and put the `mdbook` file somewhere on your `PATH`.

3. **If you already have Rust installed:**

   ```bash
   cargo install mdbook --locked
   ```

Check it with `mdbook --version`. The course was written with `mdbook
v0.5.4`.

## 3. Clone and verify

One thing to know before your first command: **`main` always holds the most
recently finished day** of the course, while every checkpoint's exact state
lives forever under its tag. This page is about Day 0, so jump to its
checkpoint first:

```bash
git clone https://github.com/Learning-LLM-By-Coding/build-nano-lance-in-python.git
cd build-nano-lance-in-python
git switch --detach v1-day-00
uv run nanolance
```

The first `uv run` does the one-time setup: it downloads Python 3.12 if
you don't have it, creates a private environment for the project in a
folder called `.venv`, and installs the pinned tools into it. Then it runs
the course's command. The setup lines vary from machine to machine — the
last line is the one that matters:

```text
$ uv run nanolance
Using CPython 3.12.13
Creating virtual environment at: .venv
   Building nanolance @ file:///…/build-nano-lance-in-python
      Built nanolance @ file:///…/build-nano-lance-in-python
Installed 7 packages in 7ms
nanolance 0.1.0: scaffold is alive
```

(The two `file:///…` paths are the folder you cloned into, shortened here.)

If you see `nanolance 0.1.0: scaffold is alive`, your tools work and every
later day will run. (If you skip the `git switch` and run straight from
`main`, you will see the *latest* day's output instead. Nothing is wrong;
you are ahead of this page.) Return to the newest state anytime with
`git switch main`.

Now open the book locally, with live reload as chapters change:

```bash
mdbook serve book --open
```

Two cloning rules, because the checkpoints live in *tags* and tags are easy
to lose. The symptom is the same for both:
`fatal: invalid reference: v1-day-…` on a tag that plainly exists upstream.

1. **Clone the original, not a fork.** GitHub forks copy only the default
   branch — *none of the tags*. You never push to this repository, so you
   don't need a fork to follow the course. If you do want your build-along
   branch on your own GitHub, fork for pushing but fetch the checkpoints
   from the original:

   ```bash
   git remote add upstream https://github.com/Learning-LLM-By-Coding/build-nano-lance-in-python.git
   git fetch upstream --tags
   ```

2. **Clone plainly, as shown above.** A *shallow* clone (`--depth 1`, or a
   tool that shallow-clones for speed) skips every checkpoint tag that
   points into the unfetched history. The fix:

   ```bash
   git fetch --unshallow --tags
   ```

## 4. Choose how you follow along

Every day is built as a few sections, and **every section is one commit with
its own checkpoint tag**: Day 2's sections are `v1-day-02a`, `v1-day-02b`, …
and the day's last section doubles as the day tag `v1-day-02`. Two
workflows:

**Inspect mode** — jump to any finished checkpoint and poke at it:

```bash
git switch --detach v1-day-02
uv run pytest -q
```

**Build mode** — start from yesterday's checkpoint, write today's code
yourself by following the chapter, and compare after each section:

```bash
git switch -c my-course v1-day-01
# ...follow the Day 2 chapter, section A...
./scripts/compare.sh v1-day-02a    # code-only diff against the checkpoint
# ...section B...
./scripts/compare.sh v1-day-02b
# ...and after the last section:
./scripts/compare.sh v1-day-02     # the finished day
```

The compare script checks only the code you are expected to write (`src/`,
`tests/`, `pyproject.toml`). Chapters, the README, `uv.lock`, and course
infrastructure are excluded on purpose. It is also forgiving about style:
it parses your Python and prints it back in a standard form before
comparing, so comments, docstrings, blank lines, formatting, and the order
of top-level definitions (your function above or below the checkpoint's —
both fine) are all ignored. It reads your files exactly as they sit on disk
— no need to `git add` or commit before comparing, and comparing never
touches your git state. **Its final ✓ line means the section is done**,
even though your copy of the book still shows yesterday's prose.

You can try it right now, on the scaffold:

```text
$ ./scripts/compare.sh v1-day-00
✓ your code matches v1-day-00 (comments, docstrings, formatting, and top-level order ignored)
```

You haven't changed anything, so every file matches. On later days, a file
that differs only in style gets a `~` line, and a real difference gets a
`✗` line with a diff underneath.

<div class="callout">

**While the course is under construction**, checkpoint tags are
occasionally re-pointed when earlier days receive fixes — and plain
`git fetch` / `git pull` deliberately does *not* move a tag you already
have. If a checkpoint ever looks stale (a missing file, output that does
not match its chapter), refresh your tags first:

```bash
git fetch --tags --force
```

</div>

## 5. The green bar

Every checkpoint of this course — including this one — must end *green*:
every check passes, and the last line reads `GREEN: all gates passed`.
Get in the habit now:

```bash
./scripts/check.sh
```

The script (a few lines of bash — read it) runs six gates in order:

```text
uv sync --locked            # the pinned versions, exactly
uv run ruff format --check  # formatting, book code blocks included
uv run ruff check           # lints: common mistakes and unused code
uv run pytest -q            # all tests
uv run nanolance            # the day's smoke command
mdbook build book           # the book itself builds
```

The formatting gate covers the book too: Ruff also checks the Python code
blocks inside these Markdown pages, so a code sample in a chapter is held
to the same style as the code it was copied from.

The `--locked` flag makes uv refuse to run if the pinned versions in
`uv.lock` and the project's `pyproject.toml` disagree, so a checkpoint runs
on exactly the versions it was tagged with — today and years from now. At
`v1-day-00` the run looks like this:

```text
$ ./scripts/check.sh
10 files already formatted
All checks passed!
..                                                                       [100%]
2 passed in 0.03s
nanolance 0.1.0: scaffold is alive
 INFO Book building has started
 INFO Running the html backend
 INFO HTML book written to `/…/build-nano-lance-in-python/book/book`
GREEN: all gates passed
```

(The book path is shortened here; yours shows your clone's folder.)

Read it line by line (the first gate, `uv sync`, runs quietly and prints
nothing when all is well):

- `10 files already formatted` — `ruff format --check` looked at every
  Python file in the repository, plus the Python code blocks inside the
  book's Markdown pages, and found nothing to reformat.

- `All checks passed!` — `ruff check` found no lint problems.

- `..` and `2 passed in 0.03s` — pytest ran the two tests in
  `tests/test_scaffold.py`; each dot is one passing test. (Your time will
  differ a little.)

- `nanolance 0.1.0: scaffold is alive` — the smoke command ran the
  course's command line, `main` in `src/nanolance/cli.py`.

- the three `INFO` lines — mdBook built this book into `book/book/`.

- `GREEN: all gates passed` — the last line of `scripts/check.sh`, printed
  only when every gate above succeeded.

## 6. A look inside the scaffold

You won't type anything today, but it is worth a minute to see the three
small files every later day grows from. The package lives under
`src/nanolance/` (the folder layout is called a
[src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)),
and the tests live under `tests/`.

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.python.org/3.12/tutorial/modules.html#packages">packages &amp; <code>__init__.py</code></a>
<a href="https://docs.python.org/3.12/tutorial/modules.html">modules &amp; <code>import</code></a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#documentation-strings">docstrings</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#defining-functions">functions (<code>def</code>)</a>
<a href="https://docs.python.org/3.12/tutorial/controlflow.html#function-annotations">type annotations (<code>-&gt; int</code>)</a>
<a href="https://docs.python.org/3.12/tutorial/inputoutput.html#formatted-string-literals">f-strings</a>
<a href="https://docs.python.org/3.12/library/__main__.html#main-py-in-python-packages"><code>__main__.py</code></a>
<a href="https://docs.python.org/3.12/library/sys.html#sys.exit"><code>sys.exit</code></a>
</div>

`src/nanolance/__init__.py` makes the folder a package and holds its
version number:

```python
"""nanolance: a tiny Lance-style columnar format, built one tested day at a time."""

__version__ = "0.1.0"
```

`src/nanolance/cli.py` is the command line. The line
`nanolance = "nanolance.cli:main"` in `pyproject.toml` is what turns
`uv run nanolance` into a call to this `main` function
([entry points](https://docs.astral.sh/uv/concepts/projects/config/#entry-points)):

```python
"""The `nanolance` command line."""

from nanolance import __version__


def main() -> int:
    """Print a hello line, proving the package installs and runs."""
    print(f"nanolance {__version__}: scaffold is alive")
    return 0
```

`src/nanolance/__main__.py` lets `python -m nanolance` run the same
command — the tests use that form:

```python
"""Lets `python -m nanolance` run the same command line as `nanolance`."""

import sys

from nanolance.cli import main

sys.exit(main())
```

<div class="python-concepts"><span>Python used here:</span>
<a href="https://docs.pytest.org/en/stable/getting-started.html">pytest: test functions</a>
<a href="https://docs.python.org/3.12/reference/simple_stmts.html#the-assert-statement"><code>assert</code></a>
<a href="https://docs.python.org/3.12/library/subprocess.html#subprocess.run"><code>subprocess.run</code></a>
<a href="https://docs.python.org/3.12/library/importlib.metadata.html#distribution-versions"><code>importlib.metadata.version</code></a>
</div>

`tests/test_scaffold.py` holds the two tests. pytest runs every function
whose name starts with `test_`; a test passes when none of its `assert`
lines fail:

```python
import subprocess
import sys
from importlib.metadata import version

import nanolance


def test_version_matches_installed_package():
    assert nanolance.__version__ == version("nanolance")


def test_cli_says_hello():
    result = subprocess.run(
        [sys.executable, "-m", "nanolance"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == f"nanolance {nanolance.__version__}: scaffold is alive\n"
```

- `test_version_matches_installed_package` checks that the version in
  `__init__.py` matches the version `pyproject.toml` declares, so the two
  can never drift apart.

- `test_cli_says_hello` runs the command in a fresh Python process — the
  way you run it — and checks it prints exactly the hello line.

**Checkpoint reached: `v1-day-00`.** On Day 1 you store your first table —
once row by row, once column by column — and count how many bytes a
question about one column has to read from each.
