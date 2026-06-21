"""
TrafficOS API — FastAPI backend
Runs the analytics engine once at startup, caches results, and serves
them as JSON for the frontend.
"""

import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np

import engine as eng

app = FastAPI(
    title="TrafficOS API",
    description="Bengaluru congestion intelligence engine — density ranking, "
                 "predictive pressure scoring, and resource-aware deployment.",
    version="6.0",
)

# CORS open for the demo — tighten origins before any real production use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = os.environ.get(
    "TRAFFICOS_DATA_PATH",
    os.path.join(os.path.dirname(__file__), "data", "violations.csv"),
)

# ── In-memory cache, populated once at startup ──────────────────────────────
_cache = {}


def _df_to_records(df: pd.DataFrame):
    """Convert a DataFrame to JSON-safe records (handles NaN, numpy types, dates)."""
    out = df.replace({np.nan: None}).copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].astype(str)
        elif out[col].dtype == "object":
            out[col] = out[col].apply(
                lambda v: str(v) if hasattr(v, "strftime") else v
            )
    return out.to_dict(orient="records")


def run_pipeline():
    """Runs the full engine once. Called at startup and cached in memory."""
    junc = eng.load_and_weight(DATA_FILE)
    density, robust, sensitivity = eng.run_module1(junc)
    coverage = eng.run_coverage_report(junc)
    pressure = eng.run_module2(junc, robust)
    trucks, uncovered, day_slots = eng.run_module3(
        junc, pressure, target_day="Friday", n_trucks=3
    )
    heatmap = eng.run_severity_heatmap(junc, density)
    df_raw = pd.read_csv(DATA_FILE, low_memory=False)

    _cache["junc"] = junc
    _cache["density"] = density
    _cache["robust"] = robust
    _cache["sensitivity"] = sensitivity
    _cache["coverage"] = coverage
    _cache["pressure"] = pressure
    _cache["trucks"] = trucks
    _cache["uncovered"] = uncovered
    _cache["day_slots"] = day_slots
    _cache["heatmap"] = heatmap
    _cache["df_raw"] = df_raw
    _cache["loaded_at"] = datetime.utcnow().isoformat()
    _cache["ready"] = True


@app.on_event("startup")
def startup():
    try:
        run_pipeline()
    except Exception as e:
        # Don't crash the whole server if the CSV is missing on first deploy —
        # surface a clear error on every endpoint instead of a blank 500.
        _cache["ready"] = False
        _cache["error"] = str(e)


def _ensure_ready():
    if not _cache.get("ready"):
        raise HTTPException(
            status_code=503,
            detail=f"Engine not ready: {_cache.get('error', 'still loading')}",
        )


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "TrafficOS API",
        "status": "ready" if _cache.get("ready") else "not ready",
        "loaded_at": _cache.get("loaded_at"),
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"ready": _cache.get("ready", False), "error": _cache.get("error")}


@app.get("/api/density")
def get_density(limit: int = Query(10, ge=1, le=168)):
    """Top hotspots by peak avg PCU — Module 1 primary ranking."""
    _ensure_ready()
    d = _cache["density"].head(limit).reset_index()
    d = d.rename(columns={"index": "rank"})
    return {"count": len(d), "data": _df_to_records(d)}


@app.get("/api/sensitivity")
def get_sensitivity():
    """3x3 BPR sensitivity grid (VOT x demand ratio) — phantom cost range."""
    _ensure_ready()
    return {"data": _df_to_records(_cache["sensitivity"])}


@app.get("/api/coverage")
def get_coverage():
    """Tiered data-sufficiency report across all 168 junctions."""
    _ensure_ready()
    cov = _cache["coverage"]
    tier_counts = cov["tier"].value_counts().to_dict()
    return {
        "total_junctions": len(cov),
        "tier_counts": tier_counts,
        "data": _df_to_records(cov),
    }


@app.get("/api/pressure")
def get_pressure(
    risk_tier: str | None = None,
    junction: str | None = None,
    limit: int = Query(100, ge=1, le=2000),
):
    """Module 2 predictive pressure profiles, optionally filtered."""
    _ensure_ready()
    p = _cache["pressure"]
    if risk_tier:
        p = p[p["risk_tier"] == risk_tier.upper()]
    if junction:
        p = p[p["junction_name"].str.contains(junction, case=False, na=False)]
    return {"count": len(p), "data": _df_to_records(p.head(limit))}


