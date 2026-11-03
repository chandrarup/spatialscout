"""Record a whole investigation for immutable replay: run the recorded question as a cached tool rerun, approve
its plan, and copy the finished investigation directory (state.json, events.jsonl, audit_log.jsonl, artifacts/,
package.zip) to `fixtures/recordings/<recording_id>/investigation/`.

No model is called: the run serves the recording's stored responses, so it inherits that recording's origin
(hand-authored for the walking skeleton). Run after `build_skeleton_recording.py`; `make fixtures` runs both.

    uv run python scripts/record_replay_investigation.py [recording_id]
"""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

from spatialscout.agent import DEFAULT_REGISTRY, Orchestrator
from spatialscout.contracts import TERMINAL_STATUSES, InvestigationStatus
from spatialscout.data import DatasetStore
from spatialscout.gateway import RecordingLibrary
from spatialscout.gateway.replay import RECORDED_INVESTIGATION_DIR
from spatialscout.settings import Settings

DEFAULT_RECORDING = "syn01-podocyte-lrp2"


async def wait_for(investigation, statuses) -> None:
    for _ in range(600):
        if investigation.state.status in statuses:
            return
        await asyncio.sleep(0.05)
    raise TimeoutError(f"{investigation.investigation_id} stuck at {investigation.state.status}")


async def record(recording_id: str) -> Path:
    settings = Settings.from_env()
    recording_dir = settings.recordings_dir / recording_id
    destination = recording_dir / RECORDED_INVESTIGATION_DIR
    if destination.exists():
        shutil.rmtree(destination)  # so the library below serves stored responses, not the old replay
    library = RecordingLibrary(settings.recordings_dir)
    question = next(info.question for info in library.infos() if info.recording_id == recording_id)
    with tempfile.TemporaryDirectory() as scratch:
        orchestrator = Orchestrator(
            store=DatasetStore(settings.fixtures_dir),
            recordings=library,
            registry=DEFAULT_REGISTRY,
            investigations_dir=Path(scratch),
            dataset_id=settings.dataset_id,
        )
        investigation = orchestrator.start(question, "cached_tool_rerun")
        await wait_for(investigation, {InvestigationStatus.AWAITING_APPROVAL, *TERMINAL_STATUSES})
        orchestrator.approve(investigation.investigation_id)
        await wait_for(investigation, TERMINAL_STATUSES)
        await orchestrator.shutdown()
        if investigation.state.status != InvestigationStatus.COMPLETE:
            raise SystemExit(f"the recorded run failed: {investigation.events[-1]}")
        shutil.copytree(investigation.directory, destination)
    return destination


def main() -> None:
    recording_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RECORDING
    destination = asyncio.run(record(recording_id))
    events = (destination / "events.jsonl").read_text().splitlines()
    print(f"recorded {len(events)} events for immutable replay in {destination}")


if __name__ == "__main__":
    main()
