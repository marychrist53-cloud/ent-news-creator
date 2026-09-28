"""HTTP lifecycle, provider health, and secret-safe logging."""

import asyncio
import logging
import re
from datetime import datetime, timezone

import httpx


class SecretFormatter(logging.Formatter):
    def __init__(self, secrets, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secrets = secrets

    def format(self, record):
        text = super().format(record)
        for value in self.secrets():
            if value and len(value) > 5:
                text = text.replace(value, "[REDACTED]")
        return re.sub(r"bot\d+:[A-Za-z0-9_-]+", "bot[REDACTED]", text)


class HttpService:
    def __init__(self):
        self.client = None
        self.limit = asyncio.Semaphore(6)

    async def get(self, url, params=None, headers=None):
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(15, connect=5),
                follow_redirects=True,
                limits=httpx.Limits(max_connections=8, max_keepalive_connections=6),
            )
        async with self.limit:
            for attempt in range(2):
                try:
                    response = await self.client.get(url, params=params, headers=headers)
                    if response.status_code not in (429, 500, 502, 503, 504) or attempt:
                        return response
                except httpx.TransportError:
                    if attempt:
                        raise
                await asyncio.sleep(0.5)
        raise RuntimeError("HTTP retry loop ended unexpectedly")

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None


class Health:
    def __init__(self):
        self.states = {}

    def record(self, name, ok, error=""):
        previous = self.states.get(name, {})
        self.states[name] = {
            "last_attempt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "last_success": datetime.now(timezone.utc).isoformat(timespec="seconds")
            if ok
            else previous.get("last_success"),
            "failures": 0 if ok else previous.get("failures", 0) + 1,
            "error": "" if ok else error,
        }

    async def fetch(self, name, awaitable, timeout=65):
        try:
            result = await asyncio.wait_for(awaitable, timeout=timeout)
            self.record(name, bool(result), "No usable results")
            return result
        except Exception as exc:
            self.record(name, False, type(exc).__name__)
            logging.getLogger("ent-news-bot").warning(
                "Provider %s failed (%s)", name, type(exc).__name__
            )
            return []

    def lines(self):
        return [
            f"{name}: last success {state['last_success'] or 'never'}; failures {state['failures']}"
            for name, state in sorted(self.states.items())
        ]
