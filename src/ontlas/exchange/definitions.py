"""Import definitions drafted outside the studio: the tables a team keeps as YAML, JSON or a workbook (`exchange.workbook`)
before any of it is a module.

A draft names Objects, the Entities under them with their properties, enumerations, relations, rules with the layer
each is meant for, the named values rules read and a glossary. Several files make one draft; a key is read by its
English name or the Korean one a sheet uses. What comes out is a library's modules: the domain module, an AXIOM module
for the rules marked so, and a customer module for those marked Custom. Names written with a vocabulary prefix
(`shop:Sku`) lose it, and a name with no prefix is aligned to the standard vocabulary the draft says it follows.

Nothing is guessed: what has no place in a module is named in the report, not dropped in silence.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ontlas.exchange.owl import ExchangeReport
from ontlas.model import TYPES
from ontlas.modules import SECTIONS, Module, Requirement

# a layer as a draft may say it (a candidate or a proposal is still that layer's)
_LAYER = (("axiom", "axiom"), ("법령", "axiom"), ("custom", "custom"), ("고객", "custom"))
_CARD_TYPE = {"의무": "duty", "금지": "ban", "제한": "limit", "판정": "decide", "계산": "compute", "표시": "display",
              "전이": "transition", "복원": "restore", "순서": "order", "감시": "watch"}
_VALUE_TYPE = {"text": "string", "string": "string", "url": "string", "integer": "integer", "int": "integer",
               "number": "decimal", "float": "decimal", "decimal": "decimal", "monetaryamount": "decimal",
               "quantitativevalue": "decimal", "boolean": "boolean", "bool": "boolean", "date": "date",
               "datetime": "datetime"}
_CARDINALITY = {"1:1": "one_to_one", "1:n": "one_to_many", "n:1": "many_to_one", "n:m": "many_to_many",
                "n:n": "many_to_many", "m:n": "many_to_many", "1": "many_to_one", "0..1": "many_to_one",
                "0..n": "many_to_many", "1..n": "many_to_many", "*": "many_to_many"}
_RELATION = {"혼동주의": "confusable", "혼동": "confusable", "confusable": "confusable", "동의어": "synonyms",
             "synonym": "synonyms", "synonyms": "synonyms", "쓰지않는표현": "avoid", "금칙어": "avoid", "avoid": "avoid",
             "상위": "broader", "broader": "broader", "하위": "narrower", "narrower": "narrower",
             "상위하위": "narrower", "하위상위": "broader"}  # 상위 · 하위: the standard term (A) above the other (B)
_NUMBER = re.compile(r"^(-?\d[\d,]*(?:\.\d+)?)\s*(%|원|일|개|시간|분|개월|년|kg|cm)?$")


def _ident(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", str(s or "").strip())
    return s if s and not s[0].isdigit() else f"_{s}"


def _split(name: Any) -> tuple[str, str]:
    """`prefix:Name` as (prefix, Name); a name with no prefix has an empty one."""
    head, sep, tail = str(name or "").strip().partition(":")
    return (head, tail) if sep and tail and "/" not in tail else ("", head)


def _get(d: dict, *keys: str, default: Any = "") -> Any:
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return default


def _text(v: Any) -> str:
    s = " ".join(str(v or "").split())
    return "" if s in ("—", "-") else s


def _strings(v: Any) -> list[str]:
    if isinstance(v, (list, tuple)):
        return [x for x in (_text(i) for i in v) if x]
    return [x for x in (_text(i) for i in re.split(r"\s*[,;]\s*", str(v or ""))) if x]


def _own(entity: str, name: str) -> str:
    """The name a property goes by on one Entity when another Entity's property of that name holds something else."""
    return f"{entity[:1].lower()}{entity[1:]}{name[:1].upper()}{name[1:]}"


def _yes(v: Any) -> bool:
    """A check column as a draft marks it: true, Y, 예."""
    return v is True or str(v or "").strip().lower() in ("y", "yes", "true", "예", "o")


def _layer(v: Any) -> str:
    s = str(v or "").lower()
    return next((layer for word, layer in _LAYER if word in s), "standard")


