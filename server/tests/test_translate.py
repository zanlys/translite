import unittest
from unittest.mock import patch

import translate


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"translations": [{"text": "terjemahan"}]}


class FakeClient:
    def __init__(self):
        self.payload = None

    async def post(self, url, headers, json):
        self.payload = json
        return FakeResponse()


class DeepLSourceLanguageTests(unittest.IsolatedAsyncioTestCase):
    async def test_lets_deepl_detect_the_source_language(self):
        client = FakeClient()
        translate._cache.clear()
        with patch.object(translate, "DEEPL_API_KEY", "test-key"):
            with patch.object(translate, "_get_client", return_value=client):
                result = await translate.translate_to_indonesian("你好世界")

        self.assertEqual("terjemahan", result)
        self.assertEqual("ID", client.payload["target_lang"])
        self.assertNotIn("source_lang", client.payload)
