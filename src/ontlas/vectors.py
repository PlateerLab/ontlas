"""Vector store port: the same few calls on any store, and a test that they give the same answers.

This is the graph side's bargain on the vector side. A store says what it can do, implements `ensure`, `upsert`, `search`,
`count` and `delete`, and joins the supported list by agreeing with the exact in-memory search in `conformance`.
"""
from __future__ import annotations

import json
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

NAME_SPACE = uuid.UUID("6f1c9c1e-6d0e-4f6a-9a53-5c7f0f1b2a11")


class VectorError(RuntimeError):
    """The store refused or could not be reached. The message never carries a key or a password."""


@dataclass
class Point:
    id: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Hit:
    id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorCapabilities:
    metric: str = "cosine"
    filter: bool = True
    persistent: bool = False
    exact: bool = True  # False: approximate search, so conformance allows a small difference in the last places

    def to_dict(self) -> dict:
        return asdict(self)


class VectorStore:
    kind = ""
    name = ""
    capabilities = VectorCapabilities()

    def ensure(self, collection: str, dim: int) -> None:
        raise NotImplementedError

    def upsert(self, collection: str, points: list[Point]) -> int:
        raise NotImplementedError

    def search(self, collection: str, vector: list[float], k: int = 5, where: dict | None = None) -> list[Hit]:
        raise NotImplementedError

    def count(self, collection: str) -> int:
        raise NotImplementedError

    def delete(self, collection: str, ids: list[str]) -> int:
        raise NotImplementedError

    def drop(self, collection: str) -> None:
        raise NotImplementedError

    def collections(self) -> list[str]:
        raise NotImplementedError

    def describe(self) -> dict:
        return {"kind": self.kind, "name": self.name, **self.capabilities.to_dict()}


def _matches(payload: dict, where: dict | None) -> bool:
    for k, want in (where or {}).items():
        have = payload.get(k)
        if isinstance(want, (list, tuple, set)):
            if have not in want:
                return False
        elif have != want:
            return False
    return True


class MemoryStore(VectorStore):
    """Exact cosine search in this process. The reference every other store is held against."""

    kind = "memory"

    def __init__(self, name: str = "memory"):
        self.name = name
        self.capabilities = VectorCapabilities()
        self.data: dict[str, dict[str, Point]] = {}
        self.dims: dict[str, int] = {}
        self.lock = threading.Lock()

    def ensure(self, collection: str, dim: int) -> None:
        with self.lock:
            if self.dims.get(collection, dim) != dim:
                raise VectorError(f"collection '{collection}' holds {self.dims[collection]} dimensions, not {dim}")
            self.dims[collection] = dim
            self.data.setdefault(collection, {})

    def upsert(self, collection: str, points: list[Point]) -> int:
        with self.lock:
            into = self.data.setdefault(collection, {})
            for p in points:
                into[p.id] = p
        return len(points)

    def search(self, collection: str, vector: list[float], k: int = 5, where: dict | None = None) -> list[Hit]:
        with self.lock:
            points = list(self.data.get(collection, {}).values())
        scored = [(sum(a * b for a, b in zip(vector, p.vector)), p) for p in points if _matches(p.payload, where)]
        scored.sort(key=lambda x: (-x[0], x[1].id))
        return [Hit(p.id, s, dict(p.payload)) for s, p in scored[:k]]

    def count(self, collection: str) -> int:
        return len(self.data.get(collection, {}))

    def delete(self, collection: str, ids: list[str]) -> int:
        with self.lock:
            into = self.data.get(collection, {})
            return sum(into.pop(i, None) is not None for i in ids)

    def drop(self, collection: str) -> None:
        with self.lock:
            self.data.pop(collection, None)
            self.dims.pop(collection, None)

    def collections(self) -> list[str]:
        return sorted(self.data)


