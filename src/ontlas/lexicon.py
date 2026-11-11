"""The lexicon: what people call each definition, and which words must not be taken for one another.

A term is a word a business uses, tied to the definition it names: an area (`area:Order`), an object type
(`object:Order`), a property (`property:Payment.amount`), a code value (`value:Order.status=DELIVERED`), a decision, a
metric. Beside its preferred label (Korean, and English) it carries the labels it also goes by (synonyms,
abbreviations), what each screen or channel calls it (`channels`), hidden labels only matching reads (typos, everyday
phrasing), the terms around it (related, broader, narrower), and the terms it looks like but must never be swapped
with (`confusable`, each with a note). Terms live in modules as `terms:`, so they plug in and out with the definitions
they name, and the management screens write theirs to the workspace module like any other edit.

An entry from before keeps working as it was: {term, synonyms, avoid, definition, english, abbreviation, column}.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Callable

STATUSES = ("active", "draft", "review", "deprecated")  # review: a glossary marked it to be checked (확인 필요)
LABEL_KINDS = ("preferred", "english", "alternative", "abbreviation", "channel", "hidden")
LABEL_WORD = {"preferred": "대표어", "english": "영문", "alternative": "동의어", "abbreviation": "약어", "channel": "채널 표기",
              "hidden": "숨은 표기"}
CONCEPT_KINDS = {"area": "Object", "object": "Entity", "property": "속성", "value": "코드값", "decision": "결정표",
                 "metric": "지표", "query": "질의", "action": "Action", "parameter": "기준값", "link": "관계",
                 "function": "함수"}
_SECTION = {"decision": "decisions", "metric": "metrics", "query": "queries", "action": "actions",
            "parameter": "parameters", "link": "links", "function": "functions"}
LINK_ORDER = ("object", "property", "value", "area", "decision", "metric", "query", "action")  # who a bare label names first
FIELDS = ("term", "english", "kind", "concept", "definition", "synonyms", "abbreviations", "channels", "hidden",
          "related", "broader", "narrower", "confusable", "avoid", "source", "cite", "owner", "status")
LISTS = ("synonyms", "abbreviations", "hidden", "related", "broader", "narrower", "avoid")
# what a glossary's relation column says, lower case without spaces
RELATIONS = {"동의어": "synonym", "유의어": "synonym", "이음동의어": "synonym", "같은말": "synonym", "synonym": "synonym",
             "alias": "synonym", "약어": "abbreviation", "줄임말": "abbreviation", "abbreviation": "abbreviation",
             "abbr": "abbreviation", "관련어": "related", "연관어": "related", "related": "related", "상위어": "broader",
             "broader": "broader", "하위어": "narrower", "narrower": "narrower", "혼동주의": "confusable", "혼동": "confusable",
             "혼동어": "confusable", "confusable": "confusable", "영문": "english", "영문명": "english", "english": "english",
             "숨은표기": "hidden", "오타": "hidden", "구어": "hidden", "hidden": "hidden"}
PAIR_HEADERS = {
    "kind": ["구분", "분류", "category", "kind", "group"],
    "a": ["용어a", "용어1", "기준용어", "terma", "term1", "from"],
    "b": ["용어b", "용어2", "대상용어", "termb", "term2", "to"],
    "relation": ["관계", "관계유형", "relation", "relationship", "type"],
    "note": ["설명", "비고", "note", "description", "comment"],
    "cite": ["근거", "출처", "cite", "reference", "source"],
    "check": ["확인필요", "검토필요", "확인", "review", "check", "needsreview"],
}
TERM_EXTRA = {  # what a term list says beyond the glossary sheet definitions.py reads
    "kind": ["용어구분", "구분", "분류", "kind", "category"],
    "related": ["관련용어", "관련어", "related", "relatedterms"],
    "hidden": ["숨은표기", "오타", "구어", "hidden"],
    "broader": ["상위어", "broader"], "narrower": ["하위어", "narrower"], "confusable": ["혼동주의", "혼동어", "confusable"],
    "owner": ["담당", "담당자", "owner"], "cite": ["근거", "출처", "cite"], "concept": ["연결정의", "concept", "element"],
}
NO = {"", "n", "no", "false", "0", "-", "x", "아니오", "아니요", "불필요", "없음"}
_OLD_NAMES = {"term": ("name",), "synonyms": ("aliases",), "abbreviations": ("abbreviation", "abbr"),
              "definition": ("description",), "avoid": ("forbidden",)}  # what an entry from before may call a field
_ASCII = re.compile(r"^[\x00-\x7f]+$")


def _list(v: Any) -> list[str]:
    """Several words in one cell, or a list of them."""
    items = v if isinstance(v, (list, tuple)) else re.split(r"[,;]", str(v or ""))
    return list(dict.fromkeys(s for s in (str(x).strip() for x in items) if s))


def norm(label: str) -> str:
    """A label as two labels are compared: no spaces, lower case."""
    return re.sub(r"\s+", "", str(label or "")).lower()


def term_id(d: dict) -> str:
    """The id an entry is edited by: its own, or its term with the definition it names, so two meanings of one word stay
    two entries."""
    if str(d.get("id") or "").strip():
        return str(d["id"]).strip()
    term = str(d.get("term") or d.get("name") or "").strip()
    return f"{term}@{d['concept']}" if term and d.get("concept") else term


def entry(d: dict) -> dict:
    """An entry in full, whatever shape it was written in."""
    d = d or {}
    conf = []
    for c in d.get("confusable") or []:
        t, note = (str(c.get("term") or "").strip(), str(c.get("note") or "")) if isinstance(c, dict) else (str(c).strip(), "")
        if t and t not in [x["term"] for x in conf]:
            conf.append({"term": t, "note": note})
    status = str(d.get("status") or "active")
    return {"id": term_id(d), "term": str(d.get("term") or d.get("name") or "").strip(), "english": str(d.get("english") or ""),
            "kind": str(d.get("kind") or ""), "concept": str(d.get("concept") or ""),
            "definition": str(d.get("definition") or d.get("description") or ""),
            "synonyms": _list(d.get("synonyms") or d.get("aliases")),
            "abbreviations": _list([*_list(d.get("abbreviations")), *_list(d.get("abbreviation") or d.get("abbr"))]),
            "channels": {str(k): str(v).strip() for k, v in (d.get("channels") or {}).items() if str(v or "").strip()},
            "hidden": _list(d.get("hidden")), "related": _list(d.get("related")), "broader": _list(d.get("broader")),
            "narrower": _list(d.get("narrower")), "confusable": conf, "avoid": _list(d.get("avoid") or d.get("forbidden")),
            "source": str(d.get("source") or ""), "cite": str(d.get("cite") or ""), "owner": str(d.get("owner") or ""),
            "status": status}


def labels(e: dict) -> list[tuple[str, str]]:
    """Every label an entry goes by, with its kind: what a question or a document may call it."""
    out = [(e["term"], "preferred")] if e.get("term") else []
    out += [(e["english"], "english")] if e.get("english") else []
    out += [(x, "alternative") for x in e.get("synonyms") or []]
    out += [(x, "abbreviation") for x in e.get("abbreviations") or []]
    out += [(x, "channel") for x in (e.get("channels") or {}).values()]
    out += [(x, "hidden") for x in e.get("hidden") or []]
    seen: set[str] = set()
    return [(x, k) for x, k in out if norm(x) and not (norm(x) in seen or seen.add(norm(x)))]


def collect(modules) -> tuple[list[dict], dict[str, str]]:
    """The terms of modules in composition order, and the module each comes from. A later module's entry with an id
    already given replaces it where it stood; `remove: {terms: [id]}` takes one out; one module may say a word twice."""
    held: dict[str, dict] = {}
    origin: dict[str, str] = {}
    for m in modules:
        for tid in (m.remove or {}).get("terms") or []:
            held.pop(str(tid), None)
            origin.pop(str(tid), None)
        mine: set[str] = set()
        for t in m.terms or []:
            if not isinstance(t, dict):
                continue
            tid, n = term_id(t), 2
            while tid in mine or not tid:
                tid, n = f"{term_id(t)}#{n}", n + 1
            mine.add(tid)
            held[tid] = t if tid == term_id(t) else {"id": tid, **t}
            origin[tid] = m.name
    return list(held.values()), origin


def concept_of(onto, element: str) -> dict | None:
    """What a term names, by its label; None when the definition has no such thing."""
    kind, _, name = str(element or "").partition(":")
    if onto is None or not name or kind not in CONCEPT_KINDS:
        return None
    label, of = "", ""
    if kind == "area":
        a = onto.areas.get(name)
        if a is None:
            return None
        label = a.label or name
    elif kind == "object":
        t = onto.objects.get(name)
        if t is None:
            return None
        label = t.label or name
    elif kind in ("property", "value"):
        from ontlas.check import _find_prop

        path, _, code = name.partition("=")
        type_name, _, prop = path.partition(".")
        p = _find_prop(onto, type_name, prop) if type_name in onto.objects else None
        if p is None or (kind == "value" and code not in [str(v) for v in p.values or []] and code not in (p.labels or {})):
            return None
        of = onto.objects[type_name].label or type_name
        label = (p.labels or {}).get(code) or code if kind == "value" else p.label or prop
        if kind == "value":
            of = f"{of} · {p.label or prop}"
    else:
        x = getattr(onto, _SECTION[kind]).get(name)
        if x is None:
            return None
        label = getattr(x, "label", "") or name
    return {"concept": element, "kind": kind, "kind_label": CONCEPT_KINDS[kind], "label": label, "of": of}


def concepts(onto) -> list[dict]:
    """Every definition a term can name, as `concept_of` reads it: what a person picks from to tie a term."""
    if onto is None:
        return []
    ids = [f"area:{a}" for a in onto.areas] + [f"object:{t}" for t in onto.objects]
    for t in onto.objects.values():
        for p in t.properties.values():
            if not p.internal:
                ids.append(f"property:{t.name}.{p.name}")
                ids += [f"value:{t.name}.{p.name}={v}" for v in p.values or []]
    ids += [f"{kind}:{k}" for kind in ("decision", "metric") for k in getattr(onto, _SECTION[kind])]
    return [c for c in (concept_of(onto, i) for i in ids) if c is not None]


def candidates(onto, words: list[str]) -> list[str]:
    """The definitions whose label is one of these words, as element ids."""
    want = {norm(w) for w in words if norm(w)}
    if onto is None or not want:
        return []
    out = [f"area:{a.name}" for a in onto.areas.values() if norm(a.label) in want]
    for t in onto.objects.values():
        if norm(t.label) in want:
            out.append(f"object:{t.name}")
        for p in t.properties.values():
            if p.internal:
                continue
            if norm(p.label) in want:
                out.append(f"property:{t.name}.{p.name}")
            out += [f"value:{t.name}.{p.name}={code}" for code, lab in (p.labels or {}).items() if norm(lab) in want]
    for kind, section in _SECTION.items():
        out += [f"{kind}:{k}" for k, x in getattr(onto, section).items() if norm(getattr(x, "label", "")) in want]
    return out


def link(e: dict, onto) -> tuple[str, list[str]]:
    """The definition an entry names when its label says so of one alone: (element, []), or ("", the candidates)."""
    for words in ([e["term"]], [e.get("english", ""), *e.get("synonyms", [])]):
        found = candidates(onto, words)
        if not found:
            continue
        kind = next(k for k in LINK_ORDER + tuple(CONCEPT_KINDS) if any(f.startswith(f"{k}:") for f in found))
        best = [f for f in found if f.startswith(f"{kind}:")]
        if len(best) > 1 and kind == "property":  # 주문 번호 names the order's key, not every type that carries it
            paths = [f.split(":", 1)[1].split(".", 1) for f in best]
            best = [f for f, (t, p) in zip(best, paths) if onto.objects[t].key == p] or best
        return (best[0], []) if len(best) == 1 else ("", found)
    return "", []


def conflicts(terms: list[dict], onto=None) -> list[dict]:
    """What the lexicon says two ways: one label claimed by two definitions, a pair called both the same word and two
    words not to be swapped, a term naming a definition that is not there."""
    es = [entry(t) for t in terms]
    out: list[dict] = []
    claims: dict[str, dict[str, list[dict]]] = {}
    for e in es:
        for label, kind in labels(e):
            claims.setdefault(norm(label), {}).setdefault(e["concept"] or f"term:{e['id']}", []).append(
                {"id": e["id"], "term": e["term"], "as": kind, "label": label})
    for by in claims.values():
        if len(by) > 1:
            said = [x for xs in by.values() for x in xs]
            out.append({"kind": "label", "label": said[0]["label"], "terms": [x["id"] for x in said],
                        "concepts": [c for c in by if not c.startswith("term:")],
                        "text": f"표기 '{said[0]['label']}'을(를) 서로 다른 용어 {', '.join(dict.fromkeys(x['term'] for x in said))}이(가) "
                                "함께 쓰고 있습니다. 한 용어에만 남기거나 혼동주의로 바꿔 주세요."})
    same = {}
    for e in es:
        for label, kind in labels(e):
            if kind != "preferred":
                same.setdefault(frozenset((norm(e["term"]), norm(label))), e)
    seen: set[frozenset] = set()
    for e in es:
        for c in e["confusable"]:
            pair = frozenset((norm(e["term"]), norm(c["term"])))
            if pair in same and pair not in seen:
                seen.add(pair)
                out.append({"kind": "synonym_confusable", "label": c["term"], "terms": [e["id"], same[pair]["id"]],
                            "concepts": [x for x in (e["concept"], same[pair]["concept"]) if x],
                            "text": f"'{e['term']}'와(과) '{c['term']}'이(가) 동의어이면서 혼동주의로 함께 정해져 있습니다. 하나로 정해 주세요."})
    if onto is not None:
        for e in es:
            if e["concept"] and concept_of(onto, e["concept"]) is None:
                out.append({"kind": "missing_concept", "label": e["term"], "terms": [e["id"]], "concepts": [e["concept"]],
                            "text": f"용어 '{e['term']}'이(가) 연결한 정의 {e['concept']}이(가) 없습니다. 연결을 바꾸거나 비워 주세요."})
    return out


def pairs(terms: list[dict]) -> dict[str, list[dict]]:
    """Each term's confusables, from either side: {preferred label (as compared): [{term, note}]}."""
    out: dict[str, list[dict]] = {}
    es = [entry(t) for t in terms]
    for own in (True, False):  # a term's own note first; the other side's where it gives none
        for e in es:
            for c in e["confusable"]:
                a, b = (e["term"], c["term"]) if own else (c["term"], e["term"])
                if norm(b) not in [norm(x["term"]) for x in out.setdefault(norm(a), [])]:
                    out[norm(a)].append({"term": b, "note": c["note"]})
    return out


