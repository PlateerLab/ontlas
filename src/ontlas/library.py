"""Ontology library: every domain package (commerce, logistics, energy, ...) kept apart, versioned, composable."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ontlas.modules import KINDS, SECTIONS, SINGULAR, Module, ModuleError, Requirement, version_key

APPLIED = "applied.yaml"  # beside the modules, written by a studio that keeps what was switched on and off


class Library:
    """A folder of modules laid out as <root>/<name>/<version>.yaml (or .json); the newest version is the default."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _files(self, name: str) -> dict[str, Path]:
        d = self.root / name
        if not d.is_dir():
            return {}
        return {p.stem: p for p in d.iterdir() if p.suffix.lower() in (".yaml", ".yml", ".json")}

    def names(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if p.is_dir() and self._files(p.name))

    def versions(self, name: str) -> list[str]:
        return sorted(self._files(name), key=version_key)

    def get(self, name: str, version: str = "") -> Module:
        files = self._files(name)
        if not files:
            raise ModuleError(f"no module '{name}' in {self.root}")
        if not version:
            version = self.versions(name)[-1]
        if version not in files:
            raise ModuleError(f"module '{name}' has no version {version}; it has {self.versions(name)}")
        return Module.load(files[version])

    def list(self) -> list[dict[str, Any]]:
        rows = []
        for n in self.names():
            m = self.get(n)
            rows.append({"name": n, "label": m.label, "kind": m.kind, "latest": m.version,
                         "versions": self.versions(n), "requires": [str(r) for r in m.requires],
                         "counts": m.counts(), "description": m.description})
        return rows

    def save(self, module: Module, *, overwrite: bool = False, fmt: str = "yaml") -> Path:
        if module.kind not in KINDS:
            raise ModuleError(f"kind must be one of {KINDS}")
        path = self.root / module.name / f"{module.version}.{fmt}"
        if path.exists() and not overwrite:
            raise ModuleError(f"{module.key} already exists; raise the version or pass overwrite=True")
        module.dump(path)
        return path

    def create(self, name: str, *, kind: str = "domain", label: str = "", description: str = "",
               namespace: str = "", requires: list[str] = (), version: str = "0.1.0") -> Module:
        if self._files(name):
            raise ModuleError(f"module '{name}' already exists")
        m = Module(name=name, version=version, kind=kind, label=label, description=description, namespace=namespace,
                   requires=[Requirement.parse(r) for r in requires],
                   body={**{s: {} for s in SECTIONS}, "questions": [], "exclusive": []})
        self.save(m)
        return m

    def delete(self, name: str, version: str = "") -> None:
        files = self._files(name)
        if not files:
            raise ModuleError(f"no module '{name}'")
        for other in self.names():
            if other == name:
                continue
            for r in self.get(other).requires:
                if r.name == name and (not version or len(files) == 1):
                    raise ModuleError(f"{other} requires {name}; delete or change it first")
        if version:
            files[version].unlink()
            if not self._files(name):
                shutil.rmtree(self.root / name)
        else:
            shutil.rmtree(self.root / name)

    def keep_applied(self, names: list[str]) -> None:
        """The modules a running studio has on, for its next start."""
        import yaml

        (self.root / APPLIED).write_text(yaml.safe_dump({"modules": list(names)}, allow_unicode=True), encoding="utf-8")

    def applied(self) -> list[str]:
        import yaml

        p = self.root / APPLIED
        return list((yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("modules") or []) if p.is_file() else []

    def resolve(self, wanted: list[str]) -> list[Module]:
        """Pick a module for each requirement, pulling in what those require, newest allowed version first."""
        chosen: dict[str, Module] = {}
        todo = [Requirement.parse(w) for w in wanted]
        while todo:
            r = todo.pop(0)
            if r.name in chosen:
                if not r.allows(chosen[r.name].version):
                    raise ModuleError(f"'{r}' conflicts with {chosen[r.name].key} already chosen")
                continue
            ok = [v for v in self.versions(r.name) if r.allows(v)]
            if not ok:
                raise ModuleError(f"no version of '{r.name}' satisfies '{r}'; have {self.versions(r.name)}")
            m = self.get(r.name, ok[-1])
            chosen[r.name] = m
            todo += m.requires
        return list(chosen.values())

    def diff(self, name: str, a: str, b: str) -> dict[str, list[str]]:
        ma, mb = self.get(name, a), self.get(name, b)

        def flat(m: Module) -> dict[str, str]:
            out = {}
            for s in SECTIONS:
                for k, v in (m.body.get(s) or {}).items():
                    out[f"{SINGULAR[s]}:{k}"] = json.dumps(v, sort_keys=True, ensure_ascii=False)
            for s, items in (m.extend or {}).items():
                for k, v in (items or {}).items():
                    out[f"extend {SINGULAR.get(s, s)}:{k}"] = json.dumps(v, sort_keys=True, ensure_ascii=False)
            for q in m.body.get("questions") or []:
                out[f"question:{q['id']}"] = json.dumps(q, sort_keys=True, ensure_ascii=False)
            return out

        fa, fb = flat(ma), flat(mb)
        return {"added": sorted(fb.keys() - fa.keys()), "removed": sorted(fa.keys() - fb.keys()),
                "changed": sorted(k for k in fa.keys() & fb.keys() if fa[k] != fb[k])}

    def import_owl(self, text: str, name: str, *, kind: str = "domain", label: str = "", version: str = "0.1.0",
                   namespace: str = "", requires: list[str] = (), fmt: str = "turtle") -> tuple[Module, Any]:
        """A standard vocabulary (schema.org, GS1 ...) as a new module, its source IRIs kept as alignments."""
        from ontlas.exchange.importer import from_owl

        onto, report = from_owl(text, namespace=namespace, fmt=fmt, name=name)
        d = onto.to_dict()
        body = {s: d.get(s, {}) for s in SECTIONS}
        body["questions"], body["exclusive"] = [], []
        m = Module(name=name, version=version, kind=kind, label=label or onto.label or name, namespace=onto.namespace,
                   requires=[Requirement.parse(r) for r in requires], body=body)
        self.save(m)
        return m, report


class OverlayLibrary(Library):
    """Modules held in memory over a library folder (or over nothing), e.g. a draft that has not been saved. The
    folder is never written: a module saved here is kept in memory, as the newest version of its name."""

    def __init__(self, base: Library | None, modules: list[Module]):
        self.base = base
        self.root = base.root if base is not None else Path(".")
        self.extra = {m.name: m for m in modules}
        self.held: dict[str, dict[str, Module]] = {}  # earlier in-memory versions, by name

    def names(self) -> list[str]:
        return sorted(set(self.base.names() if self.base is not None else []) | set(self.extra))

    def versions(self, name: str) -> list[str]:
        below = self.base.versions(name) if self.base is not None else []
        mine = [*self.held.get(name, {}), *([self.extra[name].version] if name in self.extra else [])]
        return sorted(set(below) | set(mine), key=version_key)

    def get(self, name: str, version: str = "") -> Module:
        m = self.extra.get(name)
        if m is not None and (not version or version == m.version):
            return m
        if version and version in self.held.get(name, {}):
            return self.held[name][version]
        if self.base is None or not self.base.versions(name):
            if m is not None:
                raise ModuleError(f"module '{name}' has no version {version}; it has {self.versions(name)}")
            raise ModuleError(f"no module '{name}'")
        return self.base.get(name, version)

    def save(self, module: Module, *, overwrite: bool = False, fmt: str = "yaml") -> Path:
        if module.version in self.versions(module.name) and not overwrite:
            raise ModuleError(f"{module.key} already exists; raise the version or pass overwrite=True")
        prev = self.extra.get(module.name)
        if prev is not None and prev.version != module.version:
            self.held.setdefault(module.name, {})[prev.version] = prev
        self.extra[module.name] = module
        return self.root / module.name / f"{module.version}.{fmt}"

    def delete(self, name: str, version: str = "") -> None:
        raise ModuleError("modules held in memory are not deleted from here")
