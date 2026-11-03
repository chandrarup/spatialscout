"""The live-run gate: a passcode, a configured daily budget, and budget left today (ADR-0003)."""

import hmac
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import httpx2 as httpx

from .budget import SpendLedger
from .errors import LiveRunRefused
from .live import LiveClient
from .providers import LIST_PRICES, ApiKeys, PriceBook


class LiveGate:
    """Admits live runs and owns the one live client they share. `None` passcode or budget refuses every run."""

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
    ) -> None:
        self._passcode = passcode
        self._client: LiveClient | None = None
        if passcode and daily_budget_usd is not None and spend_dir is not None:
            self._client = LiveClient(keys, SpendLedger(spend_dir, daily_budget_usd, clock), prices, transport)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> LiveClient:
        """The shared live client, for a live investigation already admitted (for example one approved later)."""
        if self._client is None:
            raise LiveRunRefused("Live runs are not enabled on this server: it has no live passcode and daily budget.")
        return self._client

    def admit(self, passcode: str | None) -> LiveClient:
        """The live client, if this passcode may start a live run now; otherwise LiveRunRefused."""
        if self._client is None or not self._passcode:
            raise LiveRunRefused("Live runs are not enabled on this server: it has no live passcode and daily budget.")
        if not passcode or not hmac.compare_digest(passcode.encode(), self._passcode.encode()):
            raise LiveRunRefused("Live runs need the live passcode.")
        if self._client.ledger.remaining_usd() <= 0:
            raise LiveRunRefused("Today's live budget is spent; ask for an immutable replay or a cached tool rerun.")
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
