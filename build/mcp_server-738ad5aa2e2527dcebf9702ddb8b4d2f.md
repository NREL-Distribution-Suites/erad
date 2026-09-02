# ERAD MCP Server

The ERAD MCP (Model Context Protocol) Server provides a powerful interface for running hazard simulations, querying assets, exploring historic hazards, and analyzing distribution system resilience through AI assistants like Claude Desktop and GitHub Copilot.

## Overview

The MCP server exposes ~25 tools organized into functional categories:

- **Simulation**: Load models, run hazard simulations, generate Monte Carlo scenarios
- **Asset Analysis**: Query assets, get statistics, explore network topology
- **Historic Hazards**: Load earthquakes, hurricanes, and wildfires from database
- **Fragility Curves**: Query default curves and parameters
- **Export**: Save results to SQLite, JSON, GeoJSON
- **Cache Management**: List and manage cached models
- **Documentation**: Search ERAD docs and examples
- **Utilities**: List asset types, manage loaded systems

The server is built with a **modular architecture** for easy maintenance and extensibility. Each tool category is implemented in its own Python module, making it straightforward to add new capabilities or customize existing ones.

## Installation

The MCP server is included with ERAD. Install with MCP support:

```bash
pip install NREL-erad
```

## Quick Start

### Start the Server

```bash
# Direct invocation
erad server mcp

# Or via Python module (uses the modular erad.mcp package)
python -m erad.mcp

# Or using the dedicated command
erad-mcp
```

### Configure in VS Code

Add to your `.vscode/settings.json`:

```json
{
  "github.copilot.chat.mcp": {
    "servers": {
      "erad": {
        "command": "erad-mcp",
        "args": []
      }
    }
  }
}
```

### Configure in Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "erad": {
      "command": "erad-mcp",
      "args": []
    }
  }
}
```

## Core Concepts

### Stateful Architecture

The MCP server maintains state in memory:
- **Asset Systems**: Loaded distribution models with unique IDs
- **Hazard Systems**: Loaded hazard models with unique IDs  
- **Simulation Results**: Completed simulations with result IDs

This enables workflows like:
1. Load asset system → get ID
2. Create hazard system → get ID
3. Add historic hurricane to hazard system
4. Run simulation with both IDs → get result ID
5. Query assets from asset system ID
6. Generate scenarios from result ID
7. Export tracked changes

### System IDs

Most operations return a system ID (8-character string) that you use in subsequent operations:

```
load_distribution_model → asset_system_id: "a1b2c3d4"
create_hazard_system → hazard_system_id: "e5f6g7h8"
run_simulation(a1b2c3d4, e5f6g7h8) → simulation_id: "i9j0k1l2"
```

## model_ref Interoperability

Model-loading tools support both legacy path inputs and `model_ref`:

- `load_distribution_model`: `source` or `model_ref`
- `load_hazard_model`: `file_path` or `model_ref`

### model_ref shape

```json
{
  "model_id": "abc123def456",
  "version": 2
}
```

Direct path-carrying references are also valid:

```json
{
  "stored_path": "/abs/path/to/model.json"
}
```

### Resolution order

1. `stored_path`
2. `path`
3. `source_path`
4. Registry lookup by `model_id` / `version`

Registry lookup uses `model_ref.registry_db` first, then
`DIST_STACK_MODEL_REGISTRY_DB`.

### Example payload

```json
{
  "model_ref": {
    "model_id": "abc123def456",
    "version": 2
  }
}
```

## Architecture

The MCP server is built with a modular architecture for maintainability and extensibility. The implementation is organized into focused modules:

### Module Structure

```
src/erad/mcp/
├── server.py          # Main MCP server, tool registration, request routing
├── state.py           # ServerState class for in-memory system management
├── helpers.py         # Shared utility functions (cache, serialization)
├── simulation.py      # 5 simulation tools
├── assets.py          # 4 asset query tools
├── hazards.py         # 6 historic hazard tools
├── fragility.py       # 2 fragility curve tools
├── export.py          # 3 export tools
├── cache.py           # 2 cache management tools
├── documentation.py   # 1 documentation search tool
├── utilities.py       # 3 utility tools
└── resources.py       # MCP resource protocol handlers
```

### Key Components

**server.py**: Main MCP server implementation with tool registration and request routing. Uses MCP's `@app.list_tools()`, `@app.call_tool()`, and `@app.read_resource()` decorators.

**state.py**: Global `ServerState` singleton that maintains:
- `asset_systems`: Dict of loaded distribution models
- `hazard_systems`: Dict of loaded hazard models  
- `simulation_results`: Dict of completed simulations
- `hazard_simulators`: Dict of active simulators

**Tool Modules**: Each module exports async tool functions that:
- Take a `dict` of parameters
- Access shared state from `state.py`
- Return a `dict` result (JSON-serializable)
- Handle errors gracefully with error messages in results

### Extending the Server

To add a new tool:

1. **Create the tool function** in the appropriate module (or create a new module):
```python
# In src/erad/mcp/my_module.py
from .state import state

