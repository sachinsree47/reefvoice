import { useState, useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, ReferenceArea } from "recharts";
import "leaflet/dist/leaflet.css";

const API = (process.env.REACT_APP_API_URL || "http://localhost:8000").replace(/\/$/, "");

const fetchJson = async (path, options = {}) => {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json();
};

const scoreColor = (s) => s > 65 ? "#1D9E75" : s > 35 ? "#EF9F27" : "#E24B4A";
const scoreLabel = (s) => s > 65 ? "HEALTHY" : s > 35 ? "STRESSED" : "BLEACHED";
const scoreStatus = (s) => s > 65 ? "Healthy" : s > 35 ? "Stressed" : "Critical";
const scoreBg    = (s) => s > 65 ? "#E1F5EE" : s > 35 ? "#FAEEDA" : "#FCEBEB";
const scoreText  = (s) => s > 65 ? "#085041" : s > 35 ? "#633806" : "#A32D2D";

// ── Animated score dial ───────────────────────────────────
function ScoreDial({ score, size = 120 }) {
  const r = 46, cx = 60, cy = 60;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - score / 100);
  return (
    <svg width={size} height={size} viewBox="0 0 120 120">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e5e7eb" strokeWidth="10" />
      <circle cx={cx} cy={cy} r={r} fill="none"
        stroke={scoreColor(score)} strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dashoffset 1s ease, stroke 0.5s ease" }}
      />
      <text x={cx} y={cy - 6} textAnchor="middle" fontSize="22" fontWeight="600"
        fill={scoreColor(score)}>{score}</text>
      <text x={cx} y={cy + 12} textAnchor="middle" fontSize="10" fill="#6b7280">/ 100</text>
      <text x={cx} y={cy + 26} textAnchor="middle" fontSize="9" fontWeight="500"
        fill={scoreColor(score)}>{scoreLabel(score)}</text>
    </svg>
  );
}

