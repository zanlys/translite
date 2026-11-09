import os
import re
import numpy as np
import sherpa_onnx

from config_loader import get_config

_cfg     = get_config()
_stt_cfg = _cfg["stt"]

MODEL_DIR   = os.path.join(os.path.dirname(__file__), "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17")
MODEL_PATH  = os.path.join(MODEL_DIR, "model.int8.onnx")
TOKENS_PATH = os.path.join(MODEL_DIR, "tokens.txt")

print(f"[STT] Memuat SenseVoice Small int8...")
print(f"[STT]   model      : {MODEL_PATH}")
print(f"[STT]   tokens     : {TOKENS_PATH}")
print(f"[STT]   num_threads: {_stt_cfg['num_threads']}")

asr = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=MODEL_PATH,
    tokens=TOKENS_PATH,
    language="ko",
    use_itn=_stt_cfg["use_itn"],
    num_threads=_stt_cfg["num_threads"],
    decoding_method="greedy_search",
    debug=False,
    provider="cpu",
)

print("[STT] Model SenseVoice berhasil dimuat.")

_RE_TAG        = re.compile(r"<\|[^|]+\|>")
_RE_DOTS       = re.compile(r'\.{4,}')
_RE_COMMAS     = re.compile(r',{2,}')
_RE_NORMALIZE  = re.compile(r'[\s\-_.,!?~ㅋㅎ하하하하하하]')
_RE_WHITESPACE = re.compile(r'[\s]')
_RE_LAUGH_EN   = re.compile(r'^(ha|he|ho|hi|hu|lol|lmao|kek|hah|heh){2,}[!~]*$', re.IGNORECASE)
_RE_LAUGH_PATTERNS = re.compile(
    r'^[ㅋ]+$|^[ㅎ]+$|^(하)+$|^(히)+$|^(호)+$|^(헤)+$|^(후)+$|^(크)+$|^(푸)+$'
)
_LAUGH_CHARS = set('ㅋㅎ')


def transcribe_audio(audio_bytes: bytes, sample_rate: int = 16000) -> str:
    if not audio_bytes or len(audio_bytes) < 3200:
        return ""

    audio_np = np.frombuffer(audio_bytes, dtype=np.float32)

    if sample_rate != 16000:
        audio_np = _resample(audio_np, sample_rate, 16000)

    stream = asr.create_stream()
    stream.accept_waveform(16000, audio_np)
    asr.decode_stream(stream)

    result = stream.result.text.strip()
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

    normalized    = _RE_NORMALIZE.sub('', result.lower())
    stripped_laugh = _RE_WHITESPACE.sub('', result)

    if _RE_LAUGH_PATTERNS.fullmatch(stripped_laugh):
        return ""

    char_count  = len([c for c in result if c not in (' ', '\n')])
    laugh_count = len([c for c in result if c in _LAUGH_CHARS])
    if char_count > 0 and laugh_count / char_count > 0.7:
        return ""

    if _RE_LAUGH_EN.fullmatch(normalized):
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
