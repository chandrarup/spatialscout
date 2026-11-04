"""Playwright smoke run against the public URL (ticket 12): the first screen names the product, the diseased KPMP image
opens with its protein audit, the side-by-side view compares it with the healthy reference, and the golden path, asked
from the assistant bar, plays on the tissue and the run canvas at presenting pace to its verdicts in under three
minutes, labelled as an immutable replay with its recording time. Then the lab opens with its sub-agent timeline and
literature, and "Your data" audits the bundled sample.

    uv run python scripts/smoke_public.py [url]      # or `make smoke-public`

It checks structure and labels, never an outcome: any verdict the recording holds passes.
"""

import sys
import time

from playwright.sync_api import expect, sync_playwright

URL = "https://chandrarupdaka--spatialscout.us-east.modal.run"
GOLDEN = "My hypothesis: the podocytes this atlas calls 'endocytic' really carry LRP2"
LIMIT_S = 180


def drag_box(page, pane, fx0: float, fy0: float, fx1: float, fy1: float) -> None:
    """Drag from one fraction of the pane's box to another."""
    b = pane.bounding_box()
    page.mouse.move(b["x"] + b["width"] * fx0, b["y"] + b["height"] * fy0)
    page.mouse.down()
    page.mouse.move(b["x"] + b["width"] * (fx0 + fx1) / 2, b["y"] + b["height"] * (fy0 + fy1) / 2, steps=4)
    page.mouse.move(b["x"] + b["width"] * fx1, b["y"] + b["height"] * fy1, steps=4)
    page.mouse.up()


def compare_panes(page) -> None:
    """Two specimens: each pane's camera moves alone, and each pane's box reaches its own participant's audit."""
    top, bottom = page.locator("[data-pane=top]"), page.locator("[data-pane=bottom]")
    camera = lambda pane: pane.locator("[data-camera]").get_attribute("data-camera")  # noqa: E731
    expect(bottom.locator("[data-camera]")).to_be_attached(timeout=60_000)
    top_before, bottom_before = camera(top), camera(bottom)
    b = top.bounding_box()
    page.mouse.move(b["x"] + b["width"] * 0.5, b["y"] + b["height"] * 0.6)
    page.mouse.wheel(0, -600)
    page.wait_for_timeout(800)
    assert camera(top) != top_before, "the top pane did not zoom"
    assert camera(bottom) == bottom_before, "zooming the top pane moved the bottom pane"
    top.get_by_role("button", name="Fit").click()
    assert camera(bottom) == bottom_before, "fitting the top pane moved the bottom pane"

    sent: list[str] = []
    page.on("request", lambda r: sent.append(r.url) if "/protein-audit" in r.url and "x0=" in r.url else None)
    for pane, frac in ((top, (0.35, 0.45, 0.55, 0.85)), (bottom, (0.55, 0.4, 0.8, 0.8))):
        pane.get_by_role("button", name="Draw box").click()
        drag_box(page, pane, *frac)
        pane.get_by_role("button", name="Analyse this region").click()
        expect(pane.get_by_test_id("region-protein-audit")).to_be_visible(timeout=60_000)
    tops = [u for u in sent if "164-17" in u or "165-13" in u]
    bottoms = [u for u in sent if "31-10013" in u or "30-11101" in u]
    assert tops and bottoms, sent
    assert {u.split("x0=")[1] for u in tops}.isdisjoint({u.split("x0=")[1] for u in bottoms}), "the two boxes reached the same calculation"
    print(f"paired boxes: {len(tops)} top and {len(bottoms)} bottom region audits, each on its own participant and box")


