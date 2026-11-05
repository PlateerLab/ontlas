"""R2RML mapping of the bindings, so Ontop, Stardog or GraphDB can answer SPARQL straight from the source tables."""
from __future__ import annotations

from xgen_data_studio.model import Ontology
from xgen_data_studio.rdf import RDF_TYPE, RR, XSD, XSD_OF, Turtle, escape


def _map(onto: Ontology, name: str) -> str:
    return f"{onto.namespace}mapping/{name}"


def _ancestors(onto: Ontology, t: str) -> list[str]:
    out = []
    while t and t not in out:
        out.append(t)
        t = onto.objects[t].parent
    return out


def to_r2rml(onto: Ontology) -> str:
    ns = onto.namespace
    tt = Turtle({"rr": RR, "xsd": XSD, "ex": ns})
    for o in onto.objects.values():
        if not o.table:
            continue
        key = "%7C".join(f"{{{c}}}" for c in o.key_prop.cols)  # the IRI the projection writes, | encoded
        classes = " ; ".join(f"rr:class ex:{a}" for a in _ancestors(onto, o.name))
        pairs = [(RDF_TYPE, RR + "TriplesMap"),
                 (RR + "logicalTable", f'[ rr:tableName "{escape(o.table)}" ]'),
                 (RR + "subjectMap", f'[ rr:template "{escape(ns + o.name)}/{key}" ; {classes} ]')]
        for p in o.properties.values():
            if p.expr:
                continue
            if p.columns:
                text = "|".join(f"{{{c}}}" for c in p.columns)
                pairs.append((RR + "predicateObjectMap", f'[ rr:predicate ex:{p.name} ; rr:objectMap '
                                                         f'[ rr:template "{escape(text)}" ; rr:termType rr:Literal ] ]'))
                continue
            dtype = "" if p.type in ("string", "enum") else f" ; rr:datatype xsd:{XSD_OF[p.type]}"
            pairs.append((RR + "predicateObjectMap",
                          f'[ rr:predicate ex:{p.name} ; rr:objectMap [ rr:column "{escape(p.col)}"{dtype} ] ]'))
        for lk in onto.links.values():
            if lk.source != o.name or not lk.on:
                continue
            target = onto.objects[lk.target]
            if not target.table:
                continue
            joins = " ; ".join(f'rr:joinCondition [ rr:child "{escape(c)}" ; rr:parent "{escape(t)}" ]'
                               for c, t in zip(o.prop(lk.on[0]).cols, target.prop(lk.on[1]).cols))
            pairs.append((RR + "predicateObjectMap",
                          f"[ rr:predicate ex:{lk.name} ; rr:objectMap [ rr:parentTriplesMap "
                          f"<{_map(onto, lk.target)}> ; {joins} ] ]"))
        tt.add(_map(onto, o.name), pairs)
    for lk in onto.links.values():
        if not lk.via:
            continue
        tt.add(_map(onto, lk.name), [
            (RDF_TYPE, RR + "TriplesMap"),
            (RR + "logicalTable", f'[ rr:tableName "{escape(lk.via.table)}" ]'),
            (RR + "subjectMap", f'[ rr:template "{escape(ns + lk.source)}/{{{lk.via.source_column}}}" ]'),
            (RR + "predicateObjectMap",
             f'[ rr:predicate ex:{lk.name} ; rr:objectMap [ rr:template '
             f'"{escape(ns + lk.target)}/{{{lk.via.target_column}}}" ; rr:termType rr:IRI ] ]')])
    return tt.text()
