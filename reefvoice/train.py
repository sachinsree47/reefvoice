import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
import librosa
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import json

# ── Config ────────────────────────────────────────────────
PROCESSED = Path("reefvoice/data/processed")
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

CLASSES = ["healthy", "stressed", "bleached"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

SR = 48000
N_MELS = 128
HOP_LENGTH = 512
N_FFT = 2048
CHUNK_SEC = 3
EPOCHS = 30
BATCH_SIZE = 16
LR = 1e-3

# ── Dataset ───────────────────────────────────────────────
class ReefDataset(Dataset):
    def __init__(self, file_label_pairs):
        self.pairs = file_label_pairs

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        path, label = self.pairs[idx]
        y, _ = librosa.load(str(path), sr=SR, mono=True, duration=CHUNK_SEC)

        # Pad if shorter than 3 seconds
        target_len = SR * CHUNK_SEC
        if len(y) < target_len:
            y = np.pad(y, (0, target_len - len(y)))

        mel = librosa.feature.melspectrogram(
            y=y, sr=SR, n_mels=N_MELS,
            hop_length=HOP_LENGTH, n_fft=N_FFT
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)

        # Normalize to [-1, 1]
        mel_db = (mel_db - mel_db.mean()) / (mel_db.std() + 1e-6)

        tensor = torch.tensor(mel_db, dtype=torch.float32).unsqueeze(0)  # [1, 128, T]
        return tensor, label

# ── Model (lightweight CNN) ───────────────────────────────
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

# ── Load data ─────────────────────────────────────────────
def load_all_pairs():
    pairs = []
    for label, idx in CLASS_TO_IDX.items():
        files = list((PROCESSED / label).glob("*.wav"))
        for f in files:
            pairs.append((f, idx))
    return pairs

# ── Train ─────────────────────────────────────────────────
def train():
    print("=== ReefVoice Model Training ===\n")
    all_pairs = load_all_pairs()
    print(f"Total samples: {len(all_pairs)}")
    for label, idx in CLASS_TO_IDX.items():
        count = sum(1 for _, l in all_pairs if l == idx)
        print(f"  {label}: {count} chunks")

    train_pairs, val_pairs = train_test_split(
        all_pairs, test_size=0.2, random_state=42,
        stratify=[l for _, l in all_pairs]
    )
    print(f"\nTrain: {len(train_pairs)} | Val: {len(val_pairs)}\n")

    train_ds = ReefDataset(train_pairs)
    val_ds   = ReefDataset(val_pairs)
    train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_dl   = DataLoader(val_ds,   batch_size=BATCH_SIZE)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}\n")

    model = ReefCNN(n_classes=3).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.CrossEntropyLoss()
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    best_val_acc = 0.0

    for epoch in range(1, EPOCHS + 1):
        # Train
        model.train()
        train_loss, correct, total = 0, 0, 0
        for x, y in train_dl:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            correct += (out.argmax(1) == y).sum().item()
            total += len(y)
        train_acc = correct / total

        # Validate
        model.eval()
        val_correct, val_total = 0, 0
        all_preds, all_labels = [], []
        with torch.no_grad():
            for x, y in val_dl:
                x, y = x.to(device), y.to(device)
                out = model(x)
                preds = out.argmax(1)
                val_correct += (preds == y).sum().item()
                val_total += len(y)
                all_preds.extend(preds.cpu().tolist())
                all_labels.extend(y.cpu().tolist())
        val_acc = val_correct / val_total

        scheduler.step()

        print(f"Epoch {epoch:02d}/{EPOCHS} | "
              f"Loss: {train_loss/len(train_dl):.3f} | "
              f"Train Acc: {train_acc:.2%} | "
              f"Val Acc: {val_acc:.2%}"
              + (" ✓ best" if val_acc > best_val_acc else ""))

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODELS_DIR / "reefcnn_best.pt")

    # Final report
    print("\n── Classification Report ──")
    print(classification_report(all_labels, all_preds, target_names=CLASSES))
    print(f"Best val accuracy: {best_val_acc:.2%}")
    print(f"Model saved → models/reefcnn_best.pt")

    # Save class map
    with open(MODELS_DIR / "class_map.json", "w") as f:
        json.dump(CLASS_TO_IDX, f)
    print("Class map saved → models/class_map.json")

if __name__ == "__main__":
    train()