async def my_new_tool(args: dict) -> dict:
    """Tool description."""
    try:
        param = args.get("param")
        # Implementation
        return {"result": "success", "data": result}
    except Exception as e:
        return {"error": str(e)}
```

2. **Register in server.py** by adding to `handle_list_tools()`:
```python
Tool(
    name="my_new_tool",
    description="Tool description",
    inputSchema={
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "Parameter"}
        },
        "required": ["param"]
    }
)
```

3. **Route in server.py** by adding to `handle_call_tool()`:
```python
elif name == "my_new_tool":
    result = await my_new_tool(arguments)
```

For more details, see `src/erad/mcp/README.md`.

## Tool Reference

### Simulation Tools

#### `load_distribution_model`

Load a distribution system model from file or cache.

**Parameters:**
- `source` (string): File path or cached model name
- `from_cache` (boolean): Load from cache (true) or file (false)

**Returns:**
- `system_id`: Asset system ID for use in other tools
- `asset_count`: Number of assets loaded

**Example:**
```json
{
  "source": "/path/to/model.json",
  "from_cache": false
}
```

#### `create_hazard_system`

Create a new empty hazard system.

**Returns:**
- `system_id`: Hazard system ID

#### `load_historic_hurricane`

Load a historic hurricane from the database.

**Parameters:**
- `hazard_system_id` (string): Hazard system to add to
- `hurricane_sid` (string): Hurricane SID (e.g., "2017228N14314")

**Example:**
```json
{
  "hazard_system_id": "e5f6g7h8",
  "hurricane_sid": "2017228N14314"
}
```

#### `run_simulation`

Run a hazard simulation.

**Parameters:**
- `asset_system_id` (string): Asset system ID
- `hazard_system_id` (string): Hazard system ID
- `curve_set` (string, optional): Fragility curve set name (default: "DEFAULT_CURVES")

**Returns:**
- `simulation_id`: Simulation result ID
- `timesteps`: Number of simulation timesteps
- `timestamps`: List of simulation timestamps

#### `generate_scenarios`

Generate Monte Carlo failure scenarios.

**Parameters:**
- `simulation_id` (string): Completed simulation ID
- `num_samples` (integer, optional): Number of scenarios (default: 1)
- `seed` (integer, optional): Random seed (default: 0)

**Returns:**
- `num_samples`: Number generated
- `total_tracked_changes`: Total tracked changes
- `scenarios`: Dictionary of scenario summaries

### Asset Query Tools

#### `query_assets`

Query and filter assets from a loaded system.

**Parameters:**
- `asset_system_id` (string): Asset system ID
- `asset_type` (string, optional): Filter by type
- `min_survival_probability` (number, optional): Min survival threshold
- `max_survival_probability` (number, optional): Max survival threshold
- `latitude_min`, `latitude_max` (number, optional): Latitude bounds
- `longitude_min`, `longitude_max` (number, optional): Longitude bounds

**Returns:**
- `filtered_count`: Number of matching assets
- `assets`: List of asset details

#### `get_asset_details`

Get detailed information about a specific asset.

**Parameters:**
- `asset_system_id` (string): Asset system ID
- `asset_name` (string): Asset name

#### `get_asset_statistics`

Calculate statistics about assets.

**Parameters:**
- `asset_system_id` (string): Asset system ID

**Returns:**
- `statistics`: Object with counts, survival probability stats

#### `get_network_topology`

Get network topology as node/edge lists.

**Parameters:**
- `asset_system_id` (string): Asset system ID

**Returns:**
- `node_count`, `edge_count`: Topology size
- `nodes`, `edges`: Graph structure

### Historic Hazard Tools

#### `list_historic_hurricanes`

List available hurricanes from database.

**Parameters:**
- `year` (integer, optional): Filter by year
- `limit` (integer, optional): Max results (default: 50)

**Returns:**
- `hurricanes`: List with `sid`, `name`, `season`

#### `list_historic_earthquakes`

List available earthquakes.

**Parameters:**
- `min_magnitude` (number, optional): Minimum magnitude
- `limit` (integer, optional): Max results (default: 50)

**Returns:**
- `earthquakes`: List with `earthquake_code`, `date`, `magnitude`, location

#### `list_historic_wildfires`

List available wildfires.

**Parameters:**
- `year` (integer, optional): Filter by year
- `limit` (integer, optional): Max results (default: 50)

**Returns:**
- `wildfires`: List with `fire_name`, `fire_year`

#### `load_historic_earthquake`

Load a historic earthquake.

**Parameters:**
- `hazard_system_id` (string): Hazard system ID
- `earthquake_code` (string): Earthquake code (e.g., "ISCGEM851547")

#### `load_historic_wildfire`

Load a historic wildfire.

**Parameters:**
- `hazard_system_id` (string): Hazard system ID
- `wildfire_name` (string): Fire name (e.g., "GREAT LAKES FIRE")

### Fragility Curve Tools

#### `list_fragility_curves`

List available fragility curve sets and hazard types.

**Returns:**
- `curve_sets`: List of curve set names
- `hazard_types`: Dictionary of hazard types with asset coverage

#### `get_fragility_curve_parameters`

Get fragility curve parameters for specific asset/hazard combination.

**Parameters:**
- `hazard_type` (string): Hazard parameter (e.g., "wind_speed", "flood_depth")
- `asset_type` (string): Asset type

**Returns:**
- `curves`: List of matching curves with distribution and parameters

### Export Tools

#### `export_to_sqlite`

Export simulation results to SQLite database.

**Parameters:**
- `asset_system_id` (string): Asset system with results
- `output_path` (string): Output file path

#### `export_to_json`

Export asset or hazard system to JSON.

**Parameters:**
- `system_id` (string): System ID to export
- `system_type` (string): "asset" or "hazard"
- `output_path` (string): Output file path

#### `export_tracked_changes`

Export Monte Carlo scenario tracked changes.

**Parameters:**
- `simulation_id` (string): Simulation with tracked changes
- `output_path` (string): Output file path

### Cache Management Tools

#### `list_cached_models`

List all cached distribution and hazard models.

**Parameters:**
- `model_type` (string, optional): "distribution", "hazard", or "both" (default: "both")

**Returns:**
- `distribution_models`, `hazard_models`: Lists with name, filename, description

#### `get_cache_info`

Get cache directory paths and usage statistics.

**Returns:**
- `distribution_cache`, `hazard_cache`: Objects with directory, model count, size

### Documentation Tools

#### `search_documentation`

Search ERAD documentation for topics.

**Parameters:**
- `query` (string): Search query

**Returns:**
- `results`: List of matching files with snippets

### Utility Tools

#### `list_asset_types`

List all available asset types in ERAD.

**Returns:**
- `asset_types`: List of asset type strings

#### `list_loaded_systems`

List all currently loaded systems in memory.

**Returns:**
- `asset_systems`, `hazard_systems`, `simulations`: Currently loaded items

#### `clear_system`

Remove a system from memory.

**Parameters:**
- `system_id` (string): System ID to remove
- `system_type` (string): "asset", "hazard", or "simulation"

## MCP Resources

The server also exposes resources for direct access:

- `erad://docs/{path}` - Documentation files
- `erad://cached-model/{name}` - Cached distribution models
- `erad://asset-system/{id}` - Loaded asset systems