def _value(raw: Any) -> tuple[Any, str, str]:
    """A named value as (value, type, unit): a number where it reads as one, with the unit written after it."""
    if isinstance(raw, bool):
        return raw, "boolean", ""
    if isinstance(raw, (int, float)):
        return raw, "integer" if isinstance(raw, int) else "decimal", ""
    m = _NUMBER.match(str(raw or "").strip())
    if not m:
        return _text(raw), "string", ""
    n = m.group(1).replace(",", "")
    return (float(n), "decimal", m.group(2) or "") if "." in n else (int(n), "integer", m.group(2) or "")


class _Names:
    """Identifiers given out once: a second thing of the same name takes the fallback written for it."""

    def __init__(self) -> None:
        self.taken: dict[str, str] = {}  # identifier → what it was first given to

    def take(self, wanted: str, fallback: str, what: str) -> str:
        name = _ident(wanted)
        if name in self.taken and self.taken[name] != what:
            name = _ident(fallback)
        n, base = 2, name
        while name in self.taken and self.taken[name] != what:
            name, n = f"{base}{n}", n + 1
        self.taken[name] = what
        return name


def from_definitions(docs: list[dict], name: str, *, label: str = "", version: str = "0.1.0", namespace: str = "",
                     requires: list[str] = (), vocabulary: str = "") -> tuple[list[Module], ExchangeReport]:
    """The modules a draft makes, and what was carried, adjusted or left out. `vocabulary` is the IRI names without a
    prefix are aligned to (the draft's own `notation` is read when it gives one)."""
    rep = ExchangeReport()
    namespace = namespace or f"https://example.org/{name}#"  # as a new studio's and a draft's from files
    merged: dict[str, list] = {}
    notes: dict[str, Any] = {}
    notation: list[str] = []  # how each file says its names are written: one of them names the vocabulary
    for doc in docs:
        if not isinstance(doc, dict):
            raise ValueError("a definition draft is a mapping of sections (objects, entities, rules, terms ...)")
        for k, v in doc.items():
            if k == "meta" and isinstance(v, dict):
                notes = {**v, **notes}  # the first file's title stands
                said = v.get("notation")
                notation += [str(x) for x in (said.values() if isinstance(said, dict) else [said] if said else [])]
                rep.unsupported += [str(x) for x in v.get("not_read") or []]  # the sheets and columns a workbook's reading left
            elif k == "relations" and isinstance(v, dict):  # {object_level: [...], entity_level: [...]}
                for level, rows in v.items():
                    merged.setdefault("entity_relations" if "entity" in level else "object_relations", []).extend(rows or [])
            elif k == "relations" and isinstance(v, list):  # a glossary's relations name a standard term and its other words
                kind = "term_relations" if any(isinstance(r, dict) and ("standard" in r or "expressions" in r) for r in v) \
                    else "object_relations"
                merged.setdefault(kind, []).extend(v)
            elif isinstance(v, list):
                merged.setdefault(k, []).extend(v)
    if not vocabulary:
        found = re.search(r"https?://[^\s)]+", " ".join(notation))
        vocabulary = found.group(0) if found else ""
    if vocabulary and not vocabulary.endswith(("/", "#")):
        vocabulary += "/"

    def aligned(raw: Any, vocab: Any = None) -> list[str]:
        """The standard name a draft's name stands for: one written with no prefix, in the vocabulary the draft follows."""
        prefix, local = _split(raw)
        if not vocabulary or prefix or not local or (vocab not in (None, "") and str(vocab).lower() not in vocabulary.lower()):
            return []
        return [vocabulary + local]

    # ---- Objects: the level above the Entities ----
    areas: dict[str, dict] = {}
    area_of_label: dict[str, str] = {}
    area_of_class: dict[str, str] = {}  # an Entity's written name → its Object
    for o in merged.get("objects", []):
        raw = _get(o, "class", "name", "notation")
        ko = _text(_get(o, "label_ko", "label")) or _split(str(raw).split("@")[-1])[1]
        ident = _ident(_split(str(raw).split("@")[-1])[1])
        said = [_text(_get(o, "definition", "description"))]
        said += [f"{word}: {_text(o[k])}" for k, word in (("group", "묶음"), ("includes", "포함"), ("excludes", "제외"),
                                                           ("identifier", "식별자"), ("lifecycle", "상태 흐름"),
                                                           ("scope_without_data", "연결 없이"), ("scope_with_data", "연결 후"))
                 if _text(o.get(k))]
        area = {"label": ko, "description": " · ".join(x for x in said if x), "status": "draft"}
        if aligned(raw, o.get("vocabulary")):
            area["aligned"] = aligned(raw, o.get("vocabulary"))
        if _text(o.get("owner")):
            area["owner"] = _text(o["owner"])
        if _text(o.get("id")):  # the row it was drafted as, so the draft and the studio can be read side by side
            area["cite"] = _text(o["id"])
        areas.setdefault(ident, area)
        area_of_label[ko] = ident
        for e in o.get("entities") or []:
            area_of_class[str(_get(e, "class", "name") if isinstance(e, dict) else e)] = ident
        rep.preserved.append(f"object {ident}")

    def area_named(said: Any) -> str:
        """The Object a row names: by its label, or by its English name as a draft writes it (`Order`, `shop:Order`,
        `주문@Order`)."""
        ko, _, en = _text(said).partition("@")
        return area_of_label.get(ko.strip()) or next((a for a in (ko.strip(), _split(en or ko)[1]) if a in areas), "")

    # ---- enumerations: the codes a property allows, each with its name ----
    enums = {str(n.get("name")): [(str(v.get("value")), _text(_get(v, "label_ko", "label"))) if isinstance(v, dict) else (str(v), "")
                                  for v in n.get("values") or []] for n in merged.get("enumerations", [])}

    # ---- Entities and their properties ----
    types = _Names()
    objects: dict[str, dict] = {}
    type_of: dict[str, str] = {}  # an Entity as written (with and without its prefix) → its identifier
    pending_links: list[tuple[str, dict]] = []
    enum_of: dict[tuple[str, str], str] = {}  # (Entity, property) → the enumeration it takes, as a glossary may name it
    # an Entity two files (or two sheets) both list is one Entity: its first row stands, a later one gives what that left
    # empty, and their properties add up
    listed: dict[str, dict] = {}
    for e in merged.get("entities", []):
        first = listed.get(str(_get(e, "class", "name")))
        if first is None:
            listed[str(_get(e, "class", "name"))] = dict(e)
            continue
        have = {str(p.get("name")) for p in first.get("properties") or []}
        more = [p for p in e.get("properties") or [] if str(p.get("name")) not in have]
        first.update({f: v for f, v in e.items() if f != "properties" and first.get(f) in (None, "")})
        if more:
            first["properties"] = [*(first.get("properties") or []), *more]
    for e in listed.values():
        raw = str(_get(e, "name", "class"))
        prefix, local = _split(raw)
        ident = types.take(local, f"{prefix}_{local}", raw)
        type_of[raw] = type_of[str(_get(e, "class", default=raw))] = ident
        type_of.setdefault(local, ident)
    for e in listed.values():
        raw = str(_get(e, "name", "class"))
        ident = type_of[raw]
        area = area_of_class.get(raw) or area_of_class.get(str(e.get("class") or "")) or area_named(e.get("object"))
        said = [_text(_get(e, "definition", "description"))]
        if _text(e.get("rule_requirements")):  # what the rules need of it, as its author put it
            said.append(f"규칙이 요구하는 것: {_text(e['rule_requirements'])}")
        obj: dict[str, Any] = {"label": _text(_get(e, "label_ko", "label")) or ident, "description": " · ".join(x for x in said if x),
                               "status": "draft", "properties": {}}
        if area:
            obj["area"] = area
        if aligned(raw, e.get("vocabulary")):
            obj["aligned"] = aligned(raw, e.get("vocabulary"))
        if _text(e.get("id")):
            obj["cite"] = _text(e["id"])
        parent = type_of.get(str(e.get("subClassOf") or ""))
        if parent and parent != ident:
            obj["parent"] = parent
        names = _Names()
        key = ""
        for p in e.get("properties") or []:
            praw = str(p.get("name") or "")
            pp, plocal = _split(praw)
            kind = str(p.get("kind") or "").lower()
            rng = str(p.get("range") or "")
            if kind in ("관계", "relation", "link") or (rng in type_of and kind not in ("열거형", "enum", "enumeration")):
                pending_links.append((ident, p))
                continue
            pname = names.take(plocal, f"{pp}_{plocal}", praw)
            prop: dict[str, Any] = {"label": _text(_get(p, "label_ko", "label")) or pname}
            if rng in enums or kind in ("열거형", "enum", "enumeration"):
                codes = enums.get(rng, [])
                prop["type"] = "enum" if codes else "string"
                if codes:
                    prop["values"] = [c for c, _ in codes]
                    if any(word for _, word in codes):
                        prop["labels"] = {c: word for c, word in codes if word}
                    enum_of[(ident, pname)] = _ident(_split(rng)[1])
                else:
                    rep.adjusted.append(f"{ident}.{pname}: enumeration '{rng}' is not in the draft, kept as text")
            else:
                prop["type"] = _VALUE_TYPE.get(_split(rng)[1].lower(), "string")
                if _split(rng)[1].lower() not in _VALUE_TYPE and rng:
                    rep.adjusted.append(f"{ident}.{pname}: value type '{rng}' kept as text")
            if p.get("required") is True or str(p.get("cardinality") or "").startswith("1"):
                prop["required"] = True
            if aligned(praw, p.get("vocabulary")):
                prop["aligned"] = aligned(praw, p.get("vocabulary"))
            obj["properties"][pname] = prop
            # what a thing is told apart by: the first single required text value that reads as an identifier
            lab = prop["label"]
            if not key and prop.get("required") and prop["type"] == "string" and str(p.get("cardinality") or "1") == "1" and \
                    (re.search(r"(id|ID|Id|[Nn]umber|[Cc]ode)$", pname) or re.search(r"(번호|코드|ID|식별자)$", lab)):
                key = pname
        if not key:
            key = "id" if "id" not in obj["properties"] else names.take("key_id", "key_id2", "key")
            obj["properties"] = {key: {"type": "string", "label": "식별자", "required": True}, **obj["properties"]}
            rep.adjusted.append(f"{ident}: no property reads as its identifier, '{key}' was added")
        obj["key"] = key
        objects[ident] = obj
        rep.preserved.append(f"entity {ident}")

    # one name is one property wherever it is used, so it has one type. Where a draft gives the same name two types that
    # hold the same thing, the wider one stands (a date beside a date and time, a whole number beside a decimal). Where
    # they do not (a code beside free text), the later Entity's goes by its own name as well, so neither loses its codes.
    seen: dict[str, tuple[str, str]] = {}  # property → (type, the Entity that gave it first)
    for tname, o in objects.items():
        renamed: dict[str, str] = {}
        for pname, prop in o["properties"].items():
            first = seen.setdefault(pname, (prop["type"], tname))
            if first[0] == prop["type"]:
                continue
            pair = {first[0], prop["type"]}
            if pair in ({"date", "datetime"}, {"integer", "decimal"}):
                wide = "datetime" if "datetime" in pair else "decimal"
                rep.adjusted.append(f"property {pname}: {prop['type']} on {tname}, {first[0]} on {first[1]}; read as {wide} on both")
                seen[pname] = (wide, first[1])
            else:
                own = _own(tname, pname)
                renamed[pname] = own
                seen[own] = (prop["type"], tname)
                rep.adjusted.append(f"property {pname}: {prop['type']} on {tname}, {first[0]} on {first[1]}; on {tname} it goes by {own}")
        if renamed:
            o["properties"] = {renamed.get(k, k): v for k, v in o["properties"].items()}
            o["key"] = renamed.get(o["key"], o["key"])
            enum_of.update({(tname, renamed[p]): enum_of.pop((t, p)) for t, p in list(enum_of) if t == tname and p in renamed})
    for o in objects.values():
        for pname, prop in o["properties"].items():
            prop["type"] = seen[pname][0]

    # ---- relations between Entities: a property whose value is another Entity ----
    links: dict[str, dict] = {}
    link_of: dict[tuple[str, str], str] = {}  # (Entity, the property it was written as) → the relation's name
    link_names = _Names()
    link_names.taken.update({pname: f"property {pname}" for pname in seen})  # a relation is not named as a property is

    def link(source: str, praw: str, target_raw: str, card: Any, label_ko: Any, vocab: Any = None) -> None:
        target = type_of.get(str(target_raw))
        if source not in objects or not target:
            rep.unsupported.append(f"relation {source}.{praw} → {target_raw}: the Entity it reaches is not in the draft")
            return
        pp, plocal = _split(praw)
        lname = link_names.take(plocal, f"{source[:1].lower()}{source[1:]}{plocal[:1].upper()}{plocal[1:]}", f"{source}.{praw}")
        spec = {"from": source, "to": target, "cardinality": _CARDINALITY.get(str(card or "").lower().replace(" ", ""), "many_to_many"),
                "label": _text(label_ko) or lname, "status": "draft"}
        if str(card or "").startswith("1"):
            spec["required"] = True
        if aligned(praw, vocab):
            spec["aligned"] = aligned(praw, vocab)
        links[lname] = spec
        link_of[(source, _ident(plocal))] = lname
        rep.preserved.append(f"link {lname}")

    done: set[tuple[str, str]] = set()
    for source, p in pending_links:
        link(source, str(p.get("name")), p.get("range"), p.get("cardinality"), _get(p, "label_ko", "label"), p.get("vocabulary"))
        done.add((source, str(p.get("name"))))
    for r in merged.get("entity_relations", []):
        source = type_of.get(str(r.get("subject")), "")
        if (source, str(_get(r, "property", "predicate"))) not in done:
            link(source, str(_get(r, "property", "predicate")), r.get("object"), r.get("cardinality"), _get(r, "label_ko", "label"))
    between = {(str(r.get("subject")), str(_get(r, "predicate", "property")), str(r.get("object"))) for r in merged.get("object_relations", [])}
    if between:
        rep.unsupported.append(f"{len(between)} relations between Objects: an Object groups Entities and holds no relation of its "
                               "own; the relations between their Entities were carried")

    # ---- named values ----
    parameters: dict[str, dict] = {}
    values_of_rule: dict[str, dict] = {}
    title_of = {str(_get(r, "id", "rule")): _text(_get(r, "name", "title")) for r in merged.get("rules", [])}
    for p in merged.get("parameters", []):
        pname = _ident(str(_get(p, "key", "name")).lstrip("@"))
        value, type_, unit = _value(p.get("value"))
        used = [title_of[str(r)] for r in p.get("rules") or [] if title_of.get(str(r))]  # a value is known by the rule that reads it
        spec: dict[str, Any] = {"type": type_ if type_ in TYPES else "string", "value": value,
                                "label": _text(p.get("label")) or (used[0] if used else pname)}
        if len(used) > 1:
            spec["description"] = "쓰는 규칙: " + ", ".join(used)
        if unit:
            spec["unit"] = unit
        if _text(_get(p, "kind", "cite")):
            spec["cite"] = _text(_get(p, "kind", "cite"))
        parameters[pname] = spec
        if type_ == "string":
            rep.adjusted.append(f"parameter {pname}: '{value}' does not read as a number, kept as text")
        for rid in p.get("rules") or []:
            values_of_rule.setdefault(str(rid), {})[pname] = value
        rep.preserved.append(f"parameter {pname}")

    # ---- rules: one card each, in the module of its layer ----
    # what a rule is about, from every file that links it: the Entities it reads and the Object it is filed under
    entities_of_rule: dict[str, list[str]] = {}
    object_of_rule: dict[str, str] = {}
    for r in merged.get("rule_links", []):
        rid = str(r.get("rule"))
        reads = [type_of[x] for x in r.get("entities") or [] if x in type_of]
        entities_of_rule[rid] = list(dict.fromkeys([*entities_of_rule.get(rid, []), *reads]))
        if _text(r.get("object")):
            object_of_rule.setdefault(rid, _text(r["object"]))
    cards: dict[str, list[dict]] = {"axiom": [], "custom": [], "standard": []}
    for r in merged.get("rules", []):
        rid = re.sub(r"[^A-Za-z0-9_-]", "_", str(_get(r, "id", "rule")))
        layer = _layer(_get(r, "tier", "layer"))
        kind = str(r.get("type") or "")
        ctype = _CARD_TYPE.get(kind, kind if kind in _CARD_TYPE.values() else "decide")
        if kind and ctype == "decide" and kind not in ("판정", "decide"):
            rep.adjusted.append(f"rule {rid}: type '{kind}' is not known, filed as a decision")
        title, result = _text(_get(r, "name", "title")), _text(r.get("result"))
        named = values_of_rule.get(str(_get(r, "id", "rule")), {})
        card: dict[str, Any] = {"id": rid, "type": ctype, "statement": title or result, "status": "draft"}
        said = _text(r.get("object")) or object_of_rule.get(str(_get(r, "id", "rule")), "")  # its Object, by label or name
        area = area_named(said)
        if said and not area:
            rep.adjusted.append(f"rule {rid}: Object '{said}' is not in the draft, left off what it applies to")
        applies = ([f"area:{area}"] if area else []) + [f"object:{x}" for x in entities_of_rule.get(str(_get(r, "id", "rule")), [])] + \
            [f"parameter:{x}" for x in named]
        for field, value in (("applies_to", applies), ("conditions", _strings([r.get("condition")]) if r.get("condition") else []),
                             ("result", result if title else ""), ("exceptions", _strings([r.get("exception")]) if r.get("exception") else []),
                             ("params", named), ("source", _text(_get(r, "basis", "source"))), ("owner", _text(r.get("owner"))),
                             ("risk", _text(r.get("risk"))), ("verification", _text(r.get("verification"))),
                             # the group a sheet files it under (its 영역), the law it rests on and the kind of that source,
                             # how it stands against the policy already written, and what it is about in its author's words
                             ("category", _text(_get(r, "area", "category"))), ("law", _text(r.get("law"))),
                             ("source_kind", _text(_get(r, "basis_kind", "source_kind"))),
                             ("policy_check", _text(r.get("policy_check"))), ("related", _text(r.get("related")))):
            if value:
                card[field] = value
        if layer == "axiom":
            card["legal_review"] = "pending"  # a rule read from a law stands once a lawyer has held it against the text
        cards[layer].append(card)
        rep.preserved.append(f"rule {rid}")
    for i, b in enumerate(merged.get("banned_expressions", []), 1):
        # an expression allowed once a condition is met (조건부) is limited; the others are banned
        bkind = "limit" if re.search(r"조건|condition", str(b.get("kind") or ""), re.I) else "ban"
        card = {"id": f"BX-{i:02d}", "type": bkind, "statement": f"{_text(b.get('scope'))}: {_text(b.get('reason'))}".strip(": "),
                "status": "draft", "legal_review": "pending"}
        for field, value in (("conditions", _strings(re.split(r"\s+·\s+", str(b.get("examples") or "")))),
                             ("exceptions", _strings([b.get("allowed_when")]) if b.get("allowed_when") else []),
                             ("source", _text(b.get("basis"))), ("verification", _text(b.get("verification")))):
            if value:
                card[field] = value
        cards["axiom"].append(card)
        rep.preserved.append(f"banned expression {card['id']}")

    # ---- glossary ----
    terms: dict[str, dict] = {}

    def term(word: str) -> dict:
        ko, _, en = str(word).partition("@")
        ko = _text(ko)
        t = terms.setdefault(ko, {"term": ko})
        ident = type_of.get(en.strip()) if en else None
        area = _ident(_split(en)[1]) if en and _ident(_split(en)[1]) in areas else ""
        # `word@Class` names an Entity, or the Object of that class where no Entity is, or where the word is the Object's
        if area and (not ident or (areas[area]["label"] == ko and objects[ident]["label"] != ko)) and "concept" not in t:
            t.update(concept=f"area:{area}", **({} if ident else {"english": _split(en)[1]}))  # the class's English is its Entity's
        elif ident and "concept" not in t:
            t.update(concept=f"object:{ident}", english=_split(en)[1])
        return t

    value_concept: dict[str, list[tuple[str, str, str]]] = {}  # a code → (concept, its name, Entity) of each property allowing it
    for tname, o in objects.items():
        for pname, p in o["properties"].items():
            for code in p.get("values") or []:
                value_concept.setdefault(code, []).append((f"value:{tname}.{pname}={code}", (p.get("labels") or {}).get(code, ""), tname))
    by_label: dict[str, list[str]] = {}  # an Entity's label → the Entities called so
    for tname, o in objects.items():
        by_label.setdefault(o["label"], []).append(tname)

    def named(tname: str, english: Any) -> str:
        """What an Entity's English name stands for: a property, a relation, the enumeration a property takes, or one of
        its codes written after it (`Enumeration · Code`)."""
        if not english:
            return f"object:{tname}"
        pieces = [_text(x) for x in re.split(r"\s+·\s+", _split(english)[1], maxsplit=1)]
        head, code, props = _ident(pieces[0]), pieces[1] if len(pieces) > 1 else "", objects[tname]["properties"]
        head = head if head in props or _own(tname, head) not in props else _own(tname, head)  # it may go by its Entity's name
        if not code and head in props:
            return f"property:{tname}.{head}"
        if not code and (tname, head) in link_of:
            return f"link:{link_of[(tname, head)]}"
        takes = [p for (t, p), e in enum_of.items() if t == tname and e == head]
        if len(takes) == 1 and (not code or code in (props[takes[0]].get("values") or [])):
            return f"value:{tname}.{takes[0]}={code}" if code else f"property:{tname}.{takes[0]}"
        return ""

    def concept_of(path: Any, english: Any) -> str:
        """`Object › Entity` with the property's own name, as the definition it stands for. A row that gives several paths
        (`A › B · C › D`) stands for the first that names one; a path of an Object alone names that Object."""
        whole = str(path or "")  # a name may hold a ·, so it is read whole first unless it holds two paths' ›
        for one in [*([whole] if len(re.findall(r"[›>]", whole)) < 2 else []), *(re.split(r"\s+·\s+", whole) if "·" in whole else [])]:
            parts = [_text(x) for x in re.split(r"[›>]", one)]
            found = [n for n in by_label.get(parts[-1], []) if len(parts) < 2 or areas.get(objects[n].get("area", ""), {}).get("label") == parts[0]]
            if len(found) == 1 and (got := named(found[0], english)):
                return got
            if not found and len(parts) == 1 and not english and parts[0] in area_of_label:
                return f"area:{area_of_label[parts[0]]}"
        return ""
    for x in merged.get("terms", []):
        t = term(_get(x, "term", "name"))
        if _text(x.get("id")):  # the row's own id is the id the entry is edited by
            t.setdefault("id", _text(x["id"]))
        for field, value in (("english", _text(x.get("english"))), ("kind", _text(x.get("kind"))),
                             ("concept", concept_of(x.get("concept"), x.get("english")) if "concept" not in t else ""),
                             ("definition", _text(_get(x, "definition", "description"))), ("source", _text(x.get("source"))),
                             ("synonyms", _strings(x.get("synonyms")))):
            if value:
                t[field] = value
        rep.preserved.append(f"term {t['term']}")
    for x in merged.get("term_relations", []):
        t = term(x.get("standard"))
        field = _RELATION.get(re.sub(r"[\s·]", "", str(x.get("relation") or "")).lower()) or \
            next((f for word, f in _RELATION.items() if word in re.sub(r"\s", "", str(x.get("relation") or ""))), "")
        words = [w for w in _strings(x.get("expressions")) if w != t["term"]]
        if field == "confusable":
            t.setdefault("confusable", []).extend({"term": w, "note": _text(x.get("note"))} for w in words)
        elif field:
            t[field] = list(dict.fromkeys([*t.get(field, []), *words]))
        else:
            rep.unsupported.append(f"term relation '{x.get('relation')}' of {t['term']}: not a kind the lexicon keeps")
            continue
        # as a glossary's pair rows are read (lexicon.merge): the ground a row gives, and a row marked to be checked
        if _text(_get(x, "basis", "cite")) and not t.get("cite"):
            t["cite"] = _text(_get(x, "basis", "cite"))
        if _yes(_get(x, "needs_check", "check", default=False)):
            t["status"] = "review"
        rep.preserved.append(f"term relation {t['term']} {field}")
    for t in list(terms.values()):  # a broader term has the other as its narrower one, and the other way round
        for field, back in (("broader", "narrower"), ("narrower", "broader")):
            for w in t.get(field, []):
                if w in terms and t["term"] not in terms[w].get(back, []):
                    terms[w].setdefault(back, []).append(t["term"])
    for x in merged.get("customer_labels", []):
        code = str(x.get("standard_value") or "")
        found = value_concept.get(code, [])
        where = _text(_get(x, "area", "영역"))  # of the codes' properties, the one of the Entity or Object the row names
        pick = next((f for f in found if objects[f[2]]["label"] == where), None) or \
            next((f for f in found if areas.get(objects[f[2]].get("area", ""), {}).get("label") == where), None) or (found or [None])[0]
        if not pick:
            rep.unsupported.append(f"customer label '{x.get('customer_label')}': the value '{code}' is not a code of one property")
            continue
        concept, word = pick[:2]
        key = word or code
        if terms.get(key, {}).get("concept", concept) != concept:  # one word naming two things is two entries
            key = f"{key}@{concept}"
        t = terms.setdefault(key, {"term": word or code})
        t.setdefault("concept", concept)
        if _yes(_get(x, "needs_check", "check", default=False)):
            t["status"] = "review"
        shown = _text(x.get("customer_label"))
        if shown and shown != t["term"]:
            if "고객" in t.setdefault("channels", {}) and t["channels"]["고객"] != shown:
                t["synonyms"] = list(dict.fromkeys([*t.get("synonyms", []), shown]))
            else:
                t["channels"]["고객"] = shown
        others = [w for w in _strings(x.get("admin_labels")) if w not in (t["term"], shown)]
        if others:
            t["synonyms"] = list(dict.fromkeys([*t.get("synonyms", []), *others]))
        rep.preserved.append(f"customer label {shown}")
    # one word reads as one term: a word two terms would both answer to stays with the first that took it
    said: dict[str, str] = {}
    for t in terms.values():
        for field in ("synonyms", "avoid"):
            kept = []
            for w in t.get(field, []):
                k = re.sub(r"\s+", "", w).lower()
                if k in said and said[k] != t["term"]:
                    rep.adjusted.append(f"term {t['term']}: '{w}' already reads as {said[k]}, left off")
                    continue
                said[k] = t["term"]
                kept.append(w)
            if field in t:
                t[field] = kept
        said.setdefault(re.sub(r"\s+", "", t["term"]).lower(), t["term"])

    known = {"meta", "objects", "entities", "enumerations", "entity_relations", "object_relations", "parameters", "rules",
             "rule_links", "banned_expressions", "terms", "term_relations", "customer_labels"}
    for k in sorted(set(merged) - known):
        rep.unsupported.append(f"section '{k}' ({len(merged[k])} rows): no place in a module")

    # ---- the modules ----
    def module(mname: str, kind: str, mlabel: str, body: dict, needs: list[str], words: list[dict] = ()) -> Module:
        full = {**{s: {} for s in SECTIONS}, "questions": [], "exclusive": [], **body}
        return Module(name=mname, version=version, kind=kind, label=mlabel, namespace=namespace,
                      description=_text(notes.get("title")), requires=[Requirement.parse(r) for r in needs],
                      body=full, terms=list(words))

    title = label or _text(notes.get("title")) or name
    out = [module(name, "domain", title, {"areas": areas, "objects": objects, "links": links, "parameters": parameters,
                                         "rule_cards": cards["standard"]}, list(requires), list(terms.values()))]
    if cards["axiom"]:
        out.append(module(f"{name}-axiom", "axiom", f"{title} · AXIOM", {"rule_cards": cards["axiom"]}, [name]))
    if cards["custom"]:
        out.append(module(f"{name}-custom", "customer", f"{title} · Custom", {"rule_cards": cards["custom"]}, [name]))
    return out, rep


def read_draft(path: str | Path) -> dict:
    """One file of a draft as the mapping of sections it is: the sheets of a workbook, else YAML (which JSON is)."""
    from ontlas.exchange.workbook import WORKBOOKS, read_workbook

    p = Path(path)
    if p.suffix.lower() in WORKBOOKS:
        return read_workbook(p.read_bytes(), p.name)
    import yaml

    return yaml.safe_load(p.read_text(encoding="utf-8"))
