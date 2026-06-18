import torch
import torch.nn as nn
import librosa
import numpy as np
import json
from pathlib import Path

# ── Same model architecture as train.py ───────────────────
class ReefCNN(nn.Module):
    def __init__(self, n_classes=3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, n_classes)
        )

    def forward(self, x):
        return self.classifier(self.features(x))

# ── Config ────────────────────────────────────────────────
SR = 48000
N_MELS = 128
HOP_LENGTH = 512
N_FFT = 2048
CHUNK_SEC = 3
CLASSES = ["healthy", "stressed", "bleached"]

# Health score weights per class (healthy=100, stressed=50, bleached=0)
CLASS_SCORES = {"healthy": 100, "stressed": 50, "bleached": 0}

# ── Load model once at import ─────────────────────────────
_model = None
_device = torch.device("cpu")

def _load_model():
    global _model
    if _model is not None:
        return _model
    model = ReefCNN(n_classes=3)
    weights = Path("models/reefcnn_best.pt")
    if not weights.exists():
        raise FileNotFoundError("Model not found. Run train.py first.")
    model.load_state_dict(torch.load(weights, map_location=_device))
    model.eval()
    _model = model
    return _model

# ── Audio → mel spectrogram ───────────────────────────────
def _audio_to_mel(y: np.ndarray) -> torch.Tensor:
    mel = librosa.feature.melspectrogram(
        y=y, sr=SR, n_mels=N_MELS,
        hop_length=HOP_LENGTH, n_fft=N_FFT
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_db = (mel_db - mel_db.mean()) / (mel_db.std() + 1e-6)
    return torch.tensor(mel_db, dtype=torch.float32).unsqueeze(0).unsqueeze(0)  # [1,1,128,T]

# ── Analyze a single audio file ───────────────────────────
def analyze(audio_path: str) -> dict:
    """
    Analyzes a .wav or .mp3 file and returns a reef health report.
    Returns:
        {
            score: int (0-100),
            label: str,
            confidence: float,
            breakdown: { healthy: float, stressed: float, bleached: float },
            chunk_count: int,
            chunk_scores: list[int]
        }
    """
    model = _load_model()
    y_full, _ = librosa.load(audio_path, sr=SR, mono=True)

    chunk_len = SR * CHUNK_SEC
    n_chunks = max(1, len(y_full) // chunk_len)

    all_probs = []

    for i in range(n_chunks):
        chunk = y_full[i * chunk_len : (i + 1) * chunk_len]
        if len(chunk) < chunk_len:
            chunk = np.pad(chunk, (0, chunk_len - len(chunk)))

        # Skip near-silent chunks
        if np.max(np.abs(chunk)) < 0.005:
            continue

        mel_tensor = _audio_to_mel(chunk)
        with torch.no_grad():
            logits = model(mel_tensor)
            probs = torch.softmax(logits, dim=1).squeeze().numpy()
        all_probs.append(probs)

    if not all_probs:
        return {"score": 0, "label": "bleached", "confidence": 1.0,
                "breakdown": {"healthy": 0.0, "stressed": 0.0, "bleached": 1.0},
                "chunk_count": 0, "chunk_scores": []}

    # Average probabilities across all chunks
    avg_probs = np.mean(all_probs, axis=0)  # [healthy, stressed, bleached]

    # Weighted health score
    score = int(
        avg_probs[0] * CLASS_SCORES["healthy"] +
        avg_probs[1] * CLASS_SCORES["stressed"] +
        avg_probs[2] * CLASS_SCORES["bleached"]
    )

    # Per-chunk scores for the timeline chart
    chunk_scores = [
        int(p[0] * 100 + p[1] * 50 + p[2] * 0)
        for p in all_probs
    ]

    dominant_idx = int(np.argmax(avg_probs))
    label = CLASSES[dominant_idx]
    confidence = float(avg_probs[dominant_idx])

    return {
        "score": score,
        "label": label,
        "confidence": round(confidence, 3),
        "breakdown": {
            "healthy":  round(float(avg_probs[0]), 3),
            "stressed": round(float(avg_probs[1]), 3),
            "bleached": round(float(avg_probs[2]), 3),
        },
        "chunk_count": len(all_probs),
        "chunk_scores": chunk_scores
    }

# ── Quick test ────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    test_file = sys.argv[1] if len(sys.argv) > 1 else "data/raw/healthy/healthy_reef.mp3"
    print(f"\nAnalyzing: {test_file}")
    result = analyze(test_file)
    print(f"\n── Reef Health Report ──")
    print(f"  Score     : {result['score']} / 100")
    print(f"  Label     : {result['label'].upper()}")
    print(f"  Confidence: {result['confidence']:.1%}")
    print(f"  Breakdown : healthy={result['breakdown']['healthy']:.1%}  "
          f"stressed={result['breakdown']['stressed']:.1%}  "
          f"bleached={result['breakdown']['bleached']:.1%}")
    print(f"  Chunks    : {result['chunk_count']} analyzed")
    print(f"  Timeline  : {result['chunk_scores']}")