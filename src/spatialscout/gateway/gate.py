"""The live-run gate (ADR-0003): who may start a live run, and on whose account.

- `owner`: the owner's passcode, the server's keys and the owner's daily budget.
- `trial`: anyone, on the server's keys, under a separate small daily trial budget. Off unless the budget is set.
- `byok`: anyone, on keys they send with the request, under a spend cap they choose. The keys live in memory for
  that one investigation only: never written to disk, an event, the audit log or a log line, and gone on restart.
"""

import hmac
import json
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Literal, get_args

import httpx2 as httpx

from .budget import SpendLedger
from .errors import LiveRunRefused
from .live import LiveClient
from .providers import LIST_PRICES, ApiKeys, PriceBook

LiveAccess = Literal["owner", "trial", "byok"]
BYOK_MAX_BUDGET_USD = 5.0
BYOK_DEFAULT_BUDGET_USD = 1.0


class LiveGate:
    """Admits live runs and hands each admitted investigation its live client."""

    def __init__(
        self,
        *,
        passcode: str | None,
        daily_budget_usd: float | None,
        spend_dir: Path | None,
        keys: ApiKeys,
        clock: Callable[[], datetime],
        prices: PriceBook = LIST_PRICES,
        transport: httpx.AsyncBaseTransport | None = None,
        trial_daily_usd: float | None = None,
    ) -> None:
        self._passcode = passcode
        self._clock = clock
        self._prices = prices
        self._transport = transport
        self._client: LiveClient | None = None
        self._trial: LiveClient | None = None
        self._bound: dict[str, LiveClient] = {}
        if passcode and daily_budget_usd is not None and spend_dir is not None:
            self._client = LiveClient(keys, SpendLedger(spend_dir, daily_budget_usd, clock), prices, transport)
        if trial_daily_usd and spend_dir is not None and keys.has("meta"):
            self._trial = LiveClient(keys, SpendLedger(spend_dir / "trial", trial_daily_usd, clock), prices, transport)

    @property
    def enabled(self) -> bool:
        """Whether this server can make live calls at all (bring-your-own-key always can)."""
        return True

    @property
    def access(self) -> list[LiveAccess]:
        out: list[LiveAccess] = ["byok"]
        if self._trial is not None:
            out.insert(0, "trial")
        if self._client is not None:
            out.insert(0, "owner")
        return out

    def trial_remaining_usd(self) -> float | None:
        return None if self._trial is None else max(0.0, self._trial.ledger.remaining_usd())

    @property
    def client(self) -> LiveClient:
        """The owner's live client, for owner-only live tools (SAM 3.1, voice)."""
        if self._client is None:
            raise LiveRunRefused("Owner live runs are not enabled on this server: it has no live passcode and daily budget.")
        return self._client

    def admit(self, passcode: str | None) -> LiveClient:
        """The owner's live client, if this passcode may start a live run now; otherwise LiveRunRefused."""
        if self._client is None or not self._passcode:
            raise LiveRunRefused("Owner live runs are not enabled on this server: it has no live passcode and daily budget.")
        if not passcode or not hmac.compare_digest(passcode.encode(), self._passcode.encode()):
            raise LiveRunRefused("Live runs need the live passcode.")
        if self._client.ledger.remaining_usd() <= 0:
            raise LiveRunRefused("Today's live budget is spent; ask for an immutable replay or a cached tool rerun.")
        return self._client

    def admit_access(self, access: str | None, passcode: str | None, provider_keys: str | None, budget_usd: float | None) -> LiveClient:
        """The live client for this access, or LiveRunRefused. Without an access, the owner's passcode path."""
        if access is None or access == "owner":
            return self.admit(passcode)
        if access not in get_args(LiveAccess):
            raise LiveRunRefused(f"Unknown live access {access!r}; use one of {', '.join(get_args(LiveAccess))}.")
        if access == "trial":
            if self._trial is None:
                raise LiveRunRefused("The live trial is not open on this server.")
            if self._trial.ledger.remaining_usd() <= 0:
                raise LiveRunRefused("Today's live trial budget is spent. Recorded investigations, or your own key, still work.")
            return self._trial
        keys = parse_provider_keys(provider_keys)
        cap = BYOK_DEFAULT_BUDGET_USD if budget_usd is None else budget_usd
        if not 0 < cap <= BYOK_MAX_BUDGET_USD:
            raise LiveRunRefused(f"Your spend cap must be above $0 and at most ${BYOK_MAX_BUDGET_USD:.0f}.")
        ledger = SpendLedger(Path(tempfile.mkdtemp(prefix="spatialscout-byok-")), cap, self._clock)
        return LiveClient(keys, ledger, self._prices, self._transport)

    def bind(self, investigation_id: str, client: LiveClient) -> None:
        self._bound[investigation_id] = client

    def client_for(self, investigation_id: str) -> LiveClient:
        """The client an investigation was admitted with. After a restart an owner run falls back to the owner's
        client; a trial or bring-your-own-key run cannot continue (its keys were never stored)."""
        bound = self._bound.get(investigation_id)
        if bound is not None:
            return bound
        if self._client is not None:
            return self._client
        raise LiveRunRefused("This live run's connection is gone (the server restarted and keys are never stored); start it again.")

    async def aclose(self) -> None:
        closed: set[int] = set()
        for client in [self._client, self._trial, *self._bound.values()]:
            if client is not None and id(client) not in closed:
                closed.add(id(client))
                await client.aclose()


def parse_provider_keys(header: str | None) -> ApiKeys:
    """`X-Provider-Keys`: a JSON object of provider -> key. Meta is required (Muse Wonder and Muse Spark); Baseten or
    Fireworks serves Muse Spark Open, which drafts claims."""
    if not header:
        raise LiveRunRefused("Bring-your-own-key runs need your provider keys in the X-Provider-Keys header.")
    try:
        raw = json.loads(header)
    except ValueError:
        raise LiveRunRefused("X-Provider-Keys must be a JSON object of provider to key.") from None
    if not isinstance(raw, dict):
        raise LiveRunRefused("X-Provider-Keys must be a JSON object of provider to key.")
    allowed = {"meta", "baseten", "fireworks"}
    keys = {p: str(v).strip() for p, v in raw.items() if p in allowed and isinstance(v, str) and v.strip()}
    if "meta" not in keys:
        raise LiveRunRefused("Your Meta API key is required: Muse Wonder plans and Muse Spark reads results.")
    if "baseten" not in keys and "fireworks" not in keys:
        raise LiveRunRefused("A Baseten or Fireworks key is required: Muse Spark Open drafts the claims there.")
    return ApiKeys(keys)  # type: ignore[arg-type]