def run_workspace(page) -> None:
    """The run's split resizes from the keyboard, and a box on the RNA tissue gets a fresh scoped audit."""
    rail = page.get_by_role("complementary", name="The agent's steps")
    width = rail.bounding_box()["width"]
    separator = page.get_by_role("separator", name="Resize the tissue and the agent's steps")
    separator.focus()
    for _ in range(3):
        separator.press("ArrowRight")
    narrower = rail.bounding_box()["width"]
    assert narrower < width - 60, (width, narrower)
    page.get_by_role("button", name="Reset layout").click()
    page.get_by_role("button", name="Fit graph").click()
    print(f"run split: steps pane {width:.0f} px, {narrower:.0f} px after three arrow presses, reset")

    tissue = page.get_by_label("Tissue viewer")
    expect(tissue.get_by_role("button", name="Usual assignment")).to_be_visible(timeout=60_000)
    page.wait_for_timeout(2500)
    tissue.get_by_role("button", name="Draw box").click()
    drag_box(page, tissue.get_by_test_id("rna-box-overlay"), 0.3, 0.35, 0.7, 0.75)
    tissue.get_by_role("button", name="Analyse selected region").click()
    expect(tissue.get_by_test_id("rna-region-result")).to_be_visible(timeout=60_000)
    print(f"rna box: {' '.join(tissue.get_by_test_id('rna-region-result').inner_text().split())[:140]}")
    tissue.get_by_role("button", name="Clear the box").click()


def main(url: str) -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.goto(url, wait_until="networkidle", timeout=120_000)

        expect(page.get_by_role("heading", level=1)).to_be_visible(timeout=60_000)
        page.get_by_role("button", name="Explore the tissue").click()
        expect(page.get_by_text("CODEX protein imaging").first).to_be_visible(timeout=60_000)
        expect(page.locator("[data-testid=protein-audit-result]")).to_have_count(2, timeout=60_000)
        print("explore: diseased KPMP image and two protein audit results")

        page.get_by_role("button", name="Compare with the healthy reference").click()
        expect(page.get_by_test_id("provenance-left")).to_contain_text("real microscopy", timeout=60_000)
        expect(page.get_by_test_id("provenance-right")).to_contain_text("real microscopy")
        expect(page.locator("[data-testid=protein-audit-result]")).to_have_count(4, timeout=60_000)
        print("side by side: two KPMP strips and four protein audit results")
        compare_panes(page)

        page.get_by_role("button", name="Talk to SpatialScout").click()
        box = page.get_by_placeholder("Ask about a gene, a cell type, a condition…")
        box.fill("Is APOL1 in podocytes higher in FSGS?")
        box.press("Enter")
        expect(page.get_by_test_id("data-fit")).to_contain_text("APOL1", timeout=30_000)
        expect(page.get_by_role("button", name="Audit your data")).to_be_visible()
        print("data check: an off-panel gene is named, with the upload and public-dataset paths")
        page.get_by_role("button", name="Ask something else").click()
        started = time.monotonic()
        page.get_by_role("button", name=GOLDEN).click()
        expect(page.locator(".react-flow__node").first).to_be_visible(timeout=30_000)
        print("run canvas: the first step is drawn")
        run_workspace(page)
        page.get_by_role("button", name="See the findings").click(timeout=LIMIT_S * 1000)
        expect(page.locator("[data-testid=sub-claim-verdict]").first).to_be_visible(timeout=LIMIT_S * 1000)
        elapsed = time.monotonic() - started
        verdicts = page.locator("[data-testid=sub-claim-verdict]").evaluate_all("els => els.map(e => e.dataset.verdict)")
        banner = page.get_by_text("Immutable replay", exact=True).locator("xpath=..").inner_text()
        page.screenshot(path="smoke_public.png")

        lab_started = time.monotonic()
        page.get_by_role("button", name="Run the lab").click()
        expect(page.get_by_label("Lab timeline")).to_be_visible(timeout=60_000)
        expect(page.get_by_label("Literature").first).to_be_visible(timeout=60_000)
        lanes = page.get_by_label("Lab timeline").inner_text()
        print(f"lab: timeline and literature in {time.monotonic() - lab_started:.1f} s; {lanes.count('Literature agent')} literature lane(s)")

        page.get_by_role("button", name="Your data").click()
        upload_started = time.monotonic()
        page.get_by_role("button", name="Try it on the sample (3 GSE286184 crops)").click()
        expect(page.get_by_label("Your audit")).to_be_visible(timeout=120_000)
        print(f"your data: sample audited in {time.monotonic() - upload_started:.1f} s")
        browser.close()

    assert elapsed < LIMIT_S, f"the replay took {elapsed:.0f} s"
    assert "recorded" in banner, banner
    print(f"golden path: verdicts {verdicts} in {elapsed:.1f} s; banner: {' '.join(banner.split())[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else URL))
