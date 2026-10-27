import pytest

from nanolance import shapes
from nanolance.orders import COLUMNS, TAGGED_ORDERS
from nanolance.shapes import OFFSET, STRING, STRING_LIST


def offsets_of(*ends):
    return b"".join(OFFSET.pack(end) for end in ends)


def test_offsets_start_at_zero_and_add_up_the_lengths():
    assert shapes.offsets([5, 0, 3]) == offsets_of(0, 5, 5, 8)
    assert shapes.spans(offsets_of(0, 5, 5, 8)) == [(0, 5), (5, 5), (5, 8)]


def test_strings_are_stored_without_padding():
    assert shapes.string_trays(["tape", "bolts"]) == {
        "offsets": offsets_of(0, 4, 9),
        "data": b"tapebolts",
    }


def test_offsets_count_bytes_not_characters():
    trays = shapes.string_trays(["Ø6"])  # Ø is two bytes in UTF-8
    assert trays == {"offsets": offsets_of(0, 3), "data": "Ø6".encode()}


STRING_PAGES = {
    "no values": [],
    "empty strings": ["", "tape", ""],
    "unicode": ["drill bits Ø6", "螺丝", "🔩 bolts", "café"],
    "a 12-byte name": ["washers 50mm"],
    "a 70000-byte name": ["x" * 70_000],
    "the shop's names": [row[3] for row in TAGGED_ORDERS],
}


@pytest.mark.parametrize("values", STRING_PAGES.values(), ids=STRING_PAGES.keys())
def test_strings_give_back_exactly_what_went_in(values):
    trays = shapes.trays(STRING, values)
    assert list(trays) == ["offsets", "data"]
    assert shapes.values_from(STRING, trays) == values


def test_a_fixed_width_column_has_one_tray():
    trays = shapes.trays(COLUMNS["qty"], [3, 1, 40])
    assert list(trays) == ["values"]
    assert shapes.values_from(COLUMNS["qty"], trays) == [3, 1, 40]


def test_fixed_width_text_is_still_refused_when_too_long():
    with pytest.raises(ValueError, match="text needs 15 bytes; the slot holds 12"):
        shapes.trays(COLUMNS["name"], ["screwdriver set"])


def test_a_kind_is_recorded_by_its_format():
    assert shapes.kind_of(shapes.format_of(STRING)) == STRING
    assert shapes.kind_of(shapes.format_of(STRING_LIST)) == STRING_LIST
    assert shapes.kind_of(shapes.format_of(COLUMNS["id"])).format == "<q"


def test_a_list_is_offsets_into_its_items():
    trays = shapes.list_trays([["bulk"], [], ["a", ""]])
    assert trays == {
        "list offsets": offsets_of(0, 1, 1, 3),  # counted in items
        "offsets": offsets_of(0, 4, 5, 5),  # counted in bytes
        "data": b"bulka",
    }


LIST_PAGES = {
    "no lists": [],
    "only empty lists": [[], [], []],
    "an empty list and a list of one empty string": [[], [""], ["", ""]],
    "unicode tags": [["fragile", "très fragile"], ["螺丝"]],
    "a list of 1000 tags": [[f"tag {k}" for k in range(1000)]],
    "the shop's tags": [row[4] for row in TAGGED_ORDERS],
}


@pytest.mark.parametrize("values", LIST_PAGES.values(), ids=LIST_PAGES.keys())
def test_lists_give_back_exactly_what_went_in(values):
    trays = shapes.trays(STRING_LIST, values)
    assert list(trays) == ["list offsets", "offsets", "data"]
    assert shapes.values_from(STRING_LIST, trays) == values


def test_the_validity_bitmap_has_one_bit_per_value_lowest_bit_first():
    values = [0, 1, None, 2, None, 3]  # the example in Arrow's documentation
    assert shapes.roll_call(values) == bytes([0b00101011])
    assert shapes.present(bytes([0b00101011]), 6) == [
        True,
        True,
        False,
        True,
        False,
        True,
    ]


def test_a_page_without_missing_values_has_no_validity_tray():
    assert "validity" not in shapes.trays(STRING, ["tape", ""])


NULL_PAGES = {
    "all-missing qty": (COLUMNS["qty"], [None] * 100),
    "all-missing names": (STRING, [None] * 9),
    "all-missing tags": (STRING_LIST, [None, None]),
    "missing and empty strings": (STRING, [None, "", "tape", None]),
    "missing and empty lists": (STRING_LIST, [[], None, [""], None]),
    "missing prices across a byte": (COLUMNS["price"], [None, 4.25] * 5),
}


@pytest.mark.parametrize(("kind", "values"), NULL_PAGES.values(), ids=NULL_PAGES.keys())
def test_missing_values_come_back_missing(kind, values):
    trays = shapes.trays(kind, values)
    assert list(trays)[0] == "validity"
    assert shapes.values_from(kind, trays) == values
