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


def test_layouts_tallies_what_each_question_reads(tmp_path):
    lines = run_layouts(tmp_path)
    start = lines.index("read rows.bin back: same as the table? True")
    assert lines[start : start + 4] == [
        "read rows.bin back: same as the table? True",
        "  tally: reads 8, bytes read 256, seeks 0",
        "sum(qty) from rows.bin = 65",
        "  tally: reads 8, bytes read 256, seeks 0 (qty needs only 32 of them)",
    ]


def test_layouts_stores_the_table_as_columns_too(tmp_path):
    lines = run_layouts(tmp_path)
    start = lines.index(
        "write columns.bin: 256 bytes = id 64 + price 64 + qty 32 + name 96"
    )
    assert lines[start : start + 5] == [
        "write columns.bin: 256 bytes = id 64 + price 64 + qty 32 + name 96",
        "read columns.bin back: same as the table? True",
        "  tally: reads 4, bytes read 256, seeks 4",
        "sum(qty) from columns.bin = 65",
        "  tally: reads 1, bytes read 32, seeks 1",
    ]


def test_layouts_fetches_one_row_both_ways(tmp_path):
    lines = run_layouts(tmp_path)
    assert lines[-4:] == [
        "fetch row 5 from rows.bin = (106, 3.25, 12, 'nails')",
        "  tally: reads 1, bytes read 32, seeks 1",
        "fetch row 5 from columns.bin = (106, 3.25, 12, 'nails')",
        "  tally: reads 4, bytes read 32, seeks 4",
    ]


def run_pages(folder):
    result = subprocess.run(
        [sys.executable, "-m", "nanolance", "pages", str(folder)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def test_pages_shows_what_the_column_file_must_be_told(tmp_path):
    lines = run_pages(tmp_path)
    assert lines[0] == "the orders table: 1000 rows × 4 columns (id, price, qty, name)"
    start = lines.index("sum(qty) from columns.bin, told 1000 rows = 8125")
    assert lines[start : start + 6] == [
        "sum(qty) from columns.bin, told 1000 rows = 8125",
        "  tally: reads 1, bytes read 4000, seeks 1",
        "sum(qty) from columns.bin, told 8 rows = 474",
        "  tally: reads 1, bytes read 32, seeks 1",
        "qty of rows 10–19 from columns.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
        "  tally: reads 1, bytes read 4000, seeks 1 (rows 10–19 need only 40 of them)",
    ]


def test_pages_reads_only_the_pages_it_needs(tmp_path):
    lines = run_pages(tmp_path)
    start = lines.index("  id: 10 pages of 800 bytes, at 0, 800, …, 7200")
    assert lines[start : start + 8] == [
        "  id: 10 pages of 800 bytes, at 0, 800, …, 7200",
        "  price: 10 pages of 800 bytes, at 8000, 8800, …, 15200",
        "  qty: 10 pages of 400 bytes, at 16000, 16400, …, 19600",
        "  name: 10 pages of 1200 bytes, at 20000, 21200, …, 30800",
        "sum(qty) from pages.bin = 8125",
        "  tally: reads 10, bytes read 4000, seeks 10",
        "qty of rows 10–19 from pages.bin = [40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
        "  tally: reads 1, bytes read 400, seeks 1",
    ]


def test_pages_opens_the_file_from_its_footer(tmp_path):
    lines = run_pages(tmp_path)
    assert "write pages.bin: 33762 bytes, each column cut into pages" in lines
    start = lines.index(
        "open pages.bin: version 1, 1000 rows, columns id, price, qty, name, 40 pages"
    )
    assert lines[start : start + 6] == [
        "open pages.bin: version 1, 1000 rows, columns id, price, qty, name, 40 pages",
        "  tally: reads 2, bytes read 1762, seeks 2",
        "sum(qty) from pages.bin, told nothing = 8125",
        "  tally: reads 12, bytes read 5762, seeks 12",
        "qty of rows 10–19 from pages.bin, told nothing = "
        "[40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
        "  tally: reads 3, bytes read 2162, seeks 3",
    ]


def test_pages_refuses_a_file_that_is_not_a_page_file(tmp_path):
    lines = run_pages(tmp_path)
    assert lines[-2:] == [
        "open columns.bin as a page file: refused, not a nanolance file: "
        r"it ends with b'\x00\x00\x00\x00', not b'NLNC'",
        "  tally: reads 1, bytes read 24, seeks 1",
    ]
