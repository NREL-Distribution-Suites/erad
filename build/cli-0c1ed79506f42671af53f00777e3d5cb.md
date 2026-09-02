# Command Line Interface

A comprehensive command-line interface for running hazard simulations on distribution systems using the ERAD framework.

## Installation

Install ERAD with all dependencies:

```bash
pip install -e ".[dev]"
```

The CLI is automatically available as the `erad` command after installation.

## Quick Start

```bash
# Show version
erad version

# Show environment info
erad info

# List cached models
erad models list

# List supported hazards
erad hazards list

# Start the API server
erad server start
```

## Commands Overview

| Command | Description |
|---------|-------------|
| `erad version` | Show the ERAD version |
| `erad info` | Show environment information |
| `erad simulate` | Run a hazard simulation |
| `erad generate` | Generate Monte Carlo scenarios |
| `erad models` | Manage distribution system models |
| `erad hazards` | Hazard-related commands |
| `erad cache` | Cache management commands |
| `erad server` | Server management commands |

## Simulation Commands

### Run Simulation

Run a hazard simulation using cached distribution and hazard system models:

```bash
erad simulate <distribution_model> <hazard_model> [OPTIONS]
```

**Arguments:**
- `distribution_model`: Name of the cached distribution system model
- `hazard_model`: Name of the cached hazard system model

**Options:**
- `--curves, -c`: Fragility curve set to use (default: DEFAULT_CURVES)
- `--output, -o`: Output SQLite file path for results
- `--verbose, -v`: Verbose output

**Example:**
```bash
erad simulate my_system earthquake_scenario --output results.sqlite
erad simulate power_grid flood_hazard --curves DEFAULT_CURVES
```

### Generate Scenarios

Generate Monte Carlo scenarios using cached distribution and hazard system models:

```bash
erad generate <distribution_model> <hazard_model> [OPTIONS]
```

**Arguments:**
- `distribution_model`: Name of the cached distribution system model
- `hazard_model`: Name of the cached hazard system model

**Options:**
- `--samples, -n`: Number of scenarios to generate (default: 10)
- `--seed, -s`: Random seed for reproducibility
- `--curves, -c`: Fragility curve set to use (default: DEFAULT_CURVES)
- `--output, -o`: Output ZIP file path for scenarios (contains tracked_changes.json and time_series/)
- `--verbose, -v`: Verbose output

**Example:**
```bash
erad generate my_system flood_scenario --samples 100 --seed 42 --output scenarios.zip
erad generate power_grid earthquake_hazard --samples 50 --output eq_scenarios.zip
```

## Model Management

### List Models

List all cached distribution system models:

```bash
erad models list [OPTIONS]
```

**Options:**
- `--refresh, -r`: Refresh from cache directory before listing
- `--json, -j`: Output as JSON

**Example:**
```bash
# List models as table
erad models list

# List with JSON output
erad models list --json

# Refresh and list
erad models list --refresh
```

### Add Model

Add a distribution system model to the cache:

```bash
erad models add <file> [OPTIONS]
```

**Options:**
- `--name, -n`: Name for the model (default: filename)
- `--description, -d`: Description of the model
- `--force, -f`: Overwrite if model already exists

**Example:**
```bash
erad models add system.json --name my_system --description "Test distribution system"
```

### Show Model

Show details of a cached model:

```bash
erad models show <name> [OPTIONS]
```

**Options:**
- `--full, -f`: Show full model content (truncated to 5000 chars)

**Example:**
```bash
erad models show my_system --full
```

### Remove Model

Remove a model from the cache:

```bash
erad models remove <name> [OPTIONS]
```

**Options:**
- `--keep-file`: Keep the JSON file in cache (only remove from metadata)

**Example:**
```bash
erad models remove my_system
```

### Export Model

Export a cached model to a file:

```bash
erad models export <name> <output_path>
```

**Example:**
```bash
erad models export my_system ./exported_system.json
```

## Hazard Commands

Manage cached hazard system models.

### List Hazard Models

List all cached hazard system models:

```bash
erad hazards list [OPTIONS]
```

**Options:**
- `--refresh, -r`: Refresh from cache directory before listing
- `--json, -j`: Output as JSON

**Example:**
```bash
# List hazard models
erad hazards list

# Refresh and list
erad hazards list --refresh

# JSON output
erad hazards list --json
```

### Add Hazard Model

Add a hazard system model to the cache:

```bash
erad hazards add <file> [OPTIONS]
```

**Options:**
- `--name, -n`: Name for the model (default: filename)
- `--description, -d`: Description of the model
- `--force, -f`: Overwrite if model already exists

**Example:**
```bash
erad hazards add earthquake.json --name eq_scenario --description "Major earthquake scenario"
```

### Show Hazard Model

Show details of a cached hazard model:

```bash
erad hazards show <name> [OPTIONS]
```

