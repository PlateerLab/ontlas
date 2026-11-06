"""What the page asks of the space: documents, vectors, the ports and the map of it all.

Kept apart from api.py because none of it is about the ontology's own screens: a session gets it by inheritance, and everything
here reads `self.studio.space` and the session's catalog.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from xgen_space.embed import EmbedError
from xgen_space.values import normalize
from xgen_space.vectors import VectorError, conformance, known_kinds

SEARCH_MAX = 300  # characters of a question
K_MAX = 20
ROUTE_SYSTEM = ("질문을 분류합니다. 데이터베이스 값을 조회, 집계, 목록으로 답해야 하면 data, 규정이나 정책이나 설명을 묻는 것이면 documents 를 "
                "한 단어로만 답합니다.")
ANSWER_SYSTEM = ("당신은 문서 근거로만 답하는 안내자입니다. 주어진 [번호] 근거 안의 내용으로만 한국어 합니다체 두세 문장으로 답하고, "
                 "문장 끝에 근거 번호를 [1]처럼 적습니다. 근거에 없으면 '문서에서 찾지 못했습니다'라고만 답합니다.")


def plain(value: Any) -> Any:
    """What a page can read: an amount from a database is a Decimal, and JSON has no such thing."""
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return normalize(value)


def _human(e: Exception) -> str:
    return str(e) or type(e).__name__


class SpaceMixin:
    @property
    def space(self):
        return self.studio.space

    def _sync_space(self) -> None:
        """The catalog says which documents are in the space: what a file holds goes in, what left the catalog goes out."""
        self._hold()
        docs = [d for defs in self.definitions.values() for d in (getattr(defs, "documents", None) or [])]
        self.space.set_uploaded(docs)

    def _mentions(self, name: str) -> list[dict]:
        self._sync_space()
        return self.space.mentions_of(f"object:{name}", self.studio.onto, self._terms(), 4)

    def space_state(self) -> dict:
        self._sync_space()
        sp = self.space
        st = sp.state()
        made = sp.concepts(self.studio.onto, self._terms())
        counts: dict[str, dict] = {}
        for (doc, title), found in made["sections"].items():
            c = counts.setdefault(doc, {"sections": 0, "mentions": 0})
            c["sections"] += 1
            c["mentions"] += sum(found.values())
        docs = [{"name": n, "kind": d.get("kind", ""), "chunks": len(made["chunks"].get(n, [])), "fixed": n in sp.fixed, **counts.get(n, {"sections": 0, "mentions": 0})}
                for n, d in sp.documents().items()]
        check = None
        try:
            check = sp.check()
        except (VectorError, OSError, EmbedError) as e:
            st["error"] = _human(e)
        onto = self.studio.onto
        decided = [q.text for q in onto.questions if q.decision][:2]
        totals = [q.label for q in onto.queries.values() if q.label and not q.params and "sum" in str(q.query.get("return"))]  # a query that adds up says most
        named = (totals or [q.label for q in onto.queries.values() if q.label and not q.params])[:1]
        return {**st, "items": docs, "concepts": len(made["concepts"]), "check": check, "can_connect": self.data.allow_connect,
                "kinds": known_kinds(), "examples": decided + named + [c["text"] for c in (check or {}).get("results", [])[:2]]}

    def space_search(self, text: str, k: int = 5, store: str = "") -> dict:
        text = str(text or "").strip()[:SEARCH_MAX]
        if not text:
            raise ValueError("검색어가 없어 찾지 못했습니다. 찾을 내용을 입력해 주세요.")
        self._sync_space()
        sp = self.space
        try:
            hits = sp.search(text, max(1, min(int(k or 5), K_MAX)), store=store)
        except (VectorError, OSError, EmbedError) as e:
            raise ValueError(f"벡터 저장소에서 찾지 못했습니다. {_human(e)}") from None
        onto, terms = self.studio.onto, self._terms()
        named = sp.concepts_in(text, onto, terms)
        for h in hits:
            h["concepts"] = [c["label"] for c in sp.concepts_in(h["text"], onto, terms) if c.get("element")][:6]
        return {"ok": True, "text": text, "hits": hits, "named": named, "embedder": sp.embedder.describe(),
                "store": hits[0]["store"] if hits else sp.primary(), "can_answer": self.llm is not None,
                "compare": sp.compare(text, min(int(k or 5), K_MAX)) if len(sp.stores) > 1 else None}

    def space_ask(self, text: str, role: str = "", principal: dict | None = None) -> dict:
        """One question over everything here. The engine answers what it can, and says when a model could go further."""
        from xgen_space.tools import StudioTools

        self._sync_space()
        tools = StudioTools(self.studio, role=role or None, principal=principal, actor_id=self.who or "page")
        tools.terms = self._terms()
        try:
            out = tools.answer_question(text)
        except (VectorError, OSError, EmbedError) as e:
            raise ValueError(f"검색 엔진에서 찾지 못했습니다. {_human(e)}") from None
        except PermissionError:
            return {"ok": False, "error": "조회 권한이 없어 답변하지 못했습니다. 실행 역할을 확인해 주세요."}
        sp, onto, terms = self.space, self.studio.onto, tools.terms
        for s in out["sources"]:
            s["concepts"] = [c["label"] for c in sp.concepts_in(s["text"], onto, terms) if c.get("element")][:6]
        out["can_model"] = self.llm is not None
        return plain(out)

    def space_ask_more(self, text: str, role: str = "", principal: dict | None = None) -> dict:
        """What the engine could not settle alone: a model picks data or documents, and words only what was found."""
        if self.llm is None:
            return {"ok": False, "error": "언어 모델이 연결되어 있지 않아 답변을 만들지 못했습니다. 찾은 근거를 확인해 주세요."}
        with self.lock:
            found = self.space_ask(text, role, principal)
        if not found.get("ok"):
            return found
        llm, _ = self._budgeted()
        try:
            kind = llm(ROUTE_SYSTEM, found["question"]).strip().lower()
        except (TimeoutError, OSError, ValueError, RuntimeError):
            return {"ok": False, "error": "언어 모델이 제시간에 답하지 못했습니다. 찾은 근거를 확인해 주세요."}
        if "data" in kind and "documents" not in kind:
            def waiting(system: str, user: str) -> str:  # the data stays locked, the wait for a model does not
                self.lock.release()
                try:
                    return self.llm(system, user)
                finally:
                    self.lock.acquire()

            with self.lock:
                res = self.ask(found["question"], role=role, principal=principal, model=waiting)
            first = next(iter(res.get("results") or []), None)
            if res.get("ok") and first:
                return {"ok": True, "route": "query", "answer": f"{res.get('label') or '조회'} 결과 {len(first.get('rows') or [])}건입니다.",
                        "query": {"name": res.get("name") or "", "label": res.get("label") or "조회", "columns": first.get("columns") or [],
                                  "rows": [dict(zip(first.get("columns") or [], r)) for r in (first.get("rows") or [])[:50]],
                                  "total": len(first.get("rows") or [])}}
        lines = [f"[{i + 1}] {s['title']}: {s['text']}" for i, s in enumerate(found["sources"][:5])]
        if not lines:
            return {"ok": False, "error": "찾은 근거가 없어 답변을 만들지 못했습니다."}
        try:
            said = llm(ANSWER_SYSTEM, f"질문: {found['question']}\n\n근거:\n" + "\n".join(lines)).strip()
        except (TimeoutError, OSError, ValueError, RuntimeError):
            return {"ok": False, "error": "언어 모델이 제시간에 답하지 못했습니다. 찾은 근거를 확인해 주세요."}
        return {"ok": True, "route": "documents", "answer": said}

    def space_answer(self, text: str) -> dict:
        """An answer from the passages, each sentence pointing at its passage. The model never sees more than what was found."""
        if self.llm is None:
            return {"ok": False, "error": "언어 모델이 연결되어 있지 않아 답변을 만들지 못했습니다. 찾은 문서를 확인해 주세요."}
        found = self.space_search(text, 4)
        if not found["hits"]:
            return {"ok": False, "error": "찾은 문서가 없어 답변을 만들지 못했습니다."}
        lines = [f"[{i + 1}] {h['document']} / {h['section']}: {h['text']}" for i, h in enumerate(found["hits"])]
        llm, _ = self._budgeted()
        try:
            answer = llm(ANSWER_SYSTEM, f"질문: {found['text']}\n\n근거:\n" + "\n".join(lines)).strip()
        except (TimeoutError, OSError, ValueError, RuntimeError):
            return {"ok": False, "error": "언어 모델이 제시간에 답하지 못했습니다. 찾은 문서를 확인해 주세요."}
        return {"ok": True, "answer": answer, "hits": found["hits"]}

    def space_graph(self) -> dict:
        self._sync_space()
        return self.space.graph(self.studio.onto, self._terms())

    def space_read(self) -> dict:
        """One section per request: a model takes tens of seconds, and the page shows each result as it comes."""
        if self.llm is None:
            return {"ok": False, "error": "언어 모델이 연결되어 있지 않아 관계를 추출하지 못했습니다."}
        self._sync_space()
        sp = self.space
        key = sp.next_to_read(self.studio.onto, self._terms())
        if key is None:
            return {"ok": True, "done": True, "read": len(sp.relations), "relations": sum(len(v) for v in sp.relations.values())}
        llm, _ = self._budgeted()
        try:
            rows = sp.read_section(llm, key)
        except (TimeoutError, OSError, RuntimeError):
            return {"ok": False, "error": "언어 모델이 제시간에 답하지 못했습니다. 다시 시도해 주세요."}
        left = sp.next_to_read(self.studio.onto, self._terms())
        return {"ok": True, "done": left is None, "section": key[1], "document": key[0], "found": len(rows), "read": len(sp.relations),
                "relations": sum(len(v) for v in sp.relations.values())}

    def space_section(self, document: str, section: str) -> dict:
        self._sync_space()
        rows = [c for c in self.space.chunks.values() if c.document == document and c.section == section]
        rows.sort(key=lambda c: c.ordinal)
        made = self.space.concepts(self.studio.onto, self._terms())
        ids = made["sections"].get((document, section), {})
        return {"document": document, "section": section, "text": "\n\n".join(c.text for c in rows),
                "concepts": [{"label": made["concepts"][i].label, "kind": made["concepts"][i].kind, "element": made["concepts"][i].element,
                              "count": n} for i, n in sorted(ids.items(), key=lambda kv: -kv[1]) if i in made["concepts"]]}

    def space_queries(self) -> dict:
        """The document ontology answers through the same engine: its queries, their text in other languages, and whether
        the SQL side and the graph side agree."""
        self._sync_space()
        st = self.space.studio(self.studio.onto, self._terms())
        out = []
        for name, q in st.onto.queries.items():
            params = dict(q.example or {})
            row = {"name": name, "label": q.label, "params": params}
            try:
                res = st.run(name, params)
                row.update(columns=res.columns, rows=[list(r) for r in res.rows[:12]], total=len(res.rows))
                row["sparql"] = st.translate(name, "sparql").text
                row["cypher"] = st.translate(name, "cypher").text
            except Exception as e:  # the page shows one query's failure beside the others
                row["error"] = _human(e)
            out.append(row)
        rep = st.conformance().summary() if len(st.backends) > 1 else None
        return {"queries": out, "conformance": rep}

    def space_store(self, op: str, name: str = "", kind: str = "", url: str = "") -> dict:
        """Another vector store beside the one in use, on an install that allows connections."""
        if not self.data.allow_connect:
            raise PermissionError("공개 데모에서는 외부 저장소 연결이 비활성화되어 있어 추가하지 못했습니다.")
        name = str(name or kind).strip()[:32]
        if op == "remove":
            self.space.remove_store(name)
            return self.space_state()
        if kind not in known_kinds():
            raise ValueError(f"벡터 저장소 종류를 확인할 수 없어 추가하지 못했습니다. 지원 종류: {', '.join(known_kinds())}")
        field = "dsn" if kind == "pgvector" else "url"
        try:
            r = self.space.add_store(name, {"kind": kind, field: url.strip()} if kind != "memory" else {"kind": kind})
        except ImportError:
            raise ValueError(f"{kind} 드라이버가 설치되어 있지 않아 추가하지 못했습니다.") from None
        except Exception:  # what a driver says may carry the address and the password
            self.space.stores.pop(name, None)
            self.space.errors.pop(name, None)
            raise ValueError(f"{kind} 저장소에 연결하지 못했습니다. 주소와 네트워크를 확인해 주세요.") from None
        if name in r["errors"]:
            err = r["errors"][name]
            self.space.stores.pop(name, None)
            self.space.errors.pop(name, None)
            raise ValueError(f"{kind} 저장소에 쓰지 못했습니다. {err}")
        self.event("adapter", f"벡터 저장소 {name} 추가")
        return self.space_state()

    def connect_gateway(self, url: str, connection: Any, token: str, dialect: str = "postgres", label: str = "",
                        rules: dict | None = None) -> dict:
        """A draft from a connection a platform lends: its query service reads, the token stays in this session's memory."""
        from urllib.parse import urlparse

        from xgen_space.backends.gateway import GatewayBackend, GatewayError
        from xgen_space.draft import draft

        if not self.data.allow_connect:
            raise PermissionError("공개 데모에서는 플랫폼 연결이 비활성화되어 있어 연결하지 못했습니다. 파일 업로드를 이용해 주세요.")
        url = str(url or "").strip()
        if urlparse(url).scheme not in ("http", "https") or not str(connection or "").strip():
            raise ValueError("쿼리 서비스 주소와 연결 번호가 없어 연결하지 못했습니다. 주소와 연결 번호를 입력해 주세요.")
        wanted: Any = str(connection).strip()
        b = GatewayBackend(url, connection=int(wanted) if wanted.isdigit() else wanted, dialect=dialect or "postgres", token=str(token or "").strip())
        where = f"쿼리 서비스 {urlparse(url).hostname} · 연결 {wanted}"  # never the token
        r = self._rules(rules)
        try:
            d = draft(b, name="my-db", label=(label or "플랫폼 연결")[:40], lang="ko", rules=r, definitions=self._defs(),
                      origin={"kind": "database", "detail": where})
        except GatewayError as e:
            raise ValueError(f"{where}에 연결하지 못했습니다. {e}") from None
        self.pending = (d, b, [], r)
        return self.files_state()

    # ---- pipelines kept: what was applied is there after a restart, where repositories are ---------------------------------

    def _pipelines_root(self) -> Path | None:
        return Path(self.data.repositories) / "pipelines" if self.data.repositories else None

    def save_pipelines(self) -> None:
        """Modules and rows for each pipeline. A connected database keeps its modules only: its address holds a password,
        which is never written here, so that pipeline asks to be connected again."""
        from xgen_space.backends.sql import SqliteBackend

        root = self._pipelines_root()
        if root is None:
            return
        root.mkdir(parents=True, exist_ok=True)
        index = []
        for p in self.pipelines[1:]:
            st, d = p["studio"], root / p["id"]
            d.mkdir(exist_ok=True)
            src = st.backends.get(st.source)
            (d / "modules.json").write_text(json.dumps([m.to_dict() for m in st.composition.modules], ensure_ascii=False), encoding="utf-8")
            kept = isinstance(src, SqliteBackend)
            if kept:
                (d / "data.sql").write_text("\n".join(src.conn.iterdump()), encoding="utf-8")
            index.append({"id": p["id"], "label": p["label"], "name": st.onto.name, "origin": p["origin"], "data": kept})
        tmp = root / "index.json.tmp"
        tmp.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, root / "index.json")
        for d in root.iterdir():  # one that was deleted on the page
            if d.is_dir() and d.name not in {e["id"] for e in index}:
                shutil.rmtree(d, ignore_errors=True)

    def load_pipelines(self) -> None:
        from xgen_space.backends.sql import SqliteBackend
        from xgen_space.library import OverlayLibrary
        from xgen_space.modules import Module
        from xgen_space.studio import Studio

        root = self._pipelines_root()
        if root is None or not (root / "index.json").is_file():
            return
        for e in json.loads((root / "index.json").read_text(encoding="utf-8")):
            d = root / e["id"]
            if not e.get("data"):
                self.event("pipeline", f"{e['label']}은(는) DB 연결이 필요해 복원하지 않았습니다. DB 연결에서 다시 연결해 주세요.")
                continue
            try:
                modules = [Module.from_dict(m) for m in json.loads((d / "modules.json").read_text(encoding="utf-8"))]
                st = Studio.from_modules(modules, library=OverlayLibrary(self.studio.library, modules), name=e.get("name", ""),
                                         use_zen=self.studio.use_zen)
                src = SqliteBackend()
                src.script((d / "data.sql").read_text(encoding="utf-8"))
                st.add_backend("source", src, source=True)
                try:
                    from xgen_space.backends.rdf import RdflibBackend

                    st.add_backend("graph", RdflibBackend())
                    st.project(into=["graph"])
                except ImportError:  # the graph is an extra: the pipeline still reads its source
                    pass
            except (OSError, ValueError, KeyError) as err:
                self.event("pipeline", f"{e['label']}을(를) 복원하지 못했습니다. {err}")
                continue
            st.space, st.reasoners = self.space, self.studio.reasoners
            self.pipelines.append({"id": e["id"], "label": e["label"], "studio": st, "origin": e.get("origin") or {},
                                   "rows": st.library.list(), "log": []})

    # ---- rules: what a table does beyond one answer -----------------------------------------------------------------------

    def rules_state(self) -> dict:
        """Parameters, metrics, what a table leaves open, sources that disagree, what the clock has made due."""
        from dataclasses import asdict

        from xgen_space.decide.checks import decision_findings
        from xgen_space.decide.conflicts import conflict_view
        from xgen_space.decide.metrics import dictionary
        from xgen_space.decide.periods import overlapping_periods
        from xgen_space.web.api import plain

        st, o = self.studio, self.studio.onto
        comp = st.composition
        params = [{"name": p.name, "label": p.label or p.name, "value": p.value, "unit": p.unit, "type": p.type, "min": p.min, "max": p.max,
                   "cite": p.cite, "touched": [self._label(m) for m in (comp.touched.get(f"parameter:{p.name}", []) if comp else [])]}
                  for p in o.parameters.values()]
        try:
            periods = overlapping_periods(st)
        except Exception:  # a source that holds no such table yet: DB 대조 says so
            periods = []
        due = [asdict(d) for d in st.actions.due()] if st.source else []
        views = [{"name": t.name, "label": t.label or t.name, "view": t.view_name, "inline": bool(t.view.get("inline"))} for t in o.objects.values() if t.view]
        findings = [{**f.to_dict(), "label": o.decisions[f.decision].label or f.decision} for f in decision_findings(o)]
        return plain({"parameters": params, "metrics": dictionary(o), "findings": findings,
                      "conflicts": [conflict_view(c) for c in o.source_conflicts()], "periods": periods, "due": due, "views": views})

    def metric_run(self, name: str, since: str | None = None, until: str | None = None) -> dict:
        from xgen_space.decide.metrics import MetricError, answer_metric
        from xgen_space.web.api import plain

        try:
            out = plain(answer_metric(self.studio, name, since=since, until=until).to_dict())
            out["notes"] = ["기간을 지정하지 않아 전체 기간 기준입니다." if "no window" in n else n for n in out["notes"]]
            return out
        except MetricError as e:
            raise ValueError(f"지표를 계산하지 못했습니다. {e}") from None

    def conflict_pick(self, cid: str, source: str, reason: str = "") -> dict:
        """A person's pick is a change like any other: it waits in the pending edits and goes through review."""
        from xgen_space.decide.conflicts import record_pick

        c = next((x for x in self.studio.onto.source_conflicts() if x.id == cid), None)
        if c is None:
            raise LookupError(f"출처 충돌 {cid}")
        ws = self._ws()
        record_pick(ws.module, c, source, by=self.who, reason=str(reason or "")[:200])
        return {"ok": True, "pending": True}

    def transitions_advance(self) -> dict:
        moved = self.studio.actions.advance()
        return {"ok": True, "moved": len(moved)}

    # ---- ports: every kind of thing that can be swapped, and whether it agrees ---------------------------------------

    def adapters(self) -> dict:
        from xgen_space.embed import _KINDS as EMBEDDERS
        from xgen_space.preview import TARGETS

        self._sync_space()
        st = self.studio
        sp = self.space.state()
        backends = [{"name": n, "language": b.capabilities.language, "dialect": b.capabilities.dialect, "source": n == st.source,
                     "write": b.capabilities.write, "load": b.capabilities.load} for n, b in st.backends.items()]
        return {"backends": backends, "languages": [label for _, label in TARGETS], "vectors": sp["stores"],
                "vector_kinds": known_kinds(), "embedder": sp["embedder"], "embedder_kinds": sorted(EMBEDDERS),
                "retriever": self.space.knowledge(st.onto, self._terms()).describe(),
                "reasoners": [r.describe() for r in st.reasoners.values()], "domains": self._domains(),
                "can_connect": self.data.allow_connect}

    def _domains(self) -> list[dict]:
        comp = self.studio.composition
        on = {m.name for m in comp.modules} if comp else set()
        return [{"name": r["name"], "label": r.get("label") or r["name"], "kind": r["kind"], "on": r["name"] in on}
                for r in self._library_rows if r["kind"] in ("domain", "industry", "customer")]

    def adapters_check(self) -> dict:
        """The tests that make swapping safe, run now on what this space holds."""
        from xgen_space.reason.port import agreement

        self._sync_space()
        sp, st = self.space, self.studio
        sp.index()
        chunks = list(sp.chunks.values())[:200]
        texts = [c.text[:200] for c in chunks[:: max(len(chunks) // 8, 1)]][:8]
        vectors = sp.embedder.embed([c.text for c in chunks]) if chunks else []
        from xgen_space.vectors import Point

        points = [Point(c.id, v, {"document": c.document}) for c, v in zip(chunks, vectors)]
        queries = list(zip(texts, sp.embedder.embed(texts))) if texts else []
        rep = conformance(sp.stores, points, queries).to_dict() if points else {"stores": {}, "cases": []}
        started = time.perf_counter()
        graph = st.conformance().summary() if len(st.backends) > 1 else None
        return {"vectors": rep["stores"], "graph": graph, "graph_ms": round((time.perf_counter() - started) * 1000),
                "reasoners": agreement(st.reasoners, st.onto, st.projection) if st.projection is not None else {}}

    def reasoner_run(self, name: str) -> dict:
        st = self.studio
        r = st.reasoners.get(name)
        if r is None:
            raise LookupError(f"추론기 {name}")
        if st.projection is None:
            raise ValueError("그래프 저장소에 반영된 데이터가 없어 추론하지 못했습니다.")
        return r.run(st.onto, st.projection).to_dict()

    # ---- the map of the space: the asset ontology ---------------------------------------------------------------------

    def space_map(self) -> dict:
        from xgen_space.catalog import from_space, map_graph

        self._sync_space()
        cat = from_space(self.studio, self.space, self.repositories.files(self.repo))
        self._map = cat
        def read(a) -> bool:  # a link table is read through its columns
            return any(r.kind != "contains" for r in cat._in[a.id]) or any(
                x.kind == "mapsTo" for r in cat._out[a.id] if r.kind == "contains" for x in cat._in[r.target])

        lonely = [a for a in cat.assets.values() if a.kind in ("table", "file", "document") and not read(a)]
        return {**map_graph(cat), "unused": [{"id": a.id, "label": a.label or a.id, "kind": a.kind} for a in lonely][:20]}

    def space_map_node(self, node: str) -> dict:
        cat = getattr(self, "_map", None)
        if cat is None or node not in cat.assets:
            self.space_map()
            cat = self._map
        a = cat.assets.get(node)
        if a is None:
            raise LookupError(f"자산 {node}")
        impact = cat.impact(node)
        uses = [cat.assets[r.target] for r in cat.relations if r.source == node and r.target in cat.assets]
        row = lambda x: {"id": x.id, "kind": x.kind, "label": x.label or x.id}  # noqa: E731
        return {"id": a.id, "kind": a.kind, "label": a.label or a.id, "impact": [row(x) for x in impact[:300]], "uses": [row(x) for x in uses[:300]]}

    # ---- the way in from outside ---------------------------------------------------------------------------------------

    def integrations(self) -> dict:
        from xgen_space.rest import tool_list

        return {"rest": bool(getattr(self.data, "rest", False)), "openapi": "/v1/openapi.json", "tools": tool_list(), "gateway": self.data.allow_connect}


def attach(session: Any) -> None:
    """Every studio a session adopts shares the session's space: documents do not change with the pipeline."""
    from xgen_space.embed import open_embedder
    from xgen_space.reason.port import open_reasoners
    from xgen_space.space import open_space

    st = session.studio
    held = getattr(session, "_held_space", None)
    if held is None:
        held = st.space if st.space is not None else open_space(None)
        if session.data.embedder:
            held.embedder = open_embedder(session.data.embedder)
        session._held_space = held
    st.space = held
    if not st.reasoners:
        st.reasoners = open_reasoners(None)
