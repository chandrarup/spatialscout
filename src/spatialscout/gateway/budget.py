"""The daily spend budget for live calls: reserve before a call, settle after it (ADR-0003).

One JSON file per UTC day under the spend directory holds what was spent and what is reserved. Every change
reads, checks and rewrites that file while holding an exclusive `flock` on a lock file beside it, so parallel
calls (threads, event loops or processes sharing the directory) can never reserve more than the budget.
`flock` is used rather than `lockf`: `lockf` locks belong to the process, so threads would not exclude each
other. The lock is never held across an `await`.
"""

import fcntl
import json
import os
import secrets
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .errors import BudgetExhausted

# A reservation older than this belongs to a call that died without settling; it stops holding budget.
STALE_RESERVATION = timedelta(minutes=15)


class SpendLedger:
    def __init__(self, directory: Path, daily_budget_usd: float, clock: Callable[[], datetime]) -> None:
        self._directory = Path(directory)
        self.daily_budget_usd = daily_budget_usd
        self._clock = clock

    def reserve(self, amount_usd: float, label: str) -> str:
        """Hold `amount_usd` of today's budget for one call, or raise BudgetExhausted. Returns the reservation id."""
        reservation_id = secrets.token_hex(8)
        with self._day() as day:
            committed = day["spent_usd"] + sum(r["amount_usd"] for r in day["reserved"].values())
            if committed + amount_usd > self.daily_budget_usd + 1e-12:
                raise BudgetExhausted(
                    f"live call refused: it could cost ${amount_usd:.4f}, and only "
                    f"${max(self.daily_budget_usd - committed, 0):.4f} of today's ${self.daily_budget_usd:.2f} budget is left"
                )
            day["reserved"][reservation_id] = {"amount_usd": amount_usd, "label": label, "at": self._clock().isoformat()}
        return reservation_id

    def settle(self, reservation_id: str, actual_usd: float) -> None:
        """Release a reservation and record what the call really cost (zero if it failed before any work)."""
        with self._day() as day:
            day["reserved"].pop(reservation_id, None)
            day["spent_usd"] += actual_usd
            day["calls"] += 1

    def remaining_usd(self) -> float:
        with self._day() as day:
            committed = day["spent_usd"] + sum(r["amount_usd"] for r in day["reserved"].values())
        return max(self.daily_budget_usd - committed, 0.0)

    def spent_usd(self) -> float:
        with self._day() as day:
            return day["spent_usd"]

    @contextmanager
    def _day(self) -> Iterator[dict[str, Any]]:
        now = self._clock()
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"spend-{now.date().isoformat()}.json"
        with (self._directory / "spend.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                day = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"spent_usd": 0.0, "reserved": {}, "calls": 0}
                day["reserved"] = {
                    k: r for k, r in day["reserved"].items() if now - datetime.fromisoformat(r["at"]) < STALE_RESERVATION
                }
                yield day
                temporary = path.with_suffix(".tmp")
                temporary.write_text(json.dumps(day, indent=1), encoding="utf-8")
                os.replace(temporary, path)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
