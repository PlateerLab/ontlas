"""What the later screens of Ontology ask beyond the session's own routes: the change request being written
(its title and what it will be numbered), how one term of the lexicon came to read as it does, and taking the last
deployed change back as a new version."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from weakref import WeakKeyDictionary

from ontlas.web.routes import get, post

TERM_FIELD_WORD = {"term": "용어", "english": "영문 표기", "kind": "구분", "concept": "연결 개념", "definition": "정의",
                   "synonyms": "동의어", "abbreviations": "약어", "channels": "채널 표기", "hidden": "숨은 표기",
                   "related": "관련어", "broader": "상위어", "narrower": "하위어", "confusable": "혼동주의",
                   "avoid": "쓰지 않는 표현", "source": "출처", "cite": "근거", "note": "메모", "owner": "담당자", "status": "상태"}
STATUS_WORD = {"pending": "검토 중", "approved": "배포됨", "rejected": "반려됨"}
TERM_STATUS_WORD = {"active": "사용 중", "draft": "초안", "review": "확인 필요", "deprecated": "폐기 예정"}
TITLE_MAX, DESCRIPTION_MAX, NOTE_MAX = 60, 500, 500
ROLLBACK_SAY = "{} 롤백"  # the reason a rollback request carries: the change it takes back
KEPT = "ont2"  # the journal records of these screens


# ---- what these screens keep beside the change requests ---------------------------------------------------------------
# Which request takes which change back (a rejected one is given the reason it was rejected for), and why a term was
# edited, with the fields that edit touched and how many requests there were then: a reason belongs to the first request
# after it that changes the term, whatever the clock says. Kept per change service, and in its journal where the server
# keeps one, so a restart forgets none of it.
_kept: WeakKeyDictionary = WeakKeyDictionary()


def _take(got: dict, r: dict) -> None:
    if r.get("rollback"):
        got["rollbacks"][r["rollback"]] = r.get("of") or ""
    elif r.get("term"):
        got["notes"].append({k: r.get(k) for k in ("term", "fields", "text", "by", "at", "after")})


def _store(s) -> dict:
    ch = s.studio.changes
    got = _kept.get(ch)
    if got is None:
        got = {"rollbacks": {}, "notes": []}
        for r in ch.journal.read() if ch.journal is not None else []:
            if r.get("kind") == KEPT:
                _take(got, r)
        _kept[ch] = got
    return got


def _keep(s, record: dict) -> None:
    _take(_store(s), record)
    if s.studio.changes.journal is not None:
        s.studio.changes.journal.write(KEPT, record)


def _rolled_back(s, cr) -> str:
    """The change a request takes back, or ''."""
    said = re.fullmatch(ROLLBACK_SAY.format(r"(C\d+)"), cr.reason or "")
    return _store(s)["rollbacks"].get(cr.id) or (said.group(1) if said else "")


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
    said = ws.module.description if own and ws.module.description != ws.module.label else ""  # one without its own reads as its title
    return {"title": ws.module.label if own else "", "description": said,
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
    if not ws.dirty:  # a title with nothing under it would wait unseen for the next edit
        raise ValueError("포함 항목이 없어 저장하지 못했습니다. 정의나 용어를 먼저 편집해 주세요.")
    if not _titled(ws) and ws.current is not None and title == ws.current.label:
        raise ValueError("직전 배포 변경 요청과 제목이 같아 저장하지 못했습니다. 다른 제목을 입력해 주세요.")
    if _titled(ws) and (title, description or title) == (ws.module.label, ws.module.description):  # as kept below
        raise ValueError("변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.")
    # a module file without a description is given the workspace's long default when it is read again, which would read
    # as an edit nobody made: a request without a description of its own is described by its title
    ws.module.label, ws.module.description = title, description or title
    return {"ok": True, **_draft(s)}


# ---- one term of the lexicon, change by change ------------------------------------------------------------------------

def _said(field: str, v: Any, onto=None) -> Any:
    """A term's field as a person reads it: a list by commas, a pair not to be swapped with its note, its status and
    the definition it names by their words."""
    if v in (None, "", [], {}):
        return None
    if field == "status":
        return TERM_STATUS_WORD.get(v, v)
    if field == "concept" and onto is not None:
        from ontlas.lexicon import concept_of

        c = concept_of(onto, v)
        return f"{c['kind_label']} · {c['of'] + ' › ' if c['of'] else ''}{c['label']}" if c else v
    if field == "confusable":
        return ", ".join(f"{c['term']} ({c['note']})" if c.get("note") else c["term"] for c in v)
    if field == "channels":
        return ", ".join(f"{k} = {x}" for k, x in v.items())
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return v


def _term_fields(before: dict | None, after: dict | None, only: str = "", onto=None) -> list[dict]:
    rows = []
    for f, word in TERM_FIELD_WORD.items():
        if only and f != only:
            continue
        b, x = (before or {}).get(f), (after or {}).get(f)
        if f == "status" and (before is None or after is None):  # a term added or taken out in use says nothing of its status
            b, x = (None if b == "active" else b), (None if x == "active" else x)
        if _said(f, b) != _said(f, x):
            rows.append({"field": f, "label": word, "before": _said(f, b, onto), "after": _said(f, x, onto)})
    return rows


def _term_all(term: dict | None, onto=None) -> list[dict]:
    """Every field a term holds, by its word, as it reads after a change (before it, where the change took it out)."""
    return [{"field": f, "label": word, "value": v} for f, word in TERM_FIELD_WORD.items()
            if (v := _said(f, (term or {}).get(f), onto)) is not None]


def _terms(module) -> tuple[dict, set]:
    from ontlas.lexicon import entry, term_id

    if module is None:
        return {}, set()
    return {term_id(t): entry(t) for t in module.terms or []}, set((module.remove or {}).get("terms") or [])


def _elsewhere(st, name: str) -> dict:
    """Every term as the applied modules other than `name` give it, by its id."""
    from ontlas.lexicon import collect, entry, term_id
    from ontlas.modules import order

    comp = st.composition
    if comp is None:
        return {}
    return {term_id(t): entry(t) for t in collect(order([m for m in comp.modules if m.name != name]))[0]}


def _sides(tid: str, new: tuple, old: tuple, elsewhere) -> tuple[dict | None, dict | None] | None:
    """One term before and after a module replaced its earlier version (`new` and `old` as `_terms` reads them), or None
    where the module leaves it as it was. On each side the term is what the module writes, nothing where it takes the
    term out, and otherwise what the other modules give."""
    if not any(tid in part for side in (new, old) for part in side):
        return None

    def read(terms: dict, removed: set) -> dict | None:
        return None if tid in removed else terms.get(tid) or elsewhere().get(tid)

    before, after = read(*old), read(*new)
    return None if before == after else (before, after)


def _replaced(st, cr):
    """The module a change request carries, and the version of that module it replaced (None where it had none)."""
    import yaml

    from ontlas.modules import Module

    new = Module.from_dict(yaml.safe_load(cr.text))
    was = (cr.review or {}).get("from_version") or ""
    lib = st.library
    return new, (lib.get(cr.module, was) if was and lib is not None and was in lib.versions(cr.module) else None)


def _change_kind(sides) -> str:
    return "added" if sides[0] is None else "removed" if sides[1] is None else "changed"


@get("ont2/term/history")
def term_history(s, a, who) -> dict:
    """Every change request that wrote, rewrote or took out one term, newest first, with what it read before and after.
    `field` keeps the changes of one field (the synonyms, the pairs not to be swapped). The edits not yet sent come
    first. A term is read from the module a change carries and from the version that module replaced; where the term
    came from another module, from the lexicon as that module leaves it."""
    tid, only = str(a.get("id") or ""), str(a.get("field") or "")
    if not tid:
        raise ValueError("용어가 없어 이력을 찾지 못했습니다.")
    if only and only not in TERM_FIELD_WORD:
        raise ValueError(f"용어에 {only} 항목이 없어 이력을 찾지 못했습니다.")
    st = s.studio
    comp = st.composition

    entries = []  # every change of the term, oldest first, whichever field it touched: the reasons are paired on these
    for n, cr in enumerate(st.changes.requests.values()):
        try:
            new, old = _replaced(st, cr)
        except Exception:  # a request whose file no longer reads has nothing to say of a term
            continue
        sides = _sides(tid, _terms(new), _terms(old), lambda name=cr.module: _elsewhere(st, name))
        if sides is not None:
            entries.append({"change": cr.id, "version": cr.version, "status": cr.status, "status_label": STATUS_WORD.get(cr.status, cr.status),
                            "at": cr.decided_at or cr.at, "by": cr.requested_by, "reason": cr.reason, "deployed": cr.status == "approved",
                            "n": n, "sides": sides})
    if comp is not None:
        ws = s._ws()
        sides = _sides(tid, _terms(ws.module), _terms(ws.current), lambda: _elsewhere(st, ws.module.name)) if ws.dirty else None
        if sides is not None:
            entries.append({"change": "", "version": "", "status": "draft", "status_label": "작성 중", "at": "", "by": s.who,
                            "reason": "", "deployed": False, "n": len(st.changes.requests), "sides": sides})
    for e in entries:
        e["notes"] = []
    # why a term was edited: each reason goes with the first change of the term made after it was written
    for note in _store(s)["notes"]:
        if note["term"] == tid and (not only or not note["fields"] or only in note["fields"]):
            e = next((e for e in entries if e["n"] >= (note["after"] or 0)), None)
            if e is not None:
                e["notes"].append({k: note[k] for k in ("at", "by", "text")})
    # a reason kept with the older comments of the term (before they were kept as above) goes by its time
    old = sorted(s._notes().get(f"term:{tid}", []), key=lambda n: str(n.get("at") or ""))
    for i, e in enumerate(entries):
        older = entries[i - 1]["at"] if i else ""
        e["notes"] += [n for n in old if str(n.get("at") or "") > str(older or "") and (not e["at"] or str(n.get("at") or "") <= str(e["at"]))]
    out = []
    for e in reversed(entries):
        sides = e.pop("sides")
        del e["n"]
        e.update(fields=_term_fields(*sides, only, st.onto), kind=_change_kind(sides), before=sides[0], after=sides[1],
                 all=_term_all(sides[1] or sides[0], st.onto))
        if e["fields"] or not only:
            out.append(e)
    return {"id": tid, "entries": out}


@post("ont2/term/note", needs="editor")
def term_note(s, a, who) -> dict:
    """Why a term was edited, with the fields the edit touched: shown with the change that carries the edit."""
    tid, text = str(a.get("id") or ""), " ".join(str(a.get("text") or "").split())[:NOTE_MAX]
    if not tid or not text:
        raise ValueError("변경 사유가 없어 남기지 못했습니다. 변경 사유를 입력해 주세요.")
    fields = [f for f in a.get("fields") or [] if f in TERM_FIELD_WORD]
    _keep(s, {"term": tid, "fields": fields, "text": text, "by": who.name if who is not None else (s.who or "page"),
              "at": datetime.now().isoformat(timespec="minutes"), "after": len(s.studio.changes.requests)})  # when it was said, as a request is stamped
    return {"ok": True}



@get("ont2/change/terms")
def change_terms(s, a, who) -> dict:
    """The terms one change request adds, rewrites or takes out, field by field: a term is no element of the definition,
    so the request's own list of changed elements does not hold it."""
    st = s.studio
    cid = str(a.get("id") or "")
    cr = st.changes.requests.get(cid)
    if cr is None:
        raise ValueError("변경 요청이 없어 용어 변경을 찾지 못했습니다. 변경 요청을 다시 선택해 주세요.")
    try:
        new, old = _replaced(st, cr)
    except Exception:  # a request whose file no longer reads has nothing to say of a term
        return {"id": cid, "terms": []}
    nt, ot, kept = _terms(new), _terms(old), []

    def elsewhere() -> dict:
        if not kept:
            kept.append(_elsewhere(st, cr.module))
        return kept[0]

    out = []
    for tid in dict.fromkeys([*nt[0], *nt[1], *ot[0], *ot[1]]):
        sides = _sides(tid, nt, ot, elsewhere)
        if sides is None:
            continue
        x = sides[1] or sides[0]
        out.append({"id": tid, "term": x["term"], "english": x.get("english") or "", "change": _change_kind(sides),
                    "fields": _term_fields(*sides, onto=st.onto)})
    return {"id": cid, "terms": out}

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
    """Beside the version list: the deployed changes that are a rollback (the change each took back, the version each
    brought back), how many versions are kept, and the title each request was sent with."""
    import yaml

    applied = s._applied_changes()
    back = []
    for c in applied:  # a rollback says which change it took back; a change may also read as an earlier version again
        v, of = _restored(s, c), _rolled_back(s, c)
        if v or of:
            back.append({"change": c.id, "module": c.module, "restored": v, "of": of, "at": s._decided_at(c)})
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
        of = _rolled_back(s, c)  # a rollback carries the file of the version it brought back: it is called by what it took back
        if of:
            titles[c.id] = ROLLBACK_SAY.format(of)
    return {"rollbacks": back, "kept": len(applied) + 1, "titles": titles}


@post("ont2/rollback", needs="approver")
def rollback(s, a, who) -> dict:
    """Take back the change that made the version in use: its module as it read before, sent as a new version. Where
    one person is both sides it is tried and deployed at once; in a team it waits for someone else to approve it."""
    import yaml

    from ontlas.modules import Module

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
    s.studio.changes.requests[change["id"]].reason = ROLLBACK_SAY.format(cid)  # kept with the request through its approval
    _keep(s, {"rollback": change["id"], "of": cid})  # and after it is rejected for a reason of its own
    if not s.studio.changes.self_approve:
        return {"ok": True, "pending": True, "change": change}
    out = s.decide_change(change["id"], True)
    if not out["ok"]:
        s.studio.changes.reject(change["id"], by=s.who, reason="롤백 정의의 통과 조건 미충족")
        raise ValueError(out["error"])
    return {"ok": True, "pending": False, "change": out["change"]}
