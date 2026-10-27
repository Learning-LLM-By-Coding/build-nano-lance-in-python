from nanolance import page_file
from nanolance.counting import CountingFile
from nanolance.orders import COLUMNS, ORDERS, many_orders
from nanolance.page_file import Page


def test_each_column_is_cut_into_pages(tmp_path):
    pages = page_file.write(tmp_path / "pages.bin", ORDERS, rows_per_page=3)
    assert pages["id"] == [
        Page(offset=0, size=24, rows=3),
        Page(offset=24, size=24, rows=3),
        Page(offset=48, size=16, rows=2),
    ]
    assert pages["price"][0].offset == 64  # right after the id column


def test_every_column_round_trips_through_its_pages(tmp_path):
    path = tmp_path / "pages.bin"
    orders = many_orders(1000)
    pages = page_file.write(path, orders)
    with CountingFile(path) as f:
        for position, (column, codec) in enumerate(COLUMNS.items()):
            values = page_file.read_column(f, codec, pages[column])
            assert values == [row[position] for row in orders]


def test_reading_some_rows_reads_only_the_pages_that_hold_them(tmp_path):
    path = tmp_path / "pages.bin"
    orders = many_orders(1000)
    pages = page_file.write(path, orders)
    codec, qty_pages = COLUMNS["qty"], pages["qty"]
    qty = [row[2] for row in orders]
    with CountingFile(path) as f:
        assert page_file.read_rows(f, codec, qty_pages, 10, 20) == qty[10:20]
        assert (f.reads, f.bytes_read, f.seeks) == (1, 400, 1)
    with CountingFile(path) as f:  # rows 95-104 straddle pages 0 and 1
        assert page_file.read_rows(f, codec, qty_pages, 95, 105) == qty[95:105]
        assert (f.reads, f.bytes_read, f.seeks) == (2, 800, 2)
