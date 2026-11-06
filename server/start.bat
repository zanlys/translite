@echo off
setlocal
echo ================================
echo       Translite Server
echo ================================
echo.

cd /d "%~dp0"

if not exist .env (
    echo [*] File .env belum ada, membuat dari template...
    copy .env.example .env >nul
    echo.
    echo [!] Buka file server\.env dan isi DEEPL_API_KEY kamu.
    echo [!] Setelah diisi, jalankan start.bat lagi.
    echo.
    pause
    exit /b 1
)

findstr /r "DEEPL_API_KEY=.\+" .env >nul 2>&1
if errorlevel 1 (
    echo [!] DEEPL_API_KEY di file .env belum diisi!
    echo [!] Buka server\.env dan isi API key kamu.
    echo.
    pause
    exit /b 1
)

if not exist venv (
    echo [*] Membuat virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [!] Gagal membuat venv. Pastikan Python 3.9+ sudah terinstall.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

python -c "import fastapi, uvicorn, sherpa_onnx, dotenv, httpx" >nul 2>&1
if errorlevel 1 (
    echo [*] Menginstall dependencies, mohon tunggu...
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [!] Gagal install dependencies.
        pause
        exit /b 1
    )
    echo [*] Dependencies berhasil diinstall.
) else (
    echo [*] Dependencies sudah terinstall.
)

set MODEL_DIR=sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17
set MODEL_FILE=%MODEL_DIR%\model.int8.onnx

if not exist "%MODEL_FILE%" (
    echo.
    echo [*] Model SenseVoice belum ada.
    echo [*] Mengunduh model ^(~155MB^), mohon tunggu...
    echo [*] Jangan tutup window ini.
    echo.
    python -c ^
        "import urllib.request, sys; ^
         url = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2'; ^
         def progress(count, block, total): ^
             pct = min(int(count*block*100/total), 100); ^
             bar = '#'*(pct//5) + '-'*(20-pct//5); ^
             sys.stdout.write(f'\r  [{bar}] {pct}%%'); sys.stdout.flush() ^
         ; ^
         urllib.request.urlretrieve(url, 'model.tar.bz2', reporthook=progress); ^
         print()"
    if errorlevel 1 (
        echo.
        echo [!] Gagal mengunduh model. Cek koneksi internet dan coba lagi.
        if exist model.tar.bz2 del model.tar.bz2
        pause
        exit /b 1
    )
    echo [*] Mengekstrak model...
    python -c "import tarfile, os; tarfile.open('model.tar.bz2').extractall('.'); os.remove('model.tar.bz2')"
    if errorlevel 1 (
        echo [!] Gagal mengekstrak model.
        pause
        exit /b 1
    )
    echo [*] Model berhasil diunduh dan diekstrak.
)

echo.
echo [*] Memulai server di ws://localhost:8765
echo [*] Tekan Ctrl+C untuk berhenti
echo.
python main.py

pause
