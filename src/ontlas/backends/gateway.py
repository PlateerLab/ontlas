"""A relational source reached through someone else's query service.

A platform that already holds database connections, with their passwords and read-only policies, can lend one out: SQL goes
there as text, rows come back, and the password never reaches this side. The space stays a third party to that platform: it
reads through the platform's rules and writes nothing. Fields are named in the studio file, so any service of this shape fits.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ontlas.backends.base import Backend, Capabilities, Result
from ontlas.compile.base import Compiled

_QMARK = re.compile(r"\?(?=(?:[^']*'[^']*')*[^']*$)")
_FIELDS = {"connection": "connection_id", "query": "query", "max_rows": "max_rows", "rows": "rows", "columns": "columns",
           "success": "success", "error": "error"}


class GatewayError(RuntimeError):
    """What the service said, without the token or the address's secrets."""


def literal(value: Any, dialect: str) -> str:
    """A value as SQL text: the service takes text, not bound parameters, so quoting here is what stands between a value and
    the statement."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return ("TRUE" if value else "FALSE") if dialect in ("postgres", "mysql") else ("1" if value else "0")
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        value = value.isoformat()
    text = str(value).replace("'", "''")
    if dialect == "mysql":
        text = text.replace("\\", "\\\\")  # MySQL reads a backslash as an escape unless told not to
    if "\x00" in text:
        raise ValueError("NUL in a value")
    return f"'{text}'"


def inline(sql: str, args: tuple | list, dialect: str) -> str:
    values = iter(args)
    try:
        return _QMARK.sub(lambda _: literal(next(values), dialect), sql)
    except StopIteration:
        raise ValueError("fewer values than placeholders") from None


class GatewayBackend(Backend):
    kind = "gateway"

    def __init__(self, url: str, *, connection: Any, dialect: str = "postgres", token: str = "", token_env: str = "", max_rows: int = 500,
                 timeout: float = 30.0, fields: dict | None = None, name: str = "gateway"):
        self.url, self.connection, self.max_rows, self.timeout, self.name = url, connection, int(max_rows), float(timeout), name
        self.token = token or (os.environ.get(token_env, "") if token_env else "")
        self.fields = {**_FIELDS, **(fields or {})}
        self.capabilities = Capabilities("sql", dialect, write=False)
        self.truncated = 0  # answers that came back full: there may have been more rows than the service returns

    def _call(self, sql: str) -> tuple[list[str], list[tuple]]:
        f = self.fields
        body = {f["connection"]: self.connection, f["query"]: sql, f["max_rows"]: self.max_rows}
        req = urllib.request.Request(self.url, data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "ontlas"})
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                out = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            word = {401: "인증이 거절되었습니다. 토큰을 확인해 주세요.", 403: "이 연결을 사용할 권한이 없습니다.",
                    404: "연결을 찾을 수 없거나 이 계정에 공유되지 않았습니다."}.get(e.code, f"서비스가 {e.code}로 응답했습니다.")
            raise GatewayError(word) from None
        except (OSError, ValueError):
            raise GatewayError("쿼리 서비스가 응답하지 않습니다. 주소와 네트워크를 확인해 주세요.") from None
        if out.get(f["success"]) is False:
            raise GatewayError(str(out.get(f["error"]) or "쿼리를 실행하지 못했습니다."))
        columns = [str(c) for c in out.get(f["columns"]) or []]
        rows = out.get(f["rows"]) or []
        if rows and isinstance(rows[0], dict):
            columns = columns or list(rows[0])
            rows = [tuple(r.get(c) for c in columns) for r in rows]
        else:
            rows = [tuple(r) for r in rows]
        if len(rows) >= self.max_rows:
            self.truncated += 1
        return columns, rows

    def fetch(self, sql: str, args: tuple = ()) -> list[tuple]:
        return self._call(inline(sql, args, self.capabilities.dialect))[1]

    def execute(self, compiled: Compiled, values: dict[str, Any] | None = None) -> Result:
        text, args = compiled.bind(values)
        before = self.truncated
        rows = self._call(inline(text, args, self.capabilities.dialect))[1]
        res = Result(compiled.columns, rows, self.name, compiled)
        res.truncated = self.truncated > before  # a list cut at the service's limit must not read as the whole answer
        return res

    def run(self, sql: str, args: tuple = ()) -> int:
        raise PermissionError("쿼리 게이트웨이는 읽기 전용입니다. 원천에는 쓰지 않습니다.")

    def run_many(self, statements: list[tuple[str, tuple]]) -> int:
        raise PermissionError("쿼리 게이트웨이는 읽기 전용입니다. 원천에는 쓰지 않습니다.")

    def columns(self, table: str) -> dict[str, str] | None:
        dialect = self.capabilities.dialect
        if dialect == "oracle":
            rows = self.fetch("SELECT column_name, data_type FROM all_tab_columns WHERE table_name = ?", (table.upper(),))
        else:
            rows = self.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?", (table,))
        return {str(r[0]).lower(): str(r[1] or "") for r in rows} if rows else None
