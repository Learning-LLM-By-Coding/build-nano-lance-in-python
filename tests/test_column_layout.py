from nanolance import column_layout
from nanolance.counting import CountingFile
from nanolance.orders import ORDERS, many_orders, pack_value


def test_each_column_is_stored_in_one_piece(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, ORDERS)
    data = path.read_bytes()
    assert len(data) == 256
    ids = b"".join(pack_value("id", row[0]) for row in ORDERS)
    assert data[: len(ids)] == ids


def test_columns_start_where_the_earlier_columns_end():
    starts = [column_layout.column_start(c, 8) for c in ("id", "price", "qty", "name")]
    assert starts == [0, 64, 128, 160]


def test_columns_round_trip_exactly(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, ORDERS)
    with CountingFile(path) as f:
        assert column_layout.read_all(f, len(ORDERS)) == ORDERS
        assert (f.reads, f.bytes_read, f.seeks) == (4, 256, 4)


def test_summing_one_column_reads_only_that_column(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, ORDERS)
    with CountingFile(path) as f:
        assert column_layout.sum_column(f, "qty", len(ORDERS)) == 65
        assert (f.reads, f.bytes_read, f.seeks) == (1, 32, 1)


def test_fetching_one_row_visits_every_column(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, ORDERS)
    for index, expected in enumerate(ORDERS):
        with CountingFile(path) as f:
            assert column_layout.fetch_row(f, index, len(ORDERS)) == expected
            assert (f.reads, f.bytes_read, f.seeks) == (4, 32, 4)


def test_a_wrong_row_count_reads_the_wrong_bytes_without_error(tmp_path):
    path = tmp_path / "columns.bin"
    column_layout.write(path, many_orders(1000))
    with CountingFile(path) as f:
        assert column_layout.sum_column(f, "qty", 1000) == 8125
    with CountingFile(path) as f:
        assert column_layout.sum_column(f, "qty", 8) == 474  # four ids, not qty
