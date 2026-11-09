import os
import re
import numpy as np
import sherpa_onnx
from dotenv import load_dotenv

load_dotenv()

MODEL_DIR = os.getenv(
    "SENSEVOICE_MODEL_DIR",
    os.path.join(os.path.dirname(__file__),
                 "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17")
)

MODEL_PATH  = os.path.join(MODEL_DIR, "model.int8.onnx")
TOKENS_PATH = os.path.join(MODEL_DIR, "tokens.txt")

print(f"[STT] Memuat SenseVoice Small int8...")
print(f"[STT]   model : {MODEL_PATH}")
print(f"[STT]   tokens: {TOKENS_PATH}")

asr = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=MODEL_PATH,
    tokens=TOKENS_PATH,
    language="ko",
    use_itn=False,
    num_threads=4,
    decoding_method="greedy_search",
    debug=False,
    provider="cpu",
)

print("[STT] Model SenseVoice berhasil dimuat.")


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
    result = re.sub(r"<\|[^|]+\|>", "", result).strip()

    if not result:
        return ""

    words = result.split()
    if len(words) > 4 and len(set(words)) / len(words) < 0.25:
        return ""

    stripped = result.replace(" ", "")
    if len(stripped) > 8 and len(set(stripped)) <= 3:
        return ""

    result = result.rstrip(",，")
    result = re.sub(r'\.{4,}', '…', result)
    result = re.sub(r',{2,}', '', result)
    result = result.strip(" ,.")

    if len(result) < 2:
        return ""

    normalized = re.sub(r'[\s\-_.,!?~ㅋㅎ하하하하하하]', '', result.lower())

    laugh_only_patterns = [
        r'^[ㅋ]+$',
        r'^[ㅎ]+$',
        r'^(하)+$',
        r'^(히)+$',
        r'^(호)+$',
        r'^(헤)+$',
        r'^(후)+$',
        r'^(크)+$',
        r'^(푸)+$',
    ]

    stripped_laugh = re.sub(r'[\s]', '', result)
    for pattern in laugh_only_patterns:
        if re.fullmatch(pattern, stripped_laugh):
            return ""

    laugh_chars = set('ㅋㅎ')
    char_count  = len([c for c in result if c not in (' ', '\n')])
    laugh_count = len([c for c in result if c in laugh_chars])
    if char_count > 0 and laugh_count / char_count > 0.7:
        return ""

    laugh_en_pattern = r'^(ha|he|ho|hi|hu|lol|lmao|kek|hah|heh){2,}[!~]*$'
    if re.fullmatch(laugh_en_pattern, normalized, re.IGNORECASE):
        return ""

    return result


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    duration = len(audio) / orig_sr
    target_len = int(duration * target_sr)
    resampled = np.interp(
        np.linspace(0, len(audio) - 1, target_len),
        np.arange(len(audio)),
        audio,
    )
    return resampled.astype(np.float32)
