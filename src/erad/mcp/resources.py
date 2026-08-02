"""
MCP resources for ERAD MCP Server.
"""

import json
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver import ResourceSecurity

from erad.models.asset import Asset

from .state import state
from .helpers import get_cache_directory, load_metadata, serialize_asset


def _docs_dir() -> Path:
    """Return the ERAD documentation directory."""
    return Path(__file__).parent.parent.parent.parent / "docs"


def _key_doc_files() -> list[str]:
    """Return the key documentation files exposed as resources."""
    return [
        "intro.md",
        "api/cli.md",
        "api/mcp_server.md",
        "api/data_models.md",
        "api/enumerations.md",
        "api/quantities.md",
    ]


def register(mcp: MCPServer) -> None:
    """Register ERAD resources with the MCP server."""

    @mcp.resource("erad://docs/{doc_path}", security=ResourceSecurity())
    def read_doc_resource(doc_path: str) -> str:
        """Read a documentation file by path.

        URI pattern: erad://docs/{doc_path}
        Example: erad://docs/intro.md, erad://docs/api/cli.md
        """
        docs_dir = _docs_dir()
        file_path = docs_dir / doc_path
        if not file_path.exists():
            return json.dumps(
                {
                    "error": f"Documentation file not found: {doc_path}",
                    "available": _key_doc_files(),
                }
            )
        return file_path.read_text(encoding="utf-8")

    @mcp.resource("erad://cached-model/{model_name}")
    def read_cached_model_resource(model_name: str) -> str:
        """Read a cached distribution model.

        URI pattern: erad://cached-model/{model_name}
        """
        cache_dir = get_cache_directory()
        metadata = load_metadata(cache_dir)
        if model_name not in metadata:
            return json.dumps(
                {
                    "error": f"Cached model not found: {model_name}",
                    "available": sorted(metadata.keys()),
                }
            )
        model_file = cache_dir / metadata[model_name]["filename"]
        return model_file.read_text(encoding="utf-8")

    @mcp.resource("erad://asset-system/{system_id}")
    def read_asset_system_resource(system_id: str) -> str:
        """Read a loaded asset system.

        URI pattern: erad://asset-system/{system_id}
        """
        if system_id not in state.asset_systems:
            return json.dumps(
                {
                    "error": f"Asset system not found: {system_id}",
                    "available": list(state.asset_systems.keys()),
                }
            )
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

    @mcp.resource("erad://catalog")
    def catalog() -> str:
        """List available documentation files, cached models, and loaded asset systems."""
        docs_dir = _docs_dir()
        docs = [doc for doc in _key_doc_files() if (docs_dir / doc).exists()]

        cache_dir = get_cache_directory()
        metadata = load_metadata(cache_dir)
        cached_models = sorted(metadata.keys())

        asset_systems = []
        for system_id, asset_system in state.asset_systems.items():
            asset_count = len(list(asset_system.get_components(Asset)))
            asset_systems.append({"system_id": system_id, "asset_count": asset_count})

        return json.dumps(
            {
                "docs": docs,
                "cached_models": cached_models,
                "asset_systems": asset_systems,
            },
            indent=2,
        )
