import os, requests, tarfile, shutil, zipfile
from pathlib import Path
from tqdm import tqdm
import librosa
import soundfile as sf
import numpy as np

RAW = Path("reefvoice/data/raw")
PROCESSED = Path("reefvoice/data/processed")
CLASSES = ["healthy", "stressed", "bleached"]

for c in CLASSES:
    (RAW / c).mkdir(parents=True, exist_ok=True)
    (PROCESSED / c).mkdir(parents=True, exist_ok=True)

def convert_to_wav(src: Path, dst: Path, sr=48000):
    y, orig_sr = librosa.load(str(src), sr=sr, mono=True)
    sf.write(str(dst), y, sr)

def chunk_audio(wav_path: Path, out_dir: Path, chunk_sec=3, sr=48000):
    y, _ = librosa.load(str(wav_path), sr=sr, mono=True)
    chunk_len = chunk_sec * sr
    n_chunks = len(y) // chunk_len
    saved = 0
    for i in range(n_chunks):
        chunk = y[i*chunk_len:(i+1)*chunk_len]
        if np.max(np.abs(chunk)) < 0.01:
            continue  # skip silent chunks
        out_path = out_dir / f"{wav_path.stem}_chunk{i:04d}.wav"
        sf.write(str(out_path), chunk, sr)
        saved += 1
    return saved

def process_all_raw():
    total = 0
    for label in CLASSES:
        src_dir = RAW / label
        dst_dir = PROCESSED / label
        files = list(src_dir.glob("*.wav")) + list(src_dir.glob("*.mp3"))
        print(f"\n[{label}] Processing {len(files)} files...")
        for f in files:
            wav = src_dir / (f.stem + "_converted.wav")
            if not wav.exists():
                convert_to_wav(f, wav)
            n = chunk_audio(wav, dst_dir)
            total += n
            print(f"  {f.name} → {n} chunks")
    print(f"\nDone. Total chunks: {total}")
    return total

if __name__ == "__main__":
    print("=== ReefVoice Data Pipeline ===")
    print("\nStep 1: Checking raw data folders...")
    for label in CLASSES:
        files = list((RAW / label).glob("*.*"))
        print(f"  {label}: {len(files)} files found")

    print("\nStep 2: Processing all raw audio into 3-second chunks...")
    total = process_all_raw()

    if total == 0:
        print("\nNo audio files found yet — add files manually first (see below).")
    else:
        print(f"\nAll done! {total} chunks ready in data/processed/")
        print("Next: run  python train.py")