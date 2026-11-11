"""The library people get holds commerce alone, passes its own gates, and its sample files draft into a shop."""
import re
import socket
import threading
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "examples" / "library" / "studio.yaml"
FILES = ROOT / "examples" / "files"


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession

    return StudioSession(load_studio(CFG), data=DataOptions(samples=FILES))


def test_the_examples_hold_no_other_domain():
    text = [p for p in (ROOT / "examples").rglob("*") if p.is_file() and p.suffix in (".yaml", ".sql", ".csv", ".md")]
    assert text
    found = [p.name for p in text if re.search(r"finance|금융|대출|차주|borrower", p.read_text(encoding="utf-8"), re.I)]
    assert found == []
    assert sorted(p.name for p in FILES.iterdir()) == sorted(
        ["회원.csv", "상품.csv", "판매자.csv", "주문.csv", "주문상품.csv", "주문상태이력.csv", "결제.csv", "배송.csv"])


def test_the_shop_passes_every_gate(session):
    o = session.studio.onto
    assert {"Seller", "Payment", "Refund", "Shipment", "Carrier", "Coupon", "Review"} <= set(o.objects)
    assert "Loan" not in o.objects and not o.identities
    flow = session.flow()
    assert flow["passed"], [s["id"] for s in flow["steps"] if s.get("ok") is False]
    assert session.studio.questions().accuracy == 1.0


def test_a_long_path_agrees_on_both_backends(session):
    """Five hops over the whole shop. The in-memory graph used to multiply every class on the path and never answered."""
    st = session.studio
    report = st.conformance(queries={n: q for n, q in st.registered().items() if n in ("revenueByCategory", "sellerRevenue")})
    assert report.summary()["agree"] == 2
    started = time.monotonic()
    st.run("revenueByCategory", backend="graph")
    assert time.monotonic() - started < 5


def test_patterns_walk_along_what_is_bound():
    pytest.importorskip("rdflib")
    from rdflib import RDF, URIRef, Variable

    from ontlas.backends.rdf import connected

    o, i, s = Variable("o"), Variable("i"), Variable("s")
    has, of, cls = URIRef("urn:has"), URIRef("urn:of"), URIRef("urn:Class")
    pattern = [(o, RDF.type, cls), (i, RDF.type, cls), (s, RDF.type, cls), (o, has, i), (i, of, s)]
    assert connected(pattern) == [(o, RDF.type, cls), (o, has, i), (i, RDF.type, cls), (i, of, s), (s, RDF.type, cls)]
    assert connected(pattern, lambda term: term == s)[0] == (s, RDF.type, cls)  # what the context holds comes first


def test_the_sample_files_draft_into_a_shop(session):
    assert len(session.use_samples()["files"]) == 8
    view = session.make_draft("가상 쇼핑몰")["pending"]
    labels = {x["label"] for x in next(s for s in view["steps"] if s["id"] == "objects")["items"]}
    assert {"회원", "상품", "주문", "주문상품", "결제", "배송"} <= labels
    links = next(s for s in view["steps"] if s["id"] == "links")["items"]
    assert len(links) >= 6
    assert view["issues"] == []
    states = [x for x in next(s for s in view["steps"] if s["id"] == "rules")["items"] if x["kind"] == "states"]
    assert states  # the status history gives the order its transitions


def test_the_graph_engine_is_served_apart_from_the_page():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession
    from ontlas.web.server import STATIC, kit_version, page, serve

    html = page().decode("utf-8")
    assert f"/graph-kit.js?v={kit_version()}" in html and "window.SpaceGraph" in html
    assert "window.GraphKit=" not in html.replace(" ", "")  # 200 KB stay out of a page that may never open a graph
    notice = (STATIC / "graph-kit-NOTICE.txt").read_text(encoding="utf-8")
    assert "sigma" in notice and "graphology" in notice

    data = DataOptions()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    threading.Thread(target=serve, args=(lambda: StudioSession(load_studio(CFG), data=data),),
                     kwargs={"port": port, "data": data, "quiet": True}, daemon=True).start()
    for _ in range(100):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/graph-kit.js", timeout=1) as r:
                assert "immutable" in r.headers["Cache-Control"] and "javascript" in r.headers["Content-Type"]
                assert b"GraphKit" in r.read()
            return
        except OSError:
            time.sleep(0.1)
    pytest.fail("the page did not start")


def test_an_integer_key_is_fetched_as_the_number_it_is():
    from ontlas.backends.sql import SqliteBackend
    from ontlas.modules import Module
    from ontlas.studio import Studio

    m = Module.from_dict({"module": "m", "version": "1.0.0", "kind": "domain", "namespace": "urn:m#", "objects": {
        "Thing": {"key": "id", "table": "t", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}}}})
    st = Studio.from_modules([m], name="m")
    src = SqliteBackend()
    src.script("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT); INSERT INTO t VALUES (7, 'a');")
    st.add_backend("source", src, source=True)
    assert st.fetch("Thing", "7")["name"] == "a" and st.fetch("Thing", 7)["name"] == "a"
    assert st.fetch("Thing", "x") is None


def test_a_column_named_like_its_alias_is_valid_sparql():
    pytest.importorskip("rdflib")
    from ontlas.backends.rdf import RdflibBackend
    from ontlas.backends.sql import SqliteBackend
    from ontlas.modules import Module
    from ontlas.studio import Studio

    m = Module.from_dict({"module": "m", "version": "1.0.0", "kind": "domain", "namespace": "urn:m#", "objects": {
        "X": {"key": "id", "table": "t", "properties": {"id": {"type": "string"}, "x": {"type": "string"}}}},
        "queries": {"listX": {"query": {"match": {"x": "X"}, "return": ["x.id", "x.x"], "order": ["id"]}},
                    "countX": {"query": {"match": {"x": "X"}, "return": [{"count": "x", "as": "x"}]}}}})
    st = Studio.from_modules([m], name="m")
    src = SqliteBackend()
    src.script("CREATE TABLE t (id TEXT PRIMARY KEY, x TEXT); INSERT INTO t VALUES ('a', '1'), ('b', '2');")
    st.add_backend("source", src, source=True)
    st.add_backend("graph", RdflibBackend())
    st.project()
    text = st.translate("listX", "sparql").text
    assert "AS ?x)" in text and "?x <" not in text and "?node_x <" in text
    assert st.conformance().summary()["agree"] == 2
