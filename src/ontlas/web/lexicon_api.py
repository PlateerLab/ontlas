"""The lexicon screen: the terms the definition goes by, edited and brought in from a glossary like any other edit of the
management screens (one workspace module, one undo history, one change request)."""
from __future__ import annotations

from typing import Any

TERM_OPS = ("add_term", "update_term", "delete_term")


class LexiconMixin:
    def _lexicon_now(self):
        """The workspace and what its pending edits compose to; the applied studio when they no longer hold."""
        from ontlas.modules import ModuleError

        ws = self._ws()
        try:
            return ws, ws.composed(), []
        except ModuleError as e:
            return ws, self.studio.composition, [str(e)]

    def lexicon_state(self) -> dict:
        """Every term with its labels, the definition it names, where it comes from and what reads it; how much the
        lexicon holds; and what it says two ways. New and changed are against the lexicon the studio runs with."""
        from ontlas.lexicon import concepts, view
        from ontlas.web.api import WORKSPACE, plain

        ws, comp, issues = self._lexicon_now()
        mine = ws.module
        applied = self.studio.composition
        out = view(comp.terms, comp.ontology, origin=comp.term_origin, applied=list(applied.terms) if applied else [],
                   module_label=lambda m: mine.label if m == WORKSPACE else self._label(m), readers=self._readers)
        return plain({**out, "concepts": concepts(comp.ontology),
                      "workspace": {"dirty": ws.dirty, "module": WORKSPACE, "label": mine.label, "issues": issues,
                                    "edits": [{"op": e.op, "target": e.target, "took_out": e.took_out} for e in ws.edits],
                                    "redo": len(ws._undone)}})

    def lexicon_edit(self, op: str, args: dict) -> dict:
        """One term added, changed or taken out, into the workspace module."""
        from ontlas.manage import EditError
        from ontlas.web.api import _edit_text

        if op not in TERM_OPS:
            raise ValueError(f"용어 편집({op})이 아니어서 적용하지 못했습니다. 용어 추가 · 수정 · 삭제만 보낼 수 있습니다.")
        try:
            edit = self._ws().apply(op, dict(args or {}))
        except EditError as e:
            raise ValueError(_edit_text(str(e))) from None
        return {"ok": True, "edit": {"op": edit.op, "target": edit.target, "took_out": edit.took_out}, **self.lexicon_state()}

    def lexicon_import(self, text: str = "", name: str = "", path: str = "") -> dict:
        """A glossary (CSV, XLSX, YAML or JSON) brought into the workspace as terms, as one edit: given as text, or as a
        file of the catalog. The report says what became synonyms, related or confusable terms and what conflicts."""
        from ontlas.lexicon import merge, read_glossary
        from ontlas.manage import EditError
        from ontlas.repository import clean_path
        from ontlas.web.api import _edit_text

        if path:
            path = clean_path(path)
            data: Any = self.repositories.read(self.repo, path)
            name = name or path.rsplit("/", 1)[-1]
        elif text:
            data = text.encode("utf-8")
        else:
            raise ValueError("용어 파일이 없어 불러오지 못했습니다. 파일 내용이나 카탈로그의 파일 경로를 보내 주세요.")
        glossary = read_glossary(data, name or "glossary.csv")
        ws, comp, _ = self._lexicon_now()
        entries, report = merge(glossary, comp.terms, comp.ontology, source=name)
        edit = None
        if entries:
            try:
                edit = ws.apply("import_terms", {"terms": entries, "source": name or "glossary"})
            except EditError as e:
                raise ValueError(_edit_text(str(e))) from None
        return {"ok": True, "report": report,
                "edit": {"op": edit.op, "target": edit.target, "took_out": edit.took_out} if edit else None,
                **self.lexicon_state()}


__all__ = ["LexiconMixin", "TERM_OPS"]
