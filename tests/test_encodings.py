import pytest

from nanolance import encodings
from nanolance.encodings import COUNT
from nanolance.orders import COLUMNS, many_orders, pack_value


def plain_bytes(column, values):
    return b"".join(pack_value(column, value) for value in values)


def round_trip(name, column, values):
    codec = COLUMNS[column]
    data = plain_bytes(column, values)
    raw = encodings.encode(name, codec, data)
    assert encodings.decode(name, codec, raw, len(values)) == data
    return raw


QTY_PAGES = {
    "an empty page": [],
    "one value": [7],
    "all equal": [2] * 100,
    "the widest value": [0, 2**31 - 1, 5],
    "a page of orders": [row[2] for row in many_orders(100)],
}


@pytest.mark.parametrize("values", QTY_PAGES.values(), ids=QTY_PAGES.keys())
@pytest.mark.parametrize("name", encodings.ENCODINGS)
def test_every_encoding_gives_back_exactly_what_went_in(name, values):
    round_trip(name, "qty", values)


@pytest.mark.parametrize("name", ["plain", "dictionary", "run-length"])
def test_text_and_floats_round_trip_too(name):
    orders = many_orders(100)
    round_trip(name, "name", [row[3] for row in orders])
    round_trip(name, "price", [row[1] for row in orders])


def test_plain_stores_the_plain_bytes_unchanged():
    assert round_trip("plain", "qty", [3, 1, 40]) == plain_bytes("qty", [3, 1, 40])


def test_a_dictionary_stores_each_distinct_value_once_and_one_byte_codes():
    raw = round_trip("dictionary", "name", ["tape", "bolts", "tape", "tape"])
    legend = plain_bytes("name", ["tape", "bolts"])
    assert raw == COUNT.pack(2) + legend + bytes([0, 1, 0, 0])


def test_a_dictionary_of_all_distinct_values_is_larger_than_plain():
    ids = list(range(101, 201))
    assert len(round_trip("dictionary", "id", ids)) == 4 + 800 + 100  # plain: 800


def test_a_dictionary_holds_at_most_256_distinct_values():
    round_trip("dictionary", "qty", list(range(256)))
    with pytest.raises(ValueError, match="at most 256 values; this page has 257"):
        round_trip("dictionary", "qty", list(range(257)))


def test_run_length_stores_each_run_once_with_its_length():
    raw = round_trip("run-length", "qty", [5, 5, 5, 9, 5])
    assert raw == b"".join(
        pack_value("qty", value) + COUNT.pack(length)
        for value, length in [(5, 3), (9, 1), (5, 1)]
    )


def test_run_length_without_runs_is_twice_as_large_as_plain():
    qty = [row[2] for row in many_orders(100)]  # no two neighbors are equal
    assert len(round_trip("run-length", "qty", qty)) == 100 * (4 + 4)  # plain: 400