**Options:**
- `--full, -f`: Show full model content (truncated to 5000 chars)

**Example:**
```bash
erad hazards show eq_scenario --full
```

### Remove Hazard Model

Remove a hazard model from the cache:

```bash
erad hazards remove <name> [OPTIONS]
```

**Options:**
- `--keep-file`: Keep the JSON file in cache (only remove from metadata)

**Example:**
```bash
erad hazards remove eq_scenario
```

### Export Hazard Model

Export a cached hazard model to a file:

```bash
erad hazards export <name> <output_path>
```

**Example:**
```bash
erad hazards export eq_scenario ./exported_hazard.json
```

### List Hazard Types

List supported hazard types for creating models:

```bash
erad hazards types
```

Output shows available hazard types: earthquake, flood, flood_area, wind, fire, fire_area.

### Show Hazard Example

Show an example hazard system configuration:

```bash
erad hazards example <hazard_type> [OPTIONS]
```

**Options:**
- `--output, -o`: Save example to file

**Example:**
```bash
# Show earthquake example
erad hazards example earthquake

# Save flood example to file
erad hazards example flood --output flood_example.json
```

## Cache Management

### Cache Info

Show cache directory information:

```bash
erad cache info
```

Output:
```
                     Cache Information                      
┌─────────────────┬────────────────────────────────────────┐
│ Cache Directory │ /home/user/.cache/erad/dist_models    │
│ Metadata File   │ /home/user/.cache/.../models_meta.json │
│ Total Models    │ 5                                      │
│ Total Files     │ 5                                      │
│ Total Size      │ 2.50 MB                                │
└─────────────────┴────────────────────────────────────────┘
```

### Refresh Cache

Refresh the model list from the cache directory:

```bash
erad cache refresh
```

### Clear Cache

Clear all cached models:

```bash
erad cache clear [OPTIONS]
```

**Options:**
- `--force, -f`: Skip confirmation prompt

**Example:**
```bash
# With confirmation
erad cache clear

# Skip confirmation
erad cache clear --force
```

## Server Commands

### Start REST API Server

Start the ERAD REST API server:

```bash
erad server start [OPTIONS]
```

**Options:**
- `--host, -h`: Host to bind to (default: 0.0.0.0)
- `--port, -p`: Port to bind to (default: 8000)
- `--reload, -r`: Enable auto-reload for development
- `--workers, -w`: Number of workers (default: 1)

**Example:**
```bash
# Start with defaults
erad server start

# Start on custom port with reload
erad server start --port 8080 --reload

# Production with multiple workers
erad server start --workers 4
```

### Start MCP Server

Start the ERAD MCP server for AI assistant integration:

```bash
erad server mcp
```

## Cache Directories

The CLI uses the same cache directories as the REST API and MCP server:

**Distribution Models:**
- **Linux/macOS:** `~/.cache/erad/distribution_models/`
- **Windows:** `%LOCALAPPDATA%\erad\distribution_models\`

**Hazard Models:**
- **Linux/macOS:** `~/.cache/erad/hazard_models/`
- **Windows:** `%LOCALAPPDATA%\erad\hazard_models\`

## Shell Completion

Install shell completion for your shell:

```bash
# For bash
erad --install-completion bash

# For zsh
erad --install-completion zsh

# For fish
erad --install-completion fish
```

## Examples

### Complete Workflow

```bash
# 1. Check ERAD info
erad info

# 2. Add a distribution system model
erad models add distribution_system.json --name power_grid --description "City power grid"

# 3. Add a hazard system model
erad hazards add earthquake_scenario.json --name eq_major --description "Major earthquake"

# 4. List available models
erad models list
erad hazards list

# 5. View model details
erad models show power_grid
erad hazards show eq_major

# 6. Run earthquake simulation
erad simulate power_grid eq_major --output eq_results.sqlite

# 7. Add flood hazard model and generate scenarios
erad hazards add flood_scenario.json --name flood_100yr --description "100-year flood"
erad generate power_grid flood_100yr --samples 50 --seed 42 --output flood_scenarios.zip

# 8. Start API server for programmatic access
erad server start --port 8000
```

### Batch Processing Script

```bash
#!/bin/bash

# Process multiple hazard scenarios
DIST_MODELS=$(erad models list --json | jq -r 'keys[]')
HAZARD_MODELS=$(erad hazards list --json | jq -r 'keys[]')

for dist_model in $DIST_MODELS; do
    for hazard_model in $HAZARD_MODELS; do
        echo "Processing $dist_model with $hazard_model..."
        
        erad generate "$dist_model" "$hazard_model" \
            --samples 100 \
            --seed 42 \
            --output "results/${dist_model}_${hazard_model}.zip"
    done
done
```

## See Also

- [MCP Server Documentation](mcp_server.md) - Model Context Protocol server for AI assistants
- [Data Models](data_models.md)
