import json

import pytest

from nanolance import column_layout, page_file
from nanolance.counting import CountingFile
from nanolance.orders import (
    COLUMNS,
    ORDERS,
    TAGGED_COLUMNS,
    TAGGED_ORDERS,
    many_orders,
    many_tagged_orders,
)
from nanolance.page_file import FOOTER, MAGIC, VERSION, Page, Tray
from nanolance.shapes import STRING


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


def test_the_file_ends_with_a_fixed_size_footer(tmp_path):
    path = tmp_path / "pages.bin"
    page_file.write(path, many_orders(1000))
    data = path.read_bytes()
    offset, size, version, magic = FOOTER.unpack(data[-FOOTER.size :])
    assert (version, magic) == (VERSION, MAGIC)
    assert offset == 32000  # the metadata starts right after the pages
    assert offset + size + FOOTER.size == len(data)


def test_the_metadata_tells_a_reader_everything(tmp_path):
    path = tmp_path / "pages.bin"
    orders = many_orders(1000)
    pages = page_file.write(path, orders)
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        assert (f.reads, f.seeks) == (2, 2)
        assert f.bytes_read == f.size - 32000  # the metadata plus the footer
    assert metadata.version == VERSION
    assert metadata.rows == 1000
    assert {name: codec.format for name, codec in metadata.codecs.items()} == {
        "id": "<q",
        "price": "<d",
        "qty": "<i",
        "name": "<12s",
    }
    assert metadata.pages == pages


def test_a_reader_told_nothing_reads_back_every_column(tmp_path):
    path = tmp_path / "pages.bin"
    orders = many_orders(1000)
    page_file.write(path, orders)
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        for position, (column, codec) in enumerate(metadata.codecs.items()):
            values = page_file.read_column(f, codec, metadata.pages[column])
            assert values == [row[position] for row in orders]


def open_metadata(path):
    with CountingFile(path) as f:
        return page_file.read_metadata(f)


def test_a_day_1_column_file_is_refused_by_name(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, ORDERS)
    with pytest.raises(ValueError, match="not a nanolance file: it ends with"):
        open_metadata(path)


def test_a_file_cut_short_by_an_interrupted_write_is_refused(tmp_path):
    path = tmp_path / "pages.bin"
    page_file.write(path, many_orders(1000))
    path.write_bytes(path.read_bytes()[:32000])  # the pages, but no footer
    with pytest.raises(ValueError, match="not a nanolance file: it ends with"):
        open_metadata(path)


def test_a_file_shorter_than_the_footer_is_refused_without_a_read(tmp_path):
    path = tmp_path / "tiny.bin"
    path.write_bytes(b"NLNC")
    with CountingFile(path) as f:
        with pytest.raises(ValueError, match="4 bytes is shorter than the 24-byte"):
            page_file.read_metadata(f)
        assert (f.reads, f.seeks) == (0, 0)


def test_another_version_is_refused(tmp_path):
    path = tmp_path / "pages.bin"
    page_file.write(path, ORDERS)
    data = path.read_bytes()
    offset, size, _, _ = FOOTER.unpack(data[-FOOTER.size :])
    path.write_bytes(data[: -FOOTER.size] + FOOTER.pack(offset, size, 4, MAGIC))
    with pytest.raises(
        ValueError, match="version 4; this reader reads versions 1 to 3"
    ):
        open_metadata(path)


def test_a_footer_pointing_outside_the_file_is_refused(tmp_path):
    path = tmp_path / "pages.bin"
    page_file.write(path, ORDERS)
    data = path.read_bytes()
    offset, _, _, _ = FOOTER.unpack(data[-FOOTER.size :])
    path.write_bytes(data[: -FOOTER.size] + FOOTER.pack(offset, 10**6, VERSION, MAGIC))
    with pytest.raises(ValueError, match="damaged nanolance file"):
        open_metadata(path)


def test_each_page_records_its_encoding(tmp_path):
    path = tmp_path / "pages.bin"
    pages = page_file.write(
        path, ORDERS, rows_per_page=3, encoding={"qty": "dictionary"}
    )
    assert pages["id"][0] == Page(offset=0, size=24, rows=3)  # plain by default
    assert pages["qty"][0] == Page(offset=128, size=19, rows=3, encoding="dictionary")
    with CountingFile(path) as f:
        assert page_file.read_metadata(f).pages == pages


def test_a_reader_decodes_every_page_by_its_encoding(tmp_path):
    path = tmp_path / "pages.bin"
    orders = many_orders(1000)
    page_file.write(path, orders, encoding={c: "dictionary" for c in COLUMNS})
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        for position, (column, codec) in enumerate(metadata.codecs.items()):
            values = page_file.read_column(f, codec, metadata.pages[column])
            assert values == [row[position] for row in orders]


