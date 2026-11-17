import os
import re
import threading
import numpy as np
import sherpa_onnx

from config_loader import SUPPORTED_LANGUAGES, get_config, normalize_source_language

_recognizer = None
_recognizer_lock = threading.Lock()

MODEL_DIR   = os.path.join(os.path.dirname(__file__), "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17")
MODEL_PATH  = os.path.join(MODEL_DIR, "model.int8.onnx")
TOKENS_PATH = os.path.join(MODEL_DIR, "tokens.txt")


def initialize_recognizer():
    global _recognizer
    if _recognizer is not None:
        return

    with _recognizer_lock:
        if _recognizer is not None:
            return

        stt_config = get_config()["stt"]
        language = normalize_source_language(stt_config.get("language"))
        print("[STT] Memuat SenseVoice Small int8...")
        print(f"[STT]   model      : {MODEL_PATH}")
        print(f"[STT]   tokens     : {TOKENS_PATH}")
        print(f"[STT]   bahasa     : {SUPPORTED_LANGUAGES[language]} ({language})")
        print(f"[STT]   num_threads: {stt_config['num_threads']}")
        recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=MODEL_PATH,
            tokens=TOKENS_PATH,
            language=language,
            use_itn=stt_config["use_itn"],
            num_threads=stt_config["num_threads"],
            decoding_method="greedy_search",
            debug=False,
            provider="cpu",
        )
        _recognizer = recognizer
        print("[STT] Model SenseVoice berhasil dimuat.")


def _get_recognizer():
    if _recognizer is None:
        initialize_recognizer()
    if _recognizer is None:
        raise RuntimeError("SenseVoice recognizer was not initialized.")
    return _recognizer

_RE_TAG        = re.compile(r"<\|[^|]+\|>")
_RE_DOTS       = re.compile(r'\.{4,}')
_RE_COMMAS     = re.compile(r',{2,}')
_RE_LAUGHTER  = re.compile(
    r'^(?:(?:ha|he|ho|hi|hu|lol|lmao|kek|hah|heh|ja|哈|呵|嘻|嘿|は|ひ|ふ|へ|ほ|あ|笑|하|히|호|헤|후|크|푸|ㅋ|ㅎ)){2,}$',
    re.IGNORECASE,
)
_RE_LAUGHTER_NORMALIZE = re.compile(r'[\s\W_]+')


def transcribe_audio(audio_bytes: bytes, sample_rate: int = 16000) -> str:
    if not audio_bytes or len(audio_bytes) < 3200:
        return ""

    audio_np = np.frombuffer(audio_bytes, dtype=np.float32)

    if sample_rate != 16000:
        audio_np = _resample(audio_np, sample_rate, 16000)

    recognizer = _get_recognizer()
    stream = recognizer.create_stream()
    stream.accept_waveform(16000, audio_np)
    recognizer.decode_stream(stream)

    return filter_transcript(stream.result.text)


def filter_transcript(text: str) -> str:
    result = text.strip()
    result = _RE_TAG.sub("", result).strip()

    if not result:
        return ""

    words = result.split()
    if len(words) > 4 and len(set(words)) / len(words) < 0.25:
        return ""

    stripped = result.replace(" ", "")
    if len(stripped) > 8 and len(set(stripped)) <= 3:
        return ""

    result = result.rstrip(",，")
    result = _RE_DOTS.sub('…', result)
    result = _RE_COMMAS.sub('', result)
    result = result.strip(" ,.")

    if len(result) < 2:
        return ""

    normalized_laughter = _RE_LAUGHTER_NORMALIZE.sub("", result.casefold())
    if _RE_LAUGHTER.fullmatch(normalized_laughter):
        return ""

    return result


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    duration   = len(audio) / orig_sr
    target_len = int(duration * target_sr)
    resampled  = np.interp(
        np.linspace(0, len(audio) - 1, target_len),
        np.arange(len(audio)),
        audio,
    )
    return resampled.astype(np.float32)