// ── History chart ─────────────────────────────────────────
function HistoryChart({ history, name }) {
  const data = history.slice(-48).map((h, i) => ({
    t: i,
    score: h.score,
    time: new Date(h.timestamp).toLocaleString("en-IN", { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" })
  }));

  // Find bleaching event drop point
  const dropIdx = data.findIndex((d, i) => i > 2 && d.score < 35 && data[i - 1].score >= 35);

  return (
    <div style={{ marginTop: 16 }}>
      <p style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>48-hour score history</p>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data}>
          <ReferenceArea y1={0} y2={35} fill="#FCEBEB" fillOpacity={0.5} />
          <ReferenceArea y1={35} y2={65} fill="#FAEEDA" fillOpacity={0.3} />
          {dropIdx > 0 && (
            <ReferenceLine x={dropIdx} stroke="#E24B4A" strokeDasharray="4 2"
              label={{ value: "⚠ bleaching", fill: "#E24B4A", fontSize: 10 }} />
          )}
          <XAxis dataKey="t" hide />
          <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} width={28} />
          <Tooltip
            formatter={(v) => [`${v} / 100`, "Health Score"]}
            labelFormatter={(_, p) => p?.[0]?.payload?.time || ""}
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
          />
          <Line type="monotone" dataKey="score" stroke="#378ADD"
            dot={false} strokeWidth={2}
            style={{ transition: "all 0.3s ease" }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function HomePage({ reefsCount, onGoToMap, onGoToAnalyze }) {
  const featureItems = [
    {
      title: "Sound-driven reef health",
      description: "ReefVoice listens to underwater audio, translating reef soundscapes into AI-powered ecosystem scores."
    },
    {
      title: "Global reef network",
      description: "Explore dozens of reef stations from the Pacific to the Caribbean, with live status and trend signals."
    },
    {
      title: "Rapid impact alerts",
      description: "Watch for stress and bleaching events instantly through sound-based analysis and visual reef reporting."
    },
    {
      title: "Easy audio uploads",
      description: "Drop reef recordings directly into the app and get an instant health score powered by ReefCNN."
    }
  ];

  return (
    <div className="ocean-hero">
      <div className="ocean-wave-bg" />
      <div className="ocean-bubbles">
        <span className="bubble bubble-1" />
        <span className="bubble bubble-2" />
        <span className="bubble bubble-3" />
        <span className="bubble bubble-4" />
      </div>
      <div className="ocean-hero-content">
        <div className="ocean-hero-copy">
          <span className="ocean-eyebrow">Ocean AI for reef health</span>
          <h1>ReefVoice senses coral reefs and turns sound into action.</h1>
          <p>Discover an ocean-inspired reef monitoring experience where live audio, global mapping, and conservation storytelling come together in one immersive dashboard.</p>
          <div className="ocean-hero-actions">
            <button className="ocean-button primary" onClick={onGoToMap}>Explore the live map</button>
            <button className="ocean-button secondary" onClick={onGoToAnalyze}>Analyze reef audio</button>
          </div>
          <div className="ocean-stats-row">
            <div>
              <div className="ocean-stat-value">{reefsCount || "..."}</div>
              <div className="ocean-stat-label">reef stations worldwide</div>
            </div>
            <div>
              <div className="ocean-stat-value">48h</div>
              <div className="ocean-stat-label">trend history per station</div>
            </div>
            <div>
              <div className="ocean-stat-value">3</div>
              <div className="ocean-stat-label">health tiers — healthy, stressed, bleached</div>
            </div>
          </div>
        </div>

        <div className="ocean-hero-panel">
          <div className="ocean-panel-glow" />
          <div className="ocean-panel-card">
            <div className="ocean-panel-header">
              <span className="panel-badge">Live Reef Map</span>
              <span className="panel-score">+26 stations</span>
            </div>
            <h3>Pulse of the planet's coral reefs</h3>
            <p>Every station brings a new reef perspective: acoustic monitoring, coral stress tracking, and conservation-ready alerts.</p>
            <div className="ocean-panel-tag">Global · Interactive · AI-powered</div>
          </div>
        </div>
      </div>

      <div className="ocean-features-grid">
        {featureItems.map((item, index) => (
          <div key={item.title} className="ocean-card feature-card" style={{ animationDelay: `${index * 100}ms` }}>
            <div className="feature-icon">✨</div>
            <h4>{item.title}</h4>
            <p>{item.description}</p>
          </div>
        ))}
      </div>

      <div className="ocean-details-section">
        <div className="detail-card detail-card-large">
          <h3>How ReefVoice works</h3>
          <ul>
            <li>1. Underwater audio is captured from reef stations and hydrophones.</li>
            <li>2. ReefCNN analyzes the soundscape to estimate coral health.</li>
            <li>3. The live map displays reef score, trend history, and alerts.</li>
          </ul>
        </div>
        <div className="detail-card detail-card-small">
          <h3>What you can do</h3>
          <p>Browse reef stations, explore ecosystem conditions, and upload recordings to see reef health instantly.</p>
          <div className="detail-actions">
            <button className="ocean-button tertiary" onClick={onGoToMap}>View the map</button>
            <button className="ocean-button tertiary" onClick={onGoToAnalyze}>Analyze audio</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Audio drop zone ───────────────────────────────────────
function AudioAnalyzer() {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);

  const analyze = async (file) => {
    setLoading(true); setResult(null); setError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API}/analyze`, { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      setResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) analyze(file);
  };

  const onPick = (e) => { if (e.target.files[0]) analyze(e.target.files[0]); };

  return (
    <div style={{ padding: "20px 0" }}>
      <p style={{ fontSize: 13, color: "#374151", marginBottom: 12, fontWeight: 500 }}>
        🎧 Drop any reef audio file to analyze it live
      </p>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => document.getElementById("file-pick").click()}
        style={{
          border: `2px dashed ${dragging ? "#378ADD" : "#d1d5db"}`,
          borderRadius: 12, padding: "32px 16px", textAlign: "center",
          cursor: "pointer", background: dragging ? "#EFF6FF" : "#f9fafb",
          transition: "all 0.2s"
        }}
      >
        <div style={{ fontSize: 32, marginBottom: 8 }}>🌊</div>
        <p style={{ fontSize: 13, color: "#6b7280" }}>
          {loading ? "Analyzing audio…" : "Drop a .wav or .mp3 reef recording here"}
        </p>
        <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 4 }}>or click to browse</p>
        <input id="file-pick" type="file" accept=".wav,.mp3" hidden onChange={onPick} />
      </div>

      {/* Loading pulse */}
      {loading && (
        <div style={{ textAlign: "center", marginTop: 24 }}>
          <div style={{ fontSize: 13, color: "#378ADD", animation: "pulse 1s infinite" }}>
            🔬 Classifying acoustic signature…
          </div>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div style={{
          marginTop: 20, padding: 20, borderRadius: 12,
          background: scoreBg(result.score),
          border: `1px solid ${scoreColor(result.score)}30`
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <ScoreDial score={result.score} size={110} />
            <div>
              <p style={{ fontSize: 11, color: "#6b7280", marginBottom: 4 }}>{result.filename}</p>
              <div style={{
                display: "inline-block", padding: "3px 12px", borderRadius: 20,
                background: scoreColor(result.score), color: "#fff",
                fontSize: 12, fontWeight: 600, marginBottom: 8
              }}>{scoreLabel(result.score)}</div>
              <p style={{ fontSize: 13, color: "#374151" }}>
                Confidence: <strong>{(result.confidence * 100).toFixed(1)}%</strong>
              </p>
              <p style={{ fontSize: 13, color: "#374151" }}>
                Chunks analyzed: <strong>{result.chunk_count}</strong>
              </p>
              <div style={{ display: "flex", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
                {Object.entries(result.breakdown).map(([k, v]) => (
                  <span key={k} style={{
                    fontSize: 11, padding: "2px 8px", borderRadius: 10,
                    background: "#fff", border: "1px solid #e5e7eb", color: "#374151"
                  }}>
                    {k}: {(v * 100).toFixed(1)}%
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Mini timeline */}
          {result.chunk_scores?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 11, color: "#6b7280", marginBottom: 6 }}>Score across all chunks</p>
              <ResponsiveContainer width="100%" height={80}>
                <LineChart data={result.chunk_scores.map((s, i) => ({ i, s }))}>
                  <YAxis domain={[0, 100]} hide />
                  <XAxis dataKey="i" hide />
                  <Tooltip formatter={(v) => [`${v}`, "Score"]} contentStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="s" stroke={scoreColor(result.score)}
                    dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {error && (
        <div style={{ marginTop: 12, padding: 12, background: "#FCEBEB",
          borderRadius: 8, fontSize: 13, color: "#A32D2D" }}>
          ⚠ {error}
        </div>
      )}
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────
function Sidebar({ reef, onClose }) {
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    if (!reef) return;
    let active = true;
    fetchJson(`/reefs/${reef.id}/history`)
      .then((data) => { if (active) setDetail(data); })
      .catch((err) => {
        console.error(`Failed to fetch history for reef ${reef.id}:`, err);
        if (active) setDetail(null);
      });
    return () => { active = false; };
  }, [reef]);

  if (!reef) return null;

  return (
    <div style={{
      position: "absolute", top: 0, right: 0, width: 360, height: "100%",
      background: "#fff", boxShadow: "-4px 0 24px rgba(0,0,0,0.1)",
      zIndex: 1000, overflowY: "auto", padding: 24
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: "#111827", marginBottom: 4 }}>{reef.name}</h2>
          <p style={{ fontSize: 12, color: "#6b7280" }}>{reef.country}</p>
        </div>
        <button onClick={onClose} style={{
          background: "none", border: "none", fontSize: 20,
          cursor: "pointer", color: "#9ca3af", lineHeight: 1
        }}>×</button>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16, margin: "20px 0" }}>
        <ScoreDial score={reef.score} size={110} />
        <div>
          <div style={{
            display: "inline-block", padding: "4px 12px", borderRadius: 20,
            background: scoreBg(reef.score), color: scoreText(reef.score),
            fontSize: 12, fontWeight: 600, marginBottom: 8
          }}>{scoreLabel(reef.score)}</div>
          <p style={{ fontSize: 13, color: "#6b7280", lineHeight: 1.5 }}>
            {reef.score > 65
              ? "Reef ecosystem is thriving. High biodiversity detected."
              : reef.score > 35
              ? "Reef is under stress. Reduced species activity detected."
              : "Critical — reef shows signs of bleaching. Urgent monitoring needed."}
          </p>
        </div>
      </div>

      {detail && <HistoryChart history={detail.history} name={reef.name} />}

      <div style={{
        marginTop: 20, padding: 16, background: "#f9fafb",
        borderRadius: 10, fontSize: 12, color: "#374151", lineHeight: 1.6
      }}>
        <strong style={{ fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Station Info
        </strong>
        <p style={{ marginTop: 6 }}>📍 {reef.location.lat.toFixed(2)}°, {reef.location.lng.toFixed(2)}°</p>
        <p>🔊 Passive hydrophone · 48kHz · continuous</p>
        <p>🤖 ReefCNN · mel-spectrogram classifier</p>
        <p>📡 Score updated hourly</p>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────
export default function App() {
  const [reefs, setReefs]         = useState([]);
  const [selected, setSelected]   = useState(null);
  const [tab, setTab]             = useState("home"); // "home" | "map" | "analyze"

  useEffect(() => {
    let active = true;
    fetchJson("/reefs")
      .then((data) => { if (active) setReefs(Array.isArray(data) ? data : []); })
      .catch((err) => {
        console.error("Failed to fetch reefs:", err);
      });
    return () => { active = false; };
  }, []);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", fontFamily: "Inter, system-ui, sans-serif", background: "#f8fafc" }}>

      {/* Header */}
      <div className="app-header">
        <span className="app-logo">🌊</span>
        <div>
          <div className="app-title">ReefVoice</div>
          <div className="app-subtitle">AI reef listening, global coral insight</div>
        </div>
        <div className="nav-group">
          {["home", "map", "analyze"].map(t => (
            <button key={t} onClick={() => setTab(t)} className={`nav-button ${tab === t ? "active" : ""}`}>
              {t === "home" ? "🌊 Home" : t === "map" ? "🗺 Live Map" : "🎧 Analyze Audio"}
            </button>
          ))}
        </div>
      </div>

      {/* Legend */}
      {tab === "map" && (
        <div style={{
          display: "flex", gap: 16, padding: "10px 24px",
          background: "#f8fafc", borderBottom: "1px solid #e5e7eb",
          fontSize: 13, color: "#334155", flexShrink: 0
        }}>
          <span>● <span style={{ color: "#1D9E75" }}>Healthy</span> (&gt;65)</span>
          <span>● <span style={{ color: "#EF9F27" }}>Stressed</span> (35–65)</span>
          <span>● <span style={{ color: "#E24B4A" }}>Bleached</span> (&lt;35)</span>
          <span style={{ marginLeft: "auto", color: "#64748b" }}>Click a reef to explore</span>
        </div>
      )}

      {/* Content */}
      <div style={{ flex: 1, position: "relative", overflow: "hidden", minHeight: 0 }}>

        {tab === "home" && (
          <HomePage
            reefsCount={reefs.length}
            onGoToMap={() => setTab("map")}
            onGoToAnalyze={() => setTab("analyze")}
          />
        )}

        {tab === "map" && (
          <>
            <div className="map-view-wrapper">
              <MapContainer
                center={[2, 90]} zoom={2.4}
                className="map-view"
                zoomControl={true}
              >
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
                attribution='Tiles &copy; Esri &mdash; Source: Esri, HERE, Garmin, FAO, NOAA, USGS'
              />
              {reefs.map(reef => (
                <CircleMarker
                  key={reef.id}
                  center={[reef.location.lat, reef.location.lng]}
                  radius={10}
                  pathOptions={{
                    color: scoreColor(reef.score),
                    fillColor: scoreColor(reef.score),
                    fillOpacity: 0.85,
                    weight: 2
                  }}
                  eventHandlers={{ click: () => setSelected(reef) }}
                >
                  <Popup>
                    <strong>{reef.name}</strong><br />
                    Health: {scoreStatus(reef.score)}<br />
                    Score: {reef.score}/100 · {scoreLabel(reef.score)}
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
            </div>
            <Sidebar reef={selected} onClose={() => setSelected(null)} />
          </>
        )}

        {tab === "analyze" && (
          <div style={{ maxWidth: 640, margin: "0 auto", padding: "24px 16px", overflowY: "auto", height: "100%" }}>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>
              Live audio reef analysis
            </h2>
            <p style={{ fontSize: 15, color: "#475569", marginBottom: 22 }}>
              Upload a reef recording and our ReefCNN model will classify reef health from the underwater soundscape.
            </p>
            <AudioAnalyzer />
          </div>
        )}
      </div>
    </div>
  );
}