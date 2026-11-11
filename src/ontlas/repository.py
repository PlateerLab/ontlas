"""Repositories: the raw files a person brings in, kept by folder, with what each one turned out to be.

A path here is a name in an index, never a path on disk: the bytes are stored under their SHA-256, so nothing a visitor
types reaches the file system, and two copies of a file cost one. Given a folder, the repositories are kept there and
outlive the server. Without one they live in a temporary directory that goes when the object does.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path

PART_MAX = 120
PATH_MAX = 400
DEPTH_MAX = 12
LABEL_MAX = 40
INDEX = "index.json"
DEFAULT_LABEL = "기본 레포지토리"
LITTER_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}  # what an operating system leaves in a folder
LITTER_FOLDERS = {"__macosx", ".git", ".svn"}
TRASH_MAX = 200  # items a repository's trash keeps; past it the oldest goes for good
LOG_MAX = 300  # entries of a repository's work record


def clean_path(path: str) -> str:
    """'a/b/c' from what a browser or a person sent; ValueError when it cannot name a place in a repository."""
    parts = [p.strip() for p in str(path).replace("\\", "/").split("/") if p.strip()]
    bad = next((p for p in parts if p in (".", "..") or any(ord(c) < 32 for c in p)), None)
    if bad is not None:
        raise ValueError("경로에 사용할 수 없는 이름이 있어 처리하지 못했습니다. 폴더와 파일 이름을 확인해 주세요.")
    if len(parts) > DEPTH_MAX or any(len(p) > PART_MAX for p in parts) or len("/".join(parts)) > PATH_MAX:
        raise ValueError(f"경로가 깊이 {DEPTH_MAX}단계 또는 이름 {PART_MAX}자 한도를 초과해 처리하지 못했습니다. "
                         "폴더 구조를 줄여 다시 시도해 주세요.")
    return "/".join(parts)


def parent(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def is_litter(path: str) -> bool:
    """A file nobody means to bring in: .DS_Store, Thumbs.db, a Mac archive's metadata."""
    parts = path.lower().split("/")
    return parts[-1] in LITTER_NAMES or parts[-1].startswith("._") or any(p in LITTER_FOLDERS for p in parts[:-1])


def _under(path: str, folder: str) -> bool:
    return not folder or path == folder or path.startswith(folder + "/")


def _moved(path: str, old: str, new: str) -> str:
    return new + path[len(old):]