class QdrantStore(VectorStore):
    """Qdrant over its REST API, so no client library is needed. Its point ids must be numbers or UUIDs: ours ride in the
    payload and the UUID is made from them."""

    kind = "qdrant"

    def __init__(self, url: str, *, key: str = "", key_env: str = "", prefix: str = "", timeout: float = 15.0, name: str = "qdrant"):
        self.url = url.rstrip("/")
        self.key = key or (os.environ.get(key_env, "") if key_env else "")
        self.prefix, self.timeout, self.name = prefix, timeout, name
        self.capabilities = VectorCapabilities(persistent=True, exact=False)

    def _full(self, collection: str) -> str:
        return urllib.parse.quote(self.prefix + collection, safe="")

    def _call(self, method: str, path: str, body: Any = None, ok: tuple = ()) -> dict:
        req = urllib.request.Request(self.url + path, method=method,
                                     data=None if body is None else json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        if self.key:
            req.add_header("api-key", self.key)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            if e.code in ok:
                return {}
            raise VectorError(f"Qdrant answered {e.code} on {path.split('?')[0]}") from None
        except OSError:
            raise VectorError("Qdrant did not answer") from None

    def ensure(self, collection: str, dim: int) -> None:
        have = self._call("GET", f"/collections/{self._full(collection)}", ok=(404,))
        if have:
            size = (((have.get("result") or {}).get("config") or {}).get("params") or {}).get("vectors", {}).get("size")
            if size and size != dim:
                raise VectorError(f"collection '{collection}' holds {size} dimensions, not {dim}")
            return
        self._call("PUT", f"/collections/{self._full(collection)}", {"vectors": {"size": dim, "distance": "Cosine"}})

    def upsert(self, collection: str, points: list[Point]) -> int:
        for i in range(0, len(points), 256):
            batch = [{"id": str(uuid.uuid5(NAME_SPACE, p.id)), "vector": p.vector, "payload": {**p.payload, "_id": p.id}}
                     for p in points[i:i + 256]]
            self._call("PUT", f"/collections/{self._full(collection)}/points?wait=true", {"points": batch})
        return len(points)

    @staticmethod
    def _filter(where: dict | None) -> dict | None:
        if not where:
            return None
        must = [{"key": k, "match": {"any": list(v)} if isinstance(v, (list, tuple, set)) else {"value": v}}
                for k, v in where.items()]
        return {"must": must}

    def search(self, collection: str, vector: list[float], k: int = 5, where: dict | None = None) -> list[Hit]:
        body: dict[str, Any] = {"vector": vector, "limit": k, "with_payload": True}
        flt = self._filter(where)
        if flt:
            body["filter"] = flt
        found = self._call("POST", f"/collections/{self._full(collection)}/points/search", body).get("result") or []
        out = []
        for r in found:
            payload = dict(r.get("payload") or {})
            out.append(Hit(str(payload.pop("_id", r.get("id"))), float(r.get("score", 0.0)), payload))
        return out

    def count(self, collection: str) -> int:
        r = self._call("POST", f"/collections/{self._full(collection)}/points/count", {"exact": True}, ok=(404,))
        return int((r.get("result") or {}).get("count", 0))

    def delete(self, collection: str, ids: list[str]) -> int:
        points = [str(uuid.uuid5(NAME_SPACE, i)) for i in ids]
        self._call("POST", f"/collections/{self._full(collection)}/points/delete?wait=true", {"points": points})
        return len(ids)

    def drop(self, collection: str) -> None:
        self._call("DELETE", f"/collections/{self._full(collection)}", ok=(404,))

    def collections(self) -> list[str]:
        rows = (self._call("GET", "/collections").get("result") or {}).get("collections") or []
        names = [str(c.get("name")) for c in rows]
        return sorted(n[len(self.prefix):] for n in names if n.startswith(self.prefix))


class PgVectorStore(VectorStore):
    """PostgreSQL with the vector extension: one table per collection, a cosine HNSW index on the vector."""

    kind = "pgvector"

    def __init__(self, dsn: str, *, prefix: str = "ontlas_vec_", name: str = "pgvector"):
        try:
            import psycopg
        except ImportError as e:
            raise ImportError("the pgvector store needs the [postgres] extra") from e
        self.conn = psycopg.connect(dsn, connect_timeout=10, autocommit=True)
        self.prefix, self.name = prefix, name
        self.capabilities = VectorCapabilities(persistent=True, exact=False)
        self.lock = threading.Lock()
        with self.lock:
            self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

    def _table(self, collection: str) -> str:
        return '"' + self.prefix + re.sub(r"[^0-9a-zA-Z_]", "_", collection) + '"'

    @staticmethod
    def _text(v: list[float]) -> str:
        return "[" + ",".join(repr(float(x)) for x in v) + "]"

    def ensure(self, collection: str, dim: int) -> None:
        t = self._table(collection)
        with self.lock:
            have = self.conn.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid = to_regclass(%s) AND attname = 'embedding'",
                                     (t,)).fetchone()
            if have and have[0] != dim:
                raise VectorError(f"collection '{collection}' holds {have[0]} dimensions, not {dim}")
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS {t} (id text PRIMARY KEY, embedding vector({dim}), payload jsonb)")
            self.conn.execute(f'CREATE INDEX IF NOT EXISTS {t[:-1]}_hnsw" ON {t} USING hnsw (embedding vector_cosine_ops)')

    def upsert(self, collection: str, points: list[Point]) -> int:
        t = self._table(collection)
        with self.lock, self.conn.cursor() as cur:
            cur.executemany(f"INSERT INTO {t} (id, embedding, payload) VALUES (%s, %s::vector, %s::jsonb) "
                            "ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding, payload = EXCLUDED.payload",
                            [(p.id, self._text(p.vector), json.dumps(p.payload, ensure_ascii=False)) for p in points])
        return len(points)

    def search(self, collection: str, vector: list[float], k: int = 5, where: dict | None = None) -> list[Hit]:
        t, args, clauses = self._table(collection), [self._text(vector)], []
        for key, want in (where or {}).items():
            many = want if isinstance(want, (list, tuple, set)) else [want]
            clauses.append("(" + " OR ".join("payload @> %s::jsonb" for _ in many) + ")")
            args += [json.dumps({key: w}, ensure_ascii=False) for w in many]
        tail = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        # the filter goes before ordering; with one the planner may leave the index, which is the right answer for a filter
        sql = f"SELECT id, 1 - (embedding <=> %s::vector) AS score, payload FROM {t}{tail} ORDER BY embedding <=> %s::vector, id LIMIT %s"
        with self.lock:
            rows = self.conn.execute(sql, [*args, args[0], k]).fetchall()
        return [Hit(r[0], float(r[1]), r[2] if isinstance(r[2], dict) else json.loads(r[2])) for r in rows]

    def count(self, collection: str) -> int:
        with self.lock:
            if self.conn.execute("SELECT to_regclass(%s)", (self._table(collection),)).fetchone()[0] is None:
                return 0
            return int(self.conn.execute(f"SELECT COUNT(*) FROM {self._table(collection)}").fetchone()[0])

    def delete(self, collection: str, ids: list[str]) -> int:
        with self.lock:
            return self.conn.execute(f"DELETE FROM {self._table(collection)} WHERE id = ANY(%s)", (list(ids),)).rowcount

    def drop(self, collection: str) -> None:
        with self.lock:
            self.conn.execute(f"DROP TABLE IF EXISTS {self._table(collection)}")

    def collections(self) -> list[str]:
        with self.lock:
            rows = self.conn.execute("SELECT tablename FROM pg_tables WHERE tablename LIKE %s",
                                     (self.prefix.replace("_", r"\_") + "%",)).fetchall()
        return sorted(r[0][len(self.prefix):] for r in rows)


