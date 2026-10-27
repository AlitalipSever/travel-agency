"""L3.1, L4.4: half-open open-ended brackets and quantile edges, as pure rules."""

import pytest

from locations import brackets


def test_edges_make_half_open_open_ended_brackets() -> None:
    bs = brackets.edges_to_brackets([10, 20, 25, 30])
    assert [b.label for b in bs] == ["below 10", "10 to 20", "20 to 25", "25 to 30", "30 and above"]
    assert brackets.assign(9.99, bs).label == "below 10"
    assert brackets.assign(10.0, bs).label == "10 to 20"  # lower edge included
    assert brackets.assign(19.99, bs).label == "10 to 20"
    assert brackets.assign(20.0, bs).label == "20 to 25"  # upper edge excluded
    assert brackets.assign(45.0, bs).label == "30 and above"
    assert brackets.assign(-30.0, bs).label == "below 10"


def test_single_edge_and_decimal_labels() -> None:
    bs = brackets.edges_to_brackets([17.5])
    assert [b.label for b in bs] == ["below 17.5", "17.5 and above"]


@pytest.mark.parametrize(
    ("temps", "buckets", "edges"),
    [
        ([5, 10, 15, 20, 25, 30, 35, 40], 4, [15, 25, 35]),
        ([5, 10, 15, 20, 25, 30, 35, 40], 2, [25]),
        ([20, 20, 20], 4, []),  # one distinct temperature: a single bracket
        ([10, 20], 4, [20]),  # two distinct: shrinks to two brackets
        ([], 4, []),
    ],
)
def test_quantile_edges_split_evenly_and_shrink(
    temps: list[float], buckets: int, edges: list[float]
) -> None:
    assert brackets.quantile_edges(temps, buckets) == edges


def test_quantile_edges_are_one_decimal_and_ascending() -> None:
    edges = brackets.quantile_edges([12.345, 13.999, 17.001, 22.22, 23.2, 31.1], 3)
    assert edges == [17.0, 23.2]


def test_group_keeps_empty_brackets_and_sorts() -> None:
    rows = [{"name": "A", "temp": 33.0}, {"name": "B", "temp": 12.0}, {"name": "C", "temp": 11.0}]
    out = brackets.group(rows, [10, 20, 25, 30])
    assert [b["count"] for b in out] == [0, 2, 0, 0, 1]
    assert [row["name"] for row in out[1]["locations"]] == ["C", "B"]
    assert out[0]["from"] is None and out[-1]["to"] is None
