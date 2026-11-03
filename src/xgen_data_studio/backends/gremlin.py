"""Gremlin Server (Apache TinkerPop 3.8: TinkerGraph, JanusGraph, Neptune with Gremlin) as a backend.

Each object is a vertex labelled with its type (Gremlin keeps one label, so a concept is asked for through the
labels of its bound subtypes) and keyed by its key property; each link is an edge. A projection is loaded by short
scripts whose values are all bindings.
"""
from __future__ import annotations

from typing import Any

from xgen_data_studio.backends.base import Backend, Capabilities, Result
from xgen_data_studio.compile.base import Compiled
from xgen_data_studio.compile.gremlin import gs

BATCH = 50


class GremlinBackend(Backend):
    def __init__(self, url: str = "ws://localhost:8182/gremlin", *, client: Any = None, source: str = "g",
                 name: str = "gremlin"):
        if client is None:
            try:
                from gremlin_python.driver import client as gremlin_client
            except ImportError as e:
                raise ImportError("Gremlin Server needs the [gremlin] extra (gremlinpython)") from e
            client = gremlin_client.Client(url, source)
        self.client = client
        self.name = name
        self.capabilities = Capabilities("gremlin", "tinkerpop", optional=False, load=True, computed="none")

    def run(self, text: str, bindings: dict | None = None) -> list:
        return self.client.submit(text, bindings or {}).all().result()

    def execute(self, compiled: Compiled, values: dict[str, Any] | None = None) -> Result:
        text, args = compiled.bind(values)
        rows = self.run(text, args)
        return Result(compiled.columns, [tuple(r.get(c) for c in compiled.columns) for r in rows], self.name,
                      compiled)

    def close(self) -> None:
        self.client.close()


def load_gremlin(onto, projection, backend: GremlinBackend, *, clear: bool = True) -> None:
    """Vertices first, then edges found by their end vertices' keys. Each script carries one binding, the batch of
    rows, since servers cap the bindings of a request (Gremlin Server: 16)."""
    from xgen_data_studio.projection import _graph_value

    if clear:
        backend.run("g.V().drop().iterate()")
    groups: dict[tuple[str, tuple[str, ...]], list[dict]] = {}
    for (t, _key), props in sorted(projection.nodes.items()):
        row = {p: _graph_value(v) for p, v in sorted(props.items()) if v is not None}
        groups.setdefault((t, tuple(row)), []).append(row)
    for (t, names), rows in groups.items():
        steps = "".join(f".property({gs(p)}, __.select('r').select({gs(p)}))" for p in names)
        for i in range(0, len(rows), BATCH):
            backend.run(f"g.inject(rows).unfold().as('r').addV({gs(t)}){steps}.iterate()", {"rows": rows[i:i + BATCH]})
    pairs: dict[tuple[str, str, str], list[dict]] = {}
    for link, st, sk, tt, tk in sorted(projection.edges):
        sv = projection.nodes.get((st, sk), {}).get(onto.objects[st].key, sk)
        tv = projection.nodes.get((tt, tk), {}).get(onto.objects[tt].key, tk)
        pairs.setdefault((link, st, tt), []).append({"s": _graph_value(sv), "t": _graph_value(tv)})
    for (link, st, tt), rows in pairs.items():
        sk, tk = gs(onto.objects[st].key), gs(onto.objects[tt].key)
        text = (f"g.inject(rows).unfold().as('p').V().hasLabel({gs(st)}).where(P.eq('p')).by({sk}).by('s').as('a')"
                f".V().hasLabel({gs(tt)}).where(P.eq('p')).by({tk}).by('t').addE({gs(link)}).from('a').iterate()")
        for i in range(0, len(rows), BATCH):
            backend.run(text, {"rows": rows[i:i + BATCH]})