_KINDS: dict[str, Callable[[dict], VectorStore]] = {}


def register_vector_store(kind: str, make: Callable[[dict], VectorStore]) -> None:
    """A store the package does not know joins by name: `vectors: {mine: {kind: <yours>, ...}}` in a studio file."""
    _KINDS[kind] = make


def _opt(spec: dict, *names: str) -> dict[str, Any]:
    return {k: spec[k] for k in names if k in spec}


register_vector_store("memory", lambda s: MemoryStore(s.get("name", "memory")))
register_vector_store("qdrant", lambda s: QdrantStore(s["url"], **_opt(s, "key", "key_env", "prefix", "timeout", "name")))
register_vector_store("pgvector", lambda s: PgVectorStore(s["dsn"], **_opt(s, "prefix", "name")))


def known_kinds() -> list[str]:
    return sorted(_KINDS)


def open_vector_store(spec: dict) -> VectorStore:
    kind = spec.get("kind", "memory")
    if kind not in _KINDS:
        raise ValueError(f"unknown vector store kind '{kind}'; known: {', '.join(known_kinds())}")
    return _KINDS[kind](spec)


# ---- conformance: a store is supported because it agrees, not because it answers ---------------------------------------

@dataclass
class VectorCase:
    text: str
    expected: list[str]
    floor: float = 0.0  # the score of the last place in exact search
    got: dict[str, list[str]] = field(default_factory=dict)
    scores: dict[str, list[float]] = field(default_factory=dict)

    def overlap(self, store: str) -> float:
        """How many places hold something as good as exact search's last place. Two points with one score may sit either way
        round at the cut, and neither order is wrong."""
        if not self.expected:
            return 1.0
        good = sum(s >= self.floor - 1e-4 for s in (self.scores.get(store) or [])[:len(self.expected)])
        return good / len(self.expected)


