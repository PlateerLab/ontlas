"""Render the README images: the studio screens from the example studio, and the architecture figure.

    python tools/render_screens.py            # needs playwright with chromium installed

Writes assets/screens/{library,ontology,query,decision,map}.png from `xds preview`, assets/screens/draft.png from
`xds serve` with the example files drafted, and assets/architecture.png, all at 2x.
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

from xgen_data_studio.config import load_studio  # noqa: E402
from xgen_data_studio.preview import render  # noqa: E402
from xgen_data_studio.web import DataOptions, StudioSession  # noqa: E402
from xgen_data_studio.web.server import serve  # noqa: E402


def _serve(config: Path, samples: Path) -> str:
    data = DataOptions(samples=samples)
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


def draft_screen(page, base: str, path: Path) -> None:
    page.goto(base + "/#data")
    page.get_by_text("생성 설정").first.wait_for()
    page.click("[data-act=fsample]")
    page.get_by_text("회원.csv").wait_for()
    page.click("[data-act=draft]")
    page.wait_for_function("() => { const b = document.querySelector('[data-act=dapply]'); return b && !b.disabled; }",
                           timeout=30000)
    page.click("[data-view=links]")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(400)
    page.locator("#draft").screenshot(path=str(path))


def main() -> None:
    out = ROOT / "assets"
    (out / "screens").mkdir(parents=True, exist_ok=True)
    studio = load_studio(ROOT / "examples" / "library" / "studio.yaml")
    html = render(studio, query="revenueByCategory", decision="returnEligibility", key="I1001")
    with tempfile.TemporaryDirectory() as tmp:
        page_file = Path(tmp) / "studio.html"
        page_file.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=2)
            page.goto(page_file.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            for sid in ("library", "ontology", "query", "decision", "map"):
                page.locator(f"#{sid}").screenshot(path=str(out / "screens" / f"{sid}.png"))
            draft_screen(page, _serve(ROOT / "examples" / "library" / "studio.yaml", ROOT / "examples" / "files"),
                         out / "screens" / "draft.png")
            arch = ROOT / "tools" / "architecture.html"
            page.set_viewport_size({"width": 1600, "height": 900})
            page.goto(arch.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.locator("#figure").screenshot(path=str(out / "architecture.png"))
            browser.close()
    print("written", sorted(str(p.relative_to(ROOT)) for p in out.rglob("*.png")))


if __name__ == "__main__":
    main()
