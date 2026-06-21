# TrafficOS

**Predictive parking-pressure engine for Bengaluru Traffic Police**

Built for **Flipkart Gridlock 2.0 — Round 2** · Theme 1: *Poor Visibility on Parking-Induced Congestion*

---

## What this is

TrafficOS turns 2,98,450 raw BTP parking-violation records (Nov 2023–Apr 2024)
into a ranked, cost-quantified, cross-validated enforcement plan — built to be
honest about what the data does and doesn't support.

Only 16 of 168 scanned junctions have ≥60 days of violation data, the bar
required for a full cost-impact claim. The rest get a lighter-weight signal
or an explicit "insufficient data" flag instead of a number they haven't
earned. That tiering is the core design decision behind the whole system.

## Pages

| Page | What it shows |
|---|---|
| `index.html` | City map — 168 junctions plotted by confidence tier, with the Friday truck-routing overlay |
| `heatmap.html` | Parking violation density vs. PCU-weighted congestion impact, with a targeting score that combines both |
| `hotspots.html` | Top 16 high-confidence junctions ranked by density, with a 3×3 cost sensitivity grid (Value-of-Time × demand) |
| `deployment.html` | Resource-aware, travel-time-feasible truck routing across 4 pre-computed day/fleet-size scenarios |
| `validation.html` | Three cross-validation checks — obstruction-violation overlap, heavy-vehicle baseline, TomTom sanity check |
| `coverage.html` | A system-wide honesty audit — exactly which junctions earn a cost claim, and which don't yet |

## Run it

No build step, no server-side code, no API keys. Just open `index.html`
in a browser, or serve it locally:

```bash
python3 -m http.server 8080
```

Then visit `http://localhost:8080`

## Stack


Python: pandas, numpy
Modeling: BPR volume-delay function, PCU weighting, severity classifier
Visualization: Leaflet.js + custom dark UI (single HTML)
Data: Anonymized BTP e-challan records

- Vanilla HTML/CSS/JS — no framework, no build tooling
- [Leaflet.js](https://leafletjs.com/) (vendored locally in `vendor/leaflet/`, no CDN dependency, no API key)
- CARTO dark basemap tiles (free tier, no API key)
- All analytics pre-computed and shipped as static JSON in `data/`

## Data & methodology highlights

- **PCU-weighted density**, not raw violation count — a bus blocks more
  lane than a scooter
- **Confidence-tiered claims** — junctions are only given a cost estimate
  if they clear a 60-day evidence threshold; everything else is flagged,
  not hidden
- **Cross-validated**, not just self-reported — top hotspots independently
  match raw obstruction-violation rankings (5/5) and were sanity-checked
  against TomTom's published traffic index
- **Resource-aware deployment** — truck routing respects real travel time
  and reports uncovered windows explicitly instead of silently failing

## Folder structure

```
trafficos-frontend/
├── index.html
├── heatmap.html
├── hotspots.html
├── deployment.html
├── validation.html
├── coverage.html
├── css/style.css
├── js/shared.js
├── data/               ← pre-computed JSON, no backend needed
└── vendor/leaflet/     ← vendored locally, no CDN dependency
```
trafficos-backend/
|--engine.py
|--main.py

##BACKEND
**"Poor Visibility on Parking-Induced Congestion"**

TrafficOS solves the core challenge by:
- Detecting **which** illegal parking violations actually create choke points (not just volume).
- Quantifying their **economic impact** using PCU-weighted BPR congestion modeling.
- Predicting **emerging** choke points using self-relative trends.
- Recommending **actionable** deployment plans for limited enforcement resources.

---

## Key Innovations (v7)

- **Module 4 — Parking Severity Classifier**: Replaced the structurally dead `FLOW/STATIONARY` split (always >80% parking) with subtype-weighted severity (`PARKING IN A MAIN ROAD` = 3.0, `DOUBLE PARKING` = 2.8, etc.).
- **Tiered Confidence System**: Honest reporting across all **168 junctions** (HIGH/MEDIUM/LOW/INSUFFICIENT) based on data sufficiency.
- **Lane-Aware Modeling**: Sourced / Visually Verified / Estimated lane counts with citations.
- **Full Interactive Dashboard**: Single-file HTML with Leaflet map, hotspots, deployment simulator, validation, and coverage views.
- **Strong Validation**: 5/5 obstruction overlap, heavy-vehicle baseline check, TomTom city-level sanity.

---

## Architecture

| Module | Purpose | Output |
|--------|--------|--------|
| **1** | Weighted Violation Density + Phantom Cost | Top hotspots by PCU, 6-month cost sensitivity grid (₹18.5–88.8 Cr) |
| **2** | Predictive Pressure Score | Anomaly detection + trends (e.g. KR Market +98%) |
| **3** | Resource-Aware Enforcement | Severity-ranked truck routing with travel time feasibility |
| **4** | Parking Severity Heatmap | Targeting score = violations × severity × PCU impact |

---
Main script (trafficos_v7.py) automatically runs all modules and prints:

Coverage report
Top hotspots
Phantom cost range
Emerging threats
Deployment plan (Friday, 3 trucks)
Validation checks
Business impact summary

## Business Impact (Mid Scenario)

₹42.8 Cr estimated phantom congestion cost over 6 months (range ₹18.5–88.8 Cr)
Top junctions cause up to +15 min extra delay per crossing
With 3 trucks on Friday: 77%+ critical windows covered
KR Market flagged as emerging threat (+98% trend)


## Validation Highlights

Check 1: 5/5 top PCU hotspots overlap with raw obstruction violations
Check 2: Top hotspots are light-vehicle dominated (matches urban core reality)
Check 3: Model implied speed aligns closely with TomTom Bengaluru data (deviation ~3.8%)
---

Flipkart Gridlock 2.0 · Round 2 Prototype