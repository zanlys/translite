@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo ==========================================
echo           Translite Server
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python tidak ditemukan.
    echo [!] Install Python 3.9+ dari https://python.org
    echo [!] Pastikan centang "Add Python to PATH" saat install.
    echo.
    pause
    exit /b 1
)

if not exist venv (
    echo [*] Membuat virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [!] Gagal membuat venv.
        pause
        exit /b 1
    )
    echo [*] Virtual environment berhasil dibuat.
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [!] Gagal aktivasi venv. Coba hapus folder venv dan jalankan lagi.
    pause
    exit /b 1
)

python -c "import fastapi, uvicorn, sherpa_onnx, httpx" >nul 2>&1
if errorlevel 1 (
    echo [*] Menginstall dependencies, mohon tunggu...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [!] Gagal install dependencies.
        echo [!] Pastikan koneksi internet aktif lalu coba lagi.
        pause
        exit /b 1
    )
    echo [*] Dependencies berhasil diinstall.
) else (
    echo [*] Dependencies sudah lengkap.
)

set MODEL_DIR=sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17
set MODEL_FILE=%MODEL_DIR%\model.int8.onnx

if not exist "%MODEL_FILE%" (
    echo.
    echo [*] Model SenseVoice belum ada, mengunduh sekitar 155MB...
    echo [*] Jangan tutup window ini.
    echo.
    python -c "import urllib.request, sys; url='https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2'; prog=lambda c,b,t: (sys.stdout.write('\r  [%-20s] %d%%' % ('#'*(min(int(c*b*100/t),100)//5), min(int(c*b*100/t),100))), sys.stdout.flush()); urllib.request.urlretrieve(url,'model.tar.bz2',reporthook=prog); print()"
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
    echo [*] Model berhasil diunduh dan siap digunakan.
)

if not exist config.json (
    echo [*] Membuat config.json dengan nilai default...
    python setup_config.py
    if errorlevel 1 (
        echo [!] Gagal membuat config.json.
        pause
        exit /b 1
    )
)

python -c "import json,sys; c=json.load(open('config.json')); sys.exit(0 if c.get('deepl',{}).get('api_key','') else 1)" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [!] DeepL API Key belum diisi.
    echo [!] Silakan masuk ke menu Settings untuk mengisinya.
    echo.
)

:MAIN_MENU
echo.
echo   1. Start Server
echo   2. Settings
echo   0. Keluar
echo.
set "CHOICE="
set /p CHOICE="  Pilih (1/2/0): "

if "%CHOICE%"=="1" goto START_SERVER
if "%CHOICE%"=="2" goto OPEN_SETTINGS
if "%CHOICE%"=="0" goto END
echo.
echo   [!] Pilihan tidak valid, coba lagi.
goto MAIN_MENU

:START_SERVER
echo.
echo [*] Memulai Translite Server...
echo [*] Tekan Ctrl+C untuk berhenti.
echo.
python main.py
echo.
echo [*] Server berhenti. Tekan sembarang tombol untuk kembali ke menu.
pause >nul
goto MAIN_MENU

:OPEN_SETTINGS
python settings.py
goto MAIN_MENU

:END
echo.
echo   Sampai jumpa!
echo.
endlocal
