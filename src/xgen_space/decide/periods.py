"""Rows of a period table that are valid at the same time for the same thing.

`current()` assumes one row is valid at a time; where a table holds more, it gives the highest value, so such rows are
listed for a person rather than left to decide a price.
"""
from __future__ import annotations

from typing import Any

from xgen_space.ir import Column, Query, Ref


def _of_property(studio, name: str) -> str:
    """The property that says which thing a period row belongs to."""
    t = studio.onto.objects[name]
    lk = studio.onto.links.get(t.period.get("of", ""))
    return lk.on[0] if lk is not None and lk.on else ""


def overlapping_periods(studio) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in studio.onto.objects.values():
        group = _of_property(studio, t.name) if t.period and t.table else ""
        if not group:
            continue  # without `of` nothing says which rows compete
        start, end = t.period["start"], t.period.get("end")
        names = [t.key, group, start, *([end] if end else [])]
        q = Query(nodes={"x": t.name}, columns=[Column(Ref("x", n), f"c{i}") for i, n in enumerate(names)])
        rows = [r for r in studio.run(q).rows if r[2] is not None]
        rows.sort(key=lambda r: (str(r[1]), str(r[2])))
        for a, b in zip(rows, rows[1:]):
            if a[1] != b[1]:
                continue
            a_end = a[3] if end else None
            closed = a_end is not None and (str(b[2]) >= str(a_end) if t.period.get("end_exclusive")
                                            else str(b[2]) > str(a_end))
            if not closed:
                out.append({"type": t.name, "of": a[1], "rows": [a[0], b[0]], "from": b[2], "until": a_end})
    return out
