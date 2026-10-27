"""Lets `python -m nanolance` run the same command line as `nanolance`."""

import sys

from nanolance.cli import main

sys.exit(main())
