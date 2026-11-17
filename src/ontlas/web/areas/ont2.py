"""What the later screens of Ontology ask beyond the session's own routes: the change request being written
(its title and what it will be numbered), how one term of the lexicon came to read as it does, and taking the last
deployed change back as a new version."""
from __future__ import annotations

from typing import Any

from ontlas.web.routes import get, post

TERM_FIELD_WORD = {"term": "용어", "english": "영문 표기", "kind": "구분", "concept": "연결 개념", "definition": "정의",
                   "synonyms": "동의어", "abbreviations": "약어", "channels": "채널 표기", "hidden": "숨은 표기",
                   "related": "관련어", "broader": "상위어", "narrower": "하위어", "confusable": "혼동주의",
                   "avoid": "쓰지 않는 표현", "source": "출처", "cite": "근거", "owner": "담당자", "status": "상태"}
STATUS_WORD = {"pending": "검토 중", "approved": "배포됨", "rejected": "반려됨"}
TITLE_MAX, DESCRIPTION_MAX = 60, 500


# ---- the change request being written: the edits waiting in the workspace -----------------------------------------

def _titled(ws) -> bool:
    """Whether the request being written was given a title of its own: not the one the workspace starts with, and not
    the one the last request it sent was deployed under."""
    from ontlas.manage import Workspace

    start = Workspace.__init__.__kwdefaults__["label"]
    return ws.module.label != (ws.current.label if ws.current else start)


def _draft(s) -> dict:
    ws = s._ws()
    own = _titled(ws)
    return {"title": ws.module.label if own else "", "description": ws.module.description if own else "",
            "dirty": ws.dirty, "edits": len(ws.edits), "issues": len(_issues(ws)),
            "next": s._space_version()["number"] + 1, "current": s._space_version()["number"]}


def _issues(ws) -> list[str]:
    from ontlas.modules import ModuleError

    try:
        return list(ws.composed().issues)
    except ModuleError as e:
        return [str(e)]


@get("ont2/draft")
def draft(s, a, who) -> dict:
    """The request being written: what it is called, how many edits it holds, the version it would become."""
    return _draft(s)


@post("ont2/draft", needs="editor")
def draft_save(s, a, who) -> dict:
    """Its title and description, kept on the workspace module: they go with the request when it is sent."""
    title = " ".join(str(a.get("title") or "").split())
    description = str(a.get("description") or "").strip()
    if not title:
        raise ValueError("제목이 없어 저장하지 못했습니다. 변경 요청의 제목을 입력해 주세요.")
    if len(title) > TITLE_MAX or len(description) > DESCRIPTION_MAX:
        raise ValueError(f"제목 {TITLE_MAX}자, 설명 {DESCRIPTION_MAX}자를 넘어 저장하지 못했습니다. 길이를 줄여 주세요.")
    ws = s._ws()
    if not _titled(ws) and ws.current is not None and title == ws.current.label:
        raise ValueError("직전 배포 변경 요청과 제목이 같아 저장하지 못했습니다. 다른 제목을 입력해 주세요.")
    ws.module.label, ws.module.description = title, description
    return {"ok": True, **_draft(s)}


# ---- one term of the lexicon, change by change ------------------------------------------------------------------------

def _said(field: str, v: Any) -> Any:
    """A term's field as a person reads it: a list by commas, a pair not to be swapped with its note."""
    if v in (None, "", [], {}):
        return None
    if field == "confusable":
        return ", ".join(f"{c['term']} ({c['note']})" if c.get("note") else c["term"] for c in v)
    if field == "channels":
        return ", ".join(f"{k} = {x}" for k, x in v.items())
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return v


