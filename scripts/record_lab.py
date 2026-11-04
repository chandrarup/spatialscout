"""Record the lab live on a recorded investigation, for immutable replay.

Runs the lab once against `fixtures/recordings/<recording_id>/investigation/`: Muse Wonder dispatches, Europe PMC is
searched live, Muse Spark reads the fetched records, the figures and protein checks are computed. Whatever comes back is
kept (ADR-0001); nothing is retried for a different outcome. Writes `fixtures/recordings/<recording_id>/lab/`:
`lab.json` (the run, played back verbatim), `recording.json` (its model responses), `literature.json` (Europe PMC's
responses, verbatim) and `figures/`.

Needs provider keys, SPATIALSCOUT_LIVE_PASSCODE and SPATIALSCOUT_DAILY_BUDGET_USD. Costs cents.

    uv run python scripts/record_lab.py <recording_id>
"""

import asyncio
import json
import shutil
import sys

from spatialscout.agent import utc_now
from spatialscout.contracts import Recording, ReplayInfo
from spatialscout.gateway import ApiKeys, ModelGateway
from spatialscout.gateway.gate import LiveGate
from spatialscout.gateway.live import LiveSource
from spatialscout.gateway.replay import RECORDED_INVESTIGATION_DIR, RecordingWriter
from spatialscout.lab.literature import EuropePmcLive
from spatialscout.lab.run import Finished, run_lab
from spatialscout.settings import Settings


async def record(recording_id: str) -> None:
    settings = Settings.from_env()
    live = settings.live
    if not live.configured:
        raise SystemExit("set SPATIALSCOUT_LIVE_PASSCODE and SPATIALSCOUT_DAILY_BUDGET_USD for a live run")
    gate = LiveGate(passcode=live.passcode, daily_budget_usd=live.daily_budget_usd, spend_dir=live.spend_dir,
                    keys=ApiKeys.from_env(live.env_file), clock=utc_now)
    folder = settings.recordings_dir / recording_id
    finished = Finished(folder / RECORDED_INVESTIGATION_DIR)
    out = folder / "lab"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    writer = RecordingWriter(out / "recording.json", ReplayInfo(
        recording_id=f"{recording_id}-lab", recorded_at=utc_now(), origin="live", question=finished.question,
        note="Lab model responses recorded from one live run; nothing was retried or edited.", dataset_id=None))
    source = LiveSource(gate.client, recording_id=f"{recording_id}-lab")
    europe_pmc = EuropePmcLive()
    try:
        lab = await run_lab(
            finished,
            gateway_for=lambda on_call: ModelGateway(source, utc_now, run_mode="live", on_call=on_call, recorder=writer),
            literature=europe_pmc, artifacts_dir=settings.artifacts_dir, out_dir=out, clock=utc_now, origin="live",
        )
    finally:
        await gate.aclose()
    (out / "literature.json").write_text(json.dumps(europe_pmc.fetched, indent=1) + "\n", encoding="utf-8")
    (out / "lab.json").write_text(lab.model_dump_json(indent=1) + "\n", encoding="utf-8")
    spent = sum(e.call.estimated_cost_usd or 0 for e in lab.events if e.call)
    print(f"{len(lab.tasks)} tasks, {len(lab.events)} events, ${spent:.4f}; written to {out}")
    for e in lab.events:
        print(f"  {e.at_utc.time()} {e.type:18} {e.task_id or '':6} {e.text[:140]}")
    Recording.model_validate_json((out / "recording.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    asyncio.run(record(sys.argv[1]))
