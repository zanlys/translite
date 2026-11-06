import os
import asyncio
import base64
import json
import time

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

SAMPLE_RATE = 16000
WINDOW_DURATION = 2.0
STEP_DURATION = 0.5
WINDOW_BYTES = int(SAMPLE_RATE * WINDOW_DURATION * 4)
STEP_BYTES = int(SAMPLE_RATE * STEP_DURATION * 4)


@app.get("/health")
async def health():
    return {"status": "ok", "server": "translite"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("[WS] Klien terhubung.")

    audio_buffer = bytearray()
    new_bytes_since_last = 0
    last_transcript = ""
    processing = False

    try:
        while True:
            message = await ws.receive_text()
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "audio_chunk":
                chunk_b64 = data.get("data", "")
                if not chunk_b64:
                    continue

                chunk_bytes = base64.b64decode(chunk_b64)
                audio_buffer.extend(chunk_bytes)
                new_bytes_since_last += len(chunk_bytes)

                if len(audio_buffer) > WINDOW_BYTES * 2:
                    audio_buffer = audio_buffer[-WINDOW_BYTES * 2:]

                buf_sec = len(audio_buffer) / 4 / SAMPLE_RATE
                new_sec = new_bytes_since_last / 4 / SAMPLE_RATE
                print(f"[Audio] buffer={buf_sec:.1f}s  baru={new_sec:.2f}s  processing={processing}")

                if (new_bytes_since_last >= STEP_BYTES
                        and len(audio_buffer) >= WINDOW_BYTES
                        and not processing):

                    process_bytes = bytes(audio_buffer[-WINDOW_BYTES:])
                    new_bytes_since_last = 0
                    processing = True

                    async def run_pipeline(pcm: bytes):
                        nonlocal last_transcript, processing
                        t_start = time.monotonic()
                        try:
                            transcript = await asyncio.get_event_loop().run_in_executor(
                                None, transcribe_audio, pcm, SAMPLE_RATE
                            )
                            t_stt = time.monotonic() - t_start

                            if not transcript or transcript == last_transcript:
                                return

                            last_transcript = transcript
                            translation = await translate_ko_to_id(transcript)
                            t_total = time.monotonic() - t_start

                            print(f"[{t_stt:.2f}s stt / {t_total:.2f}s total] KO: {transcript}")
                            print(f"  ID: {translation}")

                            await ws.send_text(json.dumps({
                                "type": "subtitle",
                                "korean": transcript,
                                "indonesian": translation,
                                "latency_ms": round(t_total * 1000),
                            }))
                        except Exception as e:
                            print(f"[Pipeline] Error: {e}")
                        finally:
                            processing = False

                    asyncio.create_task(run_pipeline(process_bytes))

            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "reset":
                audio_buffer.clear()
                new_bytes_since_last = 0
                last_transcript = ""
                processing = False
                print("[WS] Buffer direset.")

    except WebSocketDisconnect:
        print("[WS] Klien terputus.")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, log_level="info", reload=False)