@dataclass
class VectorConformance:
    stores: dict[str, dict] = field(default_factory=dict)
    cases: list[VectorCase] = field(default_factory=list)

    def summary(self) -> dict:
        return {name: {"overlap": s.get("overlap"), "error": s.get("error", ""), "agree": s.get("agree", False)}
                for name, s in self.stores.items()}

    def to_dict(self) -> dict:
        return {"stores": self.stores, "cases": [asdict(c) for c in self.cases]}


def conformance(stores: dict[str, VectorStore], points: list[Point], queries: list[tuple[str, list[float]]], *, k: int = 5,
                collection: str = "ontlas_conformance", where: dict | None = None) -> VectorConformance:
    """The same points and the same questions into every store, each held against exact search. A store with approximate
    search is allowed to miss a tenth of the places; an exact one none."""
    report = VectorConformance()
    reference = MemoryStore("reference")
    dim = len(points[0].vector) if points else 0
    reference.ensure(collection, dim)
    reference.upsert(collection, points)
    for t, v in queries:
        best = reference.search(collection, v, k, where)
        report.cases.append(VectorCase(t, [h.id for h in best], best[-1].score if best else 0.0))
    for name, store in stores.items():
        try:
            store.drop(collection)
            store.ensure(collection, dim)
            store.upsert(collection, points)
            if store.count(collection) != len(points):
                raise VectorError(f"holds {store.count(collection)} of {len(points)} points")
            for case, (_, v) in zip(report.cases, queries):
                hits = store.search(collection, v, k, where)
                case.got[name], case.scores[name] = [h.id for h in hits], [h.score for h in hits]
            store.drop(collection)
            overlap = sum(c.overlap(name) for c in report.cases) / max(len(report.cases), 1)
            need = 1.0 if store.capabilities.exact else 0.9
            report.stores[name] = {"overlap": round(overlap, 4), "need": need, "agree": overlap >= need, "kind": store.kind}
        except (VectorError, OSError, ValueError) as e:
            report.stores[name] = {"overlap": None, "agree": False, "kind": store.kind, "error": str(e)}
    return report