class Repositories:
    """Every repository of a server (or of one visitor): files and folders by path, their bytes by hash."""

    def __init__(self, root: str | Path | None = None):
        self.persistent = root is not None
        self.lock = threading.RLock()
        self._tmp: tempfile.TemporaryDirectory | None = None
        self._root = Path(root) if root is not None else None
        self.items: dict[str, dict] = {}
        if self._root is not None and (self._root / INDEX).is_file():
            self.items = json.loads((self._root / INDEX).read_text(encoding="utf-8"))
        if not self.items:
            self.create(DEFAULT_LABEL)

    # ---- storage ---------------------------------------------------------------------------------------------

    @property
    def root(self) -> Path:
        if self._root is None:  # made on the first file: most visitors never bring one
            self._tmp = tempfile.TemporaryDirectory(prefix="ontlas-", ignore_cleanup_errors=True)
            self._root = Path(self._tmp.name)
        return self._root

    def _blob(self, sha: str) -> Path:
        return self.root / "blobs" / sha

    def _save(self) -> None:
        if not self.persistent:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.root / (INDEX + ".tmp")
        tmp.write_text(json.dumps(self.items, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.root / INDEX)

    def _forget(self, shas: set[str]) -> None:
        """Remove the bytes no file refers to any more, in a repository or in its trash."""
        used = {f["sha256"] for r in self.items.values() for f in [*r["files"].values(), *_trashed(r)]}
        for sha in shas - used:
            self._blob(sha).unlink(missing_ok=True)

    @staticmethod
    def _log(r: dict, action: str, path: str, detail: str = "") -> None:
        r.setdefault("log", []).insert(0, {"at": _now(), "action": action, "path": path, "detail": detail})
        del r["log"][LOG_MAX:]

    # ---- repositories ----------------------------------------------------------------------------------------

    def _repo(self, repo: str) -> dict:
        if repo not in self.items:
            raise LookupError(f"레포지토리 {repo}")
        return self.items[repo]

    def create(self, label: str) -> str:
        label = str(label).strip()[:LABEL_MAX]
        if not label:
            raise ValueError("이름이 없어 레포지토리를 만들지 못했습니다. 이름을 입력해 주세요.")
        with self.lock:
            if any(r["label"] == label for r in self.items.values()):
                raise ValueError(f"{label}: 같은 이름의 레포지토리가 있어 만들지 못했습니다. 다른 이름을 입력해 주세요.")
            n = 1 + max([int(k[1:]) for k in self.items], default=0)
            self.items[f"r{n}"] = {"label": label, "created": _now(), "folders": [], "files": {}}
            self._save()
            return f"r{n}"

    def rename_repo(self, repo: str, label: str) -> None:
        label = str(label).strip()[:LABEL_MAX]
        with self.lock:
            r = self._repo(repo)
            if not label:
                raise ValueError("이름이 없어 레포지토리 이름을 바꾸지 못했습니다. 이름을 입력해 주세요.")
            if any(x is not r and x["label"] == label for x in self.items.values()):
                raise ValueError(f"{label}: 같은 이름의 레포지토리가 있어 바꾸지 못했습니다. 다른 이름을 입력해 주세요.")
            r["label"] = label
            self._save()

    def delete_repo(self, repo: str) -> None:
        with self.lock:
            r = self._repo(repo)
            if len(self.items) == 1:
                raise ValueError("마지막 레포지토리여서 삭제하지 못했습니다. 다른 레포지토리를 만든 뒤 삭제해 주세요.")
            shas = {f["sha256"] for f in [*r["files"].values(), *_trashed(r)]}
            del self.items[repo]
            self._forget(shas)
            self._save()

    def rows(self) -> list[dict]:
        with self.lock:
            return [{"id": k, "label": r["label"], "files": len(r["files"]),
                     "bytes": sum(f["bytes"] for f in r["files"].values())} for k, r in self.items.items()]

    def usage(self) -> tuple[int, int]:
        """Files and bytes across every repository, the trash with them: what is in it is still kept."""
        with self.lock:
            kept = [f for r in self.items.values() for f in [*r["files"].values(), *_trashed(r)]]
        return len(kept), sum(f["bytes"] for f in kept)

    # ---- files and folders -----------------------------------------------------------------------------------

    def files(self, repo: str) -> dict[str, dict]:
        with self.lock:
            return dict(self._repo(repo)["files"])

    def entry(self, repo: str, path: str) -> dict:
        with self.lock:
            f = self._repo(repo)["files"].get(path)
        if f is None:
            raise LookupError(f"파일 {path}")
        return f

    def read(self, repo: str, path: str) -> bytes:
        return self._blob(self.entry(repo, path)["sha256"]).read_bytes()

    def _make_parents(self, r: dict, path: str) -> None:
        while path:
            if path in r["files"]:
                raise ValueError(f"{path}: 같은 이름의 파일이 있어 폴더를 만들지 못했습니다. 다른 이름을 입력해 주세요.")
            if path not in r["folders"]:
                r["folders"].append(path)
            path = parent(path)

    def put(self, repo: str, path: str, data: bytes, **facts) -> dict:
        """Keep a file, replacing what was at its path; `facts` says what it turned out to be."""
        sha = hashlib.sha256(data).hexdigest()
        with self.lock:
            r = self._repo(repo)
            if path in r["folders"]:
                raise ValueError(f"{path}: 같은 이름의 폴더가 있어 업로드하지 못했습니다. 파일 이름을 바꿔 다시 업로드해 주세요.")
            self._make_parents(r, parent(path))
            blob = self._blob(sha)
            if not blob.exists():
                blob.parent.mkdir(parents=True, exist_ok=True)
                blob.write_bytes(data)
            before = r["files"].get(path)
            r["files"][path] = {"sha256": sha, "bytes": len(data), "uploaded": _now(),
                                "included": before["included"] if before else True,
                                "embed": before.get("embed", True) if before else True,
                                "use": before.get("use", "") if before else "", **facts}
            if before and before["sha256"] != sha:
                self._forget({before["sha256"]})
            self._log(r, "replace" if before else "upload", path, f"{len(data):,}바이트")
            self._save()
            return r["files"][path]

    def folder(self, repo: str, path: str) -> None:
        with self.lock:
            r = self._repo(repo)
            if path in r["folders"]:
                raise ValueError(f"{path}: 같은 이름의 폴더가 있어 만들지 못했습니다. 다른 이름을 입력해 주세요.")
            self._make_parents(r, path)
            self._log(r, "folder", path)
            self._save()

    def remove(self, repo: str, paths: list[str]) -> list[str]:
        """Move files and folders, what is in a folder with it, to the trash; the paths of the files that went."""
        with self.lock:
            r = self._repo(repo)
            tops = sorted({x for x in paths if x}, key=len)
            tops = [x for i, x in enumerate(tops) if not any(_under(x, y) for y in tops[:i])]  # a/b goes with a
            trash = r.setdefault("trash", [])
            gone = []
            for x in tops:
                files = {p: r["files"].pop(p) for p in [p for p in r["files"] if _under(p, x)]}
                folders = [f for f in r["folders"] if _under(f, x)]
                if not files and not folders:
                    continue
                r["folders"] = [f for f in r["folders"] if f not in folders]
                n = 1 + max([int(t["id"][1:]) for t in trash], default=0)
                trash.insert(0, {"id": f"t{n}", "path": x, "kind": "folder" if x in folders else "file", "at": _now(),
                                 "files": files, "folders": folders})
                self._log(r, "trash", x, f"파일 {len(files)}개")
                gone += files
            old = trash[TRASH_MAX:]
            del trash[TRASH_MAX:]
            self._forget({f["sha256"] for t in old for f in t["files"].values()})
            self._save()
            return gone

    def trash(self, repo: str) -> list[dict]:
        with self.lock:
            return [{"id": t["id"], "path": t["path"], "name": t["path"].rsplit("/", 1)[-1], "kind": t["kind"], "at": t["at"],
                     "files": len(t["files"]), "bytes": sum(f["bytes"] for f in t["files"].values())}
                    for t in self._repo(repo).get("trash", [])]

    def restore(self, repo: str, ids: list[str]) -> list[str]:
        """Put trashed items back where they were, all of them or none when a name is taken; the paths of the files
        that came back."""
        with self.lock:
            r = self._repo(repo)
            picked = [t for t in r.get("trash", []) if t["id"] in ids]
            files, folders = set(r["files"]), set(r["folders"])
            for t in picked:
                taken = [p for p in t["files"] if p in files or p in folders] + [f for f in t["folders"] if f in files]
                if taken:
                    raise ValueError(f"{taken[0]}: 같은 이름이 있어 복원하지 못했습니다. 그 자리의 이름을 바꾼 뒤 복원해 주세요.")
                files |= set(t["files"])
                folders |= set(t["folders"])
            back = []
            for t in picked:
                self._make_parents(r, parent(t["path"]))
                r["folders"] += [f for f in t["folders"] if f not in r["folders"]]
                r["files"].update(t["files"])
                r["trash"].remove(t)
                self._log(r, "restore", t["path"], f"파일 {len(t['files'])}개")
                back += t["files"]
            self._save()
            return back

    def purge(self, repo: str, ids: list[str] | None = None) -> int:
        """Delete trashed items for good, all of them without `ids`; how many went."""
        with self.lock:
            r = self._repo(repo)
            out = [t for t in r.get("trash", []) if ids is None or t["id"] in ids]
            r["trash"] = [t for t in r.get("trash", []) if t not in out]
            for t in out:
                self._log(r, "purge", t["path"], f"파일 {len(t['files'])}개")
            self._forget({f["sha256"] for t in out for f in t["files"].values()})
            self._save()
            return len(out)

    def history(self, repo: str) -> list[dict]:
        with self.lock:
            return list(self._repo(repo).get("log", []))

    def move(self, repo: str, path: str, to: str) -> None:
        """Rename a file or a folder, with what is in the folder."""
        with self.lock:
            r = self._repo(repo)
            if path not in r["files"] and path not in r["folders"]:
                raise LookupError(f"경로 {path}")
            if to in r["files"] or to in r["folders"]:
                raise ValueError(f"{to}: 같은 이름이 있어 바꾸지 못했습니다. 다른 이름을 입력해 주세요.")
            if _under(to, path):
                raise ValueError(f"{to}: 폴더를 그 안의 폴더로 옮길 수 없어 처리하지 못했습니다. 다른 위치를 선택해 주세요.")
            r["files"] = {(_moved(p, path, to) if _under(p, path) else p): f for p, f in r["files"].items()}
            r["folders"] = [(_moved(f, path, to) if _under(f, path) else f) for f in r["folders"]]
            self._make_parents(r, parent(to))
            self._log(r, "rename" if parent(to) == parent(path) else "move", path, to)
            self._save()

    def include(self, repo: str, paths: list[str], on: bool) -> None:
        """Set whether files, or everything in folders, go into a draft."""
        with self.lock:
            r = self._repo(repo)
            for p, f in r["files"].items():
                if any(_under(p, x) for x in paths):
                    f["included"] = on
            for x in paths:
                self._log(r, "include" if on else "exclude", x)
            self._save()

    def set_use(self, repo: str, path: str, use: str) -> dict:
        """What a file is read as, when a person says so: data (rows), definition, document or raw; '' goes back to
        what its content says."""
        with self.lock:
            r = self._repo(repo)
            f = r["files"].get(path)
            if f is None:
                raise KeyError(path)
            f["use"] = use
            self._log(r, "use", path, use or "auto")
            self._save()
            return f

    def embed(self, repo: str, paths: list[str], on: bool) -> None:
        """Set whether the documents of files, or of everything in folders, are embedded into the vector stores."""
        with self.lock:
            r = self._repo(repo)
            for p, f in r["files"].items():
                if any(_under(p, x) for x in paths):
                    f["embed"] = on
            for x in paths:
                self._log(r, "embed" if on else "unembed", x)
            self._save()

    def listing(self, repo: str, folder: str = "") -> tuple[list[dict], list[dict]]:
        """What a folder shows: its folders with what they hold, and its files."""
        with self.lock:
            r = self._repo(repo)
            if folder and folder not in r["folders"]:
                raise LookupError(f"폴더 {folder}")
            folders = []
            for p in sorted(f for f in r["folders"] if parent(f) == folder):
                inside = [f for k, f in r["files"].items() if _under(k, p)]
                folders.append({"path": p, "name": p.rsplit("/", 1)[-1], "files": len(inside),
                                "bytes": sum(f["bytes"] for f in inside),
                                "included": sum(bool(f["included"]) for f in inside),
                                "embedded": sum(f.get("embed", True) is not False for f in inside)})
            files = [{"path": k, "name": k.rsplit("/", 1)[-1], **f, "embed": f.get("embed", True) is not False}
                     for k, f in sorted(r["files"].items()) if parent(k) == folder]
            return folders, files


def _trashed(r: dict) -> list[dict]:
    return [f for t in r.get("trash", []) for f in t["files"].values()]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
