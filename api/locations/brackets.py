"""Temperature brackets (L3, L4, ADR 0004). Pure functions over edges and temperatures.

Brackets are half-open: the lower edge is included, the upper excluded, with an open bracket
below the lowest edge and one at or above the highest, so every temperature lands in exactly
one. Fixed mode takes the edge list from settings; quantile mode derives edges from the data so
that no bracket is empty, shrinking the count when fewer distinct temperatures exist.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Bracket:
    lower: float | None  # None: open below
    upper: float | None  # None: open above

    @property
    def label(self) -> str:
        if self.lower is None:
            return f"below {_fmt(self.upper)}"
        if self.upper is None:
            return f"{_fmt(self.lower)} and above"
        return f"{_fmt(self.lower)} to {_fmt(self.upper)}"

    def contains(self, temp: float) -> bool:
        return (self.lower is None or temp >= self.lower) and (
            self.upper is None or temp < self.upper
        )


def _fmt(v: float | None) -> str:
    assert v is not None
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def edges_to_brackets(edges: Sequence[float]) -> list[Bracket]:
    if not edges:
        return [Bracket(None, None)]
    e = [float(x) for x in edges]
    out = [Bracket(None, e[0])]
    out += [Bracket(a, b) for a, b in zip(e, e[1:], strict=False)]
    out.append(Bracket(e[-1], None))
    return out


def assign(temp: float, brackets: Sequence[Bracket]) -> Bracket:
    for b in brackets:
        if b.contains(temp):
            return b
    raise ValueError("brackets must cover the whole axis")  # cannot happen with edges_to_brackets


def quantile_edges(temps: Iterable[float], buckets: int) -> list[float]:
    """Edges that split the sorted temperatures into `buckets` groups of similar size.

    Returns fewer edges when there are fewer distinct temperatures than buckets; the caller
    reports the effective count. Edges are reported to one decimal (L4.4).
    """
    values = sorted(set(round(float(t), 1) for t in temps))
    if not values or buckets < 2:
        return []
    k = min(buckets, len(values))
    edges = []
    for i in range(1, k):
        pos = i * len(values) / k
        edges.append(values[min(math.ceil(pos), len(values) - 1)])
    # drop duplicates while keeping order, keep strictly ascending
    unique: list[float] = []
    for e in edges:
        if not unique or e > unique[-1]:
            unique.append(e)
    return unique


@dataclass
class Placement:
    bracket: Bracket
    locations: list[dict[str, Any]] = field(default_factory=list)


def group(rows: Sequence[dict[str, Any]], edges: Sequence[float]) -> list[dict[str, Any]]:
    """rows: dicts with at least `temp`; returns brackets ascending, locations ascending by temp,
    empty brackets kept (A4)."""
    brackets = edges_to_brackets(edges)
    placements = {b: Placement(b) for b in brackets}
    for row in sorted(rows, key=lambda r: float(r["temp"])):
        placements[assign(float(row["temp"]), brackets)].locations.append(row)
    return [
        {
            "label": p.bracket.label,
            "from": p.bracket.lower,
            "to": p.bracket.upper,
            "count": len(p.locations),
            "locations": p.locations,
        }
        for p in placements.values()
    ]
