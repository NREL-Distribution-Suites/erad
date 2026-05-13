"""
ERAD Command Line Interface

A comprehensive CLI for running hazard simulations on distribution systems.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from erad.mcp.helpers import (
    get_cache_directory as _get_cache_directory,
    get_hazard_cache_directory as _get_hazard_cache_directory,
)

# Initialize Typer app
app = typer.Typer(
    name="erad",
    help="ERAD - Energy Resilience Analysis for Distribution Systems",
    add_completion=True,
    rich_markup_mode="rich",
)

# Sub-commands
models_app = typer.Typer(help="Manage distribution system models")
hazards_app = typer.Typer(help="Hazard-related commands")
cache_app = typer.Typer(help="Cache management commands")
server_app = typer.Typer(help="Server management commands")

app.add_typer(models_app, name="models")
app.add_typer(hazards_app, name="hazards")
app.add_typer(cache_app, name="cache")
app.add_typer(server_app, name="server")

console = Console()


# ========== Cache Directory Functions ==========


def get_cache_directory() -> Path:
    """Get the platform-specific cache directory for distribution models."""
    return _get_cache_directory()


def get_hazard_cache_directory() -> Path:
    """Get the platform-specific cache directory for hazard models."""
    return _get_hazard_cache_directory()


def _load_cached_systems(
    model: str,
    hazard_model: str,
    update_status: Optional[Callable[[str], None]] = None,
):
    """Load cached distribution/hazard systems and construct runtime ERAD systems."""
    from gdm.distribution import DistributionSystem
    from erad.systems import AssetSystem, HazardSystem

    dist_models = load_cached_models()
    hazard_models = load_cached_hazard_models()

    if model not in dist_models:
        console.print(f"[red]Error:[/red] Distribution model '{model}' not found in cache.")
        console.print(f"Available models: {list(dist_models.keys())}")
        raise typer.Exit(code=1)

    if hazard_model not in hazard_models:
        console.print(f"[red]Error:[/red] Hazard model '{hazard_model}' not found in cache.")
        console.print(f"Available hazard models: {list(hazard_models.keys())}")
        raise typer.Exit(code=1)

    if update_status:
        update_status("Loading distribution system...")

    dist_file = dist_models[model]["file_path"]
    try:
        with open(dist_file, "r") as f:
            data = json.load(f)
        dist_system = DistributionSystem(**data)
    except Exception as e:
        console.print(f"[red]Error loading distribution model:[/red] {e}")
        raise typer.Exit(code=1)

    if update_status:
        update_status("Creating asset system...")
    asset_system = AssetSystem.from_gdm(dist_system)

    if update_status:
        update_status("Loading hazard system...")
    hazard_file = hazard_models[hazard_model]["file_path"]
    try:
        with open(hazard_file, "r") as f:
            hazard_data = json.load(f)
        hazard_system = HazardSystem.from_json(hazard_data)
    except Exception as e:
        console.print(f"[red]Error loading hazard model:[/red] {e}")
        raise typer.Exit(code=1)

    return asset_system, hazard_system


def get_metadata_file() -> Path:
    """Get the path to the distribution models metadata file."""
    return get_cache_directory() / "models_metadata.json"


def get_hazard_metadata_file() -> Path:
    """Get the path to the hazard models metadata file."""
    return get_hazard_cache_directory() / "models_metadata.json"


def load_metadata() -> dict:
    """Load metadata from the cache directory."""
    metadata_file = get_metadata_file()
    if metadata_file.exists():
        with open(metadata_file, "r") as f:
            return json.load(f)
    return {}


def load_hazard_metadata() -> dict:
    """Load hazard model metadata from the cache directory."""
    metadata_file = get_hazard_metadata_file()
    if metadata_file.exists():
        with open(metadata_file, "r") as f:
            return json.load(f)
    return {}


def save_metadata(metadata: dict) -> None:
    """Save metadata to the cache directory."""
    metadata_file = get_metadata_file()
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2, default=str)


def save_hazard_metadata(metadata: dict) -> None:
    """Save hazard model metadata to the cache directory."""
    metadata_file = get_hazard_metadata_file()
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2, default=str)


def load_cached_models() -> dict:
    """Load all cached distribution models from the metadata file."""
    return load_metadata()


def load_cached_hazard_models() -> dict:
    """Load all cached hazard models from the metadata file."""
    return load_hazard_metadata()


# ========== Main Commands ==========


@app.command()
def version():
    """Show the ERAD version."""
    try:
        from erad import __version__

        version_str = __version__
    except ImportError:
        version_str = "0.1.7"

    console.print(Panel(f"[bold blue]ERAD[/bold blue] version [green]{version_str}[/green]"))


@app.command()
def info():
    """Show information about ERAD and the current environment."""
    try:
        from erad import __version__

        version_str = __version__
    except ImportError:
        version_str = "0.1.7"

    cache_dir = get_cache_directory()
    models = load_cached_models()

    table = Table(title="ERAD Environment Info", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Version", version_str)
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Platform", sys.platform)
    table.add_row("Cache Directory", str(cache_dir))
    table.add_row("Cached Models", str(len(models)))

    console.print(table)


@app.command()
def simulate(
    model: str = typer.Argument(..., help="Name of the cached distribution system model"),
    hazard_model: str = typer.Argument(..., help="Name of the cached hazard system model"),
    curve_set: str = typer.Option(
        "DEFAULT_CURVES", "--curves", "-c", help="Fragility curve set to use"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output SQLite file path for results"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """
    Run a hazard simulation using cached distribution and hazard system models.

    Example:
        erad simulate my_system earthquake_scenario
        erad simulate my_system flood_hazard --output results.sqlite
    """
    from erad.runner import HazardSimulator
    from erad.models.asset import Asset

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading cached systems...", total=None)

        asset_system, hazard_system = _load_cached_systems(
            model,
            hazard_model,
            update_status=lambda description: progress.update(task, description=description),
        )

        progress.update(task, description="Running simulation...")

        # Run simulation
        try:
            simulator = HazardSimulator(asset_system)
            simulator.run(hazard_system, curve_set)

            progress.update(task, description="Simulation complete!")
        except Exception as e:
            console.print(f"[red]Error running simulation:[/red] {e}")
            raise typer.Exit(code=1)

    # Get simulation stats
    assets = list(asset_system.get_components(Asset))
    timestamps = simulator.timestamps

    # Display results
    console.print("\n[bold green]✓ Simulation completed successfully![/bold green]\n")

    table = Table(title="Simulation Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Distribution Model", model)
    table.add_row("Hazard Model", hazard_model)
    table.add_row("Assets", str(len(assets)))
    table.add_row("Timestamps", str(len(timestamps)))
    table.add_row("Curve Set", curve_set)

    console.print(table)

    if output:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        with progress:
            task = progress.add_task("Exporting results to SQLite...", total=None)
            try:
                asset_system.export_results(str(output))
                console.print(f"\n[green]✓[/green] Results exported to: [blue]{output}[/blue]")
            except Exception as e:
                console.print(f"\n[red]Error exporting results:[/red] {e}")


@app.command()
def generate(  # noqa: C901
    model: str = typer.Argument(..., help="Name of the cached distribution system model"),
    hazard_model: str = typer.Argument(..., help="Name of the cached hazard system model"),
    samples: int = typer.Option(10, "--samples", "-n", help="Number of scenarios to generate"),
    seed: Optional[int] = typer.Option(
        None, "--seed", "-s", help="Random seed for reproducibility"
    ),
    curve_set: str = typer.Option(
        "DEFAULT_CURVES", "--curves", "-c", help="Fragility curve set to use"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output ZIP file path for scenarios"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """
    Generate Monte Carlo scenarios using cached distribution and hazard system models.

    Example:
        erad generate my_system flood_scenario --samples 100 --seed 42
        erad generate my_system earthquake_hazard --output scenarios.zip
    """
    import tempfile
    import zipfile
    from erad.runner import HazardScenarioGenerator

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading cached systems...", total=None)

        asset_system, hazard_system = _load_cached_systems(
            model,
            hazard_model,
            update_status=lambda description: progress.update(task, description=description),
        )

        progress.update(task, description=f"Generating {samples} scenarios...")

        try:
            generator = HazardScenarioGenerator(
                asset_system=asset_system, hazard_system=hazard_system, curve_set=curve_set
            )
            tracked_changes = generator.samples(
                number_of_samples=samples, seed=seed if seed is not None else 0
            )
        except Exception as e:
            console.print(f"[red]Error generating scenarios:[/red] {e}")
            raise typer.Exit(code=1)

    console.print(f"\n[bold green]✓ Generated {len(tracked_changes)} scenarios![/bold green]\n")

    table = Table(title="Scenario Generation Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Distribution Model", model)
    table.add_row("Hazard Model", hazard_model)
    table.add_row("Samples", str(samples))
    table.add_row("Seed", str(seed) if seed else "Random")
    table.add_row("Scenarios Generated", str(len(tracked_changes)))

    console.print(table)

    if output:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating ZIP file...", total=None)

            try:
                # Create temporary directory for scenario files
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    # Create tracked changes JSON
                    tracked_changes_data = []
                    for change in tracked_changes:
                        tracked_changes_data.append(
                            {
                                "scenario_name": change.scenario_name,
                                "timestamp": change.timestamp.isoformat(),
                                "edits": [
                                    {
                                        "component_uuid": edit.component_uuid,
                                        "name": edit.name,
                                        "value": edit.value,
                                    }
                                    for edit in change.edits
                                ],
                            }
                        )

                    tracked_changes_file = temp_path / "tracked_changes.json"
                    with open(tracked_changes_file, "w") as f:
                        json.dump(tracked_changes_data, f, indent=2)

                    # Create ZIP file
                    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(tracked_changes_file, "tracked_changes.json")

                        # Add time series folder if it exists
                        time_series_dir = temp_path / "time_series"
                        if time_series_dir.exists():
                            for file_path in time_series_dir.rglob("*"):
                                if file_path.is_file():
                                    arcname = (
                                        f"time_series/{file_path.relative_to(time_series_dir)}"
                                    )
                                    zipf.write(file_path, arcname)

                console.print(f"\n[green]✓[/green] Scenarios saved to: [blue]{output}[/blue]")
            except Exception as e:
                console.print(f"\n[red]Error creating ZIP file:[/red] {e}")


# ========== Models Sub-commands ==========


@models_app.command("list")
def list_models(
    refresh: bool = typer.Option(False, "--refresh", "-r", help="Refresh from cache directory"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List all cached distribution system models."""
    if refresh:
        # Scan cache directory for new files
        cache_dir = get_cache_directory()
        metadata = load_metadata()

        for file_path in cache_dir.glob("*.json"):
            if file_path.name == "models_metadata.json":
                logger.info("Skipping metadata file")
                continue

            # Check if already in metadata
            model_name = (
                file_path.stem.rsplit("_", 1)[0] if "_" in file_path.stem else file_path.stem
            )
            if model_name not in metadata:
                metadata[model_name] = {
                    "description": "Imported from cache directory",
                    "created_at": datetime.now().isoformat(),
                    "file_path": str(file_path),
                }

        save_metadata(metadata)

    models = load_cached_models()

    if json_output:
        console.print_json(json.dumps(models, indent=2, default=str))
        return

    if not models:
        console.print("[yellow]No models found in cache.[/yellow]")
        console.print(f"Cache directory: {get_cache_directory()}")
        return

    table = Table(title="Cached Distribution Models")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Created", style="green")

    for name, info in models.items():
        table.add_row(
            name, info.get("description", "N/A")[:50], info.get("created_at", "N/A")[:19]
        )

    console.print(table)
    console.print(f"\nTotal: [bold]{len(models)}[/bold] models")


