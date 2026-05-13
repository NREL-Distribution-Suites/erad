# ERAD MCP Server Module Organization

## Overview
The ERAD MCP server has been refactored from a monolithic 1,886-line file into a well-organized modular package structure for better maintainability and extensibility.

## Directory Structure

```
src/erad/mcp/
├── __init__.py           # Package initialization, exports main/serve
├── server.py             # Main MCP server setup and tool registration
├── state.py              # ServerState class for managing loaded systems
├── helpers.py            # Shared helper functions
├── simulation.py         # Simulation and scenario generation tools (5 tools)
├── assets.py             # Asset query and analysis tools (4 tools)
├── hazards.py            # Historic hazard database tools (6 tools)
├── fragility.py          # Fragility curve tools (2 tools)
├── export.py             # Data export tools (3 tools)
├── cache.py              # Cache management tools (2 tools)
├── documentation.py      # Documentation search tool (1 tool)
├── utilities.py          # Utility and system management (3 tools)
└── resources.py          # MCP resource handlers (2 functions)
```

## Module Details

### Core Modules

#### `server.py`
Main MCP server implementation with:
- Server initialization using `mcp.server.Server`
- Tool registration (25+ tools total)
- Request routing via `@app.call_tool()` handler
- Resource handlers (`@app.list_resources()`, `@app.read_resource()`)
- Main entry point functions (`main()`, `serve()`)

#### `state.py`
State management for loaded systems:
- `ServerState` class with dicts for:
  - `asset_systems`: Loaded distribution models
  - `hazard_systems`: Loaded hazard models
  - `simulation_results`: Completed simulations
  - `hazard_simulators`: Active simulators
- `generate_id()`: Creates 8-character UUIDs
- `clear()`: Resets all state
- Global `state` instance shared across modules

#### `helpers.py`
Shared utility functions:
- `get_cache_directory()`: Returns user cache directory
- `get_hazard_cache_directory()`: Returns hazard cache directory
- `load_metadata()`: Loads cached model metadata
- `serialize_asset()`: Converts Asset to dict with survival probability

### Tool Modules

#### `simulation.py` (5 tools)
- `load_distribution_model_tool`: Load GDM from file/cache
- `load_hazard_model_tool`: Load hazard system from JSON
- `create_hazard_system_tool`: Create empty hazard system
- `run_simulation_tool`: Execute hazard simulation
- `generate_scenarios_tool`: Generate Monte Carlo scenarios

#### `assets.py` (4 tools)
- `query_assets_tool`: Query/filter assets with multiple criteria
- `get_asset_details_tool`: Get detailed asset information
- `get_asset_statistics_tool`: Calculate asset statistics
- `get_network_topology_tool`: Get network nodes and edges

#### `hazards.py` (6 tools)
- `list_historic_hurricanes_tool`: List hurricanes from database
- `list_historic_earthquakes_tool`: List earthquakes from database
- `list_historic_wildfires_tool`: List wildfires from database
- `load_historic_hurricane_tool`: Load hurricane into system
- `load_historic_earthquake_tool`: Load earthquake into system
- `load_historic_wildfire_tool`: Load wildfire into system

#### `fragility.py` (2 tools)
- `list_fragility_curves_tool`: List available curve sets
- `get_fragility_curve_parameters_tool`: Get curve parameters

#### `export.py` (3 tools)
- `export_to_sqlite_tool`: Export results to SQLite
- `export_to_json_tool`: Export system to JSON
- `export_tracked_changes_tool`: Export scenario tracked changes

#### `cache.py` (2 tools)
- `list_cached_models_tool`: List cached distribution/hazard models
- `get_cache_info_tool`: Get cache directory information

#### `documentation.py` (1 tool)
- `search_documentation_tool`: Search markdown documentation

#### `utilities.py` (3 tools)
- `list_asset_types_tool`: List available AssetTypes
- `list_loaded_systems_tool`: List loaded systems in memory
- `clear_system_tool`: Remove system from memory

#### `resources.py` (2 functions)
- `list_resources()`: List available MCP resources
- `read_resource(uri)`: Read resource by erad:// URI

## Entry Points

### Command Line
```bash
# Via CLI subcommand
erad server mcp

# Via standalone script
erad-mcp
```

### Programmatic
```python
from erad.mcp import main, serve

# Run the server
main()

# Or use async serve function
import asyncio
asyncio.run(serve())
```

### Legacy Compatibility
```python
from erad.mcp_server import cli_main
cli_main()  # Works for backward compatibility
```

## Benefits of Modular Structure

1. **Maintainability**: Each module has a focused purpose (~100-300 lines)
2. **Discoverability**: Clear organization by tool category
3. **Testability**: Can test individual modules in isolation
4. **Extensibility**: Easy to add new tool categories
5. **Code Reuse**: Helper functions shared across modules
6. **Documentation**: Each module can be documented separately

## Testing

All tests pass with the new structure:
```bash
pytest tests/test_mcp_server.py -v
# 13 passed, 1 warning in 1.04s
```

Tests import from modular structure:
```python
from erad.mcp.state import ServerState, state
from erad.mcp.simulation import load_distribution_model_tool
from erad.mcp.assets import query_assets_tool
# etc.
```

## Next Steps for Development

1. **Add New Tools**: Create new tool function in appropriate category module
2. **Register Tool**: Add to `handle_list_tools()` in `server.py`
3. **Route Tool**: Add case to `handle_call_tool()` in `server.py`
4. **Write Tests**: Add tests to `tests/test_mcp_server.py`
5. **Document**: Update module docstrings and `docs/api/mcp_server.md`

## File Sizes (Lines of Code)

| Module | Lines | Purpose |
|--------|-------|---------|
| server.py | ~600 | Server setup and routing |
| state.py | ~60 | State management |
| helpers.py | ~100 | Utility functions |
| simulation.py | ~250 | Simulation tools |
| assets.py | ~280 | Asset query tools |
| hazards.py | ~380 | Historic hazard tools |
| fragility.py | ~90 | Fragility curve tools |
| export.py | ~160 | Export tools |
| cache.py | ~120 | Cache management |
| documentation.py | ~90 | Documentation search |
| utilities.py | ~150 | Utility tools |
| resources.py | ~120 | Resource handlers |
| **Total** | **~2,400** | Modular implementation |
| *Original* | *1,886* | Monolithic file |

Note: The modular version is slightly larger due to proper imports and docstrings in each file, but much more maintainable.
