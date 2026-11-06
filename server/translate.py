import os
import httpx
from dotenv import load_dotenv

load_dotenv()

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
IS_FREE       = os.getenv("DEEPL_FREE", "true").lower() == "true"
BASE_URL      = (
    "https://api-free.deepl.com/v2/translate"
    if IS_FREE else
    "https://api.deepl.com/v2/translate"
)

_cache:       dict[str, str] = {}
_cache_order: list[str]      = []
CACHE_MAX = 500

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        limits = httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10,
            keepalive_expiry=30,
        )

        _client = httpx.AsyncClient(timeout=3.0, limits=limits)
    return _client


def _cache_put(key: str, value: str):
    if key in _cache:
        _cache_order.remove(key)
    elif len(_cache) >= CACHE_MAX:
        oldest = _cache_order.pop(0)
        del _cache[oldest]
    _cache[key] = value
    _cache_order.append(key)


async def translate_ko_to_id(text: str) -> str:
    if not text or not text.strip():
        return ""

    if not DEEPL_API_KEY:
        return text

    if text in _cache:
        return _cache[text]

    try:
        client   = _get_client()
        response = await client.post(
            BASE_URL,
            headers={
                "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "text":        [text],
                "source_lang": "KO",
                "target_lang": "ID",
            },
        )
        response.raise_for_status()
        translated = response.json()["translations"][0]["text"]
        _cache_put(text, translated)
        return translated

    except httpx.TimeoutException:
        print(f"[Terjemah] DeepL timeout, tampilkan teks Korea.")
        return text
    except httpx.HTTPStatusError as e:
        print(f"[Terjemah] HTTP {e.response.status_code}: {e.response.text}")
        return text
    except Exception as e:
        print(f"[Terjemah] Error: {e}")
        return text
