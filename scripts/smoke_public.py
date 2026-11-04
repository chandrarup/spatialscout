"""Playwright smoke run against the public URL (ticket 12): the first screen names the product, the diseased KPMP image
opens with its protein audit, the side-by-side view compares it with the healthy reference, and the golden path, asked
from the assistant bar, plays on the tissue and the run canvas at presenting pace to its verdicts in under three
minutes, labelled as an immutable replay with its recording time.

    uv run python scripts/smoke_public.py [url]      # or `make smoke-public`

It checks structure and labels, never an outcome: any verdict the recording holds passes.
"""

import sys
import time

from playwright.sync_api import expect, sync_playwright

URL = "https://chandrarupdaka--spatialscout.us-east.modal.run"
GOLDEN = "My hypothesis: the podocytes this atlas calls 'endocytic' really carry LRP2"
LIMIT_S = 180


def main(url: str) -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.goto(url, wait_until="networkidle", timeout=120_000)

        expect(page.get_by_role("heading", level=1)).to_be_visible(timeout=60_000)
        page.get_by_role("button", name="Start with the diseased biopsy").click()
        expect(page.get_by_text("CODEX protein imaging").first).to_be_visible(timeout=60_000)
        expect(page.locator("[data-testid=protein-audit-result]")).to_have_count(2, timeout=60_000)
        print("explore: diseased KPMP image and two protein audit results")

        page.get_by_role("button", name="Compare with the healthy reference").click()
        expect(page.get_by_test_id("provenance-left")).to_contain_text("real microscopy", timeout=60_000)
        expect(page.get_by_test_id("provenance-right")).to_contain_text("real microscopy")
        expect(page.locator("[data-testid=protein-audit-result]")).to_have_count(4, timeout=60_000)
        print("side by side: two KPMP strips and four protein audit results")

        page.get_by_role("button", name="Ask SpatialScout").click()
        started = time.monotonic()
        page.get_by_role("button", name=GOLDEN).click()
        expect(page.locator(".react-flow__node").first).to_be_visible(timeout=30_000)
        print("run canvas: the first step is drawn")
        page.get_by_role("button", name="See the verdict").click(timeout=LIMIT_S * 1000)
        expect(page.locator("[data-testid=sub-claim-verdict]").first).to_be_visible(timeout=LIMIT_S * 1000)
        elapsed = time.monotonic() - started
        verdicts = page.locator("[data-testid=sub-claim-verdict]").evaluate_all("els => els.map(e => e.dataset.verdict)")
        banner = page.get_by_text("Immutable replay", exact=True).locator("xpath=..").inner_text()
        page.screenshot(path="smoke_public.png")
        browser.close()

    assert elapsed < LIMIT_S, f"the replay took {elapsed:.0f} s"
    assert "recorded" in banner, banner
    print(f"golden path: verdicts {verdicts} in {elapsed:.1f} s; banner: {' '.join(banner.split())[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else URL))
