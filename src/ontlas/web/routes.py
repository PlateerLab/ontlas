"""Routes the screens of an area add: an area keeps its handlers in its own module under ontlas.web.areas, and the
server asks here before its own table.

    from ontlas.web.routes import get, post

    @get("ontologies")
    def ontologies(s, a, who):
        return {...}

    @post("ontology/archive", needs="admin")
    def archive(s, a, who):
        ...

A handler takes the session (StudioSession), the arguments (the query of a GET, the JSON body of a POST) and who asks
(the signed-in team user, or None where nobody signs in), and returns what the route answers. What a POST needs is a
team level (viewer, editor, approver, admin); a GET that only some may read checks with `require`. Where the request
came from (its address, the sign-in it came with) is `asked()`.
"""
from __future__ import annotations

import importlib
import pkgutil
import threading
from typing import Callable

from ontlas.web.team import LEVELS, NEEDS

GET: dict[str, Callable] = {}
POST: dict[str, Callable] = {}


def get(route: str) -> Callable:
    def register(fn: Callable) -> Callable:
        if route in GET:
            raise ValueError(f"GET {route} is registered twice")
        GET[route] = fn
        return fn
    return register


def post(route: str, *, needs: str = "editor") -> Callable:
    if needs not in LEVELS:
        raise ValueError(f"needs is one of {LEVELS}")

    def register(fn: Callable) -> Callable:
        if route in POST:
            raise ValueError(f"POST {route} is registered twice")
        POST[route] = fn
        NEEDS[route] = needs
        return fn
    return register


def find(method: str, route: str) -> Callable | None:
    return (GET if method == "GET" else POST).get(route)


def require(who, level: str) -> None:
    """A read only some may make. Where nobody signs in (a space of one's own) everyone may."""
    if who is not None and not who.may(level):
        raise PermissionError(f"{who.name} 님의 권한으로는 이 내용을 볼 수 없습니다. 권한이 있는 사람에게 요청해 주세요.")


SERVER: dict = {}  # what the server was started with (rest, logins, sessions, limits, ...), for a handler that shows it
_asking = threading.local()  # each request is answered on a thread of its own: what it came with stays with it


def asking(**said) -> None:
    """The server says where the request this thread answers came from: ip, device (the sign-in it came with)."""
    _asking.said = said


def asked() -> dict:
    return getattr(_asking, "said", None) or {}


def load() -> list:
    """Import every area module once, so its routes are registered before the first request."""
    from ontlas.web import areas

    return [importlib.import_module(f"{areas.__name__}.{m.name}") for m in pkgutil.iter_modules(areas.__path__)]


def started(**server) -> None:
    """The server tells the areas what it was started with. An area that needs it defines on_serve(**server)."""
    SERVER.clear()
    SERVER.update(server)
    for module in load():
        hook = getattr(module, "on_serve", None)
        if hook is not None:
            hook(**server)
