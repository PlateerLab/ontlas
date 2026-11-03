"""Identity resolution: records that several systems keep under their own keys, joined into one object.

An `identities:` entry names the member types, which of their properties carry each match field, and the rules that
say two records are the same thing (every field of one rule equal after normalizing). `resolve` reads the members,
joins records that share a rule's values (transitively), and writes the crosswalk the definition is bound to:

    <table>            identity_id, members
    <table>_<member>   identity_id, member_key, rule

so the identity is an ordinary object with one link to each member type, queried the same way on every backend.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from xgen_data_studio.compile.sql import qi
from xgen_data_studio.ir import Column, Query, Ref
from xgen_data_studio.model import Identity


def normalize(value: Any, how: str) -> str:
    if value is None:
        return ""
    s = str(value)
    if how == "none":
        return s
    s = s.strip()
    if how == "lower":
        return s.lower()
    if how == "digits":
        return re.sub(r"\D", "", s)
    if how == "alnum":
        return re.sub(r"[\W_]", "", s).lower()
    return s


@dataclass
class Link:
    rule: str
    a: str
    b: str
    value: str


@dataclass
class Cluster:
    id: str
    members: list[str]  # "Type:key"
    rules: list[str]
    evidence: list[Link] = field(default_factory=list)


@dataclass
class IdentityReport:
    identity: str
    records: int
    clusters: list[Cluster]
    findings: list[str] = field(default_factory=list)
    written: bool = False

    @property
    def joined(self) -> list[Cluster]:
        return [c for c in self.clusters if len(c.members) > 1]

    def summary(self) -> dict[str, Any]:
        return {"identity": self.identity, "records": self.records, "identities": len(self.clusters),
                "joined": len(self.joined), "findings": len(self.findings), "written": self.written}

    def to_dict(self) -> dict:
        return {**self.summary(), "clusters": [asdict(c) for c in self.joined],
                "findings_detail": list(self.findings)}


class _Union:
    def __init__(self, items):
        self.up = {x: x for x in items}

    def find(self, x):
        while self.up[x] != x:
            self.up[x] = self.up[self.up[x]]
            x = self.up[x]
        return x

    def join(self, a, b) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.up[max(ra, rb)] = min(ra, rb)


def _records(studio, ident: Identity) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for m in ident.members.values():
        obj = studio.onto.obj(m.type)
        fields = sorted(m.fields)
        cols = [Column(Ref("x", obj.key), "__key")] + [Column(Ref("x", m.fields[f]), f) for f in fields]
        res = studio.run(Query(nodes={"x": m.type}, columns=cols), backend=studio.source or None)
        for row in res.rows:
            if row[0] is None:
                continue
            out[f"{m.type}:{row[0]}"] = dict(zip(fields, row[1:]))
    return out


def resolve(studio, name: str, *, write: bool = True) -> IdentityReport:
    """Join the member records of one identity and, when asked, write the crosswalk into the source."""
    ident = studio.onto.identities.get(name)
    if ident is None:
        raise KeyError(f"unknown identity '{name}'")
    records = _records(studio, ident)
    uf = _Union(records)
    evidence: list[Link] = []
    for rule in ident.rules:
        seen: dict[tuple, str] = {}
        for ref in sorted(records):
            values = tuple(normalize(records[ref].get(f), rule.normalize.get(f, "trim")) for f in rule.match)
            if not all(values):
                continue
            first = seen.setdefault(values, ref)
            if first != ref:
                uf.join(first, ref)
                evidence.append(Link(rule.id, first, ref, " / ".join(values)))
    groups: dict[str, list[str]] = {}
    for ref in records:
        groups.setdefault(uf.find(ref), []).append(ref)
    clusters, findings, by_ref = [], [], {}
    for root, refs in sorted(groups.items()):
        refs = sorted(refs)
        cl = Cluster(root, refs, [])
        clusters.append(cl)
        for r in refs:
            by_ref[r] = cl
        types = [r.split(":", 1)[0] for r in refs]
        for t in sorted(set(types)):
            if types.count(t) > 1:
                findings.append(f"{root}: {types.count(t)} {t} records joined; the same system may hold a duplicate")
    for e in evidence:
        cl = by_ref[e.a]
        cl.evidence.append(e)
        if e.rule not in cl.rules:
            cl.rules.append(e.rule)
    report = IdentityReport(name, len(records), clusters, findings)
    if write:
        _write(studio, ident, clusters)
        report.written = True
    return report


def _write(studio, ident: Identity, clusters: list[Cluster]) -> None:
    b = studio.backend(studio.source or None)
    if not b.capabilities.write or not hasattr(b, "run_many"):
        raise ValueError(f"backend {b.name} cannot be written; the crosswalk needs a writable SQL source")
    key = qi(ident.key)
    stmts = [(f"CREATE TABLE IF NOT EXISTS {qi(ident.table)} ({key} VARCHAR(200) PRIMARY KEY, "
              f"{qi('members')} INTEGER)", ()), (f"DELETE FROM {qi(ident.table)}", ())]
    tables = {m: ident.member_table(m) for m in ident.members}
    for t in tables.values():
        stmts += [(f"CREATE TABLE IF NOT EXISTS {qi(t)} ({key} VARCHAR(200), {qi('member_key')} VARCHAR(200), "
                   f"{qi('rule')} VARCHAR(200))", ()), (f"DELETE FROM {qi(t)}", ())]
    for cl in clusters:
        stmts.append((f"INSERT INTO {qi(ident.table)} VALUES (?, ?)", (cl.id, len(cl.members))))
        rule_of: dict[str, str] = {}
        for e in cl.evidence:
            rule_of.setdefault(e.a, e.rule)
            rule_of.setdefault(e.b, e.rule)
        for ref in cl.members:
            t, k = ref.split(":", 1)
            stmts.append((f"INSERT INTO {qi(tables[t])} VALUES (?, ?, ?)", (cl.id, k, rule_of.get(ref, ""))))
    b.run_many(stmts)
