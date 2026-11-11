"""A server's first visitors arriving together: the graph store reads SPARQL in many threads at once, the first time in the
process. pyparsing learns each parse action's arity on its first call, and two threads learning it at once used to leave it
wrong for the life of the process (every later query: "<lambda>() missing 1 required positional argument: 'x'"). The race
needs a process that has not parsed SPARQL yet, so it runs in a fresh one."""
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
CHILD = r"""
import sys, threading
sys.path.insert(0, sys.argv[1])
import rdflib
from ontlas.backends.rdf import RdflibBackend, prepare_query
from ontlas.compile.base import Compiled

g = rdflib.Graph()
g.add((rdflib.URIRef("https://example.org/c1"), rdflib.RDF.type, rdflib.URIRef("https://example.org/Customer")))
g.add((rdflib.URIRef("https://example.org/c1"), rdflib.URIRef("https://example.org/name"), rdflib.Literal("a")))
b = RdflibBackend(g)
text = ('SELECT ?x ?n WHERE { ?x a <https://example.org/Customer> . OPTIONAL { ?x <https://example.org/name> ?n . } '
        'FILTER(?n != "b" && 3 > 2) } ORDER BY ?n LIMIT 1')
q = Compiled(language="sparql", dialect="1.1", text=text, style="inline", params=[], param_types={}, columns=["x", "n"],
             column_types={})
n = 24
gate = threading.Barrier(n)
errors = []

def one():
    gate.wait()
    try:
        b.execute(q)
    except Exception as e:
        errors.append(repr(e))

threads = [threading.Thread(target=one) for _ in range(n)]
[t.start() for t in threads]
[t.join() for t in threads]
rows = b.execute(q).rows
b.update('INSERT DATA { <https://example.org/c2> a <https://example.org/Customer> . }')
prepare_query("SELECT ?s WHERE { ?s ?p ?o } LIMIT 1")
print(len(errors), rows, errors[:1])
"""


def test_the_graph_store_reads_sparql_in_many_threads_at_once():
    pytest.importorskip("rdflib")
    out = subprocess.run([sys.executable, "-c", CHILD, str(SRC)], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-800:]
    assert out.stdout.strip().startswith("0 [('https://example.org/c1', 'a')]"), out.stdout
