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
from xgen_space.preview import KIND_LABEL
from xgen_space.values import normalize
from xgen_space.vectors import VectorError, conformance, known_kinds

SEARCH_MAX = 300  # characters of a question
K_MAX = 20
SEARCH_ROWS = 200  # hits the explorer's search returns
STORE_KINDS = ("vector_store", "graph_store", "embedder", "reasoner")
USE_KINDS = ("query", "decision", "action", "role", "agent")
GROUP_WORDS = {"group:repos": "레포지토리", "group:source": "데이터베이스", "group:document": "문서", "group:ontology": "온톨로지",
               "group:store": "저장소 어댑터", "group:use": "활용"}
GROUP_KINDS = {"group:repos": ("folder", "file"), "group:source": ("database", "table", "column"),
               "group:document": ("collection", "document"), "group:ontology": ("object", "property", "link"), "group:store": STORE_KINDS}
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
        out["now"] = self.studio.now().isoformat(timespec="minutes")  # what "4 days since delivery" is counted to
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
        from xgen_space.compile.base import CompileError
        from xgen_space.embed import _KINDS as EMBEDDERS
        from xgen_space.preview import TARGETS

        self._sync_space()
        st = self.studio
        sp = self.space.state()
        target = _target

        backends = [{"name": n, "language": b.capabilities.language, "dialect": b.capabilities.dialect, "source": n == st.source,
                     "write": b.capabilities.write, "load": b.capabilities.load,
                     "target": target(b.capabilities.language, b.capabilities.dialect)} for n, b in st.backends.items()]
        # every registered query compiled now, so a language shows what it can carry, not only that it is known
        labels = {target(*t.split(":", 1)) if t.startswith("sql:") else t: label for t, label in TARGETS}
        order = list(labels) + [b["target"] for b in backends if b["target"] not in labels]
        languages = []
        for t in dict.fromkeys(order):
            refused = []
            for q in st.onto.queries:
                try:
                    st.translate(q, t)
                except CompileError as e:
                    refused.append({"query": q, "error": str(e)})
            label = labels.get(t) or (f"SQL · {t.split(':', 1)[1]}" if t.startswith("sql:") else t)
            languages.append({"id": t, "label": label, "compiled": len(st.onto.queries) - len(refused),
                              "refused": refused, "backends": [b["name"] for b in backends if b["target"] == t]})
        return {"backends": backends, "languages": languages, "queries": len(st.onto.queries), "vectors": sp["stores"],
                "vector_kinds": known_kinds(), "embedder": sp["embedder"], "embedder_kinds": sorted(EMBEDDERS),
                "retriever": self.space.knowledge(st.onto, self._terms()).describe(),
                "reasoners": [r.describe() for r in st.reasoners.values()], "can_connect": self.data.allow_connect}

    def connections(self) -> dict:
        """What the space is connected to, tried now, for the sidebar: each store answers a one-row query or says why
        not, a vector store by the error the space keeps, the language model by how its last call went. It names kinds,
        never what the data is about."""
        from xgen_space.preview import TARGETS
        from xgen_space.web.api import said

        self._sync_space()
        st, sp = self.studio, self.space
        kinds = self.origin.get("backends") or {}
        probe = next(((n, t.key) for n, t in st.onto.objects.items() if t.table and t.key), None)
        labels = {_target(*t.split(":", 1)) if t.startswith("sql:") else t: label for t, label in TARGETS}
        stores = []
        for n, b in st.backends.items():
            started, error = time.perf_counter(), ""
            try:
                if probe is None:
                    raise LookupError("원천 테이블과 연결된 객체가 없어 질의하지 못했습니다.")
                st.run({"match": {"x": probe[0]}, "return": [f"x.{probe[1]}"], "limit": 1}, backend=n)
            except Exception as e:  # a store that does not answer is what this shows, not a failure of the page
                error = said(e)
            t = _target(b.capabilities.language, b.capabilities.dialect)
            stores.append({"name": n, "kind": kinds.get(n) or b.kind, "source": n == st.source,
                           "language": labels.get(t) or ("SQL" if t.startswith("sql:") else t.upper()),
                           "state": "bad" if error else "ok", "error": error, "ms": round((time.perf_counter() - started) * 1000)})
        ran = {_target(b.capabilities.language, b.capabilities.dialect) for b in st.backends.values()}
        emb, last = sp.embedder.describe(), self._llm_last
        return plain({
            "pipeline": self.pipeline, "stores": stores,
            "vectors": [{"name": n, "kind": s.kind, "state": "bad" if sp.errors.get(n) else "ok", "error": sp.errors.get(n, "")}
                        for n, s in sp.stores.items()],
            "translate": [label for t, label in labels.items() if t not in ran],
            "embedder": {"kind": emb.get("kind", ""), "name": emb.get("name", ""), "dim": emb.get("dim")},
            "llm": {"kind": getattr(self.llm, "kind", "") if self.llm else "", "at": (last or {}).get("at", ""),
                    "error": (last or {}).get("error", ""),
                    "state": "off" if self.llm is None else "idle" if last is None else "ok" if last["ok"] else "bad"},
            "rest": bool(getattr(self.data, "rest", False))})

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
        graph_ms = round((time.perf_counter() - started) * 1000)
        runs = {n: r.run(st.onto, st.projection) for n, r in st.reasoners.items()
                if not r.available()} if st.projection is not None else {}
        return {"vectors": rep["stores"], "graph": graph, "graph_ms": graph_ms,
                "runs": {n: {"count": len(i.derived), "found": len(i.findings), "ms": i.ms, "error": i.error} for n, i in runs.items()},
                "reasoners": agreement(st.reasoners, st.onto, st.projection, runs) if st.projection is not None else {}}

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

    # ---- the explorer: everything the space holds as folders, with what each part went through ------------------------

    def _explorer_parts(self) -> dict:
        """The asset ontology of the space and the repository it reads: the one source the explorer shows."""
        from collections import Counter

        from xgen_space.catalog import from_space

        self._sync_space()
        files = self.repositories.files(self.repo)
        cat = from_space(self.studio, self.space, files)
        return {"cat": cat, "files": files, "kinds": Counter(a.kind for a in cat.assets.values()),
                "chunks": Counter(c.document for c in self.space.chunks.values()),
                "made": {p: [d["name"] for d in (getattr(defs, "documents", None) or [])] for p, defs in self.definitions.items()},
                "folders": sorted(self.repositories.items[self.repo]["folders"])}

    def _explorer_tree(self, x: dict) -> list[dict]:
        cat, kinds, files = x["cat"], x["kinds"], x["files"]
        count = {"group:repos": sum(r["files"] for r in self.repositories.rows()), "group:source": kinds["table"],
                 "group:document": kinds["document"], "group:ontology": kinds["object"] + kinds["link"],
                 "group:store": sum(kinds[k] for k in STORE_KINDS), "group:use": sum(kinds[k] for k in USE_KINDS)}
        tree = [{"id": g, "label": label, "parent": "", "count": count[g]} for g, label in GROUP_WORDS.items()]
        tree += [{"id": f"repo:{r['id']}", "label": r["label"], "parent": "group:repos", "count": r["files"],
                  "current": r["id"] == self.repo} for r in self.repositories.rows()]
        for d in x["folders"]:
            up = d.rsplit("/", 1)[0] if "/" in d else ""
            tree.append({"id": f"dir:{d}", "label": d.rsplit("/", 1)[-1], "parent": f"dir:{up}" if up else f"repo:{self.repo}",
                         "count": sum(1 for p in files if p.startswith(d + "/"))})
        for a in cat.assets.values():
            if a.kind == "database":
                tree.append({"id": a.id, "label": a.label, "parent": "group:source", "count": len(_children(cat, a.id, "table"))})
            elif a.kind == "collection":
                tree.append({"id": a.id, "label": "문서 컬렉션", "parent": "group:document", "count": kinds["document"]})
        for group, keys in (("group:ontology", ("object", "link")), ("group:use", USE_KINDS)):
            tree += [{"id": f"kind:{k}", "label": KIND_LABEL[k], "parent": group, "count": kinds[k]} for k in keys if kinds[k]]
        return tree

    def explorer(self) -> dict:
        x = self._explorer_parts()
        k = x["kinds"]
        summary = {"files": len(x["files"]), "folders": len(x["folders"]), "tables": k["table"], "columns": k["column"],
                   "documents": k["document"], "chunks": sum(x["chunks"].values()), "objects": k["object"],
                   "properties": k["property"], "links": k["link"], "uses": sum(k[n] for n in USE_KINDS),
                   "trash": len(self.repositories.items[self.repo].get("trash", []))}
        return {"tree": self._explorer_tree(x), "repo": self.repo, "summary": summary}

    def explorer_items(self, node: str) -> dict:
        """What a node of the tree holds, each row with what it is and what it went through."""
        x = self._explorer_parts()
        cat = x["cat"]
        row = lambda a: self._explorer_row(x, a)  # noqa: E731
        if node.startswith("repo:") and node[5:] != self.repo:
            raise LookupError("사용 중인 레포지토리가 아니어서 열지 못했습니다. 레포지토리를 전환한 뒤 열어 주세요.")
        if node.startswith(("repo:", "dir:")):
            folder = node[4:] if node.startswith("dir:") else ""
            subs, here = self.repositories.listing(self.repo, folder)
            items = [self._folder_row(x, s["path"]) for s in subs] + [row(cat.assets[f"file:{f['path']}"]) for f in here]
        elif node == "group:store":
            items = [row(a) for a in cat.assets.values() if a.kind in STORE_KINDS]
        elif node.startswith("group:"):
            items = [{"id": t["id"], "kind": "group", "label": t["label"], "facts": [f"{t['count']:,}개"], "status": [],
                      "current": t.get("current", False)} for t in self._explorer_tree(x) if t["parent"] == node]
        elif node.startswith("kind:"):
            items = [row(a) for a in cat.assets.values() if a.kind == node[5:]]
        elif node in cat.assets:
            kind = cat.assets[node].kind
            if kind == "collection":
                items = [row(a) for a in cat.assets.values() if a.kind == "document"]
            else:
                inner = {"database": "table", "table": "column", "object": "property"}.get(kind)
                items = [row(cat.assets[i]) for i in _children(cat, node, inner)] if inner else []
        else:
            raise LookupError(f"항목 {node}")
        tree = {t["id"]: t["label"] for t in self._explorer_tree(x)}
        label = tree.get(node) or (cat.assets[node].label if node in cat.assets else node.split(":", 1)[-1].rsplit("/", 1)[-1])
        return {"node": node, "label": label, "trail": self._explorer_trail(x, node), "items": items}

    def _folder_row(self, x: dict, path: str) -> dict:
        files, chunks, made = x["files"], x["chunks"], x["made"]
        inside = [p for p in files if p.startswith(path + "/")]
        indexed = sum(1 for p in inside if any(chunks[d] for d in made.get(p, [])))
        included = sum(1 for p in inside if files[p].get("included"))
        failed = sum(1 for p in inside if files[p].get("error"))
        status = [{"text": f"문서 색인 {indexed}/{len(inside)}", "tone": "ok" if indexed else ""},
                  {"text": f"초안 포함 {included}/{len(inside)}", "tone": "b" if included else ""}]
        if failed:
            status.append({"text": f"읽기 실패 {failed}", "tone": "bad"})
        return {"id": f"dir:{path}", "kind": "folder", "label": path.rsplit("/", 1)[-1], "path": path, "manage": True,
                "bytes": sum(files[p]["bytes"] for p in inside), "facts": [f"파일 {len(inside):,}개"], "status": status}

    def _explorer_row(self, x: dict, a) -> dict:
        cat, files, chunks, made = x["cat"], x["files"], x["chunks"], x["made"]
        out = {"id": a.id, "kind": a.kind, "label": a.label, "facts": [], "status": []}
        say, mark = out["facts"].append, out["status"].append
        into = lambda kind: [cat.assets[r.target].label for r in cat._out[a.id] if r.kind == kind and r.target in cat.assets]  # noqa: E731
        came = lambda kind: [cat.assets[r.source].label for r in cat._in[a.id] if r.kind == kind and r.source in cat.assets]  # noqa: E731
        if a.kind == "file":
            path = a.id[5:]
            f = files.get(path, {})
            fx = f.get("facts") or {}
            out.update(path=path, manage=True, bytes=f.get("bytes", 0))
            say({"data": f"표 {fx.get('tables', 0)}개 · {fx.get('rows', 0):,}행", "document": f"문서 · 절 {fx.get('sections', 0)}개",
                 "definition": "정의서", "raw": "원본 보관", "empty": "내용 없음"}.get(fx.get("kind"), "-"))
            if f.get("error"):
                mark({"text": "읽기 실패", "tone": "bad", "why": f["error"]})
            n = sum(chunks[d] for d in made.get(path, []))
            if n:
                mark({"text": f"문서 색인 · 청크 {n}", "tone": "ok"})
            if fx.get("kind") not in ("raw", None) and not f.get("error"):
                mark({"text": "초안 포함" if f.get("included") else "초안 제외", "tone": "b" if f.get("included") else ""})
        elif a.kind == "document":
            n = chunks[a.label]
            say(f"청크 {n}")
            upload = any(r.kind == "uses" and r.target.startswith("file:") for r in cat._out[a.id])
            mark({"text": "업로드 파일" if upload else "예시 문서", "tone": "b" if upload else ""})
            seen = into("mentions")
            if seen:
                say(f"언급한 객체 {len(seen)}개")
            mark({"text": "문서 색인" if n else "색인 전", "tone": "ok" if n else "warn"})
        elif a.kind in ("database", "table"):
            inner = "table" if a.kind == "database" else "column"
            say(f"{KIND_LABEL[inner]} {len(_children(cat, a.id, inner))}개")
            if a.kind == "table":
                users = came("mapsTo")
                mark({"text": f"객체 · {', '.join(users[:3])}", "tone": "ok"} if users else {"text": "사용하지 않는 테이블", "tone": "warn"})
        elif a.kind == "column":
            props = came("mapsTo")
            if props:
                mark({"text": f"속성 · {', '.join(props[:3])}", "tone": "ok"})
        elif a.kind == "object":
            say(f"속성 {len(_children(cat, a.id, 'property'))}개")
            tables = into("mapsTo")
            mark({"text": f"테이블 · {tables[0]}", "tone": "ok"} if tables else {"text": "원천 연결 없음", "tone": "warn"})
            docs = came("mentions")
            if docs:
                say(f"언급 문서 {len(docs)}개")
        elif a.kind == "property":
            if a.attrs.get("type"):
                say(str(a.attrs["type"]))
            cols = into("mapsTo")
            if cols:
                mark({"text": f"컬럼 · {cols[0]}", "tone": "ok"})
        else:
            uses, used = into("uses") + into("canRead"), came("uses") + came("canRead")
            if uses:
                say(f"사용 {len(uses)}개")
            if used:
                say(f"이 항목을 쓰는 곳 {len(used)}개")
        return out

    def _explorer_trail(self, x: dict, node: str) -> list[dict]:
        """What a node sits in, from its group down to what holds it (the node itself not included), for the path bar."""
        cat = x["cat"]
        if node.startswith("group:") or not node:
            return []
        if node.startswith("repo:"):
            return [{"id": "group:repos", "label": GROUP_WORDS["group:repos"]}]
        if node.startswith(("dir:", "file:")):
            out = [{"id": "group:repos", "label": GROUP_WORDS["group:repos"]},
                   {"id": f"repo:{self.repo}", "label": self.repositories.items[self.repo]["label"]}]
            parts = node.split(":", 1)[1].split("/")
            out += [{"id": "dir:" + "/".join(parts[:i + 1]), "label": parts[i]} for i in range(len(parts) - 1)]
            return out
        kind = node[5:] if node.startswith("kind:") else cat.assets[node].kind if node in cat.assets else ""
        group = next((g for g, ks in GROUP_KINDS.items() if kind in ks), "group:use")
        out = [{"id": group, "label": GROUP_WORDS[group]}]
        if node.startswith("kind:"):
            return out
        holder = next((r.source for r in cat._in[node] if r.kind in ("contains", "hasProperty") and r.source in cat.assets), "")
        if holder:
            out = self._explorer_trail(x, holder) + [{"id": holder, "label": cat.assets[holder].label}]
        elif kind in ("object", "link") + USE_KINDS:
            out.append({"id": f"kind:{kind}", "label": KIND_LABEL[kind]})
        elif kind == "document" and f"collection:{self.space.collection}" in cat.assets:
            out.append({"id": f"collection:{self.space.collection}", "label": "문서 컬렉션"})
        return out

    def explorer_search(self, q: str, kind: str = "") -> dict:
        """One search over everything: names and paths, the definitions a question names, and the documents by their words and
        by meaning. Each hit says which of these found it."""
        from xgen_space.embed import shared_wording

        q = str(q or "").strip()[:SEARCH_MAX]
        if not q:
            raise ValueError("검색어가 없어 찾지 못했습니다. 찾을 내용을 입력해 주세요.")
        x = self._explorer_parts()
        cat = x["cat"]
        hits: dict[str, dict] = {}

        def hit(row: dict | None, how: str, *, snippet: str = "", score: float = 0.0) -> None:
            if row is None or (kind and row["kind"] != kind):
                return
            h = hits.setdefault(row["id"], {**row, "found": [], "score": 0.0, "snippet": ""})
            if how not in h["found"]:
                h["found"].append(how)
            h["score"], h["snippet"] = max(h["score"], score), h["snippet"] or snippet

        low = q.lower()
        for a in cat.assets.values():
            label, key = a.label.lower(), a.id.split(":", 1)[-1].lower()
            if low in label or low in key:
                hit(self._explorer_row(x, a), "경로" if a.kind == "file" and low not in label else "이름",
                    score=1.0 if low == label else 0.6)
        for d in x["folders"]:
            if low in d.rsplit("/", 1)[-1].lower():
                hit(self._folder_row(x, d), "이름", score=1.0 if low == d.rsplit("/", 1)[-1].lower() else 0.6)
        for c in self.space.concepts_in(q, self.studio.onto, self._terms()):
            if c.get("element") in cat.assets:
                hit(self._explorer_row(x, cat.assets[c["element"]]), "정의", score=0.8)
        try:
            found = self.space.search(q, K_MAX)
        except (VectorError, OSError, EmbedError):  # a store that cannot be reached leaves names and definitions to answer
            found = []
        meaning = self.space.embedder.semantic  # a wording embedder finds words, so it does not say meaning
        for h in found:
            a = cat.assets.get(f"document:{h['document']}")
            if a is not None:
                words = not meaning or shared_wording(q, h["text"]) > 0
                hit(self._explorer_row(x, a), "단어 일치" if words else "의미 유사",
                    snippet=f"{h['section']} · {h['text'][:160]}", score=float(h["score"]))
        layer = {"이름": "name", "경로": "name", "정의": "definition", "단어 일치": "text", "의미 유사": "text"}
        rows = sorted(hits.values(), key=lambda h: (-len({layer[f] for f in h["found"]}), -h["score"], h["label"]))
        for h in rows[:SEARCH_ROWS]:
            h["trail"] = self._explorer_trail(x, h["id"])
        return {"q": q, "hits": rows[:SEARCH_ROWS], "total": len(rows)}

    # ---- the way in from outside ---------------------------------------------------------------------------------------

    def integrations(self) -> dict:
        from xgen_space.rest import tool_list

        return {"rest": bool(getattr(self.data, "rest", False)), "openapi": "/v1/openapi.json", "tools": tool_list(), "gateway": self.data.allow_connect}


def _target(lang: str, dialect: str) -> str:
    """The language a store reads, named as the compilers are."""
    from xgen_space.compile.sql import _NAMES as SQL_NAMES

    return f"sql:{SQL_NAMES.get(dialect, dialect) or 'postgres'}" if lang == "sql" else lang


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


def _children(cat, asset: str, kind: str) -> list[str]:
    """What an asset holds of one kind: a database's tables, a table's columns, an object's properties."""
    return [r.target for r in cat._out[asset]
            if r.kind in ("contains", "hasProperty") and r.target in cat.assets and cat.assets[r.target].kind == kind]
