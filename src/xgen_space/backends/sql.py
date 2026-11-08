"""Relational backends: SQLite for local work and tests, any DB-API 2.0 connection for the rest."""
from __future__ import annotations

import re
import sqlite3
from typing import Any

from xgen_space.backends.base import Backend, Capabilities, Result
from xgen_space.compile.base import Compiled

_QMARK = re.compile(r"\?(?=(?:[^']*'[^']*')*[^']*$)")
_QUOTED = re.compile(r"""'(?:[^']|'')*'|"((?:[^"]|"")*)\"""")
_DDL = re.compile(r"\s*(CREATE|ALTER|DROP|RENAME)\b", re.IGNORECASE)


class SqliteBackend(Backend):
    kind = "sqlite"

    def __init__(self, path: str = ":memory:", *, conn: sqlite3.Connection | None = None, name: str = "sqlite"):
        self.conn = conn or sqlite3.connect(path, check_same_thread=False)
        self.name = name
        self.capabilities = Capabilities("sql", "sqlite", write=True)

    def script(self, sql: str) -> None:
        self.conn.executescript(sql)
        self.conn.commit()

    def execute(self, compiled: Compiled, values: dict[str, Any] | None = None) -> Result:
        text, args = compiled.bind(values)
        cur = self.conn.execute(text, args)
        return Result(compiled.columns, [tuple(r) for r in cur.fetchall()], self.name, compiled)

    def run(self, sql: str, args: tuple = ()) -> int:
        cur = self.conn.execute(sql, args)
        self.conn.commit()
        return cur.rowcount

    def run_many(self, statements: list[tuple[str, tuple]]) -> int:
        """Run several writes as one transaction: all of them, or none."""
        n = 0
        try:
            for sql, args in statements:
                n += max(self.conn.execute(sql, args).rowcount, 0)
        except BaseException:
            self.conn.rollback()
            raise
        self.conn.commit()
        return n

    def fetch(self, sql: str, args: tuple = ()) -> list[tuple]:
        return [tuple(r) for r in self.conn.execute(sql, args).fetchall()]

    def columns(self, table: str) -> dict[str, str] | None:
        rows = self.conn.execute(f'PRAGMA table_info("{table.replace(chr(34), chr(34) * 2)}")').fetchall()
        return {r[1].lower(): (r[2] or "") for r in rows} if rows else None