def _pattern(label: str) -> re.Pattern:
    """A label as a sentence may write it: spaces anywhere or nowhere, and a Latin word whole and in any case."""
    body = r"\s*".join(re.escape(ch) for ch in re.sub(r"\s+", "", label))
    if _ASCII.match(label):
        return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I)
    return re.compile(body)


def read(text: str, terms: list[dict]) -> dict:
    """The terms a sentence uses, by any label: the sentence in their preferred words, what each stands for, and the
    terms each must not be taken for. Longest label first, each stretch of text read once."""
    text = str(text or "")
    index = sorted(((label, kind, e) for e in (entry(t) for t in terms) for label, kind in labels(e) if len(norm(label)) >= 2),
                   key=lambda x: -len(norm(x[0])))
    taken = [False] * len(text)
    spans: list[tuple[int, int, str, dict]] = []
    matched: list[dict] = []
    for label, kind, e in index:
        hit = False
        for m in _pattern(label).finditer(text):
            if any(taken[m.start():m.end()]):
                continue
            taken[m.start():m.end()] = [True] * (m.end() - m.start())
            spans.append((m.start(), m.end(), kind, e))
            hit = True
        if hit and not any(x["id"] == e["id"] and x["as"] == kind for x in matched):
            matched.append({"label": label, "as": kind, "as_label": LABEL_WORD[kind], "id": e["id"], "term": e["term"],
                            "concept": e["concept"], "definition": e["definition"]})
    out, at = [], 0
    for start, end, kind, e in sorted(spans, key=lambda s: s[0]):
        out.append(text[at:start])
        out.append(text[start:end] if kind == "preferred" else e["term"])
        at = end
    out.append(text[at:])
    known = pairs(terms)
    confusables = []
    for m in matched:
        for c in known.get(norm(m["term"]), []):
            if not any(x["term"] == m["term"] and x["confusable"] == c["term"] for x in confusables):
                confusables.append({"term": m["term"], "id": m["id"], "confusable": c["term"], "note": c["note"]})
    return {"text": "".join(out), "matched": matched, "confusables": confusables}


