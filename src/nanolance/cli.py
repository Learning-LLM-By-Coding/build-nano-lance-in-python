"""The `nanolance` command line."""

from nanolance import __version__


def main() -> int:
    """Print a hello line, proving the package installs and runs."""
    print(f"nanolance {__version__}: scaffold is alive")
    return 0
