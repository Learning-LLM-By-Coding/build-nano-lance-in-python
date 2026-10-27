import subprocess
import sys


def run_layouts(folder):
    result = subprocess.run(
        [sys.executable, "-m", "nanolance", "layouts", str(folder)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def test_layouts_stores_the_table_as_rows(tmp_path):
    lines = run_layouts(tmp_path)
    assert lines[0] == "the orders table: 8 rows × 4 columns (id, price, qty, name)"
    assert "write rows.bin: 256 bytes = 8 rows × 32 bytes" in lines
    assert "read rows.bin back: same as the table? True" in lines
