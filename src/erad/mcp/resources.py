"""
MCP resources for ERAD MCP Server.
"""

import json
from pathlib import Path

from mcp.types import Resource

from erad.models.asset import Asset

from .state import state
from .helpers import get_cache_directory, load_metadata, serialize_asset


async def list_resources() -> list[Resource]:
    """List available documentation resources."""
    resources = []

    # Add documentation resources
    docs_dir = Path(__file__).parent.parent.parent.parent / "docs"
    if docs_dir.exists():
        # Key documentation files
        doc_files = [
            "intro.md",
            "api/cli.md",
            "api/mcp_server.md",
            "api/data_models.md",
            "api/enumerations.md",
            "api/quantities.md",
        ]

        for doc_file in doc_files:
            file_path = docs_dir / doc_file
            if file_path.exists():
                resources.append(
                    Resource(
                        uri=f"erad://docs/{doc_file}",
                        name=f"Documentation: {doc_file}",
                        mimeType="text/markdown",
                        description=f"ERAD documentation - {doc_file}",
                    )
                )

    # Add cached model resources
    cache_dir = get_cache_directory()
    metadata = load_metadata(cache_dir)
    for model_name in metadata.keys():
        resources.append(
            Resource(
                uri=f"erad://cached-model/{model_name}",
                name=f"Cached Model: {model_name}",
                mimeType="application/json",
                description=f"Cached distribution model: {model_name}",
            )
        )

    # Add loaded asset systems as resources
    for system_id, asset_system in state.asset_systems.items():
        asset_count = len(list(asset_system.get_components(Asset)))
        resources.append(
            Resource(
                uri=f"erad://asset-system/{system_id}",
                name=f"Asset System: {system_id}",
                mimeType="application/json",
                description=f"Loaded asset system with {asset_count} assets",
            )
        )

    return resources


async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    if uri.startswith("erad://docs/"):
        # Read documentation file
        doc_path = uri.replace("erad://docs/", "")
        docs_dir = Path(__file__).parent.parent.parent.parent / "docs"
        file_path = docs_dir / doc_path

        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Documentation file not found: {doc_path}")

    elif uri.startswith("erad://cached-model/"):
        # Read cached model
        model_name = uri.replace("erad://cached-model/", "")
        cache_dir = get_cache_directory()
        metadata = load_metadata(cache_dir)

        if model_name in metadata:
            model_file = cache_dir / metadata[model_name]["filename"]
            return model_file.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Cached model not found: {model_name}")

    elif uri.startswith("erad://asset-system/"):
        # Read asset system
        system_id = uri.replace("erad://asset-system/", "")
        if system_id in state.asset_systems:
            asset_system = state.asset_systems[system_id]
            assets = list(asset_system.get_components(Asset))
            return json.dumps(
                {
                    "system_id": system_id,
                    "asset_count": len(assets),
                    "assets": [serialize_asset(asset) for asset in assets],
                },
                indent=2,
            )
        else:
            raise ValueError(f"Asset system not found: {system_id}")

    else:
        raise ValueError(f"Unknown resource URI: {uri}")
