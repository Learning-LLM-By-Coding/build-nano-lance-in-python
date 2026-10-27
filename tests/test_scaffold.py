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
