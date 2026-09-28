import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

_test_root = tempfile.TemporaryDirectory()
os.environ["BOT_ENV_FILE"] = str(Path(_test_root.name) / "no-secrets.env")
os.environ["BOT_DATA_DIR"] = str(Path(_test_root.name) / "data")
os.environ["ADMIN_TELEGRAM_ID"] = "42"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["NEWSAPI_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["TMDB_TOKEN"] = ""
os.environ["PEXELS_API_KEY"] = ""

import bot  # noqa: E402
from entnews.storage import Store  # noqa: E402


class BotTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        bot._store = Store(Path(self.directory.name) / "bot.sqlite3")

    def test_startup_requires_token_but_not_an_admin_id(self):
        with patch.object(bot, "TELEGRAM_BOT_TOKEN", ""):
            with self.assertRaisesRegex(SystemExit, "TELEGRAM_BOT_TOKEN"):
                bot.build_app()
        with (
            patch.object(
                bot,
                "TELEGRAM_BOT_TOKEN",
                "123456789:" + "a" * 35,
            ),
            patch.object(bot, "ADMIN_ID", 0),
        ):
            self.assertIsNotNone(bot.build_app())

    async def test_public_updates_are_allowed_in_private_chat_and_blocked_in_groups(self):
        private_context = SimpleNamespace(chat_data={})
        private_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=77, type="private"),
            callback_query=None,
            effective_message=SimpleNamespace(text="/start"),
        )
        await bot.prepare_public_update(private_update, private_context)
        self.assertEqual(private_context.chat_data["chat_id"], 77)

        group_message = SimpleNamespace(text="/start", reply_text=AsyncMock())
        group_update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=-1001, type="supergroup"),
            callback_query=None,
            effective_message=group_message,
        )
        with self.assertRaises(bot.ApplicationHandlerStop):
            await bot.prepare_public_update(group_update, SimpleNamespace(chat_data={}))
        group_message.reply_text.assert_awaited_once()

    def test_public_draft_limits_apply_per_chat_and_globally(self):
        context = SimpleNamespace(chat_data={"chat_id": 77})
        now = datetime(2026, 9, 28, 12, tzinfo=bot.YANGON)
        with (
            patch.object(bot, "ADMIN_ID", 42),
            patch.object(bot, "MAX_PUBLIC_DRAFTS_PER_DAY", 2),
            patch.object(bot, "MAX_PUBLIC_DRAFTS_GLOBAL_PER_DAY", 3),
            patch.object(bot, "PUBLIC_DRAFT_COOLDOWN_SECONDS", 0),
            patch.object(bot, "now_local", return_value=now),
        ):
            self.assertIsNone(bot.public_generation_limit_message(context))
            self.assertIsNone(bot.public_generation_limit_message(context))
            self.assertIn("Daily public draft limit", bot.public_generation_limit_message(context))
            other_context = SimpleNamespace(chat_data={"chat_id": 78})
            self.assertIsNone(bot.public_generation_limit_message(other_context))
            self.assertIn("daily draft capacity", bot.public_generation_limit_message(other_context))

    def test_operator_commands_are_hidden_from_public_command_menu(self):
        public_names = {command.command for command in bot.telegram_bot_commands()}
        admin_names = {command.command for command in bot.telegram_bot_commands(admin=True)}
        self.assertNotIn("status", public_names)
        self.assertNotIn("setkey", public_names)
        self.assertTrue({"status", "setkey"}.issubset(admin_names))

    def test_publication_time_is_parsed_and_missing_dates_are_rejected(self):
        with patch.object(
            bot, "now_local", return_value=datetime(2026, 9, 25, 12, tzinfo=bot.YANGON)
        ):
            self.assertTrue(bot.fresh_article({"publishedAt": "2026-09-24T04:00:00Z"}))
            self.assertFalse(bot.fresh_article({"publishedAt": "2026-09-01T04:00:00Z"}))
            self.assertFalse(bot.fresh_article({"publishedAt": ""}))
            self.assertFalse(bot.fresh_article({"publishedAt": "2026-09-26T04:00:00Z"}))

    def test_today_requires_local_date_and_release_language(self):
        with patch.object(
            bot, "now_local", return_value=datetime(2026, 9, 25, 12, tzinfo=bot.YANGON)
        ):
            tmdb = {"provider": "TMDB", "release_date": "2026-09-25"}
            self.assertTrue(bot.fresh_article(tmdb, today_only=True))
            self.assertFalse(
                bot.fresh_article({**tmdb, "release_date": "2026-09-24"}, today_only=True)
            )
            news = {"title": "Movie releases today", "publishedAt": "2026-09-25T04:00:00Z"}
            self.assertTrue(bot.fresh_article(news, today_only=True))
            self.assertFalse(
                bot.fresh_article({**news, "title": "Movie opens soon"}, today_only=True)
            )

    def test_upcoming_parser_rejects_invalid_or_zero_dates(self):
        self.assertIsNone(bot.parse_upcoming_window(["2026-00-12"]))
        self.assertIsNone(bot.parse_upcoming_window(["2026-02-00"]))
        self.assertIsNone(bot.parse_upcoming_window(["2026-09-31"]))
        self.assertIsNone(bot.parse_upcoming_window(["Jan 0 2027"]))
        result = bot.parse_upcoming_window(["2026-09-25"])
        self.assertEqual(result[:2], (date(2026, 9, 25), date(2026, 9, 25)))

    async def test_upcoming_results_are_filtered_against_actual_date_range(self):
        results = [
            {"id": 1, "title": "Inside", "release_date": "2026-09-25"},
            {"id": 2, "title": "Before", "release_date": "2026-09-24"},
            {"id": 3, "title": "Unknown"},
        ]
        with (
            patch.object(bot, "TMDB_TOKEN", "configured"),
            patch.object(
                bot,
                "tmdb_get",
                new=AsyncMock(side_effect=[({"results": results}, None), ({"results": []}, None)]),
            ),
        ):
            fetched = await bot.fetch_tmdb_upcoming_range(date(2026, 9, 25), date(2026, 9, 30))
        self.assertEqual([article["tmdb_id"] for article in fetched], [1])

    async def test_failed_generation_is_explicitly_fallback_and_not_saved(self):
        article = {"title": "A movie", "description": "A summary", "url": "https://example.org"}
        with patch.object(bot, "GEMINI_API_KEY", ""):
            result = await bot.generate_article_text(article)
        self.assertFalse(result.generated)
        self.assertIn("not a completed draft", result.text)
        self.assertEqual(bot.get_store().posts(), [])

    async def test_burmese_prompt_labels_catalogue_metadata_and_bounds_instructions(self):
        prompt = bot.build_burmese_post_prompt(
            {
                "provider": "TMDB",
                "content_kind": "title_metadata",
                "title": "Movie — TMDB Trending",
                "description": "Release: 2026-10-02\nA short catalogue overview.",
                "release_date": "2026-10-02",
            },
            instructions="x" * 900,
        )
        self.assertIn("not translating or paraphrasing the English source sentence by sentence", prompt)
        self.assertIn("treat this as catalogue information, not breaking news", prompt)
        self.assertIn("Length: 6–8 flowing paragraphs, approximately 280–420 Burmese words", prompt)
        self.assertIn('"title": "Movie"', prompt)
        self.assertNotIn("TMDB Trending", prompt)
        self.assertNotIn('"description": "Release:', prompt)
        self.assertIn("EDITOR_REWRITE_REQUEST: " + "x" * 800, prompt)

    def test_gemini_prefers_flash_with_lite_as_fallback(self):
        with (
            patch.object(bot, "GEMINI_MODEL", "gemini-3.5-flash"),
            patch.object(bot, "GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite"),
        ):
            self.assertEqual(
                bot._gemini_model_order(),
                ("gemini-3.5-flash", "gemini-3.5-flash-lite"),
            )

    def test_gemini_does_not_retry_quota_exhaustion(self):
        error = RuntimeError("RESOURCE_EXHAUSTED HTTP 429")
        error.code = 429
        self.assertFalse(bot._gemini_is_retryable(error))

    async def test_empty_search_cache_refetches_same_search_before_using_a_number(self):
        context = SimpleNamespace(chat_data={"chat_id": 11})
        bot.update_chat(
            context, selection={"kind": "search", "query": "Dune", "label": "Search: Dune"}
        )
        story = {"title": "Dune", "url": "https://example.org/dune"}
        update = SimpleNamespace()
        with (
            patch.object(bot, "current_articles", return_value=[]),
            patch.object(bot, "search_all_sources", new=AsyncMock(return_value=[story])) as search,
            patch.object(bot, "fetch_news", new=AsyncMock()) as topic_fetch,
            patch.object(bot, "create_from_article", new=AsyncMock()) as create,
        ):
            await bot.create_from_index(update, context, 1)
        search.assert_awaited_once_with("Dune")
        topic_fetch.assert_not_awaited()
        create.assert_awaited_once()
        self.assertEqual(create.await_args.args[2], story)

    async def test_empty_results_never_create_a_different_story(self):
        context = SimpleNamespace(chat_data={"chat_id": 12})
        bot.update_chat(
            context, selection={"kind": "search", "query": "Missing", "label": "Search"}
        )
        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=12), effective_message=SimpleNamespace()
        )
        update.effective_message.reply_text = AsyncMock()
        with (
            patch.object(bot, "current_articles", return_value=[]),
            patch.object(bot, "search_all_sources", new=AsyncMock(return_value=[])),
            patch.object(bot, "create_from_article", new=AsyncMock()) as create,
            patch.object(bot, "send_chat_text", new=AsyncMock()) as reply,
        ):
            await bot.create_from_index(update, context, 1)
        create.assert_not_awaited()
        reply.assert_awaited_once()

    async def test_photo_query_uses_title_and_album_attribution_lists_each_photo(self):
        query = bot.photo_query_from_article({"title": "Dune Part Two — TMDB Trending"})
        self.assertEqual(query, "Dune Part Two")
        photos = [
            {
                "url": "https://example.org/a.jpg",
                "caption": "A",
                "provider": "Commons",
                "creator": "Artist",
                "license": "CC BY",
                "source_url": "https://example.org/a",
            },
            {
                "url": "https://example.org/b.jpg",
                "caption": "B",
                "provider": "Openverse",
                "creator": "Maker",
                "license": "CC0",
            },
        ]
        update = type(
            "UpdateStub",
            (),
            {"effective_chat": type("ChatStub", (), {"id": 1})(), "get_bot": lambda self: None},
        )()
        context = type(
            "ContextStub",
            (),
            {
                "bot": type(
                    "BotStub",
                    (),
                    {
                        "send_media_group": AsyncMock(),
                        "send_message": AsyncMock(),
                        "send_photo": AsyncMock(),
                    },
                )()
            },
        )()
        await bot.send_photos(update, context, photos, "Photo results")
        context.bot.send_media_group.assert_awaited_once()
        credit_message = context.bot.send_message.await_args.kwargs["text"]
        self.assertIn("Artist", credit_message)
        self.assertIn("Maker", credit_message)
        self.assertIn("https://example.org/a", credit_message)


if __name__ == "__main__":
    unittest.main()
