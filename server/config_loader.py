import os
import json
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

_DEFAULTS = {
    "deepl": {
        "api_key": "",
        "free_tier": True,
        "timeout_seconds": 3.0,
    },
    "stt": {
        "num_threads": 2,
        "use_itn": False,
    },
    "vad": {
        "silence_trigger_seconds": 0.20,
        "max_utterance_seconds": 6.0,
        "min_utterance_seconds": 0.3,
        "silence_rms_threshold": 0.003,
        "max_silence_buffer_extra": 2,
    },
    "translate": {
        "cache_size": 500,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config() -> dict:
    cfg = _deep_merge({}, _DEFAULTS)

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            file_cfg.pop("_comment", None)
            cfg = _deep_merge(cfg, file_cfg)
        except Exception as e:
            print(f"[Config] Gagal baca config.json: {e}, pakai default.")

    if not cfg["deepl"]["api_key"]:
        env_key = os.getenv("DEEPL_API_KEY", "")
        if env_key:
            cfg["deepl"]["api_key"] = env_key

    if not cfg["deepl"]["api_key"]:
        cfg["deepl"]["free_tier"] = os.getenv("DEEPL_FREE", "true").lower() == "true"

    return cfg


def save_config(cfg: dict):
    save = {k: v for k, v in cfg.items() if k != "_comment"}
    save["_comment"] = "Translite configuration file. Edit via Settings menu or manually."
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(save, f, indent=2, ensure_ascii=False)


_config: dict | None = None


def get_config() -> dict:
    global _config
    if _config is None:
        _config = load_config()
    return _config
