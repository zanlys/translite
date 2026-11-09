import urllib.request
import sys
import os
import tarfile

URL      = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2"
ARCHIVE  = "model.tar.bz2"


def progress(count, block_size, total_size):
    if total_size <= 0:
        return
    pct  = min(int(count * block_size * 100 / total_size), 100)
    bar  = "#" * (pct // 5) + "-" * (20 - pct // 5)
    sys.stdout.write(f"\r  [{bar}] {pct}%")
    sys.stdout.flush()


print("[*] Mengunduh model SenseVoice (~155MB)...")
urllib.request.urlretrieve(URL, ARCHIVE, reporthook=progress)
print()

print("[*] Mengekstrak model...")
with tarfile.open(ARCHIVE) as tar:
    tar.extractall(".")
os.remove(ARCHIVE)

print("[*] Model berhasil diunduh dan siap digunakan.")
