"""
Cache management tools for ERAD MCP Server.
"""

from pathlib import Path

from loguru import logger

from .helpers import get_cache_directory, get_hazard_cache_directory, load_metadata


async def list_cached_models_tool(args: dict) -> dict:
    """List cached models."""
    model_type = args.get("model_type", "both")

    try:
        result = {}

        if model_type in ("distribution", "both"):
            cache_dir = get_cache_directory()
            metadata = load_metadata(cache_dir)
            result["distribution_models"] = [
                {
                    "name": name,
                    "filename": info.get("filename"),
                    "description": info.get("description"),
                    "added": info.get("added"),
                }
                for name, info in metadata.items()
            ]

        if model_type in ("hazard", "both"):
            hazard_cache_dir = get_hazard_cache_directory()
            hazard_metadata = load_metadata(hazard_cache_dir)
            result["hazard_models"] = [
                {
                    "name": name,
                    "filename": info.get("filename"),
                    "description": info.get("description"),
                    "added": info.get("added"),
                }
                for name, info in hazard_metadata.items()
            ]

        return {"success": True, "result": result}

    except Exception as e:
        logger.error(f"Error listing cached models: {e}")
        return {"error": str(e)}


async def get_cache_info_tool(args: dict) -> dict:
    """Get cache information."""
    try:
        dist_cache_dir = get_cache_directory()
        hazard_cache_dir = get_hazard_cache_directory()

        def get_dir_size(path: Path) -> int:
            return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

        dist_metadata = load_metadata(dist_cache_dir)
        hazard_metadata = load_metadata(hazard_cache_dir)

        return {
            "success": True,
            "distribution_cache": {
                "directory": str(dist_cache_dir),
                "model_count": len(dist_metadata),
                "size_bytes": get_dir_size(dist_cache_dir),
            },
            "hazard_cache": {
                "directory": str(hazard_cache_dir),
                "model_count": len(hazard_metadata),
                "size_bytes": get_dir_size(hazard_cache_dir),
            },
        }

    except Exception as e:
        logger.error(f"Error getting cache info: {e}")
        return {"error": str(e)}