def test_a_version_1_file_still_reads_as_all_plain(tmp_path):
    path = tmp_path / "pages.bin"
    orders = many_orders(1000)
    page_file.write(path, orders)
    data = path.read_bytes()
    offset, size, _, _ = FOOTER.unpack(data[-FOOTER.size :])
    metadata = json.loads(data[offset : offset + size])
    for column in metadata["columns"]:
        for page in column["pages"]:
            del page["encoding"]  # version 1 box lists had no packing notes
    raw = json.dumps(metadata).encode("utf-8")
    path.write_bytes(data[:offset] + raw + FOOTER.pack(offset, len(raw), 1, MAGIC))
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        assert metadata.version == 1
        qty = page_file.read_column(f, metadata.codecs["qty"], metadata.pages["qty"])
    assert qty == [row[2] for row in orders]


def test_smallest_can_pack_each_page_of_a_column_differently(tmp_path):
    path = tmp_path / "pages.bin"
    rows = many_orders(100) + [(1001 + k, 1.0, 5, "tape") for k in range(100)]
    pages = page_file.write(path, rows, encoding={"qty": "smallest"})
    assert [page.encoding for page in pages["qty"]] == ["bit-packed", "run-length"]
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        qty = page_file.read_column(f, metadata.codecs["qty"], metadata.pages["qty"])
    assert qty == [row[2] for row in rows]


def test_a_string_page_holds_two_trays_back_to_back(tmp_path):
    path = tmp_path / "names.bin"
    names = [(row[3],) for row in TAGGED_ORDERS]  # 54 bytes of letters
    pages = page_file.write(path, names, columns={"name": STRING})
    trays = (Tray("offsets", 36, 9), Tray("data", 54, 54))
    assert pages["name"] == [Page(0, 90, 8, "trays", trays)]
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        assert metadata.codecs == {"name": STRING}
        assert metadata.pages == pages
        assert page_file.read_column(f, STRING, pages["name"]) == [n for (n,) in names]


def test_one_string_costs_two_reads_its_offsets_then_its_bytes(tmp_path):
    path = tmp_path / "names.bin"
    names = [(row[3],) for row in TAGGED_ORDERS]
    page = page_file.write(path, names, columns={"name": STRING})["name"][0]
    with CountingFile(path) as f:
        assert page_file.read_string(f, page, 4) == "drill bits Ø6"
        assert (f.reads, f.bytes_read, f.seeks) == (2, 8 + 14, 2)


def test_one_string_needs_plain_trays(tmp_path):
    path = tmp_path / "names.bin"
    names = [(row[3],) for row in TAGGED_ORDERS]
    pages = page_file.write(
        path, names, encoding={"name": "bit-packed"}, columns={"name": STRING}
    )
    with CountingFile(path) as f:
        with pytest.raises(ValueError, match="the offsets tray is bit-packed"):
            page_file.read_string(f, pages["name"][0], 4)


def test_a_version_2_file_still_reads(tmp_path):
    path = tmp_path / "pages.bin"
    orders = many_orders(1000)
    page_file.write(path, orders, encoding={c: "smallest" for c in COLUMNS})
    data = path.read_bytes()
    offset, size, _, _ = FOOTER.unpack(data[-FOOTER.size :])
    path.write_bytes(data[: -FOOTER.size] + FOOTER.pack(offset, size, 2, MAGIC))
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        assert metadata.version == 2
        names = page_file.read_column(f, COLUMNS["name"], metadata.pages["name"])
    assert names == [row[3] for row in orders]


def test_an_all_missing_page_reads_back_missing_and_its_bitmap_stays_plain(tmp_path):
    path = tmp_path / "prices.bin"
    prices = [(None,)] * 100 + [(4.25,)] * 100
    pages = page_file.write(
        path,
        prices,
        encoding={"price": "smallest"},
        columns={"price": COLUMNS["price"]},
    )
    first, second = pages["price"]
    assert [(tray.name, tray.encoding) for tray in first.trays] == [
        ("validity", "plain"),  # bit-packing 13 zero bytes would leave 1
        ("values", "run-length"),
    ]
    assert second.trays == ()  # nothing missing: a page as on Day 3
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        values = page_file.read_column(
            f, metadata.codecs["price"], metadata.pages["price"]
        )
    assert values == [price for (price,) in prices]


def test_the_shop_table_round_trips_every_column_every_way(tmp_path):
    path = tmp_path / "shop.bin"
    orders = many_tagged_orders(1000)
    for name in ["plain", "smallest"]:
        encoding = {column: name for column in TAGGED_COLUMNS}
        page_file.write(path, orders, encoding=encoding, columns=TAGGED_COLUMNS)
        with CountingFile(path) as f:
            metadata = page_file.read_metadata(f)
            columns = [
                page_file.read_column(f, kind, metadata.pages[column])
                for column, kind in metadata.codecs.items()
            ]
        assert list(zip(*columns, strict=True)) == orders


def test_a_take_by_scanning_reads_every_page_of_every_column_asked(tmp_path):
    path = tmp_path / "shop.bin"
    tagged = many_tagged_orders(1000)
    pages = page_file.write(path, tagged, columns=TAGGED_COLUMNS)
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
    with CountingFile(path) as f:
        rows = page_file.take_by_scan(f, metadata, [6, 2, 6], ["name", "price"])
        assert rows == [("gloves", None), ("washers", None), ("gloves", None)]
        every_page = pages["name"] + pages["price"]
        assert (f.reads, f.bytes_read) == (20, sum(p.size for p in every_page))
