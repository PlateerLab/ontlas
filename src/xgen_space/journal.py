"""What has to outlive the process: requests, approvals and the audit trail, one JSON line each.

The source database keeps what an action wrote. Without this file a restart forgets who asked for it, who approved it,
what it replaced and what was still waiting, so it could not be rolled back or answered for.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Iterator


class Journal:
    """An append-only file. A line is never rewritten: a later line about the same request says how it stands now."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def write(self, kind: str, record: dict[str, Any]) -> None:
        line = json.dumps({"kind": kind, **record}, ensure_ascii=False, default=str)
        with self.lock, self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    def read(self) -> Iterator[dict[str, Any]]:
        if not self.path.is_file():
            return
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except ValueError:  # a line cut off by a crash mid-write: the ones before it still count
                    continue


def next_number(ids: list[str], prefix: str) -> int:
    """The number after the highest id kept, so a new request never takes an old one's id."""
    nums = [int(i[len(prefix):]) for i in ids if i.startswith(prefix) and i[len(prefix):].isdigit()]
    return max(nums, default=0) + 1
