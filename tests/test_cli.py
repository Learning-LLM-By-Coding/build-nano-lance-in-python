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
    assert "write pages.bin: 34522 bytes, each column cut into pages" in lines
    start = lines.index(
        "open pages.bin: version 3, 1000 rows, columns id, price, qty, name, 40 pages"
    )
    assert lines[start : start + 6] == [
        "open pages.bin: version 3, 1000 rows, columns id, price, qty, name, 40 pages",
        "  tally: reads 2, bytes read 2522, seeks 2",
        "sum(qty) from pages.bin, told nothing = 8125",
        "  tally: reads 12, bytes read 6522, seeks 12",
        "qty of rows 10–19 from pages.bin, told nothing = "
        "[40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
        "  tally: reads 3, bytes read 2922, seeks 3",
    ]


def test_pages_refuses_a_file_that_is_not_a_page_file(tmp_path):
    lines = run_pages(tmp_path)
    assert lines[-2:] == [
        "open columns.bin as a page file: refused, not a nanolance file: "
        r"it ends with b'\x00\x00\x00\x00', not b'NLNC'",
        "  tally: reads 1, bytes read 24, seeks 1",
    ]


def run_packing(folder):
    result = subprocess.run(
        [sys.executable, "-m", "nanolance", "packing", str(folder)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def test_packing_shows_what_each_first_page_holds(tmp_path):
    lines = run_packing(tmp_path)
    assert lines[:11] == [
        "the orders table: 1000 rows × 4 columns (id, price, qty, name), "
        "100 rows per page",
        "the first page of each column, orders as placed:",
        "  id: 800 bytes plain — 100 distinct, longest run 1, largest 200 needs 8 bits",
        "  price: 800 bytes plain — 8 distinct, longest run 1",
        "  qty: 400 bytes plain — 6 distinct, longest run 1, largest 40 needs 6 bits",
        "  name: 1200 bytes plain — 8 distinct, longest run 1",
        "the first page of each column, orders sorted by name:",
        "  id: 800 bytes plain — 100 distinct, longest run 1, "
        "largest 893 needs 10 bits",
        "  price: 800 bytes plain — 1 distinct, longest run 100",
        "  qty: 400 bytes plain — 1 distinct, longest run 100, largest 3 needs 2 bits",
        "  name: 1200 bytes plain — 1 distinct, longest run 100",
    ]


def test_packing_packs_every_column_every_way(tmp_path):
    lines = run_packing(tmp_path)
    start = lines.index(
        "every column packed every way, orders as placed (bytes, all pages):"
    )
    assert lines[start : start + 7] == [
        "every column packed every way, orders as placed (bytes, all pages):",
        "  id: plain 8000, dictionary 9040, run-length 12000, bit-packed 1212",
        "  price: plain 8000, dictionary 1680, run-length 12000, bit-packed —",
        "  qty: plain 4000, dictionary 1280, run-length 8000, bit-packed 760",
        "  name: plain 12000, dictionary 2000, run-length 16000, bit-packed —",
        "write dictionary.bin: 15612 bytes, pages 12960 (plain: 32000)",
        "  read back, told nothing: same as the table? True",
    ]


def test_packing_stacks_the_sorted_orders_in_runs(tmp_path):
    lines = run_packing(tmp_path)
    start = lines.index(
        "every column packed every way, orders sorted by name (bytes, all pages):"
    )
    assert lines[start : start + 7] == [
        "every column packed every way, orders sorted by name (bytes, all pages):",
        "  id: plain 8000, dictionary 9040, run-length 12000, bit-packed 1364",
        "  price: plain 8000, dictionary 1168, run-length 192, bit-packed —",
        "  qty: plain 4000, dictionary 1100, run-length 120, bit-packed 424",
        "  name: plain 12000, dictionary 1232, run-length 256, bit-packed —",
        "write sorted.bin: 11168 bytes, pages 8568 (plain: 32000)",
        "  read back, told nothing: same as the table? True",
    ]


def test_packing_keeps_the_smallest_and_reads_fewer_bytes(tmp_path):
    lines = run_packing(tmp_path)
    start = lines.index("write smallest.bin: 8320 bytes, pages 5652 (plain: 32000)")
    assert lines[start : start + 3] == [
        "write smallest.bin: 8320 bytes, pages 5652 (plain: 32000)",
        "  read back, told nothing: same as the table? True",
        "  chosen: id bit-packed ×10, price dictionary ×10, "
        "qty bit-packed ×10, name dictionary ×10",
    ]
    assert lines[-8:] == [
        "sum(qty) from plain.bin, told nothing = 8125",
        "  tally: reads 12, bytes read 6522, seeks 12 (opening 2522, pages 4000)",
        "sum(qty) from smallest.bin, told nothing = 8125",
        "  tally: reads 12, bytes read 3428, seeks 12 (opening 2668, pages 760)",
        "qty of rows 10–19 from plain.bin, told nothing = "
        "[40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
        "  tally: reads 3, bytes read 2922, seeks 3 (opening 2522, pages 400)",
        "qty of rows 10–19 from smallest.bin, told nothing = "
        "[40, 2, 1, 12, 4, 2, 3, 1, 40, 2]",
        "  tally: reads 3, bytes read 2744, seeks 3 (opening 2668, pages 76)",
    ]


def run_shapes(folder):
    result = subprocess.run(
        [sys.executable, "-m", "nanolance", "shapes", str(folder)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def test_shapes_shows_what_fixed_widths_cannot_say(tmp_path):
    lines = run_shapes(tmp_path)
    assert lines[0] == "the orders as the shop sends them: 8 rows"
    assert lines[5] == "  (105, 23.5, 1, 'drill bits Ø6', ['fragile'])"
    assert lines[9:14] == [
        "names of Day 3's 1000 orders, in 12-byte slots: 12000 bytes, "
        "6250 of them letters, 5750 padding",
        "pack 'drill bits Ø6' as a name: refused, name needs 14 bytes; "
        "the slot holds 12",
        "pack None as a price: refused, required argument is not a float",
        "  stored as 0.0 instead: the cheapest order is gloves at 0.0",
        "  and the average price is 8.19; the 6 known prices average 10.92",
    ]


def test_shapes_stores_names_as_strings(tmp_path):
    lines = run_shapes(tmp_path)
    start = lines.index(
        "the same names as strings (in slots: plain 12000, smallest 2000):"
    )
    assert lines[start : start + 9] == [
        "the same names as strings (in slots: plain 12000, smallest 2000):",
        "  strings.bin: 10290 bytes = offsets plain 4040 + data plain 6250",
        "    read back, told nothing: same as the table? True",
        "  strings-smallest.bin: 6765 bytes = "
        "offsets bit-packed 1280 + data bit-packed 5485",
        "    read back, told nothing: same as the table? True",
        "the shop's names as strings, read back: ['bolts', 'hammer', 'washers', "
        "'tape', 'drill bits Ø6', 'nails', 'gloves', 'padlock']",
        "one name, row 4, from a box the picker already knows:",
        "  padded.bin: 'drill bits' — tally: reads 1, bytes read 12, seeks 1",
        "  strings.bin: 'drill bits' — tally: reads 2, bytes read 18, seeks 2",
    ]


def test_shapes_stores_tags_as_lists(tmp_path):
    lines = run_shapes(tmp_path)
    start = lines.index("the shop's tags as one box of lists, tray by tray:")
    assert lines[start : start + 9] == [
        "the shop's tags as one box of lists, tray by tray:",
        "  list offsets: [0, 1, 1, 3, 3, 4, 5, 5, 7]",
        "  offsets: [0, 4, 8, 19, 26, 30, 34, 41]",
        "  data: b'bulkbulksmall partsfragilebulkgiftfragile'",
        "tags of 1000 shop orders: 875 tags, 375 empty lists",
        "  tags.bin: 12705 bytes = "
        "list offsets plain 4040 + offsets plain 3540 + data plain 5125",
        "    read back, told nothing: same as the table? True",
        "  tags-smallest.bin: 6465 bytes = list offsets bit-packed 900 + "
        "offsets bit-packed 1065 + data bit-packed 4500",
        "    read back, told nothing: same as the table? True",
    ]


def test_shapes_stores_the_shop_table_with_its_missing_prices(tmp_path):
    lines = run_shapes(tmp_path)
    start = lines.index("write shop.bin: 26169 bytes, every column packed smallest")
    assert lines[start:] == [
        "write shop.bin: 26169 bytes, every column packed smallest",
        "  id: 1212 = bit-packed 1212",
        "  price: 1730 = validity plain 130 + values dictionary 1600",
        "  qty: 760 = bit-packed 760",
        "  name: 8030 = offsets bit-packed 1280 + data plain 6750",
        "  tags: 6465 = list offsets bit-packed 900 + offsets bit-packed 1065 + "
        "data bit-packed 4500",
        "  read back, told nothing: same as the table? True",
        "sum(qty) from shop.bin, told nothing = 8125",
        "  tally: reads 12, bytes read 8732, seeks 12 (opening 7972, pages 760)",
        "average price from shop.bin = 10.92, 250 missing",
        "  tally: reads 12, bytes read 9702, seeks 12 (opening 7972, pages 1730)",
        "names of rows 10–19 from shop.bin = ['washers', 'tape', 'drill bits Ø6', "
        "'nails', 'gloves', 'padlock', 'bolts', 'hammer', 'washers', 'tape']",
        "  tally: reads 3, bytes read 8770, seeks 3 (opening 7972, pages 798)",
    ]


def run_take(folder):
    result = subprocess.run(
        [sys.executable, "-m", "nanolance", "take", str(folder)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def test_take_by_scanning_reads_every_page_for_ten_rows(tmp_path):
    lines = run_take(tmp_path)
    assert lines[:15] == [
        "write shop.bin: 10000 shop orders, 100 rows per page, 263487 bytes",
        "open it once and keep the box lists — tally: "
        "reads 2, bytes read 77910, seeks 2",
        "the pick list, 10 row ids: "
        "[7342, 15, 9999, 2718, 404, 6001, 8123, 3141, 0, 5050]",
        "take by scanning every column:",
        "  row 7342: (7443, None, 4, 'gloves', [])",
        "  row 15: (116, 15.0, 2, 'padlock', ['gift', 'fragile'])",
        "  row 9999: (10100, 15.0, 2, 'padlock', ['gift', 'fragile'])",
        "  row 2718: (2819, None, 4, 'gloves', [])",
        "  row 404: (505, 23.5, 1, 'drill bits Ø6', ['fragile'])",
        "  row 6001: (6102, 12.5, 1, 'hammer', [])",
        "  row 8123: (8224, 7.0, 2, 'tape', [])",
        "  row 3141: (3242, 3.25, 12, 'nails', ['bulk'])",
        "  row 0: (101, 4.25, 3, 'bolts', ['bulk'])",
        "  row 5050: (5151, None, 40, 'washers', ['bulk', 'small parts'])",
        "  tally: reads 500, bytes read 185577, seeks 500",
    ]


def test_take_box_by_box_reads_only_the_boxes_on_the_list(tmp_path):
    lines = run_take(tmp_path)
    start = lines.index("start numbers of the qty boxes: [0, 100, 200] … 9900")
    assert lines[start : start + 6] == [
        "start numbers of the qty boxes: [0, 100, 200] … 9900",
        "  row 7342: box 73, place 42",
        "  row 15: box 0, place 15",
        "  the whole list: 9 boxes per column, [0, 4, 27, 31, 50, 60, 73, 81, 99]",
        "take box by box: the same rows? True",
        "  tally: reads 45, bytes read 16672, seeks 45",
    ]


def test_take_from_row_groups_reads_every_chunk(tmp_path):
    lines = run_take(tmp_path)
    start = lines.index("write groups.bin: 4 row groups of 2500 orders, 200201 bytes")
    assert lines[start : start + 7] == [
        "write groups.bin: 4 row groups of 2500 orders, 200201 bytes",
        "  group 0: id 0, price 3751, qty 6624, name 8500, tags 30061",
        "  group 1: id 48855, price 52919, qty 55792, name 57668, tags 79239",
        "open it once and keep the box lists — tally: "
        "reads 2, bytes read 3500, seeks 2",
        "  the pick list: 4 groups, [0, 1, 2, 3]",
        "take from the row groups: the same rows? True",
        "  tally: reads 20, bytes read 196701, seeks 20",
    ]


def test_take_counts_scan_and_pick_list_for_every_box_size(tmp_path):
    lines = run_take(tmp_path)
    start = lines.index(
        "box size: what a scan and the pick list read, every column (reads, bytes)"
    )
    assert lines[start:] == [
        "box size: what a scan and the pick list read, every column (reads, bytes)",
        "    rows per box | box lists |         scan |    pick list",
        "              10 |    753278 | 5000, 238534 |     50, 2355",
        "             100 |     77910 |  500, 185577 |    45, 16672",
        "            2500 |      3496 |   20, 196701 |   20, 196701",
        "           10000 |      1084 |    5, 204917 |    5, 204917",
        "  2500 in groups |      3500 |   20, 196701 |   20, 196701",
    ]
