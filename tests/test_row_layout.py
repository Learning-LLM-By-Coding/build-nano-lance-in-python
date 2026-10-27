from nanolance import row_layout
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