def view(terms: list[dict], onto=None, *, origin: dict[str, str] | None = None, module_label: Callable[[str], str] | None = None,
         applied: list[dict] | None = None, readers: Callable[[str], list[str]] | None = None) -> dict:
    """The lexicon as the page shows it: a row per term, how much it holds, and what it says two ways. `applied` is the
    lexicon the studio runs with, against which a row is new or changed; `readers` names what reads a definition."""
    origin = origin or {}
    found = conflicts(terms, onto)
    hits: dict[str, int] = {}
    for c in found:
        for i in c["terms"]:
            hits[i] = hits.get(i, 0) + 1
    before = {term_id(t): entry(t) for t in applied} if applied is not None else None
    questions = list(getattr(onto, "questions", None) or [])
    rows, kinds = [], {k: 0 for k in LABEL_KINDS}
    for t in terms:
        e = entry(t)
        said = labels(e)
        for _, k in said:
            kinds[k] += 1
        c = concept_of(onto, e["concept"]) if e["concept"] else None
        used = [f"검증 질문 {q.id}" for q in questions if any(_pattern(x).search(q.text or "") for x, _ in said)]
        if c is not None and readers is not None:
            el = e["concept"] if c["kind"] != "value" else "property:" + e["concept"].split(":", 1)[1].split("=")[0]
            used += readers(el)  # a code value is read where its property is
        module = origin.get(e["id"], "")
        rows.append({**e, "concept_label": c["label"] if c else "", "concept_kind": c["kind_label"] if c else "",
                     "concept_of": c["of"] if c else "", "concept_found": c is not None if e["concept"] else None,
                     "labels": {k: [x for x, kk in said if kk == k] for k in LABEL_KINDS},
                     "module": module, "module_label": module_label(module) if module_label and module else module,
                     "used_by": list(dict.fromkeys(used))[:12], "conflicts": hits.get(e["id"], 0),
                     "new": before is not None and e["id"] not in before,
                     "pending": before is not None and e["id"] in before and before[e["id"]] != e})
    concepts = {r["concept"] for r in rows if r["concept"]}
    stats = {"terms": len(rows), "labels": sum(kinds.values()), "by_label": kinds,
             "linked": sum(1 for r in rows if r["concept"]), "concepts": len(concepts),
             "unlinked": sum(1 for r in rows if not r["concept"]),
             "confusables": len({frozenset((norm(r["term"]), norm(c["term"]))) for r in rows for c in r["confusable"]}),
             "conflicts": len(found), "review": sum(1 for r in rows if r["status"] == "review")}
    removed = sorted(set(before) - {r["id"] for r in rows}) if before is not None else []
    return {"stats": stats, "rows": rows, "conflicts": found, "removed": removed,
            "label_kinds": [{"kind": k, "label": LABEL_WORD[k]} for k in LABEL_KINDS],
            "statuses": list(STATUSES), "concept_kinds": [{"kind": k, "label": v} for k, v in CONCEPT_KINDS.items()]}


