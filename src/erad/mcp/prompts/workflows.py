"""Pre-built prompt templates for common ERAD workflows."""

from __future__ import annotations

from mcp.server import MCPServer


def register(mcp: MCPServer) -> None:
    """Register workflow prompt templates."""

    @mcp.prompt()
    def run_resilience_study(
        system_path: str = "",
        hazard_description: str = "a hurricane landfall",
    ) -> str:
        """End-to-end prompt: run a full resilience study on a distribution system.

        Guides the LLM through the pipeline: load the asset system, load or create
        a hazard system, run the simulation, generate failure scenarios, and export
        results.
        """
        system_clause = (
            f'Load the distribution system using `load_distribution_model` with source="{system_path}".'
            if system_path
            else "Load a distribution system using `load_distribution_model` (ask the user for a file path or cached model name)."
        )
        return f"""Run a complete energy resilience study for a distribution system.

{system_clause}

Scenario: {hazard_description}

Follow these steps in order:

1. **Load the asset system**: Use `load_distribution_model` and note the returned
   `system_id`.
2. **Load or create a hazard system**: Use `load_historic_hurricane`,
   `load_historic_earthquake`, `load_historic_wildfire`, or `create_hazard_system`
   to build the hazard system for {hazard_description}.
3. **Run the simulation**: Use `run_simulation` with the asset and hazard system
   IDs. Report the asset count and number of timesteps.
4. **Generate scenarios**: Use `generate_scenarios` with `num_samples` of your
   choice to produce Monte Carlo failure scenarios.
5. **Analyze failures**: Use `get_failed_assets` to list assets whose survival
   probability drops below the threshold.
6. **Export results**: Use `export_csv` or `export_parquet` to save the results,
   and `export_tracked_changes` to save the scenario changes.

After each step, report what was created and any relevant statistics.
"""

    @mcp.prompt()
    def explore_historic_hazard(hazard_type: str = "hurricane", year: int | None = None) -> str:
        """Prompt template for exploring the historic hazard database."""
        year_clause = f" from year {year}" if year else ""
        return f"""Explore historic {hazard_type} events{year_clause} and set up a hazard system.

1. List available events: use `list_historic_hurricanes`, `list_historic_earthquakes`,
   or `list_historic_wildfires` as appropriate for {hazard_type}.
2. Create an empty hazard system with `create_hazard_system`.
3. Load 1-3 notable events into the hazard system using the matching
   `load_historic_*` tool.
4. Summarise each loaded event (timestamps, intensity, and any other metadata).

If the user then wants a full study, proceed with `run_resilience_study`.
"""

    @mcp.prompt()
    def analyze_asset_system(system_id: str = "") -> str:
        """Prompt template for analyzing a loaded asset system."""
        system_clause = (
            f'Use asset_system_id="{system_id}".'
            if system_id
            else "First call `list_loaded_systems` to pick an asset system."
        )
        return f"""Analyze the loaded asset system and provide a detailed summary.

{system_clause}

1. Get asset statistics with `get_asset_statistics`.
2. Query assets with `query_assets` to list them (optionally filtered by type
   or location).
3. Retrieve the network topology with `get_network_topology`.
4. Summarise the asset mix, any spatial patterns, and the network structure.

If the user wants to assess resilience, proceed with `run_resilience_study`.
"""
