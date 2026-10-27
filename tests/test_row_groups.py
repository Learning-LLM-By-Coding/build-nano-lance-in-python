import pytest

from nanolance import page_file, row_groups
from nanolance.counting import CountingFile
from nanolance.orders import ORDERS, TAGGED_COLUMNS, many_orders, many_tagged_orders
from nanolance.page_file import Page


def test_chunks_are_stored_group_after_group(tmp_path):
    chunks = row_groups.write(tmp_path / "groups.bin", ORDERS, rows_per_group=3)
    # group 0: 3 ids (24 bytes), 3 prices (24), 3 qtys (12), 3 names (36)
    assert [chunks[c][0] for c in ("id", "price", "qty", "name")] == [
        Page(offset=0, size=24, rows=3),
        Page(offset=24, size=24, rows=3),
        Page(offset=48, size=12, rows=3),
        Page(offset=60, size=36, rows=3),
    ]
    assert chunks["id"][1] == Page(offset=96, size=24, rows=3)  # then group 1
    assert chunks["name"][2] == Page(offset=232, size=24, rows=2)  # 2 rows left


def test_the_page_file_reader_reads_a_row_group_file_unchanged(tmp_path):
    path = tmp_path / "groups.bin"
    tagged = many_tagged_orders(1000)
    every_column = {column: "smallest" for column in TAGGED_COLUMNS}
    row_groups.write(path, tagged, 300, every_column, TAGGED_COLUMNS)
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
        assert [page.rows for page in metadata.pages["tags"]] == [300, 300, 300, 100]
        columns = list(metadata.codecs)
        rows = page_file.take(f, metadata, list(range(1000)), columns)
    assert rows == tagged


@pytest.mark.parametrize("row_ids", [[0, 999], [512, 3, 998], [7, 7, 2], []])
def test_a_take_from_row_groups_gives_the_same_rows_as_from_pages(tmp_path, row_ids):
    tagged = many_tagged_orders(1000)
    taken = []
    for write in (page_file.write, row_groups.write):
        path = tmp_path / "table.bin"
        write(path, tagged, 250, {"name": "smallest"}, TAGGED_COLUMNS)
        with CountingFile(path) as f:
            metadata = page_file.read_metadata(f)
            taken.append(page_file.take(f, metadata, row_ids, list(TAGGED_COLUMNS)))
    assert taken[0] == taken[1]


def test_one_value_from_a_row_group_reads_its_whole_chunk(tmp_path):
    path = tmp_path / "groups.bin"
    row_groups.write(path, many_orders(1000), rows_per_group=250)
    with CountingFile(path) as f:
        metadata = page_file.read_metadata(f)
    with CountingFile(path) as f:
        assert page_file.take(f, metadata, [260], ["qty"]) == [(1,)]
        assert (f.reads, f.bytes_read, f.seeks) == (1, 250 * 4, 1)  # one whole chunk
