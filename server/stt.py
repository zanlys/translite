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
    num_threads=2,
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

    if len(result) > 150:
        result = result[:150].rsplit(" ", 1)[0]

    stripped = result.replace(" ", "")
    if len(stripped) > 10 and len(set(stripped)) <= 3:
        return ""

    words = result.split()
    if len(words) > 5 and len(set(words)) / len(words) < 0.25:
        return ""

    result = result.rstrip(",，")
    result = re.sub(r'\.{4,}', '…', result)
    result = re.sub(r',{2,}', '', result)
    result = result.strip(" ,.")

    if len(result) < 2:
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