@models_app.command("add")
def add_model(
    file: Path = typer.Argument(..., help="Path to the distribution system JSON file"),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Name for the model (default: filename)"
    ),
    description: str = typer.Option("", "--description", "-d", help="Description of the model"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if model already exists"),
):
    """Add a distribution system model to the cache."""
    import shutil

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(code=1)

    if not file.suffix == ".json":
        console.print("[red]Error:[/red] File must be a JSON file")
        raise typer.Exit(code=1)

    model_name = name or file.stem
    models = load_cached_models()

    if model_name in models and not force:
        console.print(
            f"[red]Error:[/red] Model '{model_name}' already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    # Validate JSON
    try:
        with open(file, "r") as f:
            json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON file: {e}")
        raise typer.Exit(code=1)

    # Copy to cache directory
    cache_dir = get_cache_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_file = cache_dir / f"{model_name}_{timestamp}.json"

    shutil.copy2(file, dest_file)

    # Update metadata
    models[model_name] = {
        "description": description,
        "created_at": datetime.now().isoformat(),
        "file_path": str(dest_file),
    }
    save_metadata(models)

    console.print(f"[green]✓[/green] Model '{model_name}' added to cache.")
    console.print(f"  File: {dest_file}")


@models_app.command("remove")
def remove_model(
    name: str = typer.Argument(..., help="Name of the model to remove"),
    keep_file: bool = typer.Option(False, "--keep-file", help="Keep the JSON file in cache"),
):
    """Remove a distribution system model from the cache."""
    models = load_cached_models()

    if name not in models:
        console.print(f"[red]Error:[/red] Model '{name}' not found.")
        raise typer.Exit(code=1)

    file_path = models[name].get("file_path")

    # Remove from metadata
    del models[name]
    save_metadata(models)

    # Optionally delete file
    if not keep_file and file_path:
        try:
            Path(file_path).unlink(missing_ok=True)
            console.print(f"[green]✓[/green] Model '{name}' and file removed.")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not delete file: {e}")
            console.print(f"[green]✓[/green] Model '{name}' removed from metadata.")
    else:
        console.print(f"[green]✓[/green] Model '{name}' removed from metadata (file kept).")


@models_app.command("show")
def show_model(
    name: str = typer.Argument(..., help="Name of the model to show"),
    full: bool = typer.Option(False, "--full", "-f", help="Show full model content"),
):
    """Show details of a cached distribution system model."""
    models = load_cached_models()

    if name not in models:
        console.print(f"[red]Error:[/red] Model '{name}' not found.")
        raise typer.Exit(code=1)

    info = models[name]

    table = Table(title=f"Model: {name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Name", name)
    table.add_row("Description", info.get("description", "N/A"))
    table.add_row("Created", info.get("created_at", "N/A"))
    table.add_row("File Path", info.get("file_path", "N/A"))

    # Get file size
    file_path = info.get("file_path")
    if file_path and Path(file_path).exists():
        size = Path(file_path).stat().st_size
        table.add_row("File Size", f"{size / 1024:.2f} KB")

    console.print(table)

    if full and file_path:
        console.print("\n[bold]Model Content:[/bold]")
        with open(file_path, "r") as f:
            data = json.load(f)
        console.print_json(json.dumps(data, indent=2, default=str)[:5000])
        if len(json.dumps(data)) > 5000:
            console.print("\n[dim]... (truncated)[/dim]")


@models_app.command("export")
def export_model(
    name: str = typer.Argument(..., help="Name of the model to export"),
    output: Path = typer.Argument(..., help="Output file path"),
):
    """Export a cached model to a file."""
    models = load_cached_models()

    if name not in models:
        console.print(f"[red]Error:[/red] Model '{name}' not found.")
        raise typer.Exit(code=1)

    import shutil

    file_path = models[name].get("file_path")
    if not file_path or not Path(file_path).exists():
        console.print("[red]Error:[/red] Model file not found.")
        raise typer.Exit(code=1)

    shutil.copy2(file_path, output)
    console.print(f"[green]✓[/green] Model exported to: {output}")


# ========== Hazards Sub-commands ==========


@hazards_app.command("list")
def list_hazard_models(
    refresh: bool = typer.Option(False, "--refresh", "-r", help="Refresh from cache directory"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List all cached hazard system models."""
    if refresh:
        # Scan cache directory for new files
        cache_dir = get_hazard_cache_directory()
        metadata = load_hazard_metadata()

        for file_path in cache_dir.glob("*.json"):
            if file_path.name == "models_metadata.json":
                logger.info("Skipping metadata file")
                continue

            # Check if already in metadata
            model_name = (
                file_path.stem.rsplit("_", 1)[0] if "_" in file_path.stem else file_path.stem
            )
            if model_name not in metadata:
                metadata[model_name] = {
                    "description": "Imported from cache directory",
                    "created_at": datetime.now().isoformat(),
                    "file_path": str(file_path),
                }

        save_hazard_metadata(metadata)

    models = load_cached_hazard_models()

    if json_output:
        console.print_json(json.dumps(models, indent=2, default=str))
        return

    if not models:
        console.print("[yellow]No hazard models found in cache.[/yellow]")
        console.print(f"Cache directory: {get_hazard_cache_directory()}")
        return

    table = Table(title="Cached Hazard Models")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Created", style="green")

    for name, info in models.items():
        table.add_row(
            name, info.get("description", "N/A")[:50], info.get("created_at", "N/A")[:19]
        )

    console.print(table)
    console.print(f"\nTotal: [bold]{len(models)}[/bold] hazard models")


@hazards_app.command("add")
def add_hazard_model(
    file: Path = typer.Argument(..., help="Path to the hazard system JSON file"),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Name for the model (default: filename)"
    ),
    description: str = typer.Option("", "--description", "-d", help="Description of the model"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if model already exists"),
):
    """Add a hazard system model to the cache."""
    import shutil

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(code=1)

    if not file.suffix == ".json":
        console.print("[red]Error:[/red] File must be a JSON file")
        raise typer.Exit(code=1)

    model_name = name or file.stem
    models = load_cached_hazard_models()

    if model_name in models and not force:
        console.print(
            f"[red]Error:[/red] Hazard model '{model_name}' already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    # Validate JSON
    try:
        with open(file, "r") as f:
            json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON file: {e}")
        raise typer.Exit(code=1)

    # Copy to cache directory
    cache_dir = get_hazard_cache_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_file = cache_dir / f"{model_name}_{timestamp}.json"

    shutil.copy2(file, dest_file)

    # Update metadata
    models[model_name] = {
        "description": description,
        "created_at": datetime.now().isoformat(),
        "file_path": str(dest_file),
    }
    save_hazard_metadata(models)

    console.print(f"[green]✓[/green] Hazard model '{model_name}' added to cache.")
    console.print(f"  File: {dest_file}")


@hazards_app.command("remove")
def remove_hazard_model(
    name: str = typer.Argument(..., help="Name of the hazard model to remove"),
    keep_file: bool = typer.Option(False, "--keep-file", help="Keep the JSON file in cache"),
):
    """Remove a hazard system model from the cache."""
    models = load_cached_hazard_models()

    if name not in models:
        console.print(f"[red]Error:[/red] Hazard model '{name}' not found.")
        raise typer.Exit(code=1)

    file_path = models[name].get("file_path")

    # Remove from metadata
    del models[name]
    save_hazard_metadata(models)

    # Optionally delete file
    if not keep_file and file_path:
        try:
            Path(file_path).unlink(missing_ok=True)
            console.print(f"[green]✓[/green] Hazard model '{name}' and file removed.")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not delete file: {e}")
            console.print(f"[green]✓[/green] Hazard model '{name}' removed from metadata.")
    else:
        console.print(f"[green]✓[/green] Hazard model '{name}' removed from metadata (file kept).")


@hazards_app.command("show")
def show_hazard_model(
    name: str = typer.Argument(..., help="Name of the hazard model to show"),
    full: bool = typer.Option(False, "--full", "-f", help="Show full model content"),
):
    """Show details of a cached hazard system model."""
    models = load_cached_hazard_models()

    if name not in models:
        console.print(f"[red]Error:[/red] Hazard model '{name}' not found.")
        raise typer.Exit(code=1)

    info = models[name]

    table = Table(title=f"Hazard Model: {name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Name", name)
    table.add_row("Description", info.get("description", "N/A"))
    table.add_row("Created", info.get("created_at", "N/A"))
    table.add_row("File Path", info.get("file_path", "N/A"))

    # Get file size
    file_path = info.get("file_path")
    if file_path and Path(file_path).exists():
        size = Path(file_path).stat().st_size
        table.add_row("File Size", f"{size / 1024:.2f} KB")

    console.print(table)

    if full and file_path:
        console.print("\n[bold]Hazard Model Content:[/bold]")
        with open(file_path, "r") as f:
            data = json.load(f)
        console.print_json(json.dumps(data, indent=2, default=str)[:5000])
        if len(json.dumps(data)) > 5000:
            console.print("\n[dim]... (truncated)[/dim]")


@hazards_app.command("export")
def export_hazard_model(
    name: str = typer.Argument(..., help="Name of the hazard model to export"),
    output: Path = typer.Argument(..., help="Output file path"),
):
    """Export a cached hazard model to a file."""
    models = load_cached_hazard_models()

    if name not in models:
        console.print(f"[red]Error:[/red] Hazard model '{name}' not found.")
        raise typer.Exit(code=1)

    import shutil

    file_path = models[name].get("file_path")
    if not file_path or not Path(file_path).exists():
        console.print("[red]Error:[/red] Hazard model file not found.")
        raise typer.Exit(code=1)

    shutil.copy2(file_path, output)
    console.print(f"[green]✓[/green] Hazard model exported to: {output}")


@hazards_app.command("types")
def list_hazard_types():
    """List supported hazard types for creating models."""
    hazards = [
        ("earthquake", "Earthquake Model", "EarthQuakeModel"),
        ("flood", "Flood Model", "FloodModel"),
        ("flood_area", "Flood Area Model", "FloodModelArea"),
        ("wind", "Wind Model", "WindModel"),
        ("fire", "Fire Model", "FireModel"),
        ("fire_area", "Fire Area Model", "FireModelArea"),
    ]

    table = Table(title="Supported Hazard Types")
    table.add_column("Type", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Model Class", style="green")

    for hazard_type, description, model_class in hazards:
        table.add_row(hazard_type, description, model_class)

    console.print(table)


@hazards_app.command("example")
def hazard_example(
    hazard_type: str = typer.Argument("earthquake", help="Type of hazard to show example for"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save example to file"),
):
    """Show an example hazard system configuration."""
    examples = {
        "earthquake": {
            "models": [
                {
                    "name": "earthquake_1",
                    "hazard_type": "earthquake",
                    "timestamp": "2024-01-01T00:00:00",
                    "model_data": {"data": {"asset_1": 0.5, "asset_2": 0.3}},
                }
            ],
            "timestamps": ["2024-01-01T00:00:00"],
        },
        "flood": {
            "models": [
                {
                    "name": "flood_1",
                    "hazard_type": "flood",
                    "timestamp": "2024-01-01T00:00:00",
                    "model_data": {"data": {"asset_1": 0.6, "asset_2": 0.4}},
                }
            ],
            "timestamps": ["2024-01-01T00:00:00"],
        },
        "wind": {
            "models": [
                {
                    "name": "wind_1",
                    "hazard_type": "wind",
                    "timestamp": "2024-01-01T00:00:00",
                    "model_data": {"data": {"asset_1": 0.7, "asset_2": 0.2}},
                }
            ],
            "timestamps": ["2024-01-01T00:00:00"],
        },
        "fire": {
            "models": [
                {
                    "name": "fire_1",
                    "hazard_type": "fire",
                    "timestamp": "2024-01-01T00:00:00",
                    "model_data": {"data": {"asset_1": 0.8, "asset_2": 0.5}},
                }
            ],
            "timestamps": ["2024-01-01T00:00:00"],
        },
    }

    hazard_type_lower = hazard_type.lower()
    if hazard_type_lower not in examples:
        console.print(f"[red]Error:[/red] Unknown hazard type: {hazard_type}")
        console.print(f"Available types: {list(examples.keys())}")
        raise typer.Exit(code=1)

    example = examples[hazard_type_lower]

    if output:
        with open(output, "w") as f:
            json.dump(example, f, indent=2)
        console.print(f"[green]✓[/green] Example saved to: {output}")
    else:
        console.print(f"\n[bold]Example {hazard_type} hazard system configuration:[/bold]\n")
        console.print_json(json.dumps(example, indent=2))


# ========== Cache Sub-commands ==========


@cache_app.command("info")
def cache_info():
    """Show cache directory information."""
    cache_dir = get_cache_directory()
    metadata_file = get_metadata_file()
    models = load_cached_models()

    # Calculate total size
    total_size = 0
    file_count = 0
    for file_path in cache_dir.glob("*.json"):
        total_size += file_path.stat().st_size
        file_count += 1

    table = Table(title="Cache Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Cache Directory", str(cache_dir))
    table.add_row("Metadata File", str(metadata_file))
    table.add_row("Total Models", str(len(models)))
    table.add_row("Total Files", str(file_count))
    table.add_row("Total Size", f"{total_size / 1024 / 1024:.2f} MB")

    console.print(table)


@cache_app.command("clear")
def cache_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear all cached models."""
    if not force:
        confirm = typer.confirm("Are you sure you want to clear all cached models?")
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit()

    cache_dir = get_cache_directory()

    # Delete all JSON files
    count = 0
    for file_path in cache_dir.glob("*.json"):
        file_path.unlink()
        count += 1

    console.print(f"[green]✓[/green] Cleared {count} files from cache.")


@cache_app.command("refresh")
def cache_refresh():
    """Refresh the model list from the cache directory."""
    cache_dir = get_cache_directory()
    metadata = load_metadata()

    new_count = 0
    for file_path in cache_dir.glob("*.json"):
        if file_path.name == "models_metadata.json":
            logger.info("Skipping metadata file")
            continue

        model_name = file_path.stem.rsplit("_", 1)[0] if "_" in file_path.stem else file_path.stem
        if model_name not in metadata:
            metadata[model_name] = {
                "description": "Imported from cache directory",
                "created_at": datetime.now().isoformat(),
                "file_path": str(file_path),
            }
            new_count += 1

    save_metadata(metadata)

    console.print(f"[green]✓[/green] Cache refreshed. Found {new_count} new models.")
    console.print(f"Total models: {len(metadata)}")


# ========== Server Sub-commands ==========


@server_app.command("mcp")
def server_mcp():
    """Start the ERAD MCP server for Model Context Protocol integration."""
    console.print("[bold blue]Starting ERAD MCP server...[/bold blue]")
    console.print("  Protocol: Model Context Protocol (MCP)")
    console.print("  Transport: stdio")
    console.print()
    console.print("[dim]Use with Claude Desktop, VS Code Copilot, or other MCP clients[/dim]")
    console.print()

    from erad.mcp import main as mcp_main

    mcp_main()


# ========== Main Entry Point ==========


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