@app.get("/api/emerging-threats")
def get_emerging_threats(min_pcu: float = 3.0, min_trend: float = 50.0):
    """Junctions trending upward — filtered to avoid micro-junction noise."""
    _ensure_ready()
    p = _cache["pressure"]
    emerging = p[(p["trend_pct"] > min_trend) & (p["avg_pcu"] >= min_pcu)]
    emerging = emerging.sort_values("trend_pct", ascending=False)
    return {"count": len(emerging), "data": _df_to_records(emerging.head(20))}


@app.get("/api/deployment")
def get_deployment(day: str = "Friday", n_trucks: int = Query(3, ge=1, le=10)):
    """Module 3 truck routing. Re-runs if day/n_trucks differs from cached default."""
    _ensure_ready()
    if day == "Friday" and n_trucks == 3:
        trucks, uncovered = _cache["trucks"], _cache["uncovered"]
    else:
        trucks, uncovered, _ = eng.run_module3(
            _cache["junc"], _cache["pressure"], target_day=day, n_trucks=n_trucks
        )
    uncovered_clean = []
    for u in uncovered:
        rec = u.to_dict() if hasattr(u, "to_dict") else dict(u)
        uncovered_clean.append(
            {k: (None if pd.isna(v) else v) for k, v in rec.items()}
        )
    return {
        "day": day,
        "n_trucks": n_trucks,
        "trucks": trucks,
        "uncovered": uncovered_clean,
    }


@app.get("/api/cross-validation")
def get_cross_validation():
    """Internal + external validation checks (obstruction overlap, heavy-vehicle
    baseline, TomTom city-level sanity check)."""
    _ensure_ready()
    density = _cache["density"]
    df_raw = _cache["df_raw"]
    junc = df_raw[df_raw["junction_name"] != "No Junction"].copy()
    our_top5 = density["junction_name"].head(5).tolist()

    mask = junc["violation_type"].astype(str).str.contains(
        "WRONG PARKING|PARKING IN A MAIN ROAD|NO PARKING", case=False, na=False
    )
    viol_rank = junc[mask].groupby("junction_name").size().sort_values(ascending=False)
    top10_viol = viol_rank.head(10).index.tolist()
    overlap = [j for j in our_top5 if j in top10_viol]

    heavy_set = {
        "HGV", "TANKER", "LORRY/GOODS VEHICLE", "PRIVATE BUS", "BUS (BMTC/KSRTC)",
        "TOURIST BUS", "FACTORY BUS", "MINI LORRY", "TT",
    }
    junc["is_heavy"] = (
        junc["updated_vehicle_type"].fillna(junc["vehicle_type"])
        .astype(str).str.upper().isin(heavy_set)
    )
    base_h = junc["is_heavy"].mean() * 100
    heavy_by_j = junc.groupby("junction_name")["is_heavy"].mean() * 100

    check2 = [
        {
            "junction": j,
            "heavy_pct": round(float(heavy_by_j.get(j, 0)), 2),
            "above_baseline": bool(heavy_by_j.get(j, 0) > base_h),
        }
        for j in our_top5
    ]

    FREE_FLOW_KMPH = 30
    top_pcu = density["peak_avg_pcu"].head(5).mean()
    lanes = eng.DEFAULT_LANES
    blocked = min(top_pcu / eng.BLOCK_PCU, lanes * 0.8)
    eff = max(lanes - blocked, 0.5)
    vc = (0.85 * lanes * eng.LANE_CAP) / (eff * eng.LANE_CAP)
    delay_factor = eng.ALPHA * (vc ** eng.BETA)
    implied_speed = FREE_FLOW_KMPH / (1 + delay_factor)

    return {
        "check1_obstruction_overlap": {
            "overlap_count": len(overlap),
            "total": 5,
            "matched_junctions": [j.split(" - ")[-1] for j in overlap],
        },
        "check2_heavy_vehicle_baseline": {
            "city_baseline_pct": round(float(base_h), 2),
            "junctions": check2,
        },
        "check3_tomtom_sanity_check": {
            "tomtom_published_speed_kmph": eng.TOMTOM_BENGALURU_AVG_SPEED_KMPH,
            "model_implied_speed_kmph": round(float(implied_speed), 1),
            "deviation_pct": round(
                abs(implied_speed - eng.TOMTOM_BENGALURU_AVG_SPEED_KMPH)
                / eng.TOMTOM_BENGALURU_AVG_SPEED_KMPH * 100, 1
            ),
            
        },
    }


