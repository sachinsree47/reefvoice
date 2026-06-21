import librosa
import numpy as np
import onnxruntime as ort
from pathlib import Path

SR = 48000
CHUNK_SEC = 1.536
N_MELS = 128
HOP_LENGTH = 512
N_FFT = 2048

_session = None

def _load_model():
    global _session
    if _session is not None:
        return _session
    
    weights = Path(__file__).resolve().parent / "models" / "reefcnn_best.onnx"
    if not weights.exists():
        raise FileNotFoundError(f"Model not found at {weights}")
    
    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = 1
    sess_options.inter_op_num_threads = 1
    
    _session = ort.InferenceSession(str(weights), sess_options=sess_options, providers=['CPUExecutionProvider'])
    return _session

def _audio_to_mel(y: np.ndarray) -> np.ndarray:
    mel = librosa.feature.melspectrogram(
        y=y, sr=SR, n_mels=N_MELS,
        hop_length=HOP_LENGTH, n_fft=N_FFT
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_tensor = np.expand_dims(mel_db, axis=(0, 1)).astype(np.float32)
    return mel_tensor

def analyze(audio_path: str) -> dict:
    session = _load_model()
    y_full, _ = librosa.load(audio_path, sr=SR, mono=True)
    
    chunk_len = int(SR * CHUNK_SEC)
    n_chunks = max(1, len(y_full) // chunk_len)

    MAX_CHUNKS = 5
    if n_chunks > MAX_CHUNKS:
        indices = np.linspace(0, n_chunks - 1, MAX_CHUNKS, dtype=int)
    else:
        indices = range(n_chunks)

    all_probs = []
    chunk_scores = []

    for i in indices:
        chunk = y_full[i * chunk_len : (i + 1) * chunk_len]
        if len(chunk) < chunk_len:
            pad_len = chunk_len - len(chunk)
            chunk = np.pad(chunk, (0, pad_len), mode='constant')

        mel_tensor = _audio_to_mel(chunk)
        
        # ONNX model was exported with AdaptiveAvgPool2d which hardcoded time=144 frames.
        # We MUST pass exactly 144 frames to avoid GEMM Dimension Mismatch!
        target_frames = 144
        if mel_tensor.shape[3] > target_frames:
            mel_tensor = mel_tensor[:, :, :, :target_frames]
        elif mel_tensor.shape[3] < target_frames:
            pad_width = target_frames - mel_tensor.shape[3]
            mel_tensor = np.pad(mel_tensor, ((0,0), (0,0), (0,0), (0,pad_width)), mode='constant')
        
        input_name = session.get_inputs()[0].name
        logits = session.run(None, {input_name: mel_tensor})[0]
        
        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = (exp_logits / np.sum(exp_logits, axis=1, keepdims=True))[0]
        
        all_probs.append(probs)
        chunk_scores.append(float(probs[0] * 100 + probs[1] * 50 + probs[2] * 0))

    avg_probs = np.mean(all_probs, axis=0)
    
    # 0=Healthy, 1=Degraded, 2=Dead
    score_float = float(avg_probs[0] * 100 + avg_probs[1] * 50 + avg_probs[2] * 0)
    
    spec = np.abs(librosa.stft(y_full, n_fft=N_FFT, hop_length=HOP_LENGTH))
    freq_entropy = -np.sum(
        (spec / (np.sum(spec) + 1e-9)) * np.log(spec / (np.sum(spec) + 1e-9) + 1e-9)
    )
    
    score_float = max(0.0, min(100.0, score_float))
    
    return {
        "score": round(score_float, 1),
        "health_index": int(score_float),
        "diversity_score": round(float(freq_entropy) / 10.0, 2),
        "status": "Healthy" if score_float >= 75 else "Degraded" if score_float >= 40 else "Dead",
        "confidence": float(np.max(avg_probs)),
        "chunk_count": len(indices),
        "breakdown": {
            "Healthy": float(avg_probs[0]),
            "Degraded": float(avg_probs[1]),
            "Dead": float(avg_probs[2])
        },
        "chunk_scores": chunk_scores
    }