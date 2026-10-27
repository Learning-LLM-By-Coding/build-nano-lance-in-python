from nanolance import row_layout
from nanolance.counting import CountingFile
from nanolance.orders import COLUMNS, ORDERS, ROW_WIDTH, pack_value


def test_each_row_is_stored_in_one_piece(tmp_path):
    path = tmp_path / "rows.bin"
    row_layout.write(path, ORDERS)
    data = path.read_bytes()
    assert len(data) == len(ORDERS) * ROW_WIDTH
    first_row = b"".join(
        pack_value(column, value)
        for column, value in zip(COLUMNS, ORDERS[0], strict=True)
    )
    assert data[:ROW_WIDTH] == first_row


def test_rows_round_trip_exactly(tmp_path):
    path = tmp_path / "rows.bin"
    row_layout.write(path, ORDERS)
    with open(path, "rb") as f:
        assert row_layout.read_all(f, len(ORDERS)) == ORDERS


def test_summing_one_column_reads_every_byte(tmp_path):
    path = tmp_path / "rows.bin"
    row_layout.write(path, ORDERS)
    with CountingFile(path) as f:
        assert row_layout.sum_column(f, "qty", len(ORDERS)) == 65
        assert (f.reads, f.bytes_read, f.seeks) == (8, 256, 0)


def test_fetching_one_row_is_one_seek_and_one_read(tmp_path):
    path = tmp_path / "rows.bin"
    row_layout.write(path, ORDERS)
    for index, expected in enumerate(ORDERS):
        with CountingFile(path) as f:
            assert row_layout.fetch_row(f, index) == expected
            assert (f.reads, f.bytes_read, f.seeks) == (1, 32, 1)
