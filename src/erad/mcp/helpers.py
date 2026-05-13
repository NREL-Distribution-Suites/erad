"""
Helper functions for ERAD MCP Server.
"""

import json
import os
import sys
from pathlib import Path

from erad.models.asset import Asset


def get_cache_directory() -> Path:
    """Get the platform-specific cache directory for distribution models."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / ".cache"
    else:  # Linux and others
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

    cache_dir = base / "erad" / "distribution_models"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_hazard_cache_directory() -> Path:
    """Get the platform-specific cache directory for hazard models."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / ".cache"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

    cache_dir = base / "erad" / "hazard_models"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def load_metadata(cache_dir: Path) -> dict:
    """Load metadata from cache directory."""
    metadata_file = cache_dir / "models_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, "r") as f:
            return json.load(f)
    return {}


def get_historic_hazard_db() -> Path:
    """Get path to historic hazard database."""
    # Check if database exists in expected location
    db_path = Path.home() / ".cache" / "erad" / "erad_data.sqlite"
    if not db_path.exists():
        # Try alternate location
        db_path = Path("tests/data/erad_data.sqlite")
    return db_path


def serialize_asset(asset: Asset) -> dict:
    """Serialize an Asset to a dictionary."""
    return {
        "uuid": str(asset.uuid),
        "name": asset.name,
        "asset_type": asset.asset_type.value
        if hasattr(asset.asset_type, "value")
        else str(asset.asset_type),
        "latitude": asset.latitude,
        "longitude": asset.longitude,
        "height": str(asset.height) if asset.height else None,
        "elevation": str(asset.elevation) if asset.elevation else None,
        "distribution_asset": str(asset.distribution_asset),
        "connections": [str(c) for c in asset.connections],
        "asset_states": [
            {
                "timestamp": state.timestamp.isoformat(),
                "survival_probability": state.survival_probability,
                "hazard_intensities": {
                    "wind_speed": str(state.wind_speed) if state.wind_speed else None,
                    "flood_depth": str(state.flood_depth) if state.flood_depth else None,
                    "flood_velocity": str(state.flood_velocity) if state.flood_velocity else None,
                    "fire_boundary_dist": str(state.fire_boundary_dist)
                    if state.fire_boundary_dist
                    else None,
                    "peak_ground_acceleration": str(state.peak_ground_acceleration)
                    if state.peak_ground_acceleration
                    else None,
                    "peak_ground_velocity": str(state.peak_ground_velocity)
                    if state.peak_ground_velocity
                    else None,
                },
            }
            for state in sorted(asset.asset_state, key=lambda s: s.timestamp)
        ],
    }