# ---- a glossary brought in -----------------------------------------------------------------------------------------

def _truthy(v: Any) -> bool:
    return norm(v) not in NO


def read_glossary(data: bytes, source: str) -> dict:
    """The terms and the term pairs of a glossary file: a YAML or JSON list of entries, or a CSV or Excel sheet that
    is either a term list (용어, 영문, 정의, ...) or a pair table (구분, 용어 A, 용어 B, 관계, 설명, 근거, 확인 필요)."""
    name = source or "glossary.csv"
    if name.lower().endswith((".yaml", ".yml", ".json")):
        import yaml

        try:
            d = yaml.safe_load(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, yaml.YAMLError):
            raise ValueError("용어 파일을 읽지 못했습니다. YAML 또는 JSON 형식인지 확인해 주세요.") from None
        items = d.get("terms") if isinstance(d, dict) else d
        if not isinstance(items, list) or not any(isinstance(x, dict) and (x.get("term") or x.get("name")) for x in items):
            raise ValueError("용어 목록이 없어 불러오지 못했습니다. terms 목록을 입력해 주세요.")
        return {"terms": [dict(x) for x in items if isinstance(x, dict) and (x.get("term") or x.get("name"))], "pairs": []}
    from ontlas.definitions import TERM_HEADERS, _match
    from ontlas.draft import ReadError, read_file

    try:
        sheets = read_file(data, name if "." in name.rsplit("/", 1)[-1] else name + ".csv")
    except ReadError as e:
        raise ValueError(f"용어 파일을 읽지 못했습니다. CSV 또는 XLSX 형식인지 확인해 주세요. ({e})") from None
    terms, rows = [], []
    for sh in sheets:
        cols = _match(sh.columns, PAIR_HEADERS)
        if {"a", "b", "relation"} <= set(cols):
            for i, r in enumerate(sh.rows):
                rows.append({"row": i + 2, "sheet": sh.source or sh.name,
                             **{k: str(r[j]).strip() if j < len(r) and r[j] is not None else "" for k, j in cols.items()}})
            continue
        cols = _match(sh.columns, {**TERM_HEADERS, **TERM_EXTRA})
        if "term" in cols and len(cols) > 1:
            for r in sh.rows:
                d = {k: str(r[j]).strip() for k, j in cols.items() if j < len(r) and r[j] not in (None, "")}
                if d.get("term"):
                    terms.append(d)
    if not terms and not rows:
        raise ValueError("용어 목록(용어 · 영문 · 정의)이나 용어 관계 표(용어 A · 용어 B · 관계)를 찾지 못했습니다. 머리글을 확인해 주세요.")
    return {"terms": terms, "pairs": rows}


