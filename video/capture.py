"""Drive the real SpatialScout site along docs/demo-script.md and record it for the Remotion demo.

    uv run python video/capture.py [url]

Writes video/public/screen.webm and video/src/marks.json: the time (s from the recording's start) and on-screen
rectangle of every beat, which the Remotion composition uses for chapter titles and zooms.
"""

import json
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

URL = "http://127.0.0.1:8010"
HERE = Path(__file__).parent
W, H = 1920, 1080
QUESTION = "Compare these two regions: does B-cell UMOD look like spillover in the diseased tissue but not in the healthy one?"
GOLDEN = "My hypothesis: the podocytes this atlas calls 'endocytic' really carry LRP2"

CURSOR = """
(() => {
  const install = () => {
    if (document.getElementById('__cursor')) return;
    const c = document.createElement('div');
    c.id = '__cursor';
    c.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;'
      + 'background:rgba(255,255,255,0.92);box-shadow:0 0 0 2px rgba(0,0,0,0.55),0 4px 14px rgba(0,0,0,0.5);'
      + 'pointer-events:none;z-index:2147483647;transition:transform 120ms ease-out;transform:translate(960px,540px)';
    document.body.appendChild(c);
    let x = 960, y = 540;
    addEventListener('mousemove', e => { x = e.clientX; y = e.clientY; c.style.transform = `translate(${x}px,${y}px)`; }, true);
    addEventListener('mousedown', () => {
      c.style.transform = `translate(${x}px,${y}px) scale(0.7)`;
      const r = document.createElement('div');
      r.style.cssText = `position:fixed;left:${x}px;top:${y}px;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;`
        + 'border:3px solid rgba(74,222,128,0.95);pointer-events:none;z-index:2147483646;transition:all 520ms ease-out;';
      document.body.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = 'scale(4.5)'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }, true);
    addEventListener('mouseup', () => { c.style.transform = `translate(${x}px,${y}px)`; }, true);
  };
  if (document.body) install(); else addEventListener('DOMContentLoaded', install);
})();
"""


class Director:
    def __init__(self, page, t0: float):
        self.page, self.t0, self.marks = page, t0, []
        self.x, self.y = W / 2, H / 2

    def mark(self, name: str, target=None, pad: int = 120) -> None:
        rect = None
        if target is not None:
            b = target.bounding_box() if hasattr(target, "bounding_box") else target
            if b:
                rect = [max(0, b["x"] - pad), max(0, b["y"] - pad), b["width"] + 2 * pad, b["height"] + 2 * pad]
        self.marks.append({"name": name, "t": round(time.monotonic() - self.t0, 2), "rect": rect})
        print(f"{self.marks[-1]['t']:7.2f}s  {name}")

    def move(self, x: float, y: float, steps: int = 28) -> None:
        self.page.mouse.move(x, y, steps=steps)
        self.x, self.y = x, y

    def click(self, locator, name: str | None = None, pause: int = 450) -> None:
        locator.scroll_into_view_if_needed()
        b = locator.bounding_box()
        if name:
            self.mark(name, b)
        self.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
        self.page.wait_for_timeout(pause)
        self.page.mouse.down()
        self.page.wait_for_timeout(90)
        self.page.mouse.up()

    def drag(self, pane, fx0: float, fy0: float, fx1: float, fy1: float) -> None:
        b = pane.bounding_box()
        self.move(b["x"] + b["width"] * fx0, b["y"] + b["height"] * fy0)
        self.page.mouse.down()
        self.move(b["x"] + b["width"] * fx1, b["y"] + b["height"] * fy1, steps=40)
        self.page.mouse.up()

    def type(self, locator, text: str) -> None:
        locator.click()
        locator.press_sequentially(text, delay=22)

    def hold(self, ms: int) -> None:
        self.page.wait_for_timeout(ms)


