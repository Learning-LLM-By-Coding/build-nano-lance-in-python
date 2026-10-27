#!/usr/bin/env bash
# The course green bar: a checkpoint is done when this script exits 0.
set -euo pipefail
cd "$(dirname "$0")/.."

# --locked: refuse to run if uv.lock and pyproject.toml disagree, so every
# checkpoint runs on exactly the pinned versions it was tagged with.
uv sync --locked --quiet
uv run --locked ruff format --check
uv run --locked ruff check
uv run --locked pytest -q
# The day's smoke command — update it whenever the CLI's shape changes.
uv run --locked nanolance
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
uv run --locked nanolance layouts "$scratch"
uv run --locked nanolance pages "$scratch"
uv run --locked nanolance packing "$scratch"

# The book must build: a sidebar entry whose chapter file is missing fails here.
mdbook build book

echo "GREEN: all gates passed"