def merge(glossary: dict, current: list[dict], onto=None, *, source: str = "") -> tuple[list[dict], dict]:
    """The entries a glossary adds to the lexicon or changes in it, and what became of each row: the words that became
    synonyms, related, broader or narrower terms, the pairs not to be swapped, the definitions each term was tied to,
    and what now says one thing two ways. A pair row reads as "B is A's <relation>": B a synonym of A, B a broader
    term of A; of an abbreviation pair the shorter word is the abbreviation. Related and confusable go both ways."""
    have: dict[str, dict] = {}  # preferred label -> the entry written back
    for t in current:
        have.setdefault(norm(t.get("term")), t)
    out: dict[str, dict] = {}
    report: dict[str, Any] = {"source": source, "read": {"terms": len(glossary.get("terms") or []),
                                                         "pairs": len(glossary.get("pairs") or [])},
                              "added": [], "updated": [], "synonym": [], "abbreviation": [], "english": [], "hidden": [],
                              "related": [], "broader": [], "narrower": [], "confusable": [], "linked": [],
                              "unlinked": [], "review": [], "skipped": [], "conflicts": []}

    def get(term: str, create: bool = True) -> dict | None:
        key = norm(term)
        if key in out:
            return out[key]
        if key in have:
            e = copy.deepcopy(have[key])
            e["id"] = term_id(have[key])
            out[key] = e
            return e
        if not create:
            return None
        out[key] = {"term": term.strip(), **({"source": source} if source else {})}
        return out[key]

    def add(e: dict, field: str, value: str) -> bool:
        cur = _list(e.get(field))
        if not value or norm(value) in {norm(x) for x in cur} or norm(value) == norm(e.get("term")):
            return False
        e[field] = [*cur, value]
        return True

    for d in glossary.get("terms") or []:
        e = get(str(d.get("term") or d.get("name") or ""))
        for k in ("english", "kind", "definition", "owner", "cite", "concept"):
            if d.get(k) and not e.get(k):
                e[k] = str(d[k])
        if d.get("abbreviation"):
            add(e, "abbreviations", str(d["abbreviation"]))
        for k in (*LISTS, "abbreviations"):
            for x in _list(d.get(k) or (d.get("aliases") if k == "synonyms" else None)):
                add(e, k, x)
        given = d.get("confusable")
        for x in (given if isinstance(given, list) else _list(given)):
            _confuse(e, x if isinstance(x, dict) else {"term": str(x), "note": ""})
        if d.get("status") in STATUSES:
            e["status"] = d["status"]
    for r in glossary.get("pairs") or []:
        a, b, rel = r.get("a", ""), r.get("b", ""), RELATIONS.get(norm(r.get("relation")), "")
        if not a or not b:
            report["skipped"].append({"row": r["row"], "reason": "용어 A 또는 용어 B가 비어 있어 건너뛰었습니다."})
            continue
        if not rel:
            report["skipped"].append({"row": r["row"], "reason": f"관계 '{r.get('relation', '')}'을(를) 알 수 없어 건너뛰었습니다. "
                                                                 "동의어, 약어, 관련어, 상위어, 하위어, 혼동주의 중 하나로 적어 주세요."})
            continue
        if rel == "abbreviation" and len(norm(a)) < len(norm(b)):  # PG, 결제대행: the shorter word is the abbreviation
            a, b = b, a
        e = get(a)
        if r.get("kind") and not e.get("kind"):
            e["kind"] = r["kind"]
        if r.get("cite") and not e.get("cite"):
            e["cite"] = r["cite"]
        said = {"term": a, "with": b, "note": r.get("note", ""), "row": r["row"]}
        if rel == "synonym":
            add(e, "synonyms", b)
        elif rel == "abbreviation":
            add(e, "abbreviations", b)
        elif rel == "english":
            e["english"] = e.get("english") or b
        elif rel == "hidden":
            add(e, "hidden", b)
        elif rel == "related":
            add(e, "related", b)
            other = get(b, create=False)
            if other is not None:
                add(other, "related", a)
        elif rel in ("broader", "narrower"):
            add(e, rel, b)
            other = get(b, create=False)
            if other is not None:
                add(other, "narrower" if rel == "broader" else "broader", a)
        else:
            _confuse(e, {"term": b, "note": r.get("note", "")})
            _confuse(get(b), {"term": a, "note": r.get("note", "")})
        report[rel].append(said)
        if r.get("check") and _truthy(r["check"]):
            e["status"] = "review"
            if a not in report["review"]:
                report["review"].append(a)
    for key, e in out.items():
        (report["updated"] if key in have else report["added"]).append(e["term"])
        if not e.get("concept"):
            found, among = link(entry(e), onto)
            if found:
                e["concept"] = found
                report["linked"].append({"term": e["term"], "concept": found,
                                         "label": (concept_of(onto, found) or {}).get("label", "")})
            else:
                report["unlinked"].append({"term": e["term"], "candidates": among[:6]})
    after = [t for t in current if norm(t.get("term")) not in out] + list(out.values())
    known = {(c["kind"], c["label"], tuple(c["terms"])) for c in conflicts(current, onto)}
    report["conflicts"] = [c for c in conflicts(after, onto) if (c["kind"], c["label"], tuple(c["terms"])) not in known]
    return list(out.values()), report