def main(url: str) -> int:
    video_dir = HERE / "out" / "raw"
    shutil.rmtree(video_dir, ignore_errors=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--hide-scrollbars"])
        ctx = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=str(video_dir), record_video_size={"width": W, "height": H})
        ctx.add_init_script(CURSOR)
        page = ctx.new_page()
        t0 = time.monotonic()
        d = Director(page, t0)
        page.goto(url, wait_until="networkidle", timeout=120_000)
        expect(page.get_by_role("heading", level=1)).to_be_visible(timeout=60_000)
        rec = page.get_by_role("button", name="Recording mode")
        if rec.count():
            rec.click()
        d.hold(1500)

        d.mark("overview")
        d.move(W * 0.55, H * 0.45, steps=60)
        d.hold(5000)

        d.click(page.get_by_role("button", name="Explore the tissue"), "explore")
        expect(page.locator("[data-testid=protein-audit-result]")).to_have_count(2, timeout=60_000)
        d.hold(2500)
        d.click(page.get_by_role("button", name="Compare with the healthy reference"), "compare")
        expect(page.locator("[data-testid=protein-audit-result]")).to_have_count(4, timeout=60_000)
        top, bottom = page.locator("[data-pane=top]"), page.locator("[data-pane=bottom]")
        expect(bottom.locator("[data-camera]")).to_be_attached(timeout=60_000)
        d.hold(2500)

        b = top.bounding_box()
        d.mark("zoom-top", b, pad=0)
        d.move(b["x"] + b["width"] * 0.5, b["y"] + b["height"] * 0.6)
        for _ in range(4):
            page.mouse.wheel(0, -160)
            d.hold(180)
        d.hold(1200)
        d.click(top.get_by_role("button", name="Fit"))
        d.hold(1000)

        for label, pane, frac in (("box-top", top, (0.35, 0.45, 0.55, 0.85)), ("box-bottom", bottom, (0.55, 0.4, 0.8, 0.8))):
            d.mark(label, pane, pad=10)
            d.click(pane.get_by_role("button", name="Draw box"))
            d.hold(300)
            d.drag(pane, *frac)
            d.hold(400)
            d.click(pane.get_by_role("button", name="Analyse this region"))
            result = pane.get_by_test_id("region-protein-audit")
            expect(result).to_be_visible(timeout=60_000)
            d.hold(600)
            d.mark(f"{label}-result", result, pad=30)
            d.hold(2200)

        d.click(page.get_by_role("button", name="Ask SpatialScout about both regions"), "ask-both")
        box = page.get_by_placeholder("Ask about a gene, a cell type, a condition…")
        expect(box).to_be_visible(timeout=15_000)
        d.mark("question", box)
        d.type(box, QUESTION)
        d.hold(500)
        box.press("Enter")
        trial = page.get_by_role("button", name="Run it live (free trial)")
        run = page.get_by_role("button", name="Run it", exact=True).or_(page.get_by_role("button", name="Run on what is here"))
        try:
            expect(trial.or_(run).first).to_be_visible(timeout=30_000)
            d.mark("data-fit", page.get_by_test_id("data-fit"), pad=20)
            d.hold(2500)
            d.click(trial if trial.count() else run.first, "go-live")
            d.hold(9000)
            d.mark("live-running")
            d.hold(5000)
        except Exception as e:  # keep recording the rest of the story
            print(f"live start skipped: {e}")
            d.mark("live-skipped")

        page.goto(url, wait_until="networkidle", timeout=120_000)
        d.hold(1500)
        follow = page.get_by_role("button", name="Follow an investigation")
        if follow.count():
            d.click(follow, "follow")
            golden = page.get_by_role("button", name=GOLDEN)
            if golden.count():
                d.click(golden)
        else:
            d.click(page.get_by_role("button", name="Talk to SpatialScout"))
            d.click(page.get_by_role("button", name=GOLDEN), "follow")
        team = page.get_by_test_id("team-job")
        expect(team).to_have_count(5, timeout=30_000)
        d.mark("team", page.get_by_role("complementary", name="The agent's steps"), pad=0)
        d.hold(6000)

        sep = page.get_by_role("separator", name="Resize the tissue and the agent's steps")
        sb = sep.bounding_box()
        d.mark("resize", sb, pad=200)
        d.move(sb["x"] + sb["width"] / 2, sb["y"] + sb["height"] / 2)
        page.mouse.down()
        d.move(sb["x"] + 260, sb["y"] + sb["height"] / 2, steps=40)
        page.mouse.up()
        d.hold(5000)

        tissue = page.get_by_label("Tissue viewer")
        expect(tissue.get_by_role("button", name="Follow evidence")).to_be_visible(timeout=150_000)
        d.mark("evidence", tissue, pad=0)
        d.hold(4000)
        d.click(tissue.get_by_role("button", name="3D molecule depth"), "depth")
        expect(tissue.get_by_test_id("depth-slice-counts")).to_be_visible(timeout=90_000)
        d.hold(1500)
        tb = tissue.bounding_box()
        cx, cy = tb["x"] + tb["width"] * 0.5, tb["y"] + tb["height"] * 0.5
        d.mark("orbit", tb, pad=0)
        d.move(cx, cy)
        page.mouse.down()
        d.move(cx + 220, cy - 60, steps=50)
        d.move(cx - 120, cy + 30, steps=50)
        page.mouse.up()
        d.hold(800)
        slider = tissue.get_by_label("Slice from (µm)")
        sl = slider.bounding_box()
        d.mark("slice", sl, pad=160)
        d.move(sl["x"] + 4, sl["y"] + sl["height"] / 2)
        page.mouse.down()
        d.move(sl["x"] + sl["width"] * 0.55, sl["y"] + sl["height"] / 2, steps=45)
        page.mouse.up()
        d.hold(3000)
        d.click(tissue.get_by_role("button", name="2D map"))
        d.hold(800)

        skip = page.get_by_role("button", name="Skip to end")
        if skip.count() and skip.is_visible():
            d.click(skip, "skip")
        findings = page.get_by_role("button", name="See the findings")
        findings.wait_for(timeout=180_000)
        d.click(findings, "findings")
        verdicts = page.locator("[data-testid=sub-claim-verdict]")
        expect(verdicts.first).to_be_visible(timeout=60_000)
        d.hold(1200)
        verdicts.first.scroll_into_view_if_needed()
        d.mark("verdict-1", verdicts.first, pad=60)
        d.hold(6000)
        verdicts.nth(1).scroll_into_view_if_needed()
        d.mark("verdict-2", verdicts.nth(1), pad=60)
        d.hold(6000)

        fig = page.locator("img[src*='fnd-fb36fadff91b78bd']").first
        if fig.count():
            fig.scroll_into_view_if_needed()
            d.mark("umod-figure", fig, pad=30)
            d.hold(8000)

        page.evaluate("document.querySelector('[aria-label=\"Checked claims\"]').open = true")
        selector = page.get_by_test_id("challenge-selector").first
        selector.scroll_into_view_if_needed()
        d.mark("challenge", selector, pad=80)
        d.hold(1500)
        d.click(selector.get_by_role("button").nth(1))
        expect(page.get_by_text("failed").first).to_be_visible(timeout=10_000)
        failed = page.get_by_text("failed").first
        d.mark("failed", failed.locator("xpath=ancestor::*[3]"), pad=40)
        d.hold(6000)

        pkg = page.locator("a[href*='package']").first
        pkg.scroll_into_view_if_needed()
        d.hold(800)
        d.mark("package", pkg, pad=260)
        d.move(*(lambda b: (b["x"] + b["width"] / 2, b["y"] + b["height"] / 2))(pkg.bounding_box()))
        d.hold(5000)
        d.mark("end")
        d.hold(1500)

        video = page.video
        ctx.close()
        browser.close()
        src = Path(video.path())

    (HERE / "public").mkdir(exist_ok=True)
    shutil.copy(src, HERE / "public" / "screen.webm")
    (HERE / "src" / "marks.json").write_text(json.dumps(d.marks, indent=1))
    print(f"wrote {HERE / 'public' / 'screen.webm'} and {len(d.marks)} marks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else URL))
