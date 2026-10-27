import pytest

from nanolance.orders import (
    COLUMNS,
    ORDERS,
    ROW_WIDTH,
    many_orders,
    pack_value,
    unpack_value,
)


def test_every_column_has_a_fixed_width():
    widths = {column: codec.size for column, codec in COLUMNS.items()}
    assert widths == {"id": 8, "price": 8, "qty": 4, "name": 12}
    assert ROW_WIDTH == 32


def test_every_value_round_trips_through_its_bytes():
    for row in ORDERS:
        for column, value in zip(COLUMNS, row, strict=True):
            raw = pack_value(column, value)
            assert len(raw) == COLUMNS[column].size
            assert unpack_value(column, raw) == value


def test_short_names_are_padded_with_zero_bytes():
    assert pack_value("name", "tape") == b"tape" + bytes(8)


def test_names_longer_than_their_slot_are_refused():
    with pytest.raises(ValueError, match="needs 15 bytes"):
        pack_value("name", "screwdriver set")


def test_many_orders_repeats_the_eight_orders_with_fresh_ids():
    orders = many_orders(20)
    assert orders[:8] == ORDERS
    assert orders[8] == (109, 4.25, 3, "bolts")
    assert [row[0] for row in orders] == list(range(101, 121))
