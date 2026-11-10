"""Render the README images: the studio screens from the example studio, and the architecture figure.

    python tools/render_screens.py            # needs playwright with chromium installed, and the [all] and [embed] extras
    XSPACE_BASE=http://127.0.0.1:7711 python tools/render_screens.py   # shoot a server already running with the example

Writes assets/screens/{library,query,decision,map}.png from `xspace preview`,
assets/screens/{home,monitor,ontology,catalog,draft,workspace,rules,changes,record,graph,space-map,documents,search,
adapters,explorer}.png from `xspace serve` with the example files, and assets/architecture.png, all at 2x.
"""
from __future__ import annotations

import os
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

from xgen_space.config import load_studio  # noqa: E402
from xgen_space.preview import render  # noqa: E402
from xgen_space.web import DataOptions, StudioSession  # noqa: E402
from xgen_space.web.server import serve  # noqa: E402


def _serve(config: Path, samples: Path, policies: Path) -> str:
    data = DataOptions(samples=samples, policies=policies, embedder={"kind": "fastembed"})
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    threading.Thread(target=serve, args=(lambda: StudioSession(load_studio(config), data=data),),
                     kwargs={"port": port, "data": data, "quiet": True}, daemon=True).start()
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
    page.goto(base + "/#" + tab)
    page.wait_for_selector("#main .card, #main .head", timeout=30000)