class DbApiBackend(Backend):
    """Any DB-API connection; `paramstyle` follows the driver (psycopg: format, oracledb: numeric, or pymssql)."""
    kind = "dbapi"

    def __init__(self, conn: Any, dialect: str = "postgres", *, paramstyle: str = "format", name: str = ""):
        self.conn = conn
        self.paramstyle = paramstyle
        self.name = name or dialect
        self.capabilities = Capabilities("sql", dialect, write=True)
        self._cased: set[str] | None = None  # Oracle: the names its catalog holds in anything but capitals

    def _oracle_name(self, name: str) -> str:
        """A name as Oracle holds it. A plain name is kept in capitals and a quoted one exactly as written, so the
        ontology's "orders" would miss the ORDERS everyone creates; only a name made in small letters stays."""
        if self._cased is None:
            cur = self.conn.cursor()  # no rollback after it: this may run in the middle of run_many
            try:
                cur.execute("SELECT object_name FROM user_objects WHERE object_name <> UPPER(object_name) "
                            "UNION SELECT column_name FROM user_tab_columns WHERE column_name <> UPPER(column_name)")
                self._cased = {r[0] for r in cur.fetchall()}
            finally:
                cur.close()
        return name if name in self._cased else name.upper()

    def _send(self, cur: Any, text: str, args: Any) -> None:
        if self.capabilities.dialect == "oracle":  # before 23ai it binds no boolean into SQL; flags are numbers anyway
            args = tuple(int(a) if isinstance(a, bool) else a for a in args)
        if self.paramstyle == "pymssql" and not args:  # with nothing to put in, a % in the text must not be looked at
            cur.execute(text)
        else:
            cur.execute(self._text(text), args)

    def _text(self, text: str) -> str:
        if self.capabilities.dialect == "oracle":
            text = _QUOTED.sub(lambda m: m[0] if m[1] is None else f'"{self._oracle_name(m[1])}"', text)
        if self.paramstyle == "qmark":
            return text
        if self.paramstyle == "format":
            return _QMARK.sub("%s", text.replace("%", "%%"))
        if self.paramstyle == "pymssql":  # replaces each %s and leaves the rest alone, a %% too
            return _QMARK.sub("%s", text)
        if self.paramstyle == "numeric":
            n = iter(range(1, 10_000))
            return _QMARK.sub(lambda _: f":{next(n)}", text)
        raise ValueError(f"unsupported paramstyle '{self.paramstyle}'")

    def _end_read(self) -> None:
        """Close the transaction a read opened, so the connection holds no locks while it waits (or after an error,
        so it can be used again)."""
        # pymssql's autocommit is the method that sets it, and autocommit_state the value
        if not getattr(self.conn, "autocommit_state", getattr(self.conn, "autocommit", False)):
            self.conn.rollback()

    def execute(self, compiled: Compiled, values: dict[str, Any] | None = None) -> Result:
        text, args = compiled.bind(values)
        cur = self.conn.cursor()
        try:
            self._send(cur, text, args)
            rows = [tuple(r) for r in cur.fetchall()]
        finally:
            cur.close()
            self._end_read()
        return Result(compiled.columns, rows, self.name, compiled)

    def run(self, sql: str, args: tuple = ()) -> int:
        cur = self.conn.cursor()
        try:
            self._send(cur, sql, args)
            n = cur.rowcount
        except BaseException:
            self.conn.rollback()
            raise
        finally:
            cur.close()
        self.conn.commit()
        if _DDL.match(sql):
            self._cased = None
        return n

    def run_many(self, statements: list[tuple[str, tuple]]) -> int:
        """Run several writes as one transaction: all of them, or none."""
        n, cur = 0, self.conn.cursor()
        try:
            for sql, args in statements:
                self._send(cur, sql, args)
                n += max(cur.rowcount, 0)
                if _DDL.match(sql):
                    self._cased = None
        except BaseException:
            self.conn.rollback()
            raise
        finally:
            cur.close()
        self.conn.commit()
        return n

    def fetch(self, sql: str, args: tuple = ()) -> list[tuple]:
        cur = self.conn.cursor()
        try:
            self._send(cur, sql, args)
            return [tuple(r) for r in cur.fetchall()]
        finally:
            cur.close()
            self._end_read()

    def columns(self, table: str) -> dict[str, str] | None:
        dialect = self.capabilities.dialect
        if dialect == "sqlite":
            rows = self.fetch(f'PRAGMA table_info("{table}")')
            return {r[1].lower(): (r[2] or "") for r in rows} if rows else None
        if dialect == "oracle":
            # NUMBER with no places is Oracle's whole number; the user's own table first, because all_tab_columns
            # adds the columns of tables with that name in other schemas
            typed = "CASE WHEN data_type = 'NUMBER' AND data_scale = 0 THEN 'INTEGER' ELSE data_type END"
            name = self._oracle_name(table)
            rows = (self.fetch(f"SELECT column_name, {typed} FROM user_tab_columns WHERE table_name = ?", (name,)) or
                    self.fetch(f"SELECT column_name, {typed} FROM all_tab_columns WHERE table_name = ?", (name,)))
        elif dialect == "tsql":
            rows = self.fetch("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                              "WHERE TABLE_SCHEMA = SCHEMA_NAME() AND TABLE_NAME = ?", (table,))
        else:
            rows = self.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?",
                              (table,))
        return {str(r[0]).lower(): str(r[1] or "") for r in rows} if rows else None
