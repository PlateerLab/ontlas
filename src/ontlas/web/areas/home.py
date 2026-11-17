"""What the home, the search screen and the AI draft screen ask beyond the routes the older screens had.

The home reads the overview the studio already keeps (maturity, the four parts, the Objects) and adds what its other
cards say: the rule cards by layer, what was uploaded, what waits to be reviewed, and the six steps of getting started,
each judged from what is here. The search screen asks for everything a question touches as one list. The AI draft
screen asks what a draft can be made from, and keeps a record of the drafts made from it.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ontlas.web.routes import get, post

FOUND_MAX = 40
JOBS_MAX = 30
# what a found entry is called on the page, and the screen that shows it
FOUND = {"object": ("Entity", "def", "objects"), "query": ("질의", "def", "query"), "action": ("Action", "def", "actions"),
         "rule": ("규칙", "rule", "semrules"), "card": ("규칙", "rule", "semrules"), "document": ("자료", "doc", "evidence"),
         "term": ("용어", "term", "lexicon")}


def _materials(s) -> dict:
    """The files of the repository in use, by what each turned out to be."""
    files = s.repositories.files(s.repo)
    out = {"files": len(files), "data": 0, "definition": 0, "document": 0, "raw": 0, "included": 0, "unread": 0}
    for f in files.values():
        if f.get("error"):
            out["unread"] += 1
            continue
        kind = (f.get("facts") or {}).get("kind")
        if kind in ("data", "definition", "document", "raw"):
            out[kind] += 1
        if f.get("included") and kind != "raw":
            out["included"] += 1
    return out


def _rules(s) -> dict:
    """The rule cards as the rules screen counts them: by layer, and how many are still drafts or under review."""
    if s.studio.composition is None:
        return {"cards": 0, "layers": {}, "draft": 0, "review": 0, "legal": 0}
    view = s.semantic_state()
    cards = view.get("cards") or []
    layers = {x["layer"]: 0 for x in view.get("layers") or []}
    for c in cards:
        layers[c["layer"]] = layers.get(c["layer"], 0) + 1
    return {"cards": len(cards), "layers": layers,
            "draft": sum(1 for c in cards if c.get("status") == "draft"),
            "review": sum(1 for c in cards if c.get("status") == "review"),
            "legal": sum(1 for c in cards if c.get("legal_review") == "pending")}


def _terms(s) -> dict:
    if s.studio.composition is None:
        return {"terms": 0, "waiting": 0}
    rows = s.lexicon_state().get("rows") or []
    return {"terms": len(rows), "waiting": sum(1 for r in rows if r.get("status") in ("draft", "review"))}


def _waiting(s, rules: dict, terms: dict) -> dict:
    """What waits for a person to review before it is part of the definition: rule cards not yet approved, a draft made
    from files that is not applied, terms not yet in use."""
    draft = s.pending[0] if s.pending else None
    concepts = len(draft.objects) + len(draft.links) if draft is not None else 0
    out = {"rules": rules["draft"] + rules["review"], "concepts": concepts, "terms": terms["waiting"],
           "draft": {"label": draft.label, "objects": len(draft.objects), "links": len(draft.links)} if draft is not None else None,
           "request": s._request_view()}
    out["all"] = out["rules"] + out["concepts"] + out["terms"]
    return out


def _changes(s) -> dict:
    ch = s.studio.changes
    dirty, edits = False, 0
    if s.studio.composition is not None:
        ws = s._ws()
        dirty, edits = ws.dirty, len(ws.edits)
    return {"pending": sum(1 for c in ch.requests.values() if c.status == "pending"),
            "approved": sum(1 for c in ch.requests.values() if c.status == "approved"), "draft": dirty, "edits": edits}


def _steps(s, ov: dict, mats: dict, waiting: dict, changes: dict) -> list[dict]:
    """The six steps a new ontology goes through, each done, under way, not started or optional, from what is here."""
    entities = ov["maturity"]["entities"]
    qa = next(c for c in ov["components"] if c["id"] == "qa")
    source = s.studio.source_info()
    rest = bool(getattr(s.data, "rest", False))
    held = waiting["all"] + changes["pending"] + (1 if changes["draft"] else 0)
    return [
        {"id": "upload", "state": "done" if mats["files"] else "todo", "files": mats["files"], "documents": mats["document"],
         "definitions": mats["definition"], "data": mats["data"]},
        {"id": "drafts", "state": "doing" if held else "done" if entities else "todo", "waiting": waiting["all"],
         "changes": changes["pending"], "edits": changes["edits"] if changes["draft"] else 0},
        {"id": "questions", "state": "done" if qa["counts"]["questions"] else "todo", "questions": qa["counts"]["questions"],
         "accuracy": qa.get("accuracy"), "failed": qa["counts"]["failed"]},
        {"id": "version", "state": "done" if entities else "todo", "label": ov["version"]["label"], "number": ov["version"]["number"]},
        {"id": "agents", "state": "done" if rest and entities else "todo", "rest": rest},  # an API with nothing defined serves nothing
        {"id": "source", "state": "done" if source.get("connected") else "optional", "kind": source.get("kind") or ""},
    ]


@get("home/summary")
def summary(s, a, who) -> dict:
    """Everything the home shows in one answer: the overview as the studio keeps it, and beside it the rule cards, the
    uploaded material, what waits for review, the change requests, and the steps of getting started."""
    from ontlas.web.api import plain

    ov = s.overview()
    rules, terms, mats, changes = _rules(s), _terms(s), _materials(s), _changes(s)
    waiting = _waiting(s, rules, terms)
    lib = next((x for x in getattr(s, "libraries", []) if x.get("id") == getattr(s, "library_id", "")), None)
    o = s.studio.onto
    return plain({"name": (lib or {}).get("label") or o.label or o.name, **ov, "rules": rules, "terms": terms, "materials": mats,
                  "waiting": waiting, "changes": changes, "steps": _steps(s, ov, mats, waiting, changes)})


def _go(kind: str, f: dict) -> str:
    """Where a found entry is looked at: an Entity on the Entity screen, a rule on the rules screen, and so on."""
    return FOUND[kind][2]


@get("home/find")
def find(s, a, who) -> dict:
    """Everything a search or a question touches, as one list: the Entities, queries and actions it names, the rules
    it reaches, the terms it uses, and the passages of the documents. Each says what it is and where it is shown."""
    from ontlas.backends.base import NoSource
    from ontlas.embed import shared_wording
    from ontlas.tools import StudioTools

    text = " ".join(str(a.get("q") or "").split())[:300]
    folder = str(a.get("folder") or "")  # the scope the question was asked in: only that folder's passages
    if not text:
        raise ValueError("검색어가 없어 검색하지 못했습니다. 검색어를 입력해 주세요.")
    s._sync_space()
    tools = StudioTools(s.studio, actor_id=s.who or "page")
    tools.terms = s._terms()
    out: list[dict] = []
    try:
        matched = tools.read_terms(text).get("matched") or []
    except (KeyError, ValueError, NoSource):
        matched = []
    seen: set[str] = set()
    for m in matched:
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        said = m.get("label") or m.get("concept_label") or ""
        out.append({"id": f"term:{m['id']}", "kind": "term", "word": FOUND["term"][0], "group": "term", "title": m.get("term") or "",
                    "sub": " · ".join(x for x in ("표준 용어", str(said)) if x), "go": "lexicon", "element": m.get("concept") or ""})
    try:
        index = tools.knowledge(folder)
        found = index.find(text, FOUND_MAX)
    except Exception:  # a store that cannot be reached leaves the terms to answer; the page says nothing was found there
        index, found = None, []
    if index is not None:
        # the index fills its list with what is near in letters and what is tied to that; an entry belongs to the question
        # when it has the question's wording, is what a matched term stands for, or is a passage a store of meanings
        # found, and a definition also when it is tied to one of those (the Entities a matched rule reads)
        meaning = bool(getattr(getattr(s.space, "embedder", None), "semantic", False))
        named = {m.get("concept") for m in matched} - {None, ""}
        said = {f["id"] for f in found if f.get("element") in named or (meaning and f["kind"] == "document")
                or shared_wording(text, f"{f['title']} {f.get('text') or ''}") > 0}
        tied = {x for a, _, b in index.links for x, y in ((a, b), (b, a)) if y in said}
        found = [f for f in found if f["id"] in said or (f["kind"] != "document" and f["id"] in tied)]
    for f in found:
        kind = f["kind"]
        if kind not in FOUND:
            continue
        word, group, _ = FOUND[kind]
        if kind == "document":
            title, sub = f"{f.get('document', '')} › {f.get('section', '')}".strip(" ›"), " ".join(str(f.get("text") or "").split())[:120]
        elif kind == "rule":
            title, sub = f["title"], " ".join(x for x in (str(f.get("cite") or ""),) if x) or " ".join(str(f.get("text") or "").split())[:120]
        else:
            title, sub = f["title"], " ".join(str(f.get("text") or "").split())[:120]
        out.append({"id": f["id"], "kind": kind, "word": word, "group": group, "title": title, "sub": sub, "go": _go(kind, f),
                    "element": f.get("element") or "", "score": f.get("score", 0),
                    **({"document": f.get("document") or ""} if kind == "document" else {})})
    # the rule cards that are written down only: the index above holds the rows of the decision tables, not these
    # (a text with no word of two letters or more matches every card there, so it asks for none)
    worded = any(len(w) >= 2 for w in text.split())
    cards = tools.find_rules(text, k=FOUND_MAX)["rules"] if s.studio.composition is not None and worded else []
    for c in cards:
        word, group, go = FOUND["card"]
        out.append({"id": f"card:{c['id']}", "kind": "card", "word": word, "group": group, "title": f"{c['id']} · {c['statement']}",
                    "sub": " · ".join(str(x) for x in (c.get("layer_label"), c.get("source")) if x), "go": go, "element": ""})
    counts: dict[str, int] = {"def": 0, "rule": 0, "term": 0, "doc": 0}
    for x in out:
        counts[x["group"]] += 1
    return {"q": text, "found": out, "total": len(out), "counts": counts}


def _jobs(s) -> list[dict]:
    if getattr(s, "_ai_jobs", None) is None:
        s._ai_jobs = []
    return s._ai_jobs


def _job_state(s, job: dict) -> tuple[str, str]:
    """Where a draft made here stands now: still waiting for review, filed as a change request, or done with."""
    if job.get("error"):
        return "failed", "실패"
    if job["kind"] == "concepts":
        d = s.pending[0] if s.pending else None
        if d is not None and d.label == job.get("label") and len(d.objects) == job["made"].get("objects"):
            return "waiting", "검토 대기"
        return "done", "검토 완료"
    hit = [c for c in s.studio.changes.requests.values() if c.module == job.get("module")]
    if not hit:
        return "waiting", "검토 대기"
    last = hit[-1]
    return ("filed", "변경 요청 검토 중") if last.status == "pending" else ("done", "배포됨" if last.status == "approved" else "반려됨")


def _ai_state(s) -> dict:
    from ontlas.preview import MODULE_KIND

    st, o = s.studio, s.studio.onto
    comp = st.composition
    rules, terms = _rules(s), _terms(s)
    docs = [{"name": x["name"], "kind": x.get("kind") or "other", "sections": len(x.get("sections") or [])}
            for d in s.definitions.values() for x in (getattr(d, "documents", None) or [])]
    tables = sum(len(ts) for ts in s.uploads.values()) + sum(len(d.tables) for d in s.definitions.values())
    packs = [{"name": m.name, "label": s._label(m.name), "version": m.version, "kind": m.kind, "kind_label": MODULE_KIND.get(m.kind, m.kind)}
             for m in (comp.modules if comp else []) if m.kind in ("domain", "industry", "law", "customer")]
    running = bool(s._draft and s._draft["out"] is None)
    jobs = []
    for j in _jobs(s):
        state, word = _job_state(s, j)
        jobs.append({**j, "state": state, "state_label": word})
    month = datetime.now().strftime("%Y-%m")
    mine = [j for j in jobs if str(j.get("at", "")).startswith(month)]
    return {"model": {"on": s.llm is not None, "kind": getattr(s.llm, "kind", "") if s.llm else ""},
            "materials": _materials(s), "documents": docs, "tables": tables, "sample_policy": bool(s._policy_files()),
            "samples": bool(s._sample_files()),
            "targets": [{"id": t.name, "label": t.label or t.name} for t in o.objects.values() if t.table],
            "packs": packs, "rules_by": [s._label(m) for m in (comp.rules_by if comp else [])],
            "existing": {"objects": len(o.areas), "entities": len(o.objects), "relations": len(o.links),
                         "properties": sum(len(t.properties) for t in o.objects.values()), "rules": rules["cards"],
                         "terms": terms["terms"]},
            "waiting": _waiting(s, rules, terms), "running": running, "composed": comp is not None, "jobs": jobs,
            "month": {"jobs": len(mine), "made": sum(j["made"].get("all", 0) for j in mine),
                      "excluded": sum(j["made"].get("excluded", 0) for j in mine)}}


@get("home/ai")
def ai(s, a, who) -> dict:
    """What a draft can be made from here (the uploaded material, the modules applied, what is already defined), whether
    a model is connected, what waits for review, and the drafts made from this screen with where each stands."""
    from ontlas.web.api import plain

    s._hold()
    return plain(_ai_state(s))


@post("home/ai/job", needs="editor")
def ai_job(s, a, who) -> dict:
    """Record a draft that was just made, from what the studio holds of it: a draft from files (the Entities and
    relations it made, the tables it left out) or a rule draft from a policy (its rules, and what its check found).
    A making that failed is recorded with why, so the screen does not show the one before it as the last."""
    from ontlas.web.api import plain

    kind = str(a.get("kind") or "")
    now = datetime.now().isoformat(timespec="minutes")
    base: dict[str, Any] = {"at": now, "by": s.who or "", "kind": kind, "model": getattr(s.llm, "kind", "") if s.llm else "",
                            "files": _materials(s)["included"]}
    error = " ".join(str(a.get("error") or "").split())[:300]
    if error and kind in ("concepts", "rules"):
        job = {**base, "label": "", "scope": str(a.get("scope") or "")[:200], "error": error, "made": {"all": 0, "excluded": 0}}
    elif kind == "concepts":
        if not s.pending:
            raise ValueError("생성된 초안이 없어 기록하지 못했습니다. 초안을 먼저 생성해 주세요.")
        d = s.pending[0]
        left = len(getattr(d, "skipped", None) or [])
        job = {**base, "label": d.label, "scope": str((d.origin or {}).get("detail") or d.label),
               "made": {"objects": len(d.objects), "links": len(d.links), "all": len(d.objects) + len(d.links), "excluded": left}}
    elif kind == "rules":
        out = (s._draft or {}).get("out")
        if not out or not out.get("ok"):
            raise ValueError("생성된 규칙 초안이 없어 기록하지 못했습니다. 규칙 초안을 먼저 생성해 주세요.")
        job = {**base, "label": out.get("label") or out.get("decision") or "", "module": out.get("module") or "",
               "scope": str(a.get("scope") or out.get("target") or ""),
               "made": {"rules": len(out.get("rules") or []), "all": len(out.get("rules") or []), "excluded": len(out.get("issues") or [])}}
    else:
        raise ValueError("초안 종류가 없어 기록하지 못했습니다. 초안 종류를 지정해 주세요.")
    jobs = _jobs(s)
    jobs.insert(0, job)
    del jobs[JOBS_MAX:]
    return plain(_ai_state(s))
