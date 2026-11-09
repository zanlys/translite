import json
import os
import sys

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def _load() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("\n[OK] Konfigurasi disimpan ke config.json")


def _ask(prompt: str, current, cast=str, choices: list = None):
    display = "true" if (cast == bool and current) else "false" if cast == bool else str(current)
    suffix = f" [{display}]: "
    while True:
        raw = input(prompt + suffix).strip()
        if raw == "":
            return current
        if cast == bool:
            if raw.lower() in ("true", "ya", "y", "1"):
                return True
            if raw.lower() in ("false", "tidak", "n", "0"):
                return False
            print("  Masukkan: true / false")
            continue
        if choices and raw not in [str(c) for c in choices]:
            print(f"  Pilihan valid: {', '.join(str(c) for c in choices)}")
            continue
        try:
            return cast(raw)
        except ValueError:
            print("  Format tidak valid, coba lagi.")


def _header(title: str):
    print()
    print("=" * 50)
    print(f"  {title}")
    print("=" * 50)


def _section(title: str):
    print()
    print(f"-- {title} " + "-" * (45 - len(title)))


def menu_deepl(cfg: dict):
    _header("Settings > DeepL API")
    d = cfg.setdefault("deepl", {})

    current_key = d.get("api_key", "")
    masked = (current_key[:8] + "..." + current_key[-4:]) if len(current_key) > 12 else (current_key or "(belum diisi)")
    print(f"\n  API Key saat ini: {masked}")

    if input("  Ganti API Key? (y/n) [n]: ").strip().lower() == "y":
        new_key = input("  Masukkan API Key baru: ").strip()
        if new_key:
            d["api_key"] = new_key

    d["free_tier"]       = _ask("  Gunakan Free tier? (true=gratis, false=Pro)", d.get("free_tier", True), bool)
    d["timeout_seconds"] = _ask("  Timeout request DeepL (detik)", d.get("timeout_seconds", 3.0), float)


def menu_stt(cfg: dict):
    _header("Settings > STT (Speech-to-Text)")
    s = cfg.setdefault("stt", {})

    print()
    print("  num_threads : jumlah CPU thread untuk inferensi model.")
    print("                Lebih banyak = lebih cepat (sampai batas core CPU).")
    s["num_threads"] = _ask("  num_threads", s.get("num_threads", 2), int)

    print()
    print("  use_itn     : normalisasi teks (angka, dll). Biasanya false untuk subtitle.")
    s["use_itn"] = _ask("  use_itn", s.get("use_itn", False), bool)


def menu_vad(cfg: dict):
    _header("Settings > VAD (Voice Activity Detection)")
    v = cfg.setdefault("vad", {})

    print()
    print("  silence_trigger_seconds : jeda hening sebelum audio diproses.")
    print("                            Lebih kecil = lebih responsif. Rekomendasi: 0.10-0.30")
    v["silence_trigger_seconds"] = _ask("  silence_trigger_seconds", v.get("silence_trigger_seconds", 0.20), float)

    print()
    print("  max_utterance_seconds   : durasi maksimal satu kalimat.")
    print("                            Lebih kecil = latensi lebih rendah. Rekomendasi: 4.0-6.0")
    v["max_utterance_seconds"] = _ask("  max_utterance_seconds", v.get("max_utterance_seconds", 6.0), float)

    print()
    print("  min_utterance_seconds   : durasi minimal sebelum dikirim ke STT. Rekomendasi: 0.2-0.5")
    v["min_utterance_seconds"] = _ask("  min_utterance_seconds", v.get("min_utterance_seconds", 0.3), float)

    print()
    print("  silence_rms_threshold   : sensitivitas deteksi suara. Rekomendasi: 0.001-0.005")
    v["silence_rms_threshold"] = _ask("  silence_rms_threshold", v.get("silence_rms_threshold", 0.003), float)


def menu_translate(cfg: dict):
    _header("Settings > Translate Cache")
    t = cfg.setdefault("translate", {})
    print()
    print("  cache_size : jumlah terjemahan yang disimpan di memori.")
    print("               Lebih besar = hemat quota DeepL untuk kalimat berulang.")
    t["cache_size"] = _ask("  cache_size", t.get("cache_size", 500), int)


def show_summary(cfg: dict):
    _header("Konfigurasi Saat Ini")

    d  = cfg.get("deepl", {})
    st = cfg.get("stt", {})
    v  = cfg.get("vad", {})
    tr = cfg.get("translate", {})

    key = d.get("api_key", "")
    masked_key = (key[:8] + "..." + key[-4:]) if len(key) > 12 else (key or "(belum diisi)")

    _section("DeepL")
    print(f"  API Key    : {masked_key}")
    print(f"  Tier       : {'Free' if d.get('free_tier', True) else 'Pro'}")
    print(f"  Timeout    : {d.get('timeout_seconds', 3.0)}s")

    _section("STT")
    print(f"  num_threads: {st.get('num_threads', 2)}")
    print(f"  use_itn    : {st.get('use_itn', False)}")

    _section("VAD")
    print(f"  silence_trigger  : {v.get('silence_trigger_seconds', 0.20)}s")
    print(f"  max_utterance    : {v.get('max_utterance_seconds', 6.0)}s")
    print(f"  min_utterance    : {v.get('min_utterance_seconds', 0.3)}s")
    print(f"  rms_threshold    : {v.get('silence_rms_threshold', 0.003)}")

    _section("Translate")
    print(f"  cache_size : {tr.get('cache_size', 500)}")
    print()


def reset_defaults(cfg: dict):
    _header("Reset ke Default")
    if input("  Yakin reset semua konfigurasi ke default? (y/n) [n]: ").strip().lower() == "y":
        saved_key = cfg.get("deepl", {}).get("api_key", "")
        cfg.clear()
        cfg.update({
            "deepl":     {"api_key": saved_key, "free_tier": True, "timeout_seconds": 3.0},
            "stt":       {"num_threads": 2, "use_itn": False},
            "vad":       {"silence_trigger_seconds": 0.20, "max_utterance_seconds": 6.0, "min_utterance_seconds": 0.3, "silence_rms_threshold": 0.003, "max_silence_buffer_extra": 2},
            "translate": {"cache_size": 500},
        })
        print("  [OK] Reset selesai. API Key tetap dipertahankan.")
    else:
        print("  Dibatalkan.")


def main():
    print()
    print("==========================================")
    print("        Translite -- Settings             ")
    print("==========================================")

    cfg = _load()

    while True:
        print()
        print("  1. DeepL API")
        print("  2. STT (threads, bahasa)")
        print("  3. VAD (sensitivitas, timing)")
        print("  4. Translate Cache")
        print("  5. Lihat semua konfigurasi")
        print("  6. Reset ke default")
        print("  0. Simpan & keluar")
        print()

        choice = input("  Pilih menu: ").strip()

        if choice == "1":
            menu_deepl(cfg)
        elif choice == "2":
            menu_stt(cfg)
        elif choice == "3":
            menu_vad(cfg)
        elif choice == "4":
            menu_translate(cfg)
        elif choice == "5":
            show_summary(cfg)
        elif choice == "6":
            reset_defaults(cfg)
        elif choice == "0":
            _save(cfg)
            print("  Sampai jumpa!")
            sys.exit(0)
        else:
            print("  Pilihan tidak valid.")


if __name__ == "__main__":
    main()
