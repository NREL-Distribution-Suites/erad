"""
ERAD MCP Server Demo

This script demonstrates how to interact with the ERAD MCP server
programmatically for testing and development purposes.

For production use, the MCP server is designed to be used with
MCP clients like Claude Desktop or VS Code Copilot.
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _demo_list_tools(session: ClientSession):
    """List available tools and resources."""
    print("Available Tools:")
    print("-" * 70)
    tools = await session.list_tools()
    for i, tool in enumerate(tools.tools, 1):
        print(f"{i:2d}. {tool.name}")
        print(f"    {tool.description}")
    print()

    print("Available Resources:")
    print("-" * 70)
    resources = await session.list_resources()
    if resources.resources:
        for resource in resources.resources[:10]:
            print(f"  • {resource.name}")
        if len(resources.resources) > 10:
            print(f"  ... and {len(resources.resources) - 10} more")
    else:
        print("  (No resources available)")
    print()


async def _demo_asset_types(session: ClientSession):
    """Demo 1: List asset types."""
    print("Demo 1: Listing Asset Types")
    print("-" * 70)
    result = await session.call_tool("list_asset_types", {})
    data = json.loads(result.content[0].text)
    if data.get("success"):
        print(f"Found {data['count']} asset types:")
        for asset_type in data["asset_types"][:10]:
            print(f"  • {asset_type}")
        if len(data["asset_types"]) > 10:
            print(f"  ... and {len(data['asset_types']) - 10} more")
    print()


async def _demo_cached_models(session: ClientSession):
    """Demo 2: List cached models."""
    print("Demo 2: Listing Cached Models")
    print("-" * 70)
    result = await session.call_tool("list_cached_models", {"model_type": "both"})
    data = json.loads(result.content[0].text)
    if data.get("success"):
        result_data = data["result"]
        dist_count = len(result_data.get("distribution_models", []))
        hazard_count = len(result_data.get("hazard_models", []))
        print(f"Distribution models: {dist_count}")
        print(f"Hazard models: {hazard_count}")

        if dist_count > 0:
            print("\nDistribution models:")
            for model in result_data["distribution_models"][:5]:
                print(f"  • {model['name']}")
                if model.get("description"):
                    print(f"    {model['description']}")
    print()


async def _demo_fragility_curves(session: ClientSession):
    """Demo 3: List fragility curves."""
    print("Demo 3: Listing Fragility Curves")
    print("-" * 70)
    result = await session.call_tool("list_fragility_curves", {})
    data = json.loads(result.content[0].text)
    if data.get("success"):
        print(f"Curve sets: {', '.join(data['curve_sets'])}")
        print("\nHazard types covered:")
        for hazard_type, info in data["hazard_types"].items():
            print(f"  • {hazard_type}: {info['curve_count']} curves")
    print()


async def _demo_historic_hurricanes(session: ClientSession):
    """Demo 4: List historic hurricanes."""
    print("Demo 4: Listing Historic Hurricanes (2017)")
    print("-" * 70)
    try:
        result = await session.call_tool("list_historic_hurricanes", {"year": 2017, "limit": 10})
        data = json.loads(result.content[0].text)
        if data.get("success"):
            print(f"Found {data['count']} hurricanes from 2017:")
            for hurricane in data["hurricanes"]:
                print(f"  • {hurricane['name']} (SID: {hurricane['sid']})")
        elif "error" in data:
            print(f"Note: {data['error']}")
            print("(Historic hazard database may not be downloaded yet)")
    except Exception as e:
        print(f"Note: Database not available - {e}")
    print()


async def _demo_hazard_system(session: ClientSession):
    """Demo 5: Create and manage systems."""
    print("Demo 5: Creating Hazard System")
    print("-" * 70)
    result = await session.call_tool("create_hazard_system", {})
    data = json.loads(result.content[0].text)
    if data.get("success"):
        print(f"✓ Created hazard system: {data['system_id']}")

        result = await session.call_tool("list_loaded_systems", {})
        data = json.loads(result.content[0].text)
        if data.get("success"):
            print("\nCurrently loaded:")
            print(f"  • Asset systems: {len(data['asset_systems'])}")
            print(f"  • Hazard systems: {len(data['hazard_systems'])}")
            print(f"  • Simulations: {len(data['simulations'])}")
    print()


async def _demo_search_docs(session: ClientSession):
    """Demo 6: Search documentation."""
    print("Demo 6: Searching Documentation")
    print("-" * 70)
    result = await session.call_tool("search_documentation", {"query": "simulation"})
    data = json.loads(result.content[0].text)
    if data.get("success"):
        print(f"Found {data['result_count']} matching documents:")
        for doc in data["results"][:3]:
            print(f"\n  📄 {doc['file']}")
            print(f"     {doc['match_count']} matches")
            if doc["snippets"]:
                snippet = doc["snippets"][0][:100]
                print(f"     Preview: {snippet}...")
    print()


async def _demo_cache_info(session: ClientSession):
    """Demo 7: Cache information."""
    print("Demo 7: Cache Information")
    print("-" * 70)
    result = await session.call_tool("get_cache_info", {})
    data = json.loads(result.content[0].text)
    if data.get("success"):
        dist = data["distribution_cache"]
        hazard = data["hazard_cache"]

        print("Distribution Model Cache:")
        print(f"  Location: {dist['directory']}")
        print(f"  Models: {dist['model_count']}")
        print(f"  Size: {dist['size_bytes'] / 1024 / 1024:.2f} MB")

        print("\nHazard Model Cache:")
        print(f"  Location: {hazard['directory']}")
        print(f"  Models: {hazard['model_count']}")
        print(f"  Size: {hazard['size_bytes'] / 1024 / 1024:.2f} MB")
    print()


async def run_demo():
    """Run MCP server demo."""

    print("=" * 70)
    print("ERAD MCP Server Demo")
    print("=" * 70)
    print()

    server_params = StdioServerParameters(command="erad-mcp", args=[], env=None)

    print("Starting MCP server...")
    print()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✓ Server connected and initialized")
            print()

            await _demo_list_tools(session)
            await _demo_asset_types(session)
            await _demo_cached_models(session)
            await _demo_fragility_curves(session)
            await _demo_historic_hurricanes(session)
            await _demo_hazard_system(session)
            await _demo_search_docs(session)
            await _demo_cache_info(session)

            print("=" * 70)
            print("Demo Complete!")
            print("=" * 70)
            print()
            print("Next Steps:")
            print("  1. Configure the MCP server in your AI assistant")
            print("  2. Load a distribution model using load_distribution_model")
            print("  3. Add hazards using load_historic_* tools")
            print("  4. Run simulations and analyze results")
            print()
            print("For full documentation, see:")
            print("  docs/api/mcp_server.md")
            print()


def main():
    """Main entry point."""
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError running demo: {e}")
        print("\nMake sure the ERAD MCP server is installed:")
        print("  pip install NREL-erad")


if __name__ == "__main__":
    main()
