"""Record one live investigation on GSE286184 and store it for immutable replay and cached tool reruns.

Runs the orchestrator in live mode (fresh calls to Muse Wonder, Muse Spark 1.3 and Muse Spark Open, under the
passcode and the file-locked daily budget), approves the proposed plan as the researcher, and waits for the end.
Whatever the models and the engine produce is kept as it is (ADR-0001): this script never retries for a different
outcome. The finished investigation directory goes to `fixtures/recordings/<recording_id>/investigation/` and its
live responses to `fixtures/recordings/<recording_id>/recording.json` (origin `live`).

Needs the ingested tables (`make data`), provider keys, `SPATIALSCOUT_LIVE_PASSCODE` and
`SPATIALSCOUT_DAILY_BUDGET_USD`. Costs cents.

    uv run python scripts/record_live_investigation.py <recording_id> "<question>" [dataset_id]
"""

import asyncio
import shutil
import sys
from pathlib import Path

from spatialscout.agent import DEFAULT_REGISTRY, Orchestrator, utc_now
from spatialscout.contracts import TERMINAL_STATUSES, InvestigationStatus, Recording
from spatialscout.data import DatasetStore
from spatialscout.gateway import ApiKeys, RecordingLibrary
from spatialscout.gateway.gate import LiveGate
from spatialscout.gateway.replay import RECORDED_INVESTIGATION_DIR
from spatialscout.settings import Settings


async def wait_for(investigation, statuses, timeout_s: float = 900) -> None:
    for _ in range(int(timeout_s / 0.25)):
        if investigation.state.status in statuses:
            return
        await asyncio.sleep(0.25)
    raise TimeoutError(f"{investigation.investigation_id} stuck at {investigation.state.status}")


async def record(recording_id: str, question: str, dataset_id: str) -> Path:
    settings = Settings.from_env()
    live = settings.live
    if not live.configured:
        raise SystemExit("set SPATIALSCOUT_LIVE_PASSCODE and SPATIALSCOUT_DAILY_BUDGET_USD for a live run")
    gate = LiveGate(
        passcode=live.passcode, daily_budget_usd=live.daily_budget_usd, spend_dir=live.spend_dir,
        keys=ApiKeys.from_env(live.env_file), clock=utc_now,
    )
    orchestrator = Orchestrator(
        store=DatasetStore(settings.fixtures_dir, artifacts_dir=settings.artifacts_dir, processed_dir=settings.processed_dir),
        recordings=RecordingLibrary(settings.recordings_dir),
        registry=DEFAULT_REGISTRY,
        investigations_dir=settings.investigations_dir,
        dataset_id=dataset_id,
        live_gate=gate,
    )
    investigation = orchestrator.start(question, "live", passcode=live.passcode, dataset_id=dataset_id)
    print(f"{investigation.investigation_id}: planning")
    await wait_for(investigation, {InvestigationStatus.AWAITING_APPROVAL, *TERMINAL_STATUSES})
    plan = investigation.plan()
    if plan is not None:
        print(f"plan: {plan.summary}")
        for step in plan.steps:
            print(f"  {step.tool} {step.arguments}")
        orchestrator.approve(investigation.investigation_id)
        await wait_for(investigation, TERMINAL_STATUSES)
    await orchestrator.shutdown()
    print(f"{investigation.investigation_id}: {investigation.state.status.value}")

    destination = settings.recordings_dir / recording_id
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(investigation.directory, destination / RECORDED_INVESTIGATION_DIR)
    recorded_path = destination / RECORDED_INVESTIGATION_DIR / "recording.json"
    recording = Recording.model_validate_json(recorded_path.read_text(encoding="utf-8"))
    recorded_path.unlink()
    info = recording.info.model_copy(update={"recording_id": recording_id, "note": "Model responses recorded from one live run; nothing was retried or edited."})
    (destination / "recording.json").write_text(Recording(info=info, calls=recording.calls).model_dump_json(indent=1) + "\n", encoding="utf-8")
    return destination


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    dataset_id = sys.argv[3] if len(sys.argv) > 3 else "GSE286184"
    print(f"recorded in {asyncio.run(record(sys.argv[1], sys.argv[2], dataset_id))}")


if __name__ == "__main__":
    main()
