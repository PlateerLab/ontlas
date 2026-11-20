"""Render the README images: the studio screens from the example studio, and the architecture figure.

    python tools/render_screens.py            # needs playwright with chromium installed, and the [all] and [embed] extras
    ONTLAS_BASE=http://127.0.0.1:7711 python tools/render_screens.py   # shoot a server already running with the example:
    #   ontlas serve examples/library/studio.yaml --samples examples/files --policies examples/policies --embedder fastembed
    #       --api-token-env ONTLAS_API_TOKEN --api-role support_agent --api-name "상담원 Agent" --port 7711
    python tools/render_screens.py rule-form lexicon   # only these of the screens named in LIVE

Writes assets/screens/{library,query,decision,map}.png from `ontlas preview`, the screens named in LIVE below from
`ontlas serve` with the example files (each opened by its address), and assets/architecture.png, all at 2x.
"""
from __future__ import annotations

import os
import secrets
import socket
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ontlas.config import load_studio  # noqa: E402
from ontlas.preview import render  # noqa: E402
from ontlas.web import DataOptions, StudioSession  # noqa: E402
from ontlas.web.server import serve  # noqa: E402


def _serve(config: Path, samples: Path, policies: Path) -> str:
    # /v1 is on for one caller with an access policy, so 연동 · API has a caller and its endpoints to show
    data = DataOptions(samples=samples, policies=policies, embedder={"kind": "fastembed"}, rest=True)
    api = {"name": "상담원 Agent", "token": secrets.token_hex(16), "role": "support_agent"}
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    threading.Thread(target=serve, args=(lambda: StudioSession(load_studio(config), data=data),),
                     kwargs={"port": port, "data": data, "quiet": True, "api": api}, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(base + "/", timeout=1)
            return base
        except OSError:
            time.sleep(0.1)
    raise SystemExit(f"the studio page did not start on {base}")


def settle(page, ms: int = 600) -> None:
    page.evaluate("document.fonts.ready")
    page.wait_for_function("() => !document.querySelector('#main .spin')", timeout=60000)
    page.wait_for_timeout(ms)


def open_tab(page, base: str, tab: str) -> None:
    page.goto("about:blank")  # a hash alone does not reload: the page is left behind
    page.goto(base + "/#" + tab, wait_until="networkidle")
    page.wait_for_selector("#main h1, #main .wsbar", timeout=30000)


# the screens of the README: the file, the address, and what is done on the screen before it is shot
LIVE = [
    ("home", "home", []),
    ("objects", "objmgr", []),
    ("entity", "objects", []),
    ("ontology", "model", []),
    ("workspace", "model?ws=1", [("click", "#ercanvas [data-er=OrderItem]")]),
    ("lexicon", "lexicon", []),
    ("rule-layers", "semrules", []),
    ("rule-form", "rule-form?id=card%3Alaw-return-min-days", [("scroll", "320")]),  # down to the fields of the card
    ("rules", "mgrules", []),
    ("record", "records", [("click", "[data-act=rec]")]),
    ("graph", "graph", []),
    ("actions", "actions", []),
    ("space-map", "map", []),
    ("documents", "docs", []),
    ("search", "search", [("say", "I1001 반품 되나요?")]),
    ("monitor", "monitor", []),
    ("adapters", "adapters", []),
    ("connect", "connect", []),
    # from here the session holds the example files, which the screens before it are shot without
    ("catalog", "catalog", [("click", "[data-act=fsample]")]),
    ("explorer", "explorer", []),
    ("draft", "ai", []),
    ("changes", "changes", [("request", "")]),  # last: its edits stay out of the screens before it
]


def file_a_request(page) -> None:
    """One edit filed (one visitor is both sides: it is approved as it is filed) and one more saved and not filed, so
    변경 요청 · 버전 has a version, and a request being written, to show."""
    page.evaluate("""async () => {
        const post = (path, body) => fetch('/api/' + path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Ontlas-Request': '1' }, body: JSON.stringify(body) });
        await post('manage/edit', { op: 'update_property', args: { object: 'Order', name: 'status', label: '주문 진행 상태' } });
        await post('manage/propose', {});
        await post('manage/edit', { op: 'update_property', args: { object: 'Customer', name: 'grade', label: '회원 등급' } });
    }""")


def live_screens(page, base: str, out: Path, only: list[str]) -> None:
    page.goto(base + "/", wait_until="networkidle")
    for name, tab, steps in LIVE:
        if only and name not in only:
            continue
        if ("request", "") in steps:
            file_a_request(page)
        open_tab(page, base, tab)
        settle(page, 900)
        for what, arg in steps:
            if what == "click" and page.locator(arg).count():
                page.locator(arg).first.click()
            if what == "scroll":  # the screen scrolls inside #main
                page.evaluate("(y) => document.querySelector('#main').scrollTo(0, y)", int(arg))
            if what == "say" and page.get_by_text(arg).count():  # an example question under the box
                page.get_by_text(arg).first.click()
                page.wait_for_timeout(4000)
            settle(page, 900)
        page.screenshot(path=str(out / f"{name}.png"))


def main() -> None:
    only = sys.argv[1:]  # names of LIVE screens: only those are shot, and the preview and the figure are left as they are
    unknown = [n for n in only if n not in [name for name, _, _ in LIVE]]
    if unknown:
        raise SystemExit(f"no screen named {unknown}; LIVE names {[name for name, _, _ in LIVE]}")
    out = ROOT / "assets"
    (out / "screens").mkdir(parents=True, exist_ok=True)
    studio = load_studio(ROOT / "examples" / "library" / "studio.yaml")
    html = render(studio, query="revenueByCategory", decision="returnEligibility", key="I1001")
    with tempfile.TemporaryDirectory() as tmp:
        page_file = Path(tmp) / "studio.html"
        page_file.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist",
                                              "--enable-unsafe-swiftshader"])  # the graph is WebGL
            page = browser.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=2)
            page.on("dialog", lambda d: d.accept())
            if not only:
                page.goto(page_file.as_uri(), wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                for sid in ("library", "query", "decision", "map"):
                    page.locator(f"#{sid}").screenshot(path=str(out / "screens" / f"{sid}.png"))
            page.set_viewport_size({"width": 1500, "height": 900})
            # ONTLAS_BASE names a running `ontlas serve` to shoot instead of starting one here (the Playwright
            # interpreter need not have the [embed] extra then)
            base = os.environ.get("ONTLAS_BASE") or _serve(ROOT / "examples" / "library" / "studio.yaml",
                                                            ROOT / "examples" / "files", ROOT / "examples" / "policies")
            live_screens(page, base, out / "screens", only)
            if not only:
                arch = ROOT / "tools" / "architecture.html"
                page.set_viewport_size({"width": 1600, "height": 900})
                page.goto(arch.as_uri(), wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                page.locator("#figure").screenshot(path=str(out / "architecture.png"))
            browser.close()
    print("written", sorted(str(p.relative_to(ROOT)) for p in out.rglob("*.png")))


if __name__ == "__main__":
    main()