def _confuse(e: dict, c: dict) -> None:
    cur = [x if isinstance(x, dict) else {"term": str(x), "note": ""} for x in e.get("confusable") or []]
    if c.get("term") and norm(c["term"]) != norm(e.get("term")) and norm(c["term"]) not in {norm(x["term"]) for x in cur}:
        cur.append({"term": str(c["term"]), "note": str(c.get("note") or "")})
    e["confusable"] = cur


# ---- the management screens' edits ---------------------------------------------------------------------------------

class TermEdits:
    """Term edits of the workspace (manage.Workspace): what it defines it changes in place; a term another module
    defines it writes again under the same id, which the later module's entry replaces, or takes out with `remove`."""

    def _given(self, a: dict, cur: dict | None = None) -> dict:
        d = {**(cur or {}), **{k: copy.deepcopy(a[k]) for k in FIELDS if k in a}}
        for k, old in _OLD_NAMES.items():  # a field given anew replaces what the entry said of it under an older name
            if k in a:
                for x in old:
                    d.pop(x, None)
        e = entry(d)
        if not e["term"]:
            raise ValueError("a term needs its word")
        if e["status"] not in STATUSES:
            raise ValueError(f"term status '{e['status']}' is not one of {', '.join(STATUSES)}")
        if e["concept"] and concept_of(self.composed().ontology, e["concept"]) is None:
            raise ValueError(f"term {e['term']}: concept '{e['concept']}' is unknown")
        if norm(e["term"]) in {norm(c["term"]) for c in e["confusable"]}:
            raise ValueError(f"term {e['term']} cannot be confused with itself")
        e["confusable"] = [{"term": c["term"], **({"note": c["note"]} if c["note"] else {})} for c in e["confusable"]]
        kept = {k: v for k, v in d.items() if k not in (*FIELDS, "id", *(x for xs in _OLD_NAMES.values() for x in xs))}
        out = {**kept, **{k: v for k, v in e.items() if k != "id" and v not in ("", [], {}, None)
                          and not (k == "status" and v == "active")}}  # a column a glossary named stays with it
        return {"id": cur["id"], **out} if cur and cur.get("id") else out

    def _own_term(self, tid: str) -> int | None:
        return next((i for i, t in enumerate(self.module.terms) if term_id(t) == tid), None)

    def _add_term(self, a: dict) -> str:
        e = self._given(a)
        if a.get("id"):
            e = {"id": str(a["id"]), **e}
        tid = term_id(e)
        if any(term_id(t) == tid for t in self.composed().terms):
            raise ValueError(f"term '{tid}' already exists")
        self.module.terms.append(e)
        return f"term:{tid}"

    def _update_term(self, a: dict) -> str:
        tid = str(a.get("id") or "")
        cur = next((t for t in self.composed().terms if term_id(t) == tid), None)
        if cur is None:
            raise ValueError(f"term '{tid}' is unknown")
        e = self._given(a, {**cur, "id": tid})  # the id stays what it was, whatever the word or its definition become
        i = self._own_term(tid)
        if i is None:
            self.module.terms.append(e)
        else:
            self.module.terms[i] = e
        return f"term:{tid}"

    def _delete_term(self, a: dict) -> str:
        from ontlas.modules import order

        tid = str(a.get("id") or "")
        if not any(term_id(t) == tid for t in self.composed().terms):
            raise ValueError(f"term '{tid}' is unknown")
        i = self._own_term(tid)
        base = collect(order(self.base))[0]
        if i is not None:
            del self.module.terms[i]
        if any(term_id(t) == tid for t in base) and tid not in self._removed("terms"):
            self._removed("terms").append(tid)
        return f"term:{tid}"

    def _import_terms(self, a: dict) -> str:
        """Entries a glossary brought in (merge), as one edit: each is added or written over the one with its id."""
        items = [x for x in a.get("terms") or [] if isinstance(x, dict)]
        if not items:
            raise ValueError("no terms to import")
        held = {term_id(t): t for t in self.composed().terms}
        for x in items:
            tid = term_id(x)
            e = self._given(x, {**held[tid], "id": tid} if tid in held else None)
            if tid not in held and x.get("id"):
                e = {"id": tid, **e}
            i = self._own_term(tid)
            if i is None:
                self.module.terms.append(e)
            else:
                self.module.terms[i] = e
        return f"terms:{a.get('source') or 'import'}"


__all__ = ["CONCEPT_KINDS", "LABEL_KINDS", "STATUSES", "TermEdits", "collect", "concept_of", "conflicts", "entry", "labels",
           "link", "merge", "norm", "read", "read_glossary", "term_id", "view"]
