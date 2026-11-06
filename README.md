# Translite

Real time Korean → Indonesian subtitle di manapun (YouTube, Weverse, VLive, dll).

**Stack:**
- Chrome Extension (Manifest V3) — audio capture + overlay UI
- Python + FastAPI + WebSocket — local server
- SenseVoice Small int8 (sherpa-onnx) — speech-to-text, berjalan lokal di CPU
- DeepL API — Korean → Indonesian translation

---

## Setup

### 1. DeepL API Key

1. Daftar di https://www.deepl.com/pro-api (Free tier = 500K karakter/bulan)
2. Salin API key, nanti diisi di file `.env`

### 2. Server Python

**Cara mudah — double-click:**

```
server/start.bat
```

`start.bat` akan otomatis: membuat venv → install dependencies → download model (~155MB, sekali saja) → menjalankan server.

**Cara manual lewat terminal:**

```cmd
cd server
copy .env.example .env
```

Edit `.env`, isi `DEEPL_API_KEY`:

```
DEEPL_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx
DEEPL_FREE=true
```

Lalu setup dan jalankan:

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Untuk menjalankan berikutnya (venv sudah ada):

```cmd
cd server
venv\Scripts\activate
python main.py
```

Server berjalan di `ws://localhost:8765`. Pertama kali start, model SenseVoice (~155MB) akan didownload otomatis — tunggu sampai muncul pesan `[STT] Model SenseVoice berhasil dimuat.`

### 3. Chrome Extension

1. Buka Chrome → `chrome://extensions/`
2. Aktifkan **Developer mode** (toggle kanan atas)
3. Klik **Load unpacked** → pilih folder `extension/`
4. Extension muncul di toolbar

### 4. Penggunaan

1. Pastikan server sudah berjalan
2. Buka tab yang ada audio Korea (YouTube, Weverse, VLive, dll)
3. Klik icon Translite di toolbar
4. Klik **▶ Mulai Subtitle**
5. Subtitle muncul sebagai overlay di bagian bawah halaman

---

## Konfigurasi

Edit file `server/.env`:

| Key | Default | Keterangan |
|-----|---------|------------|
| `DEEPL_API_KEY` | — | **Wajib diisi** |
| `DEEPL_FREE` | `true` | `true` = Free tier, `false` = Pro |
| `SERVER_HOST` | `localhost` | Host server |
| `SERVER_PORT` | `8765` | Port WebSocket server |

---

## Troubleshooting

**Subtitle tidak muncul:**
- Pastikan server sudah berjalan dan muncul pesan model loaded
- Cek console DevTools extension: klik kanan icon → Inspect popup
- Pastikan ada audio yang sedang diputar di tab tersebut

**"Server tidak berjalan" di popup:**
- Jalankan `start.bat` atau `python main.py` di folder `server/`
- Pastikan port 8765 tidak diblokir firewall

**Model gagal didownload:**
- Butuh koneksi internet saat pertama kali
- Hapus file `model.tar.bz2` yang mungkin tersisa lalu coba lagi
- Model tersimpan di `server/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/`

**Delay terlalu besar:**
- Tutup aplikasi berat lainnya untuk membebaskan CPU
- Pastikan menggunakan model int8 (sudah default)

---

## Struktur Project

```
translite/
├── extension/
│   ├── manifest.json       # Extension config
│   ├── background.js       # Service worker, tabCapture, WebSocket
│   ├── offscreen.html/js   # Audio processing (MV3 requirement)
│   ├── content.js          # Subtitle overlay di halaman web
│   ├── audio-processor.js  # AudioWorklet processor
│   ├── popup.html/js       # UI tombol on/off
│   └── icons/              # Icon PNG
├── server/
│   ├── main.py             # FastAPI WebSocket server
│   ├── stt.py              # SenseVoice (sherpa-onnx) wrapper
│   ├── translate.py        # DeepL API client
│   ├── requirements.txt
│   ├── .env.example
│   └── start.bat           # Windows quick-start
├── .gitignore
└── README.md
```
