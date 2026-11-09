import os
import asyncio
import base64
import json
import time

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from stt import transcribe_audio
from translate import translate_ko_to_id

load_dotenv()

HOST = os.getenv("SERVER_HOST", "localhost")
PORT = int(os.getenv("SERVER_PORT", "8765"))

app = FastAPI(title="Translite Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_RATE           = 16000
FRAME_BYTES           = int(SAMPLE_RATE * 0.1 * 4)
MAX_UTTERANCE_S       = 6.0
MAX_UTTERANCE_B       = int(SAMPLE_RATE * MAX_UTTERANCE_S * 4)
SILENCE_TRIGGER_S     = 0.35
SILENCE_FRAMES        = int(SILENCE_TRIGGER_S / 0.1)
SILENCE_RMS_THRESHOLD = 0.003
MIN_UTTERANCE_B       = int(SAMPLE_RATE * 0.3 * 4)


class LatencyTracker:
    def __init__(self, name: str, max_samples: int = 100):
        self.name = name
        self._samples: list[float] = []
        self._max = max_samples

    def record(self, ms: float):
        self._samples.append(ms)
        if len(self._samples) > self._max:
            self._samples.pop(0)

    def p50(self) -> float:
        if not self._samples: return 0.0
        s = sorted(self._samples)
        return s[int(len(s) * 0.50)]

    def p95(self) -> float:
        if not self._samples: return 0.0
        s = sorted(self._samples)
        return s[int(len(s) * 0.95)]

    def report(self) -> str:
        return (f"[{self.name}] p50={self.p50():.0f}ms "
                f"p95={self.p95():.0f}ms (n={len(self._samples)})")


lat_stt   = LatencyTracker("STT")
lat_trans = LatencyTracker("Translation")
lat_e2e   = LatencyTracker("E2E")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "server": "translite",
        "latency": {
            "stt_p50_ms":   round(lat_stt.p50()),
            "stt_p95_ms":   round(lat_stt.p95()),
            "trans_p50_ms": round(lat_trans.p50()),
            "trans_p95_ms": round(lat_trans.p95()),
            "e2e_p50_ms":   round(lat_e2e.p50()),
            "e2e_p95_ms":   round(lat_e2e.p95()),
        }
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("[WS] Klien terhubung.")

    audio_buffer        = bytearray()
    last_transcript     = ""
    stt_seq             = 0
    trans_seq           = 0
    stt_active          = False
    silence_frame_count = 0
    has_voice_started   = False
    pending_translations: dict[int, str] = {}
    latest_sent_seq     = -1
    chunk_recv_ts: dict[int, float] = {}

    translate_queue: asyncio.Queue = asyncio.Queue(maxsize=5)

    async def translation_worker():
        nonlocal trans_seq, latest_sent_seq
        while True:
            try:
                item = await asyncio.wait_for(translate_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if item is None:
                break

            seq, transcript, recv_ts = item

            if not translate_queue.empty():
                try:
                    peek_seq = translate_queue._queue[0][0]
                    if peek_seq > seq + 2:
                        print(f"[Trans] Skip seq {seq}, ada seq {peek_seq} lebih baru")
                        translate_queue.task_done()
                        continue
                except (IndexError, AttributeError):
                    pass

            t_start = time.monotonic()
            try:
                translation = await translate_ko_to_id(transcript)
            except Exception as e:
                print(f"[Trans] Error seq {seq}: {e}")
                translate_queue.task_done()
                continue
            finally:
                translate_queue.task_done()

            t_trans_ms = (time.monotonic() - t_start) * 1000
            lat_trans.record(t_trans_ms)

            if seq <= latest_sent_seq:
                print(f"[Trans] Drop seq {seq} (sudah kirim seq {latest_sent_seq})")
                continue

            latest_sent_seq = seq

            if recv_ts > 0:
                e2e_ms = (time.monotonic() - recv_ts) * 1000
                lat_e2e.record(e2e_ms)
            else:
                e2e_ms = 0

            total_ms = round(e2e_ms)
            print(f"[Trans {t_trans_ms:.0f}ms | E2E {total_ms}ms] seq={seq}")
            print(f"  KO: {transcript}")
            print(f"  ID: {translation}")

            try:
                await ws.send_text(json.dumps({
                    "type":       "subtitle",
                    "korean":     transcript,
                    "indonesian": translation,
                    "latency_ms": total_ms,
                    "seq":        seq,
                }))
            except Exception as e:
                print(f"[Trans] Gagal kirim ke client: {e}")

    trans_worker_task = asyncio.create_task(translation_worker())

    async def run_stt(pcm: bytes, seq: int, recv_ts: float):
        nonlocal last_transcript, stt_active

        t_start = time.monotonic()
        try:
            loop       = asyncio.get_running_loop()
            transcript = await loop.run_in_executor(None, transcribe_audio, pcm, SAMPLE_RATE)
        except Exception as e:
            print(f"[STT] Error seq {seq}: {e}")
            return
        finally:
            stt_active = False

        t_stt_ms = (time.monotonic() - t_start) * 1000
        lat_stt.record(t_stt_ms)

        if not transcript:
            return

        if transcript != last_transcript:
            try:
                await ws.send_text(json.dumps({
                    "type":   "partial",
                    "korean": transcript,
                    "seq":    seq,
                }))
            except Exception:
                pass

        last_transcript = transcript

        print(f"[STT {t_stt_ms:.0f}ms] seq={seq} KO: {transcript}")

        try:
            translate_queue.put_nowait((seq, transcript, recv_ts))
        except asyncio.QueueFull:
            try:
                old = translate_queue.get_nowait()
                translate_queue.task_done()
                print(f"[Queue] Buang terjemahan lama seq={old[0]} (antrian penuh)")
            except asyncio.QueueEmpty:
                pass
            try:
                translate_queue.put_nowait((seq, transcript, recv_ts))
            except asyncio.QueueFull:
                print(f"[Queue] Gagal masukkan seq={seq}, skip")

    try:
        report_timer = time.monotonic()

        while True:
            message  = await ws.receive_text()
            data     = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "audio_chunk":
                chunk_b64 = data.get("data", "")
                if not chunk_b64:
                    continue

                recv_ts     = time.monotonic()
                chunk_bytes = base64.b64decode(chunk_b64)
                frame_np    = np.frombuffer(chunk_bytes, dtype=np.float32)
                frame_rms   = float(np.sqrt(np.mean(frame_np ** 2))) if len(frame_np) else 0.0
                is_voice    = frame_rms > SILENCE_RMS_THRESHOLD

                if is_voice:
                    silence_frame_count = 0
                    has_voice_started   = True
                    audio_buffer.extend(chunk_bytes)
                else:
                    if has_voice_started:
                        silence_frame_count += 1
                        audio_buffer.extend(chunk_bytes)

                flush_reason = None
                if has_voice_started and len(audio_buffer) >= MIN_UTTERANCE_B:
                    if silence_frame_count >= SILENCE_FRAMES:
                        flush_reason = "silence"
                    elif len(audio_buffer) >= MAX_UTTERANCE_B:
                        flush_reason = "max_length"

                if flush_reason and not stt_active:
                    process_bytes = bytes(audio_buffer)
                    print(f"[VAD] Flush utterance ({flush_reason}), "
                          f"≈ {len(process_bytes) / (SAMPLE_RATE * 4):.2f}s")

                    audio_buffer.clear()
                    silence_frame_count = 0
                    has_voice_started   = False

                    stt_active = True
                    stt_seq   += 1
                    asyncio.create_task(run_stt(process_bytes, stt_seq, recv_ts))

                if time.monotonic() - report_timer > 60.0:
                    report_timer = time.monotonic()
                    print(lat_stt.report())
                    print(lat_trans.report())
                    print(lat_e2e.report())
                    print(f"[Queue] translate_queue size: {translate_queue.qsize()}")

            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "reset":
                audio_buffer.clear()
                last_transcript     = ""
                stt_active          = False
                stt_seq             = 0
                latest_sent_seq     = -1
                silence_frame_count = 0
                has_voice_started   = False

                while not translate_queue.empty():
                    try:
                        translate_queue.get_nowait()
                        translate_queue.task_done()
                    except asyncio.QueueEmpty:
                        break
                print("[WS] Buffer direset.")

    except WebSocketDisconnect:
        print("[WS] Klien terputus.")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        await translate_queue.put(None)
        try:
            await asyncio.wait_for(trans_worker_task, timeout=3.0)
        except asyncio.TimeoutError:
            trans_worker_task.cancel()

        print(lat_stt.report())
        print(lat_trans.report())
        print(lat_e2e.report())
        print("[WS] Koneksi ditutup.")


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, log_level="info", reload=False)
