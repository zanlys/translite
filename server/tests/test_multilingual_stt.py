import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from config_loader import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_source_language
import main
import stt
from stt import filter_transcript


class InteractiveInput(io.StringIO):
    def isatty(self):
        return True


class SourceLanguageTests(unittest.TestCase):
    def test_lists_the_languages_supported_by_the_model(self):
        self.assertEqual({"zh", "en", "ja", "ko", "yue"}, set(SUPPORTED_LANGUAGES))

    def test_uses_korean_for_missing_or_unsupported_language(self):
        self.assertEqual(DEFAULT_LANGUAGE, normalize_source_language(None))
        self.assertEqual(DEFAULT_LANGUAGE, normalize_source_language("fr"))
        self.assertEqual("yue", normalize_source_language("yue"))

    def test_initializes_sensevoice_with_the_selected_language(self):
        previous_recognizer = stt._recognizer
        stt._recognizer = None
        config = {"stt": {"language": "yue", "num_threads": 2, "use_itn": False}}
        try:
            with patch.object(stt, "get_config", return_value=config):
                with patch.object(
                    stt.sherpa_onnx.OfflineRecognizer,
                    "from_sense_voice",
                    return_value=object(),
                ) as create_recognizer:
                    stt.initialize_recognizer()
            self.assertEqual("yue", create_recognizer.call_args.kwargs["language"])
        finally:
            stt._recognizer = previous_recognizer

    def test_server_start_prompt_applies_the_selected_language(self):
        config = {"stt": {"language": "ko"}}
        interactive_input = InteractiveInput("5\n")
        with patch.object(main, "_cfg", config):
            with patch.object(main.sys, "stdin", interactive_input):
                with redirect_stdout(io.StringIO()):
                    main.choose_source_language()
        self.assertEqual("yue", config["stt"]["language"])


class MultilingualTranscriptFilterTests(unittest.TestCase):
    def test_filters_laughter_in_supported_scripts(self):
        for laughter in ("hahaha", "哈哈哈", "ははは", "ㅋㅋㅋ", "하하하"):
            with self.subTest(laughter=laughter):
                self.assertEqual("", filter_transcript(laughter))

    def test_preserves_valid_multilingual_speech(self):
        for speech in ("Hello, how are you?", "你好世界", "こんにちは", "안녕하세요"):
            with self.subTest(speech=speech):
                self.assertTrue(filter_transcript(speech))

    def test_filters_repeated_words_and_removes_sensevoice_tags(self):
        self.assertEqual("", filter_transcript("hello hello hello hello hello"))
        self.assertEqual("你好世界", filter_transcript("<|zh|>你好世界"))


if __name__ == "__main__":
    unittest.main()