def live_screens(page, base: str, out: Path) -> None:
    open_tab(page, base, "home")
    page.wait_for_function("() => document.querySelector('#main .hask') && !document.querySelector('#main .spin')", timeout=60000)
    settle(page, 1200)
    page.screenshot(path=str(out / "home.png"))

    open_tab(page, base, "monitor")
    page.wait_for_selector(".spacesvg")
    settle(page, 2500)
    page.locator(".mcard").screenshot(path=str(out / "monitor.png"))

    open_tab(page, base, "onto")  # the ontology as cards, a module a region
    page.wait_for_selector("#ontocanvas [data-er]", timeout=30000)
    settle(page, 1200)
    page.locator("#main .grid").first.screenshot(path=str(out / "ontology.png"))

    open_tab(page, base, "catalog")
    page.locator(".cempty").wait_for()
    page.click("[data-act=fsample]")
    page.get_by_text("회원.csv").first.wait_for()
    settle(page, 500)
    page.screenshot(path=str(out / "catalog.png"))

    open_tab(page, base, "data")  # the draft reviewed step by step: the objects step, a table picked
    page.get_by_text("회원.csv").first.wait_for()
    page.click("[data-act=draft]")
    page.wait_for_selector("[data-act=dview][data-view=objects]", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    page.click("[data-act=dview][data-view=objects]")
    settle(page, 400)
    rows = page.locator("[data-act=dpick]")
    if rows.count():
        rows.nth(min(1, rows.count() - 1)).click()
    settle(page, 700)
    page.locator("#draft").screenshot(path=str(out / "draft.png"))

    open_tab(page, base, "model")  # the modelling workspace, an object picked
    page.wait_for_selector("#ercanvas [data-er=OrderItem]", timeout=60000)
    page.click("#ercanvas [data-er=OrderItem]")
    settle(page, 900)
    page.screenshot(path=str(out / "workspace.png"))

    open_tab(page, base, "mgrules")  # a decision table with its checks and simulator
    page.wait_for_selector("td[data-act=mgrule][data-name=vip-window]", timeout=60000)
    sim = page.locator("select[data-in=simkey]")
    if sim.count():
        opts = sim.locator("option").all_inner_texts()
        if len(opts) > 1:
            sim.select_option(index=1)
            settle(page, 1200)
    settle(page, 500)
    page.screenshot(path=str(out / "rules.png"))

    open_tab(page, base, "records")
    page.wait_for_selector("[data-act=rec]", timeout=60000)
    page.locator("[data-act=rec]").first.click()
    page.wait_for_selector(".rhead", timeout=30000)
    settle(page, 900)
    page.screenshot(path=str(out / "record.png"))

    open_tab(page, base, "graph")
    page.fill("[data-in=gxq]", "C001")
    page.keyboard.press("Enter")
    page.wait_for_selector("input[data-in=gxrel]:not([disabled])", timeout=30000)  # a relation to open, with its count
    page.locator("input[data-in=gxrel]:not([disabled])").first.check()
    settle(page, 1500)
    page.screenshot(path=str(out / "graph.png"))

    open_tab(page, base, "map")
    page.wait_for_selector("#mapgraph .kg-stage canvas", timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(out / "space-map.png"))

    open_tab(page, base, "docs")
    page.wait_for_selector("#docgraph .kg-stage canvas", timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(out / "documents.png"))

    open_tab(page, base, "search")
    page.wait_for_selector("[data-act=srex]", timeout=30000)
    page.locator("[data-act=srex]").first.click()
    page.wait_for_function("() => !document.querySelector('#main .spin') && document.querySelectorAll('#main .card').length > 1", timeout=30000)
    page.wait_for_timeout(500)
    page.screenshot(path=str(out / "search.png"))

    changes_screen(page, base, out)
    adapters_screen(page, base, out)
    explorer_screen(page, base, out)


def changes_screen(page, base: str, out: Path) -> None:
    """A change request as the page reviews it: an edit is made in the workspace and filed, then opened."""
    open_tab(page, base, "model")
    page.wait_for_selector("#ercanvas [data-er=Order]", timeout=60000)
    page.click("#ercanvas [data-er=Order]")
    settle(page, 600)
    page.fill("[data-in=mgf][data-f=label]", "주문서")
    page.click("[data-act=mgsave]")
    settle(page, 800)
    page.click("[data-act=mdreview]")  # the review first: the edits and a run on a copy, then the apply in that panel
    page.wait_for_selector(".wsleft .wstrial", timeout=60000)
    page.click(".wsleft [data-act=mgpropose]")
    page.wait_for_function("() => { const t = document.querySelector('#toast'); return t && /변경/.test(t.innerText); }", timeout=60000)
    open_tab(page, base, "changes")
    page.wait_for_selector("[data-act=chgsel]", timeout=30000)
    page.locator("[data-act=chgsel]").first.click()
    page.wait_for_selector("[data-act=chgitem]", timeout=30000)
    page.locator("[data-act=chgitem]").first.click()
    settle(page, 900)
    page.screenshot(path=str(out / "changes.png"))


def explorer_screen(page, base: str, out: Path) -> None:
    open_tab(page, base, "explorer")  # the sample files are in the repository by now: the catalog step loaded them
    page.wait_for_selector(".exbody", timeout=60000)
    settle(page, 400)
    page.screenshot(path=str(out / "explorer.png"))


def adapters_screen(page, base: str, out: Path) -> None:
    open_tab(page, base, "adapters")  # the page runs the conformance tests once on opening
    page.wait_for_function("() => document.querySelector('#main .stats') && !document.querySelector('#main .spin')", timeout=90000)
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "adapters.png"))


def main() -> None:
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
            page.goto(page_file.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            for sid in ("library", "query", "decision", "map"):
                page.locator(f"#{sid}").screenshot(path=str(out / "screens" / f"{sid}.png"))
            page.set_viewport_size({"width": 1500, "height": 900})
            # XSPACE_BASE names a running `xspace serve` to shoot instead of starting one here (the Playwright
            # interpreter need not have the [embed] extra then)
            base = os.environ.get("XSPACE_BASE") or _serve(ROOT / "examples" / "library" / "studio.yaml",
                                                            ROOT / "examples" / "files", ROOT / "examples" / "policies")
            live_screens(page, base, out / "screens")
            arch = ROOT / "tools" / "architecture.html"
            page.set_viewport_size({"width": 1600, "height": 900})
            page.goto(arch.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.locator("#figure").screenshot(path=str(out / "architecture.png"))
            browser.close()
    print("written", sorted(str(p.relative_to(ROOT)) for p in out.rglob("*.png")))


if __name__ == "__main__":
    main()
