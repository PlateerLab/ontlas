"""What the home and the version history ask for: every version of the space (판본) with the change that made it, what a
change makes worse or better beside its review, and where the space stands as a whole: how far each Entity has come
(L0 to L3), the four parts it is built from, the Objects it is filed under, what waits on people and the milestones its
studio file names.

Kept apart from api.py and pages_api.py like the other page mixins; everything here reads `self.studio` through the
same helpers the other screens use. The overview measures nothing anew: it reads the last measurement the flow took.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Any

from ontlas.web.space_api import plain

APPLIES = ("replace", "attach")  # review modes in which an approved change is swapped into the space, not only filed


def _pct(v: Any) -> str:
    return "-" if v is None else f"{v * 100:.1f}".removesuffix(".0") + "%"


class HomeMixin:
    """The version history, the regression beside a change, and the home's overview of the space."""

    # ---- what a change makes worse or better ------------------------------------------------------------------------

    def _standing_measured(self) -> dict:
        """The studio as it stands, measured once per definition (the same measurement the review's "before" shows): what
        a review compares its trial copy with."""
        self._standing_gates()
        return dict(self._standing[2]) if self._standing else {}

    def _regression_view(self, reg: dict | None) -> dict | None:
        """A review's regression as the page reads it: the conditions by their names, an error in the page's words, and
        one line that says what moved."""
        if not reg:
            return None
        from ontlas.web.api import GATE_LABEL, STAGE_LABEL, UNMEASURED, said

        def gate(g: dict) -> dict:
            return {**g, "label": GATE_LABEL.get((g["stage"], g["condition"]), g["condition"]),
                    "stage_label": STAGE_LABEL.get(g["stage"], g["stage"])}

        failing = [{**q, "error": said(q["error"]) if q.get("error") else ""} for q in reg.get("newly_failing") or []]
        parts = [f"새로 틀리는 질문 {len(failing)}개" if failing else "",
                 f"새로 맞는 질문 {len(reg.get('newly_passing') or [])}개" if reg.get("newly_passing") else ""]
        for key, word in (("accuracy", "정답률"), ("grounded", "근거 제시율"), ("agreement", "판정 일치율")):
            m = reg.get(key)
            if m and m.get("change"):
                parts.append(f"{word} {_pct(m['before'])} → {_pct(m['after'])}")
        parts += [f"통과 조건 {len(reg['gates_failing'])}개 미충족으로 바뀜" if reg.get("gates_failing") else "",
                  f"통과 조건 {len(reg['gates_passing'])}개 충족으로 바뀜" if reg.get("gates_passing") else ""]
        if reg.get("unmeasured"):  # questions that read rows, with none to read: neither failed nor passed
            parts.append(f"측정 대상 아닌 질문 {len(reg['unmeasured'])}개 (원천 미연결)")
        said_line = " · ".join(p for p in parts if p) or "달라진 결과 없음"
        return {**reg, "newly_failing": failing, "gates_failing": [gate(g) for g in reg.get("gates_failing") or []],
                "gates_passing": [gate(g) for g in reg.get("gates_passing") or []],
                "note": UNMEASURED["no_source"] if reg.get("unmeasured") else "", "summary": said_line}

    # ---- every version of the space and of each module ---------------------------------------------------------------

    def _applied_changes(self) -> list:
        """The approved changes that were swapped into the space, in the order they were approved: each one made a new
        version of it. The audit keeps that order across a restart."""
        ch = self.studio.changes
        seen: list[str] = []
        for e in ch.audit:
            if e.get("event") == "approved" and e.get("change") not in seen:
                seen.append(e["change"])
        crs = [ch.requests[i] for i in seen if i in ch.requests]
        crs += [c for c in ch.requests.values() if c.status == "approved" and c.id not in seen]  # no audit kept for it
        return [c for c in crs if c.status == "approved" and (c.review or {}).get("mode") in APPLIES]

    def _space_version(self) -> dict:
        """The space as it is applied now: its number among the versions approved changes made, a key that is the same for
        the same modules at the same versions, and the modules."""
        from ontlas.preview import MODULE_KIND
        from ontlas.web.api import WORKSPACE

        st = self.studio
        comp = st.composition
        mods = [{"name": m.name, "label": (m.label or m.name) if m.name == WORKSPACE else self._label(m.name), "kind": m.kind,
                 "kind_label": MODULE_KIND.get(m.kind, m.kind), "version": m.version} for m in comp.modules] if comp else [
            {"name": st.onto.name, "label": st.onto.label or st.onto.name, "kind": "", "kind_label": "", "version": st.onto.version}]
        applied = self._applied_changes()
        number = len(applied) + 1
        last = applied[-1] if applied else None
        key = hashlib.sha256("|".join(sorted(f"{m['name']}@{m['version']}" for m in mods)).encode("utf-8")).hexdigest()[:8]
        return {"number": number, "label": f"판본 {number}", "key": key, "modules": mods,
                "change": last.id if last else "", "at": self._decided_at(last) if last else ""}

    def _decided_at(self, cr) -> str:
        """When a change was approved or rejected: kept with it, or for one decided before that was kept, its audit line."""
        if cr.decided_at:
            return cr.decided_at
        return next((e.get("at", "") for e in reversed(self.studio.changes.audit)
                     if e.get("change") == cr.id and e.get("event") in ("approved", "rejected")), "")

    def _change_summary(self, cr) -> str:
        """What a change does, in one line: the elements it changes, adds and removes by their names, the first few."""
        rv = cr.review or {}
        if rv.get("issues"):
            return f"정의 오류 {len(rv['issues'])}건"
        diff = rv.get("diff") or {}
        said = [f"{self._element_label(el)} {word}" for k, word in (("changed", "변경"), ("added", "추가"), ("removed", "제거"))
                for el in diff.get(k) or []]
        if not said:
            return f"라이브러리에 {cr.version} 저장" if rv.get("mode") == "library" else "바뀐 요소 없음"
        return ", ".join(said[:3]) + (f" 외 {len(said) - 3}건" if len(said) > 3 else "")

    def _version_row(self, cr, number: int | None) -> dict:
        from ontlas.web.api import CHANGE_STATUS

        rv = cr.review or {}
        diff = rv.get("diff") or {}
        return {"id": cr.id, "module": cr.module, "module_label": self._change_label(cr), "mode": rv.get("mode", ""),
                "from": rv["from_version"] if "from_version" in rv else rv.get("base_version", ""), "to": cr.version,
                "status": cr.status, "status_label": CHANGE_STATUS.get(cr.status, cr.status),
                "applied": cr.status == "approved" and rv.get("mode") in APPLIES, "number": number,
                "requested_by": cr.requested_by, "requested_at": cr.at, "decided_by": cr.decided_by,
                "decided_at": self._decided_at(cr) if cr.status != "pending" else "", "reason": cr.reason,
                "passed": rv.get("passed"), "counts": {k: len(diff.get(k) or []) for k in ("added", "changed", "removed")},
                "summary": self._change_summary(cr), "regression": self._regression_view(rv.get("regression"))}

    def _library_versions(self) -> list[dict]:
        """Every module the library holds, each version with whether it is applied, whether it is a file in the library
        folder (or held for this visit only) and the change that made it."""
        from ontlas.library import OverlayLibrary
        from ontlas.preview import MODULE_KIND
        from ontlas.web.api import KIND_ORDER

        st = self.studio
        lib, comp = st.library, st.composition
        on = {m.name: m for m in comp.modules} if comp else {}
        folder = lib.base if isinstance(lib, OverlayLibrary) else lib
        made = {(c.module, c.version): c.id for c in st.changes.requests.values() if c.status == "approved"}
        known = {r["name"]: r for r in self._library_rows}
        names = lib.names() if lib is not None else []
        rows = []
        for name in sorted(set(names) | set(on)):
            versions = lib.versions(name) if name in names else [on[name].version]
            files = set(folder.versions(name)) if folder is not None and name in names else set()
            if name in known:
                label, kind = known[name]["label"], known[name]["kind"]
            else:
                m = on.get(name) or lib.get(name)
                label, kind = m.label, m.kind
            applied = on[name].version if name in on else ""
            rows.append({"name": name, "label": label or name, "kind": kind, "kind_label": MODULE_KIND.get(kind, kind), "applied": applied,
                         "latest": versions[-1] if versions else "",
                         "versions": [{"version": v, "applied": v == applied, "on_disk": v in files, "change": made.get((name, v), "")}
                                      for v in reversed(versions)]})
        rows.sort(key=lambda r: (KIND_ORDER.index(r["kind"]) if r["kind"] in KIND_ORDER else 99, r["name"]))
        return rows

    def versions(self) -> dict:
        """The space's current version, the changes under review that would make the next one, every decided change
        newest first, and every module version in the library with the one applied."""
        ch = self.studio.changes
        applied = self._applied_changes()
        numbers = {c.id: i + 2 for i, c in enumerate(applied)}  # version 1 is the space as it was first built
        order = {c.id: n for n, c in enumerate(ch.requests.values())}
        pending = [c for c in ch.requests.values() if c.status == "pending"]
        decided = sorted((c for c in ch.requests.values() if c.status in ("approved", "rejected")),
                         key=lambda c: (self._decided_at(c), order[c.id]), reverse=True)
        return plain({"current": self._space_version(),
                      "pending": [self._version_row(c, None) for c in reversed(pending)],
                      "history": [self._version_row(c, numbers.get(c.id)) for c in decided],
                      "library": self._library_versions(), "writes_folder": ch.store is not None})

    # ---- where the space stands, for the home -----------------------------------------------------------------------

    def _entity_levels(self) -> dict[str, int]:
        """Each Entity's level as the management screens give it (bindings.entity_level), on the definition as applied:
        the source's columns where they were read, and the last database check where it was taken on this definition."""
        from ontlas.bindings import entity_level
        from ontlas.draft import _catalog

        st, o = self.studio, self.studio.onto
        src = st.backends.get(st.source) if st.source else None
        catalog, _ = self._source_catalog(src, _catalog)
        held = {t: {c.lower() for c, _ in cols} for t, cols, _, _ in catalog}
        bind = self._measured.get("bind") if self._measured_of is o else None
        found = None if bind is None else {str(f.get("element", "")) for f in bind.get("findings") or []}
        return {t.name: entity_level(o, t.name, columns=held.get(t.table), found=found) for t in o.objects.values()}

    def _object_row(self, name: str, label: str, members: list[str], levels: dict[str, int], **extra) -> dict:
        from ontlas.web.api import LEVEL_LABEL

        o = self.studio.onto
        spread = [sum(1 for n in members if levels[n] == i) for i in range(4)]
        low = min((levels[n] for n in members), default=None)
        return {"name": name, "label": label, **extra, "count": len(members), "levels": spread,
                "level": low, "level_label": LEVEL_LABEL[low] if low is not None else "",
                "entities": [{"name": n, "label": o.objects[n].label or n, "level": levels[n], "level_label": LEVEL_LABEL[levels[n]]}
                             for n in members]}

    def _milestones(self) -> list[dict]:
        """The milestones the studio file names (milestones: [{date, label, detail}]), by date, each past, next or later as
        the studio's clock reads today."""
        raw = self.studio.settings.get("milestones")
        now = self.studio.now()
        today = now.date() if isinstance(now, datetime) else date.today()
        rows = []
        for m in raw if isinstance(raw, list) else []:
            label = str(m.get("label") or "").strip() if isinstance(m, dict) else ""
            if not label:
                continue
            when = m.get("date")
            if isinstance(when, datetime):
                when = when.date()
            elif not isinstance(when, date):
                try:
                    when = date.fromisoformat(str(when or "").strip()[:10])
                except ValueError:  # a date the file does not give as YYYY-MM-DD: kept, in no place on the calendar
                    when = None
            rows.append((when, {"date": when.isoformat() if when else str(m.get("date") or ""), "label": label,
                                "detail": str(m.get("detail") or ""), "days": (when - today).days if when else None}))
        rows.sort(key=lambda x: (x[0] is None, x[0] or date.min))
        upcoming = next((r for when, r in rows if when is not None and when >= today), None)
        for when, r in rows:
            r["state"] = "past" if when is not None and when < today else "next" if r is upcoming else "later"
        return [r for _, r in rows]

    def overview(self) -> dict:
        """The home's view of the space, read from what is here: the last measurement the flow took (none is taken) and the
        to-do list as the home shows it. How many Entities stand at each level, the four parts the space is built from
        with one status each, the Objects with their Entities' levels, what waits on people, the milestones and the
        version applied."""
        from ontlas.answer import rule_owner
        from ontlas.preview import MODULE_KIND
        from ontlas.review import gates as flow_gates
        from ontlas.review import tally
        from ontlas.web.api import KIND_ORDER, LEVEL_LABEL

        st, o = self.studio, self.studio.onto
        comp = st.composition
        levels = self._entity_levels()
        spread = [sum(1 for v in levels.values() if v == i) for i in range(4)]
        objects = [self._object_row(a.name, a.label or a.name, [t.name for t in o.objects.values() if t.area == a.name], levels,
                                    description=a.description, tier=str(getattr(a, "tier", "") or ""))
                   for a in o.areas.values()]
        loose = [t.name for t in o.objects.values() if t.area not in o.areas]
        if loose:  # Entities filed under no Object
            objects.append(self._object_row("", "미분류", loose, levels, description="", tier=""))
        measured = self._measured or {}
        current = bool(measured) and self._measured_of is o
        bind = measured.get("bind") if current else None

        # semantic rules: decision tables and their rules by the kind of module that wrote them
        kinds = {m.name: m.kind for m in comp.modules} if comp else {}
        by_kind: dict[str, list[int]] = {}
        for d in o.decisions.values():
            by_kind.setdefault(kinds.get(comp.owner(f"decision:{d.name}"), "") if comp else "", [0, 0])[0] += 1
            for r in d.rules:
                by_kind.setdefault(kinds.get(rule_owner(comp, d.name, r.id), "") if comp else "", [0, 0])[1] += 1
        uncited = sum(1 for d in o.decisions.values() for r in d.rules if not (r.cite or d.cite))
        rules = sum(len(d.rules) for d in o.decisions.values())
        semantic = {"id": "semantic", "title": "시맨틱 규칙", "part": "Semantic layer",
                    "counts": {"decisions": len(o.decisions), "rules": rules, "uncited": uncited, "parameters": len(o.parameters),
                               "functions": len(o.functions), "metrics": len(o.metrics)},
                    "by_kind": [{"kind": k, "kind_label": MODULE_KIND.get(k, k) or "정의", "decisions": v[0], "rules": v[1]}
                                for k, v in sorted(by_kind.items(), key=lambda x: KIND_ORDER.index(x[0]) if x[0] in KIND_ORDER else 99)],
                    **self._status("empty" if not o.decisions else "attention" if uncited else "ok",
                                   "정의 전" if not o.decisions else "근거 보완" if uncited else "정의됨")}

        # the ontology: Objects, Entities, relations, properties
        unfiled = len(loose) if o.areas else 0
        ontology = {"id": "ontology", "title": "온톨로지", "part": "Ontology manager",
                    "counts": {"objects": len(o.areas), "entities": len(o.objects), "relations": len(o.links),
                               "properties": sum(len(t.properties) for t in o.objects.values()), "unfiled": unfiled,
                               "definition_only": spread[0]},
                    # an Entity that is a name only (L0) is what is left to define; the unfiled are shown, not held against it
                    **self._status("empty" if not o.objects else "attention" if spread[0] else "ok",
                                   "정의 전" if not o.objects else "보완 필요" if spread[0] else "정의됨")}

        # data binding: what is bound to the source, and how the last check of it went
        bound = [t for t in o.objects.values() if t.table]
        tables = {t.table for t in bound} | {lk.via.table for lk in o.links.values() if lk.via}
        info = st.source_info()
        if not info["connected"]:
            state = ("unmeasured", "원천 미연결") if bound else ("empty", "연결 전")
        elif not bound:
            state = ("empty", "연결 전")
        elif bind is None:
            state = ("unmeasured", "대조 전")
        elif bind.get("errors"):
            state = ("attention", "대조 오류")
        elif bind.get("warnings"):
            state = ("attention", "대조 경고")
        else:
            state = ("ok", "연결됨")
        binding = {"id": "binding", "title": "데이터 바인딩", "part": "Data binder",
                   "counts": {"entities": len(o.objects), "bound": len(bound), "tables": len(tables)}, "source": info,
                   "check": {"errors": bind.get("errors", 0), "warnings": bind.get("warnings", 0)} if bind else None,
                   **self._status(*state)}

        # QA: the validation questions and the pass conditions, as the last measurement found them
        check = measured.get("check") or {}
        met = tally(flow_gates(measured, st.flow)) if measured else None
        if not measured:
            state = ("unmeasured", "미측정")
        elif not current:
            state = ("unmeasured", "다시 측정 필요")
        elif not met["all"]:
            state = ("unmeasured", "측정 대상 아님")
        elif met["met"] < met["all"]:
            state = ("attention", "미달")
        else:
            state = ("ok", "통과")
        asked = len(o.questions) - len(check.get("unasked") or []) if check else 0
        qa = {"id": "qa", "title": "QA", "part": "QA",
              "counts": {"questions": len(o.questions), "measured": asked, "failed": len(check.get("failed") or [])},
              "accuracy": check.get("accuracy"), "grounded": check.get("grounded"), "gates": met,
              "measured": current, "stale": bool(measured) and not current, **self._status(*state)}

        box = self.inbox()
        kinds_waiting: dict[str, int] = {}
        for x in box["items"]:
            kinds_waiting[x["kind"]] = kinds_waiting.get(x["kind"], 0) + 1
        version = self._space_version()
        return plain({
            "maturity": {"levels": [{"level": i, "label": LEVEL_LABEL[i], "entities": spread[i]} for i in range(4)],
                         "entities": len(o.objects), "objects": len(o.areas), "checked": bind is not None},
            "components": [semantic, ontology, binding, qa],
            "objects": objects,
            "todo": {**box["counts"], "kinds": kinds_waiting},
            "milestones": self._milestones(),
            "version": {k: version[k] for k in ("number", "label", "key", "change", "at")},
        })

    @staticmethod
    def _status(status: str, word: str) -> dict:
        return {"status": status, "status_label": word}