@app.get("/api/business-impact")
def get_business_impact():
    """Summary numbers for the business-impact / judge-facing slide."""
    _ensure_ready()
    density, robust, sensitivity, coverage = (
        _cache["density"], _cache["robust"], _cache["sensitivity"], _cache["coverage"]
    )
    mid_cost = sensitivity.loc[
        (sensitivity["vot"] == "mid") & (sensitivity["demand"] == "mid"), "total_6mo_rs"
    ].values[0]
    top3 = density["junction_name"].head(3).tolist()
    top3_pcu = density["peak_avg_pcu"].head(3).tolist()
    tier_counts = coverage["tier"].value_counts().to_dict()

    delay_rows = []
    for j, pcu in zip(top3, top3_pcu):
        lanes = eng.LANE_MAP.get(j, eng.DEFAULT_LANES)
        delay_min = eng._delay_per_vehicle_min(pcu, lanes)
        delay_rows.append({
            "junction": j.split(" - ")[-1],
            "delay_min": round(float(delay_min), 1),
            "lanes": lanes,
            "lane_confidence": eng.lane_confidence(j),
        })

    return {
        "coverage": {
            "total_junctions": len(coverage),
            "high": int(tier_counts.get("HIGH", 0)),
            "medium": int(tier_counts.get("MEDIUM", 0)),
            "low": int(tier_counts.get("LOW", 0)),
            "insufficient": int(tier_counts.get("INSUFFICIENT", 0)),
        },
        "fleet_delay_impact": delay_rows,
        "phantom_cost_6mo": {
            "mid_scenario_rs": round(float(mid_cost), 0),
            "mid_scenario_cr": round(float(mid_cost) / 1e7, 1),
            "range_low_cr": round(float(sensitivity["total_6mo_rs"].min()) / 1e7, 1),
            "range_high_cr": round(float(sensitivity["total_6mo_rs"].max()) / 1e7, 1),
            "high_confidence_junctions": int(robust["junction_name"].nunique()),
        },
    }


@app.get("/api/junction/{junction_name}")
def get_junction_detail(junction_name: str):
    """Full profile for a single junction — used by the map popup / detail page."""
    _ensure_ready()
    density = _cache["density"]
    pressure = _cache["pressure"]
    row = density[density["junction_name"] == junction_name]
    if row.empty:
        raise HTTPException(status_code=404, detail="Junction not found")
    profiles = pressure[pressure["junction_name"] == junction_name]
    lanes = eng.LANE_MAP.get(junction_name, eng.DEFAULT_LANES)
    return {
        "junction_name": junction_name,
        "rank": int(row.index[0]),
        "peak_avg_pcu": float(row["peak_avg_pcu"].values[0]),
        "lanes": lanes,
        "lane_confidence": eng.lane_confidence(junction_name),
        "hourly_profiles": _df_to_records(profiles),
    }


@app.get("/api/locations")
def get_locations():
    """Lat/lon for all junctions with data, for map rendering on the frontend."""
    _ensure_ready()
    junc = _cache["junc"]
    loc = junc.groupby("junction_name")[["latitude", "longitude"]].mean().reset_index()
    density = _cache["density"].reset_index().rename(columns={"index": "rank"})
    merged = loc.merge(density, on="junction_name", how="left")
    merged["lanes"] = merged["junction_name"].map(eng.LANE_MAP).fillna(eng.DEFAULT_LANES)
    merged["lane_confidence"] = merged["junction_name"].apply(eng.lane_confidence)
    return {"count": len(merged), "data": _df_to_records(merged)}


@app.get("/api/heatmap")
def get_heatmap(limit: int = Query(168, ge=1, le=168)):
    """Parking-violation-density vs PCU-impact heatmap data — direct response
    to the brief's 'heatmap of parking violations vs. congestion impact' ask.
    Each point carries violation_count, avg_severity, peak_avg_pcu, and a
    combined targeting_score for enforcement prioritization."""
    _ensure_ready()
    h = _cache["heatmap"].head(limit)
    return {"count": len(h), "data": _df_to_records(h.reset_index().rename(columns={"index": "rank"}))}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
