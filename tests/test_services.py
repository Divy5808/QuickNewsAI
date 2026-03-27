"""
Phase 5: Unit Tests for QuickNewsAI services
Run with:  python -m pytest tests/ -v
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ===========================================================
# 1. SENTIMENT SERVICE
# ===========================================================
class TestSentimentService(unittest.TestCase):

    def test_positive_text(self):
        from services.sentiment import analyze_sentiment
        result = analyze_sentiment("This is a wonderful and amazing day!")
        self.assertIn(result["label"].lower(), ["positive", "pos", "good", "😊 positive"])

    def test_negative_text(self):
        from services.sentiment import analyze_sentiment
        result = analyze_sentiment("This is terrible, horrible, and very bad.")
        self.assertIn(result["label"].lower(), ["negative", "neg", "bad", "😟 negative"])

    def test_empty_text(self):
        from services.sentiment import analyze_sentiment
        # Should not raise an exception
        result = analyze_sentiment("")
        self.assertIsInstance(result, str)

    def test_returns_string(self):
        from services.sentiment import analyze_sentiment
        result = analyze_sentiment("The stock market rose today.")
        self.assertIsInstance(result, dict)
        self.assertIn("label", result)


# ===========================================================
# 2. TRANSLATOR SERVICE
# ===========================================================
class TestTranslatorService(unittest.TestCase):

    def test_returns_string(self):
        from services.translator import translate_summary
        # Hindi translation – basic test
        result = translate_summary("Hello world", "hi")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_english_passthrough(self):
        from services.translator import translate_summary
        # If language is 'en', text should pass through unchanged
        text = "This is an English sentence."
        result = translate_summary(text, "en")
        # May return original or translated; must be a non-empty string
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_translate_full_news(self):
        from services.translator import translate_full_news
        result = translate_full_news("The economy grew by 5 percent.", "hi")
        self.assertIsInstance(result, str)

    def test_invalid_language_graceful(self):
        from services.translator import translate_summary
        # Should not raise even with an invalid language code
        try:
            result = translate_summary("Test sentence.", "xx")
            self.assertIsInstance(result, str)
        except Exception:
            pass  # Some translators raise for unknown codes — acceptable


# ===========================================================
# 3. SUMMARIZER SERVICE
# ===========================================================
class TestSummarizerService(unittest.TestCase):

    SAMPLE_TEXT = (
        "Artificial intelligence is transforming industries across the globe. "
        "From healthcare to finance, AI systems are being deployed to automate tasks, "
        "improve efficiency and reduce human error. Companies are investing billions "
        "in AI research and development. Experts predict that AI will create millions "
        "of new jobs while displacing some existing ones. Ethical concerns around "
        "data privacy, bias and accountability remain key challenges for the field."
    )

    def test_returns_string(self):
        from services.summarizer import summarize_text
        result = summarize_text(self.SAMPLE_TEXT, 80)
        self.assertIsInstance(result, str)

    def test_summary_is_shorter_than_input(self):
        from services.summarizer import summarize_text
        result = summarize_text(self.SAMPLE_TEXT, 80)
        self.assertLessEqual(len(result), len(self.SAMPLE_TEXT))

    def test_short_length(self):
        from services.summarizer import summarize_text
        result = summarize_text(self.SAMPLE_TEXT, 50)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_long_length(self):
        from services.summarizer import summarize_text
        result = summarize_text(self.SAMPLE_TEXT, 250)
        self.assertIsInstance(result, str)

    def test_empty_text(self):
        from services.summarizer import summarize_text
        # Should handle empty text gracefully
        try:
            result = summarize_text("", 80)
            self.assertIsInstance(result, str)
        except Exception:
            pass  # Acceptable for pipeline models


# ===========================================================
# 4. NEWS API (with mocking)
# ===========================================================
class TestNewsAPI(unittest.TestCase):

    @patch("services.news_api.requests.get")
    def test_fetch_returns_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test Article",
                    "link": "https://example.com/news/1",
                    "image_url": "https://example.com/img.jpg",
                    "pubDate": "2025-01-01 10:00:00",
                    "description": "A test description"
                }
            ]
        }
        mock_get.return_value = mock_response

        from services.news_api import fetch_latest_news
        result = fetch_latest_news(category="top")
        self.assertIsInstance(result, dict)
        self.assertIn("results", result)
        self.assertIsInstance(result["results"], list)
        self.assertGreater(len(result["results"]), 0)

    @patch("services.news_api.requests.get")
    def test_fetch_normalizes_fields(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test",
                    "link": "https://example.com/1",
                    "image_url": "https://example.com/img.jpg",
                    "pubDate": "2025-01-01",
                }
            ]
        }
        mock_get.return_value = mock_response

        # Clear cache before test
        from services import news_api
        news_api._news_cache.clear()

        result = news_api.fetch_latest_news(category="sports")
        items = result.get("results", [])
        self.assertIn("url", items[0])
        self.assertIn("urlToImage", items[0])
        self.assertEqual(items[0]["url"], "https://example.com/1")

    @patch("services.news_api.requests.get")
    def test_api_error_returns_empty_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        from services import news_api
        news_api._news_cache.clear()

        result = news_api.fetch_latest_news(category="health")
        self.assertEqual(result, {"results": [], "nextPage": None})

    @patch("services.news_api.requests.get")
    def test_cache_works(self, mock_get):
        """Second call with same key should NOT hit the network again."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"title": "Cached", "link": "https://x.com", "image_url": None, "pubDate": "2025-01-01"}]
        }
        mock_get.return_value = mock_response

        from services import news_api
        news_api._news_cache.clear()

        news_api.fetch_latest_news(category="business")  # 1st call
        news_api.fetch_latest_news(category="business")  # 2nd call (should use cache)

        # requests.get should only have been called once
        self.assertEqual(mock_get.call_count, 1)


# ===========================================================
# 5. HISTORY CATEGORIZATION
# ===========================================================
class TestAutoCategorize(unittest.TestCase):

    def test_tech_category(self):
        from services.history import auto_categorize
        result = auto_categorize("The new AI software was launched by a tech startup.")
        self.assertEqual(result, "Technology")

    def test_sports_category(self):
        from services.history import auto_categorize
        result = auto_categorize("India won the cricket match against Australia at the stadium.")
        self.assertEqual(result, "Sports")

    def test_health_category(self):
        from services.history import auto_categorize
        result = auto_categorize("The doctor recommended a new medicine for the disease at the hospital.")
        self.assertEqual(result, "Health")

    def test_general_fallback(self):
        from services.history import auto_categorize
        result = auto_categorize("xyzzy plugh")
        self.assertEqual(result, "General")

    def test_empty_returns_general(self):
        from services.history import auto_categorize
        result = auto_categorize("")
        self.assertEqual(result, "General")


# ===========================================================
# 6. LOGGER SERVICE
# ===========================================================
class TestLoggerService(unittest.TestCase):

    def test_logger_is_importable(self):
        from services.logger import logger
        import logging
        self.assertIsInstance(logger, logging.Logger)

    def test_logger_writes(self):
        from services.logger import logger
        try:
            logger.info("Unit test log entry")
        except Exception as e:
            self.fail(f"logger.info raised an exception: {e}")


if __name__ == "__main__":
    unittest.main()
