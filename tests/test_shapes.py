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