def _term_fields(before: dict | None, after: dict | None, only: str = "") -> list[dict]:
    rows = []
    for f, word in TERM_FIELD_WORD.items():
        if only and f != only:
            continue
        b, x = (before or {}).get(f), (after or {}).get(f)
        if f == "status":  # a term in use says nothing of its status
            b, x = (None if b == "active" else b), (None if x == "active" else x)
        if _said(f, b) != _said(f, x):
            rows.append({"field": f, "label": word, "before": _said(f, b), "after": _said(f, x)})
    return rows


def _terms(module) -> tuple[dict, set]:
    from ontlas.lexicon import entry, term_id

    if module is None:
        return {}, set()
    return {term_id(t): entry(t) for t in module.terms or []}, set((module.remove or {}).get("terms") or [])


@get("ont2/term/history")
def term_history(s, a, who) -> dict:
    """Every change request that wrote, rewrote or took out one term, newest first, with what it read before and after.
    `field` keeps the changes of one field (the synonyms, the pairs not to be swapped). The edits not yet sent come
    first. A term is read from the module a change carries and from the version that module replaced; where the term
    came from another module, from the lexicon as that module leaves it."""
    import yaml

    from ontlas.lexicon import collect, entry, term_id
    from ontlas.modules import Module, order

    tid, only = str(a.get("id") or ""), str(a.get("field") or "")
    if not tid:
        raise ValueError("용어가 없어 이력을 찾지 못했습니다.")
    if only and only not in TERM_FIELD_WORD:
        raise ValueError(f"용어에 {only} 항목이 없어 이력을 찾지 못했습니다.")
    st = s.studio
    lib = st.library
    comp = st.composition

    def elsewhere(name: str) -> dict | None:
        """The term as the other applied modules give it."""
        if comp is None:
            return None
        terms = collect(order([m for m in comp.modules if m.name != name]))[0]
        return next((entry(t) for t in terms if term_id(t) == tid), None)

    def step(new, old, name: str) -> tuple[dict | None, dict | None] | None:
        nt, nr = _terms(new)
        ot, orr = _terms(old)
        before = ot.get(tid) or (None if tid in orr else elsewhere(name))
        after = None if tid in nr else (nt.get(tid) or (before if tid not in ot else None))
        if tid not in nt and tid not in ot and tid not in nr and tid not in orr:
            return None
        return None if before == after else (before, after)

    entries = []
    for cr in st.changes.requests.values():
        try:
            new = Module.from_dict(yaml.safe_load(cr.text))
        except Exception:  # a request whose file no longer reads has nothing to say of a term
            continue
        was = (cr.review or {}).get("from_version") or ""
        old = None
        if was and lib is not None and was in lib.versions(cr.module):
            old = lib.get(cr.module, was)
        sides = step(new, old, cr.module)
        if sides is None:
            continue
        fields = _term_fields(*sides, only)
        if only and not fields:
            continue
        kind = "added" if sides[0] is None else "removed" if sides[1] is None else "changed"
        entries.append({"change": cr.id, "version": cr.version, "status": cr.status, "status_label": STATUS_WORD.get(cr.status, cr.status),
                        "at": cr.decided_at or cr.at, "by": cr.requested_by, "reason": cr.reason, "deployed": cr.status == "approved",
                        "kind": kind, "before": sides[0], "after": sides[1], "fields": fields})
    entries.reverse()
    if comp is not None:
        ws = s._ws()
        if ws.dirty:
            sides = step(ws.module, ws.current, ws.module.name)
            fields = _term_fields(*sides, only) if sides else []
            if sides is not None and (fields or not only):
                kind = "added" if sides[0] is None else "removed" if sides[1] is None else "changed"
                entries.insert(0, {"change": "", "version": "", "status": "draft", "status_label": "작성 중", "at": "", "by": s.who,
                                   "reason": "", "deployed": False, "kind": kind, "before": sides[0], "after": sides[1], "fields": fields})
    # why a change was made is a note left with the term when it was saved (under term:<id>): each entry carries its own
    notes = sorted(s._notes().get(f"term:{tid}", []), key=lambda n: str(n.get("at") or ""))
    for i, e in enumerate(entries):
        older = entries[i + 1]["at"] if i + 1 < len(entries) else ""
        e["notes"] = [n for n in notes if str(n.get("at") or "") > str(older or "")
                      and (not e["at"] or str(n.get("at") or "") <= str(e["at"]))]
    return {"id": tid, "entries": entries}


