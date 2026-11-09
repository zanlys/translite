import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ENV_PATH    = os.path.join(os.path.dirname(__file__), ".env")


def _read_env_key() -> str:
    if not os.path.exists(ENV_PATH):
        return ""
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPL_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def main():
    api_key = _read_env_key()

    cfg = {
        "_comment": "Translite configuration file. Edit via Settings menu or manually.",
        "deepl": {
            "api_key": api_key,
            "free_tier": True,
            "timeout_seconds": 3.0
        },
        "stt": {
            "num_threads": 2,
            "use_itn": False
        },
        "vad": {
            "silence_trigger_seconds": 0.20,
            "max_utterance_seconds": 6.0,
            "min_utterance_seconds": 0.3,
            "silence_rms_threshold": 0.003,
            "max_silence_buffer_extra": 2
        },
        "translate": {
            "cache_size": 500
        }
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    if api_key:
        print("[*] config.json dibuat (API key dari .env disalin otomatis).")
    else:
        print("[*] config.json dibuat. Isi DeepL API Key via menu Settings.")


if __name__ == "__main__":
    main()
