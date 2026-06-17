from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil, tempfile, os
from pathlib import Path
from datetime import datetime, timedelta
import random
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from score import analyze
except Exception:
    # If model dependencies (torch, etc.) are not installed in this environment
    # we provide a placeholder analyze function so the API can start and
    # the /reefs endpoints remain available. The real model will be used
    # when the dependencies are installed and the server restarted.
    def analyze(path):
        raise RuntimeError("Model not available in this environment: install torch to enable audio analysis")

app = FastAPI(title="ReefVoice API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mock reef stations (seeded with realistic data) ───────
def make_history(base_score: int, days: int = 7, event_day: int = None):
    history = []
    for d in range(days * 24):
        ts = datetime.now() - timedelta(hours=(days * 24 - d))
        noise = random.randint(-4, 4)
        score = base_score + noise
        if event_day and d // 24 >= event_day:
            # Simulate bleaching event — score drops sharply
            drop = (d // 24 - event_day + 1) * 9
            score = max(3, score - drop)
        score = max(0, min(100, score))
        history.append({
            "timestamp": ts.isoformat(),
            "score": score,
            "label": "healthy" if score > 65 else "stressed" if score > 35 else "bleached"
        })
    return history

REEFS = [
    {
        "id": "gbr-north",
        "name": "Great Barrier Reef - North",
        "location": {"lat": -15.0, "lng": 145.5},
        "country": "Australia",
        "history": make_history(base_score=91, days=7),
    },
    {
        "id": "gbr-south",
        "name": "Great Barrier Reef - South",
        "location": {"lat": -23.8, "lng": 151.7},
        "country": "Australia",
        "history": make_history(base_score=88, days=7),
    },
    {
        "id": "maldives-central",
        "name": "Maldives Central Atoll",
        "location": {"lat": 3.2, "lng": 73.2},
        "country": "Maldives",
        "history": make_history(base_score=78, days=7),
    },
    {
        "id": "maldives-south",
        "name": "Maldives South Atoll",
        "location": {"lat": -0.5, "lng": 73.3},
        "country": "Maldives",
        "history": make_history(base_score=84, days=7),
    },
    {
        "id": "florida-keys",
        "name": "Florida Keys",
        "location": {"lat": 24.7, "lng": -81.3},
        "country": "USA",
        # Bleaching event starts day 4
        "history": make_history(base_score=82, days=7, event_day=4),
    },
    {
        "id": "bahamas-exuma",
        "name": "Exuma Cays",
        "location": {"lat": 23.7, "lng": -76.0},
        "country": "Bahamas",
        "history": make_history(base_score=69, days=7),
    },
    {
        "id": "belize-barrier",
        "name": "Belize Barrier Reef",
        "location": {"lat": 17.4, "lng": -88.2},
        "country": "Belize",
        "history": make_history(base_score=72, days=7),
    },
    {
        "id": "caribbean-bonaire",
        "name": "Bonaire Reef",
        "location": {"lat": 12.2, "lng": -68.3},
        "country": "Caribbean Netherlands",
        "history": make_history(base_score=61, days=7),
    },
    {
        "id": "galapagos-west",
        "name": "Galapagos West",
        "location": {"lat": -0.8, "lng": -90.3},
        "country": "Ecuador",
        "history": make_history(base_score=86, days=7),
    },
    {
        "id": "easter-island",
        "name": "Easter Island Reef",
        "location": {"lat": -27.1, "lng": -109.4},
        "country": "Chile",
        "history": make_history(base_score=58, days=7),
    },
    {
        "id": "red-sea-sharm",
        "name": "Sharm el-Sheikh Reef",
        "location": {"lat": 27.9, "lng": 34.3},
        "country": "Egypt",
        "history": make_history(base_score=74, days=7),
    },
    {
        "id": "red-sea-sudan",
        "name": "Sudan Red Sea",
        "location": {"lat": 18.3, "lng": 38.5},
        "country": "Sudan",
        "history": make_history(base_score=68, days=7),
    },
    {
        "id": "raja-ampat",
        "name": "Raja Ampat",
        "location": {"lat": -0.5, "lng": 130.5},
        "country": "Indonesia",
        "history": make_history(base_score=95, days=7),
    },
    {
        "id": "palau",
        "name": "Palau Marine Park",
        "location": {"lat": 7.5, "lng": 134.5},
        "country": "Palau",
        "history": make_history(base_score=92, days=7),
    },
    {
        "id": "fiji-suva",
        "name": "Suva Lagoon",
        "location": {"lat": -18.1, "lng": 178.4},
        "country": "Fiji",
        "history": make_history(base_score=81, days=7),
    },
    {
        "id": "sechelles",
        "name": "Seychelles Reef",
        "location": {"lat": -4.7, "lng": 55.5},
        "country": "Seychelles",
        "history": make_history(base_score=77, days=7),
    },
    {
        "id": "gulf-mannar",
        "name": "Gulf of Mannar",
        "location": {"lat": 9.1, "lng": 79.0},
        "country": "India",
        "history": make_history(base_score=54, days=7),
    },
    {
        "id": "andaman",
        "name": "Andaman Reef",
        "location": {"lat": 11.7, "lng": 92.8},
        "country": "India",
        "history": make_history(base_score=63, days=7),
    },
    {
        "id": "hawaii-north",
        "name": "Hawaii North Reef",
        "location": {"lat": 21.4, "lng": -158.0},
        "country": "USA",
        "history": make_history(base_score=83, days=7),
    },
    {
        "id": "marquesas",
        "name": "Marquesas Atoll",
        "location": {"lat": -9.6, "lng": -139.0},
        "country": "French Polynesia",
        "history": make_history(base_score=66, days=7),
    },
    {
        "id": "mozambique",
        "name": "Bazaruto Archipelago",
        "location": {"lat": -21.7, "lng": 35.3},
        "country": "Mozambique",
        "history": make_history(base_score=57, days=7, event_day=2),
    },
    {
        "id": "canary-islands",
        "name": "Canary Islands Reef",
        "location": {"lat": 28.1, "lng": -15.4},
        "country": "Spain",
        "history": make_history(base_score=62, days=7),
    },
    {
        "id": "new-caledonia",
        "name": "New Caledonia",
        "location": {"lat": -21.5, "lng": 165.5},
        "country": "France",
        "history": make_history(base_score=89, days=7),
    },
]

# If developer wants more visible points on the map during testing, auto-generate
# additional mock reef stations until we reach a reasonable count (e.g. 45).
DESIRED_REEF_COUNT = 45
if len(REEFS) < DESIRED_REEF_COUNT:
    additional_reefs = [
        {"lat": 20.0, "lng": -160.0, "name": "Central Pacific Reef 1", "country": "Pacific Ocean"},
        {"lat": 25.0, "lng": -155.0, "name": "Central Pacific Reef 2", "country": "Pacific Ocean"},
        {"lat": 15.0, "lng": -170.0, "name": "Western Pacific Reef 1", "country": "Pacific Ocean"},
        {"lat": 10.0, "lng": -165.0, "name": "Western Pacific Reef 2", "country": "Pacific Ocean"},
        {"lat": 30.0, "lng": -140.0, "name": "North Pacific Reef 1", "country": "Pacific Ocean"},
        {"lat": 5.0, "lng": -50.0, "name": "Atlantic Mid Reef 1", "country": "Atlantic Ocean"},
        {"lat": 8.0, "lng": -45.0, "name": "Atlantic Mid Reef 2", "country": "Atlantic Ocean"},
        {"lat": 15.0, "lng": -60.0, "name": "Caribbean Reef Extension 1", "country": "Caribbean"},
        {"lat": 12.0, "lng": -65.0, "name": "Caribbean Reef Extension 2", "country": "Caribbean"},
        {"lat": 0.0, "lng": -30.0, "name": "Equatorial Atlantic Reef 1", "country": "Atlantic Ocean"},
        {"lat": -10.0, "lng": -35.0, "name": "South Atlantic Reef 1", "country": "Atlantic Ocean"},
        {"lat": -5.0, "lng": 40.0, "name": "East Africa Reef 1", "country": "Indian Ocean"},
        {"lat": -18.0, "lng": 45.0, "name": "Southern Indian Reef 1", "country": "Indian Ocean"},
        {"lat": 5.0, "lng": 60.0, "name": "Arabian Sea Reef 1", "country": "Indian Ocean"},
        {"lat": 10.0, "lng": 85.0, "name": "Bay of Bengal Reef 1", "country": "Indian Ocean"},
        {"lat": 0.0, "lng": 110.0, "name": "Southeast Asia Reef 1", "country": "Pacific Ocean"},
        {"lat": -10.0, "lng": 130.0, "name": "East Australia Reef 1", "country": "Pacific Ocean"},
        {"lat": -20.0, "lng": 150.0, "name": "South Pacific Reef 1", "country": "Pacific Ocean"},
        {"lat": 5.0, "lng": 150.0, "name": "Micronesia Reef 1", "country": "Pacific Ocean"},
        {"lat": -30.0, "lng": 160.0, "name": "New Zealand Area Reef 1", "country": "Pacific Ocean"},
        {"lat": 20.0, "lng": -80.0, "name": "Gulf of Mexico Reef 1", "country": "Gulf of Mexico"},
        {"lat": 35.0, "lng": -70.0, "name": "North Atlantic Reef 1", "country": "Atlantic Ocean"},
        {"lat": -45.0, "lng": 15.0, "name": "Southern Ocean Reef 1", "country": "Southern Ocean"},
    ]
    for ar in additional_reefs:
        if len(REEFS) >= DESIRED_REEF_COUNT:
            break
        base_score = random.randint(30, 95)
        REEFS.append({
            "id": f"auto-{len(REEFS) + 1}",
            "name": ar["name"],
            "location": {"lat": ar["lat"], "lng": ar["lng"]},
            "country": ar["country"],
            "history": make_history(base_score=base_score, days=7, event_day=(random.choice([None, random.randint(0, 6)]))),
        })

def current_score(reef):
    return reef["history"][-1]["score"]

def current_label(reef):
    s = current_score(reef)
    return "healthy" if s > 65 else "stressed" if s > 35 else "bleached"


def to_ascii(text: str) -> str:
    """Normalize text to plain ASCII characters and replace common punctuation
    with simple ASCII equivalents for consistent map labels."""
    if not isinstance(text, str):
        return text
    # Replace fancy punctuation first (before normalization)
    text = text.replace('\u2014', '-')  # em-dash
    text = text.replace('\u2013', '-')  # en-dash
    text = text.replace('\u2019', "'")  # right single quote
    text = text.replace('\u201c', '"')  # left double quote
    text = text.replace('\u201d', '"')  # right double quote
    # Normalize diacritics and remove non-ASCII
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_text = nfkd.encode('ascii', 'ignore').decode('ascii')
    return ' '.join(ascii_text.split())

# ── Routes ────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ReefVoice API running", "version": "1.0.0"}

@app.get("/reefs")
def list_reefs():
    return [
        {
            "id": r["id"],
            "name": to_ascii(r["name"]),
            "location": r["location"],
            "country": to_ascii(r["country"]),
            "score": current_score(r),
            "label": current_label(r),
        }
        for r in REEFS
    ]

@app.get("/reefs/{reef_id}/history")
def reef_history(reef_id: str):
    reef = next((r for r in REEFS if r["id"] == reef_id), None)
    if not reef:
        raise HTTPException(status_code=404, detail="Reef not found")
    return {
        "id": reef["id"],
        "name": to_ascii(reef["name"]),
        "location": reef["location"],
        "country": to_ascii(reef.get("country", "")),
        "score": current_score(reef),
        "label": current_label(reef),
        "history": reef["history"],
    }

@app.post("/analyze")
async def analyze_audio(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.lower().endswith((".wav", ".mp3")):
        raise HTTPException(status_code=400, detail="Only .wav and .mp3 files supported")

    # Save to temp file
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = analyze(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)

    return {
        "filename": file.filename,
        **result
    }