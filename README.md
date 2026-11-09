# Translite

Real time Korean → Indonesian subtitle di manapun (YouTube, Weverse, VLive, dll).

**Stack:**
- Chrome Extension (Manifest V3) — audio capture + overlay UI
- Python + FastAPI + WebSocket — local server
- SenseVoice Small int8 (sherpa-onnx) — speech-to-text, berjalan lokal di CPU
- DeepL API — Korean → Indonesian translation

---

## Kebutuhan

- Windows 10/11
- Python 3.9 atau lebih baru — [download](https://python.org) (centang **Add Python to PATH** saat install)
- Google Chrome
- DeepL API Key (Free tier) — [daftar di sini](https://www.deepl.com/pro-api)

---

## Setup

### 1. Download project

Download atau clone repo ini, lalu ekstrak ke folder manapun.

### 2. Jalankan server

Double-click `server/start.bat`.

Saat pertama kali dijalankan, script akan otomatis:
1. Membuat virtual environment Python
2. Menginstall semua dependencies
3. Mengunduh model SenseVoice (~155MB, sekali saja)
4. Membuat file `config.json` dengan nilai default

Setelah itu akan muncul menu:

```
  1. Start Server
  2. Settings
  0. Keluar
```

### 3. Isi DeepL API Key

Pilih **2. Settings** → **1. DeepL API** → ikuti petunjuk untuk mengisi API key.
Simpan dengan memilih **0. Simpan & keluar** di menu Settings.

### 4. Install Chrome Extension

1. Buka Chrome → `chrome://extensions/`
2. Aktifkan **Developer mode** (toggle kanan atas)
3. Klik **Load unpacked** → pilih folder `extension/`
4. Icon Translite muncul di toolbar Chrome

### 5. Mulai pakai

1. Pastikan server sudah berjalan (pilih **1. Start Server** di `start.bat`)
2. Buka tab yang ada audio Korea (YouTube, Weverse, VLive, dll)
3. Klik icon Translite di toolbar
4. Klik **▶ Mulai Subtitle**
5. Subtitle muncul sebagai overlay di bagian bawah halaman

---

## Settings

Semua konfigurasi disimpan di `server/config.json` dan bisa diubah melalui menu **Settings** di `start.bat`.

| Kategori | Setting | Default | Keterangan |
|---|---|---|---|
| **DeepL** | `api_key` | — | Wajib diisi |
| | `free_tier` | `true` | `true` = Free, `false` = Pro |
| | `timeout_seconds` | `3.0` | Timeout request ke DeepL (detik) |
| **Server** | `host` | `localhost` | Ubah ke `0.0.0.0` untuk akses dari luar |
| | `port` | `8765` | Port WebSocket server |
| **STT** | `num_threads` | `2` | Thread CPU untuk inferensi (naikkan sesuai core CPU) |
| | `language` | `ko` | Bahasa input: `ko`, `zh`, `en`, `ja` |
| | `use_itn` | `false` | Normalisasi teks (angka, dll) |
| **VAD** | `silence_trigger_seconds` | `0.20` | Jeda hening sebelum audio diproses (detik) |
| | `max_utterance_seconds` | `6.0` | Durasi maksimal satu kalimat |
| | `min_utterance_seconds` | `0.3` | Durasi minimal sebelum dikirim ke STT |
| | `silence_rms_threshold` | `0.003` | Sensitivitas deteksi suara |
| **Cache** | `cache_size` | `500` | Jumlah terjemahan yang disimpan di memori |

---

## Tips mengurangi latency

Latency E2E rata-rata sekitar 1500–2500ms. Untuk menurunkannya:

- Naikkan `num_threads` sesuai jumlah core CPU (cek via Task Manager)
- Turunkan `silence_trigger_seconds` ke `0.10` untuk respons lebih cepat
- Turunkan `max_utterance_seconds` ke `4.0` (kalimat panjang akan dipotong)
- Tutup aplikasi berat lainnya agar CPU lebih bebas untuk STT

---

## Troubleshooting

**Terminal langsung tutup saat jalankan start.bat**
- Jalankan dari CMD/PowerShell agar bisa membaca pesan errornya:
  ```
  cd server
  start.bat
  ```

**"Server tidak berjalan" di popup extension**
- Pastikan server sudah berjalan dan muncul pesan `[STT] Model SenseVoice berhasil dimuat.`
- Pastikan port 8765 tidak diblokir firewall

**Subtitle tidak muncul**
- Pastikan ada audio yang sedang diputar di tab tersebut
- Buka DevTools extension (klik kanan icon → Inspect popup) untuk cek error

**Model gagal didownload**
- Butuh koneksi internet saat pertama kali
- Hapus file `model.tar.bz2` yang mungkin tersisa di folder `server/`, lalu coba lagi

**Karakter rusak di terminal**
- Gunakan CMD atau PowerShell, bukan terminal lain yang tidak support UTF-8

---

## Struktur Project

```
translite/
├── extension/
│   ├── manifest.json         # Extension config
│   ├── background.js         # Service worker, tabCapture, WebSocket
│   ├── offscreen.html/js     # Audio processing (MV3 requirement)
│   ├── content.js            # Subtitle overlay di halaman web
│   ├── audio-processor.js    # AudioWorklet processor
│   ├── popup.html/js         # UI tombol on/off
│   └── icons/
├── server/
│   ├── main.py               # FastAPI WebSocket server
│   ├── stt.py                # SenseVoice (sherpa-onnx) wrapper
│   ├── translate.py          # DeepL API client
│   ├── config_loader.py      # Loader konfigurasi dari config.json
│   ├── settings.py           # Menu settings interaktif
│   ├── setup_config.py       # Inisialisasi config.json saat pertama kali
│   ├── config.json           # File konfigurasi (dibuat otomatis, tidak dicommit)
│   ├── requirements.txt
│   ├── .env.example
│   └── start.bat             # Entry point — menu Start / Settings
├── .gitignore
└── README.md
```