## Workflow Examples

### Example 1: Basic Simulation

```
1. list_cached_models → See available models
2. load_distribution_model(from_cache=true, source="my_model")
   → Returns asset_system_id: "abc123"
3. create_hazard_system → Returns hazard_system_id: "def456"
4. list_historic_hurricanes(year=2017)
5. load_historic_hurricane(hazard_system_id="def456", hurricane_sid="2017228N14314")
6. run_simulation(asset_system_id="abc123", hazard_system_id="def456")
   → Returns simulation_id: "ghi789"
7. get_asset_statistics(asset_system_id="abc123") → See impact
8. export_to_sqlite(asset_system_id="abc123", output_path="results.db")
```

### Example 2: Monte Carlo Analysis

```
1. Load model and run simulation (steps 1-6 from Example 1)
2. generate_scenarios(simulation_id="ghi789", num_samples=100, seed=42)
   → Get scenario summaries
3. export_tracked_changes(simulation_id="ghi789", output_path="scenarios.json")
4. query_assets(asset_system_id="abc123", max_survival_probability=0.5)
   → Find most vulnerable assets
```

### Example 3: Multi-Hazard Analysis

```
1. load_distribution_model
2. create_hazard_system → hazard_id_1
3. load_historic_hurricane(hazard_id_1, sid="...")
4. run_simulation → simulation_id_1
5. create_hazard_system → hazard_id_2
6. load_historic_earthquake(hazard_id_2, code="...")
7. run_simulation → simulation_id_2
8. Compare results using query_assets and statistics
```

## Troubleshooting

### Database Not Found

If historic hazard queries fail:
- The database auto-downloads on first use (~500MB)
- Check `~/.cache/erad/erad_data.sqlite` exists
- Manually download from: `https://storage.googleapis.com/erad_v2_dataset/erad_data.sqlite`

### Out of Memory

For large models:
- Use `clear_system` to remove unused systems
- Process assets in batches using `query_assets` filters
- Generate fewer Monte Carlo samples

### Import Errors

Ensure all dependencies installed:
```bash
pip install "NREL-erad[dev]"
```

## Advanced Usage

### Custom Fragility Curves

Currently, custom curves must be added to hazard systems before simulation. Support for dynamic curve creation is planned.

### Batch Operations

Multiple simulations can run in parallel by creating separate hazard systems for each scenario.

### Network Analysis

Use `get_network_topology` with NetworkX for:
- Shortest path analysis
- Centrality calculations
- Community detection
- Critical node identification

## See Also

- [CLI Documentation](cli.md) - Command-line interface
- [Data Models](data_models.md) - Asset and hazard model specifications
- [API Reference](../reference/api/index.md) - Python API documentation
- `src/erad/mcp/README.md` - Detailed module architecture and development guide
