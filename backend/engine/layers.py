"""Functional layer registry and deterministic feature propagation checks."""

PREDICTIVE_LAYERS = [
    "injury_availability", "depth_chart_replacement", "offensive_line", "defensive_front",
    "ol_vs_dl", "game_script", "play_volume", "opportunity_distribution", "route_alignment",
    "coverage_assignment", "weather", "surface_stadium", "referee", "coaching", "red_zone",
    "explosive_plays", "qb_correlation", "position_matchup", "offensive_scheme", "defensive_scheme",
    "defensive_fantasy", "monte_carlo", "league_scoring", "calibration", "data_cutoff",
    "feature_provenance", "model_versioning", "player_identity_crosswalk", "position_projection_models",
    "lineup_optimization", "static_model_audit", "confidence_uncertainty",
]

METADATA_LAYERS = {
    "calibration", "data_cutoff", "feature_provenance", "model_versioning",
    "lineup_optimization", "static_model_audit", "confidence_uncertainty",
}


def layer_manifest():
    return [{
        "id": i + 1,
        "name": name,
        "kind": "metadata" if name in METADATA_LAYERS else "predictive",
        "required": True,
    } for i, name in enumerate(PREDICTIVE_LAYERS)]


def propagation_audit(factors):
    """Verify that predictive factors have explicit numeric impact evidence."""
    required = [
        "availability", "replacement", "offensive_line", "defensive_front", "trench_matchup",
        "game_script", "play_volume", "opportunity", "route_alignment", "coverage_assignment",
        "weather", "surface", "referee", "coaching", "red_zone", "explosive", "qb_correlation",
        "position_matchup", "offensive_scheme", "defensive_scheme", "defensive_fantasy",
    ]
    checks = []
    for name in required:
        item = factors.get(name, {}) if isinstance(factors, dict) else {}
        checks.append({
            "layer": name,
            "present": bool(item),
            "status": item.get("status", "missing"),
            "impact": item.get("impact"),
            "active": item.get("active", False),
        })
    return checks