# ---- the versions: which deployed change took an earlier one back, and taking the last one back -----------------------

def _same(a: dict, b: dict) -> bool:
    return {**a, "version": ""} == {**b, "version": ""}


def _restored(s, cr) -> str:
    """The earlier version of its module a deployed change reads the same as (it took the versions between back), or ''."""
    import yaml

    lib = s.studio.library
    if lib is None:
        return ""
    try:
        now = yaml.safe_load(cr.text)
    except yaml.YAMLError:
        return ""
    was = (cr.review or {}).get("from_version") or ""
    for v in reversed(lib.versions(cr.module)):
        if v in (cr.version, was):
            continue
        from ontlas.modules import version_key

        if version_key(v) < version_key(cr.version) and _same(lib.get(cr.module, v).to_dict(), now):
            return v
    return ""


@get("ont2/versions")
def versions(s, a, who) -> dict:
    """Beside the version list: the deployed changes that are a rollback (the version each brought back)."""
    import yaml

    applied = s._applied_changes()
    back = [{"change": c.id, "module": c.module, "restored": v, "at": s._decided_at(c)} for c in applied if (v := _restored(s, c))]
    from ontlas.manage import Workspace
    from ontlas.web.api import WORKSPACE

    start = Workspace.__init__.__kwdefaults__["label"]
    titles = {}
    for c in s.studio.changes.requests.values():  # a request is called what its own file says, whatever its module is called since
        try:
            title = str((yaml.safe_load(c.text) or {}).get("label") or "")
        except yaml.YAMLError:
            title = ""
        titles[c.id] = "" if c.module == WORKSPACE and title == start else title  # the label a workspace starts with is no title
    return {"rollbacks": back, "kept": len(applied) + 1, "titles": titles}


@post("ont2/rollback", needs="approver")
def rollback(s, a, who) -> dict:
    """Take back the change that made the version in use: its module as it read before, sent as a new version. Where
    one person is both sides it is tried and deployed at once; in a team it waits for someone else to approve it."""
    import yaml

    from ontlas.modules import Module
    from ontlas.web.api import WORKSPACE

    cid = str(a.get("change") or "")
    cur = s._space_version()
    if not cid or cid != cur["change"]:
        raise ValueError("최근 배포 변경 요청이 아니어서 롤백하지 못했습니다. 운영 버전의 변경 요청을 선택해 주세요.")
    if s._ws().dirty:
        raise ValueError("작성 중인 변경 요청이 있어 롤백하지 못했습니다. 작성 중인 변경 요청을 등록하거나 폐기해 주세요.")
    cr = s.studio.changes.requests[cid]
    was = (cr.review or {}).get("from_version") or ""
    lib = s.studio.changes.store or s.studio.library
    if was:
        d = lib.get(cr.module, was).to_dict()
    else:  # the change attached the module: before it, the module held nothing
        new = Module.from_dict(yaml.safe_load(cr.text))
        d = {"module": new.name, "version": new.version, "kind": new.kind, "label": new.label, "description": new.description}
    res = s.propose_module(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))
    change = res["change"]
    if not s.studio.changes.self_approve:
        return {"ok": True, "pending": True, "change": change}
    out = s.decide_change(change["id"], True)
    if not out["ok"]:
        s.studio.changes.reject(change["id"], by=s.who, reason="롤백 정의의 통과 조건 미충족")
        raise ValueError(out["error"])
    if cr.module == WORKSPACE:
        s.workspace = None
    return {"ok": True, "pending": False, "change": out["change"]}
