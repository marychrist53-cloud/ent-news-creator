import asyncio
import logging
import unittest

import httpx

from entnews.runtime import Health, HttpService, SecretFormatter


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_failure_does_not_cancel_success(self):
        health = Health()

        async def fail():
            raise ValueError("private error")

        async def good():
            return [{"title": "OK"}]

        results = await asyncio.gather(health.fetch("bad", fail()), health.fetch("good", good()))
        self.assertEqual(results, [[], [{"title": "OK"}]])
        self.assertEqual(health.states["bad"]["error"], "ValueError")
        self.assertEqual(health.states["good"]["failures"], 0)

    async def test_timeout_is_bounded_and_recovery_clears_failures(self):
        health = Health()
        self.assertEqual(await health.fetch("slow", asyncio.sleep(1), timeout=0.001), [])
        self.assertEqual(health.states["slow"]["failures"], 1)
        health.record("slow", True)
        self.assertEqual(health.states["slow"]["failures"], 0)
        self.assertTrue(health.states["slow"]["last_success"])

    async def test_http_retries_server_error_once_and_closes(self):
        requests = []

        def transport(request):
            requests.append(request)
            return httpx.Response(503 if len(requests) == 1 else 200, json={"ok": True})

        service = HttpService()
        client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
        service.client = client
        self.assertEqual((await service.get("https://example.org")).status_code, 200)
        self.assertEqual(len(requests), 2)
        await service.close()
        self.assertTrue(client.is_closed)

    async def test_http_does_not_retry_authentication_error(self):
        requests = []

        def transport(request):
            requests.append(request)
            return httpx.Response(401)

        service = HttpService()
        service.client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
        await service.get("https://example.org")
        self.assertEqual(len(requests), 1)
        await service.close()

    def test_secret_redaction_includes_tracebacks(self):
        secret = "not-a-real-secret-for-testing"
        formatter = SecretFormatter(lambda: [secret])
        try:
            raise ValueError(secret)
        except ValueError as exc:
            record = logging.LogRecord(
                "test", 40, "test", 1, "Failure " + secret, (), (type(exc), exc, exc.__traceback__)
            )
        rendered = formatter.format(record)
        self.assertNotIn(secret, rendered)
        self.assertIn("ValueError: [REDACTED]", rendered)
