# TrafficOS

> **Predictive parking-pressure engine for Bengaluru Traffic Police**
> Flipkart Gridlock 2.0 · Round 2 · Theme 1: *Poor Visibility on Parking-Induced Congestion*

---

## The Problem

Illegal on-street parking in Bengaluru chokes carriageways and intersections — but enforcement today is patrol-based and reactive. There is no system that:

- Tells officers **which parking violations are actually causing flow degradation** (not just volume)
- **Quantifies the economic cost** of each hotspot
- **Predicts where new choke points are forming** before they become chronic
- **Routes limited enforcement resources** to cover the highest-impact windows first

TrafficOS solves all four, from 2,98,450 raw BTP e-challan records.

---

## Live Demo

Open `trafficos-frontend/index.html` in any browser — no server, no API keys, no install.

Or serve locally:

```bash
cd trafficos-frontend
python3 -m http.server 8080
# visit http://localhost:8080
```

---

## Repository Structure

```
trafficos/
├── trafficos-frontend/        # Static dashboard — open index.html directly
│   ├── index.html             # City map
│   ├── heatmap.html           # Parking heatmap
│   ├── hotspots.html          # Top junctions + cost grid
│   ├── deployment.html        # Truck routing simulator
│   ├── validation.html        # Cross-validation checks
│   ├── coverage.html          # Honesty audit
│   ├── css/style.css
│   ├── js/shared.js
│   ├── data/                  # Pre-computed JSON (no backend needed at runtime)
│   └── vendor/leaflet/        # Leaflet vendored locally — no CDN, no API key
│
└── trafficos-backend/
    ├── engine.py              # Full pipeline: Module 1 → 2 → 3 → 4
    └── main.py                # Entry point — generates all data/ JSON files
```

---

## Dashboard Pages

| Page | What it shows |
|---|---|
| **Map** | 168 junctions city-wide, coloured by confidence tier, with Friday truck-routing overlay |
| **Parking Heatmap** | Violation density vs. PCU congestion impact — the targeting signal |
| **Hotspots** | Top 16 high-confidence junctions, peak PCU bar chart, 3×3 cost sensitivity grid |
| **Deployment** | 4 pre-computed day/fleet scenarios, travel-time-feasible routing, explicit resource gaps |
| **Validation** | Three independent cross-checks (see below) |
| **Coverage** | Which junctions earn a cost claim — and which ones don't yet |

---

## Engine Modules

| Module | Purpose | Key Output |
|---|---|---|
| **1 — Weighted Violation Density** | PCU-weighted hotspot ranking + BPR phantom cost | Top 16 junctions, ₹18.5–88.8 Cr 6-month range |
| **2 — Predictive Pressure Score** | Self-relative anomaly detection + trend analysis | Emerging threats (KR Market +98%, Upparpet +201%) |
| **3 — Resource-Aware Deployment** | Travel-time-feasible truck routing, severity-proportional service time | Optimal stop sequence per scenario |
| **4 — Parking Severity Heatmap** | Targeting score = violation count × subtype severity × PCU impact | Ranked heatmap across all 168 junctions |

Run the full pipeline:

```bash
cd trafficos-backend
pip install pandas numpy
python main.py
# Generates all JSON files into ../trafficos-frontend/data/
```

---

## Key Design Decisions

**PCU-weighted density, not raw violation count**
A bus blocking a lane causes 3× more flow disruption than a scooter. Raw counts treat them equally. PCU weights don't.

**Confidence-tiered claims**
168 junctions scanned. Only 16 clear the 60-day evidence threshold required for a full BPR cost claim. The other 152 get a lighter signal or an explicit `INSUFFICIENT` flag — they are never given a number they haven't earned.

**Self-relative anomaly detection (Module 2)**
Global percentile tiers would always flag the same 10 chronic junctions as `CRITICAL`. Self-relative anomaly compares each junction to its own historical baseline — catching real spikes anywhere in the network.

**Parking severity subtype weighting (Module 4)**
`PARKING IN A MAIN ROAD` (weight 3.0) is not the same enforcement priority as `PARKING NEAR BUS STOP` (weight 1.5). Module 4 replaced a structurally broken FLOW/STATIONARY split with subtype-level severity scores.

**Resource-aware routing (Module 3)**
Trucks cannot teleport. Every stop checks real travel time at 20 km/h before assignment. Service time scales with PCU load. Uncovered windows are reported explicitly, not silently dropped.

---

## Validation

| Check | Method | Result |
|---|---|---|
| **Obstruction overlap** | Top-5 PCU hotspots vs. top-10 by raw wrong/no-parking violation count | **5 / 5 match** |
| **Heavy-vehicle baseline** | Top hotspots vs. city-wide heavy-vehicle violation rate (1.36%) | Top junctions are light-vehicle dominated — confirms urban core, not industrial corridor |
| **TomTom sanity check** | Model-implied average speed at hotspots vs. TomTom Bengaluru index | **3.8% deviation** — within acceptable range for a historical-data model |

---

## Business Impact (Mid Scenario)

| Metric | Value |
|---|---|
| Phantom congestion cost (6 months) | **₹42.8 Cr** (range ₹18.5–88.8 Cr) |
| Worst junction delay | **+15 min** per crossing (Subbanna Junction) |
| Friday coverage with 3 trucks | **77%+ critical windows covered** |
| Emerging threat flagged | **KR Market Junction +98% trend** |

---

## Stack

**Backend**
- Python · pandas · numpy
- BPR volume-delay function for congestion cost
- PCU weighting (IRC standards)
- Haversine travel-time routing
- All pre-computed — zero runtime dependency for the frontend

**Frontend**
- Vanilla HTML / CSS / JavaScript — no framework, no build step
- [Leaflet.js](https://leafletjs.com/) · vendored locally, no API key
- CARTO dark basemap tiles · free tier, no API key
- All data shipped as static JSON

---
---

*Flipkart Gridlock 2.0 · Round 2 Prototype*
