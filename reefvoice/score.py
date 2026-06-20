import librosa
import numpy as np
import onnxruntime as ort
from pathlib import Path

SR = 48000
CHUNK_SEC = 3
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
    
    chunk_len = SR * CHUNK_SEC
    n_chunks = max(1, len(y_full) // chunk_len)

    all_probs = []

    for i in range(n_chunks):
        chunk = y_full[i * chunk_len : (i + 1) * chunk_len]
        if len(chunk) < chunk_len:
            pad_len = chunk_len - len(chunk)
            chunk = np.pad(chunk, (0, pad_len), mode='constant')

        mel_tensor = _audio_to_mel(chunk)
        
        input_name = session.get_inputs()[0].name
        logits = session.run(None, {input_name: mel_tensor})[0]
        
        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = (exp_logits / np.sum(exp_logits, axis=1, keepdims=True))[0]
        
        all_probs.append(probs)

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
        "status": "Healthy" if score_float >= 75 else "Degraded" if score_float >= 40 else "Dead"
    }