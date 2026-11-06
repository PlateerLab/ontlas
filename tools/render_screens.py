"""Render the README images: the studio screens from the example studio, and the architecture figure.

    python tools/render_screens.py            # needs playwright with chromium installed, and the [all] and [embed] extras

Writes assets/screens/{library,query,decision,map}.png from `xspace preview`,
assets/screens/{monitor,ontology,catalog,manage,draft,space-map,documents,search,adapters}.png from `xspace serve` with the
example files, and assets/architecture.png, all at 2x.
"""
from __future__ import annotations

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


def _serve(config: Path, samples: Path) -> str:
    data = DataOptions(samples=samples, embedder={"kind": "fastembed"})
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


def live_screens(page, base: str, out: Path) -> None:
    page.goto(base + "/#monitor")
    page.wait_for_selector(".spacesvg")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(2500)
    page.locator(".mcard").screenshot(path=str(out / "monitor.png"))
    page.goto(base + "/#onto")
    page.wait_for_selector(".kg-stage canvas", timeout=30000)
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(1500)
    page.locator("#main .grid").first.screenshot(path=str(out / "ontology.png"))
    page.goto(base + "/#catalog")
    page.locator(".cempty").wait_for()
    page.click("[data-act=fsample]")
    page.get_by_text("회원.csv").first.wait_for()
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "catalog.png"))
    page.goto(base + "/#objects")
    page.wait_for_selector("[data-act=mgnew], tr[data-name]")
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "manage.png"))
    page.goto(base + "/#data")
    page.get_by_text("생성 설정").first.wait_for()
    page.get_by_text("회원.csv").first.wait_for()
    page.click("[data-act=draft]")
    page.wait_for_function("() => { const b = document.querySelector('[data-act=dapply]'); return b && !b.disabled; }",
                           timeout=30000)
    page.click("[data-view=links]")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(400)
    page.locator("#draft").screenshot(path=str(out / "draft.png"))
    page.goto(base + "/#map")
    page.wait_for_selector("#mapgraph .kg-stage canvas", timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(out / "space-map.png"))
    page.goto(base + "/#docs")
    page.wait_for_selector("#docgraph .kg-stage canvas", timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(out / "documents.png"))
    page.goto(base + "/#search")
    page.wait_for_selector("[data-act=srex]", timeout=30000)
    page.locator("[data-act=srex]").first.click()
    page.wait_for_function("() => !document.querySelector('#main .spin') && document.querySelectorAll('#main .card').length > 1", timeout=30000)
    page.wait_for_timeout(500)
    page.screenshot(path=str(out / "search.png"))
    page.goto(base + "/#adapters")
    page.wait_for_selector("[data-act=adcheck]")
    page.click("[data-act=adcheck]")
    page.wait_for_function("() => !document.querySelector('[data-act=adcheck]').disabled", timeout=60000)
    page.wait_for_function("() => document.getElementById('toast').hidden", timeout=8000)
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
            page.goto(page_file.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            for sid in ("library", "query", "decision", "map"):
                page.locator(f"#{sid}").screenshot(path=str(out / "screens" / f"{sid}.png"))
            page.set_viewport_size({"width": 1500, "height": 900})
            live_screens(page, _serve(ROOT / "examples" / "library" / "studio.yaml", ROOT / "examples" / "files"),
                         out / "screens")
            arch = ROOT / "tools" / "architecture.html"
            page.set_viewport_size({"width": 1600, "height": 900})
            page.goto(arch.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.locator("#figure").screenshot(path=str(out / "architecture.png"))
            browser.close()
    print("written", sorted(str(p.relative_to(ROOT)) for p in out.rglob("*.png")))


if __name__ == "__main__":
    main()
