"""Tests for the ERAD CLI."""

import json
import re

import pytest
from typer.testing import CliRunner

from erad.cli import app


runner = CliRunner(env={"NO_COLOR": "1"})


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


# ========== Fixtures ==========


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "erad" / "distribution_models"
    cache_dir.mkdir(parents=True)
    return cache_dir


@pytest.fixture
def sample_model_file(tmp_path):
    """Create a sample distribution system JSON file."""
    data = {
        "name": "test_system",
        "uuid": "test-uuid-123",
        "components": [],
        "auto_add_composed_components": True,
    }
    file_path = tmp_path / "test_system.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


@pytest.fixture
def mock_cache_dir(temp_cache_dir, monkeypatch):
    """Mock the cache directory to use temp directory."""

    def mock_get_cache_dir():
        return temp_cache_dir

    monkeypatch.setattr("erad.cli.get_cache_directory", mock_get_cache_dir)
    monkeypatch.setattr("erad.cli.get_hazard_cache_directory", mock_get_cache_dir)
    return temp_cache_dir


# ========== Basic Command Tests ==========


class TestBasicCommands:
    """Test basic CLI commands."""

    def test_version(self):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "ERAD" in result.stdout

    def test_info(self):
        """Test info command."""
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "Version" in result.stdout
        assert "Python" in result.stdout
        assert "Platform" in result.stdout

    def test_help(self):
        """Test help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ERAD" in result.stdout
        assert "simulate" in result.stdout
        assert "generate" in result.stdout
        assert "models" in result.stdout


# ========== Models Command Tests ==========


class TestModelsCommands:
    """Test models subcommands."""

    def test_models_list_empty(self, mock_cache_dir):
        """Test listing models when cache is empty."""
        result = runner.invoke(app, ["models", "list"])
        assert result.exit_code == 0
        assert "No models found" in result.stdout or "Total: 0" in result.stdout

    def test_models_list_json(self, mock_cache_dir):
        """Test listing models with JSON output."""
        result = runner.invoke(app, ["models", "list", "--json"])
        assert result.exit_code == 0
        # Should be valid JSON (even if empty)
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_models_add(self, mock_cache_dir, sample_model_file):
        """Test adding a model to cache."""
        result = runner.invoke(
            app,
            [
                "models",
                "add",
                str(sample_model_file),
                "--name",
                "test_model",
                "--description",
                "Test description",
            ],
        )
        assert result.exit_code == 0
        assert "added to cache" in result.stdout

    def test_models_add_invalid_file(self, mock_cache_dir, tmp_path):
        """Test adding a non-existent file."""
        result = runner.invoke(app, ["models", "add", str(tmp_path / "nonexistent.json")])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_models_add_invalid_json(self, mock_cache_dir, tmp_path):
        """Test adding an invalid JSON file."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json")

        result = runner.invoke(app, ["models", "add", str(invalid_file)])
        assert result.exit_code == 1
        assert "Invalid JSON" in result.stdout

    def test_models_add_non_json_extension(self, mock_cache_dir, tmp_path):
        """Test adding a non-JSON file."""
        text_file = tmp_path / "model.txt"
        text_file.write_text("{}")

        result = runner.invoke(app, ["models", "add", str(text_file)])
        assert result.exit_code == 1
        assert "JSON" in result.stdout

    def test_models_remove_not_found(self, mock_cache_dir):
        """Test removing a model that doesn't exist."""
        result = runner.invoke(app, ["models", "remove", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_models_show_not_found(self, mock_cache_dir):
        """Test showing a model that doesn't exist."""
        result = runner.invoke(app, ["models", "show", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_models_export_not_found(self, mock_cache_dir, tmp_path):
        """Test exporting a model that doesn't exist."""
        result = runner.invoke(
            app, ["models", "export", "nonexistent", str(tmp_path / "output.json")]
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestModelsWorkflow:
    """Test complete models workflow."""

    def test_add_list_show_remove(self, mock_cache_dir, sample_model_file, tmp_path):
        """Test complete workflow: add -> list -> show -> export -> remove."""
        # Add
        result = runner.invoke(
            app,
            [
                "models",
                "add",
                str(sample_model_file),
                "--name",
                "workflow_test",
                "--description",
                "Workflow test model",
            ],
        )
        assert result.exit_code == 0

        # List
        result = runner.invoke(app, ["models", "list"])
        assert result.exit_code == 0
        assert "workflow_test" in result.stdout

        # Show
        result = runner.invoke(app, ["models", "show", "workflow_test"])
        assert result.exit_code == 0
        assert "workflow_test" in result.stdout

        # Export
        export_path = tmp_path / "exported.json"
        result = runner.invoke(app, ["models", "export", "workflow_test", str(export_path)])
        assert result.exit_code == 0
        assert export_path.exists()

        # Remove
        result = runner.invoke(app, ["models", "remove", "workflow_test"])
        assert result.exit_code == 0
        assert "removed" in result.stdout

        # Verify removed
        result = runner.invoke(app, ["models", "show", "workflow_test"])
        assert result.exit_code == 1


# ========== Hazards Command Tests ==========


class TestHazardsCommands:
    """Test hazards subcommands."""

    def test_hazards_list(self, mock_cache_dir):
        """Test listing hazard models (not types)."""
        result = runner.invoke(app, ["hazards", "list"])
        assert result.exit_code == 0
        # Should show empty list
        assert "No hazard models found" in result.stdout or "Total: 0" in result.stdout

    def test_hazards_example_earthquake(self):
        """Test showing earthquake example."""
        result = runner.invoke(app, ["hazards", "example", "earthquake"])
        assert result.exit_code == 0
        assert "earthquake" in result.stdout
        # New format uses models array
        assert "models" in result.stdout

    def test_hazards_example_flood(self):
        """Test showing flood example."""
        result = runner.invoke(app, ["hazards", "example", "flood"])
        assert result.exit_code == 0
        assert "flood" in result.stdout
        assert "models" in result.stdout

    def test_hazards_example_wind(self):
        """Test showing wind example."""
        result = runner.invoke(app, ["hazards", "example", "wind"])
        assert result.exit_code == 0
        assert "wind" in result.stdout
        assert "models" in result.stdout

    def test_hazards_example_fire(self):
        """Test showing fire example."""
        result = runner.invoke(app, ["hazards", "example", "fire"])
        assert result.exit_code == 0
        assert "fire" in result.stdout

    def test_hazards_example_unknown(self):
        """Test showing example for unknown hazard type."""
        result = runner.invoke(app, ["hazards", "example", "unknown"])
        assert result.exit_code == 1
        assert "Unknown hazard type" in result.stdout

    def test_hazards_example_output(self, tmp_path):
        """Test saving hazard example to file."""
        output_file = tmp_path / "example.json"
        result = runner.invoke(
            app, ["hazards", "example", "earthquake", "--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()

        # Verify valid JSON (new format is hazard system)
        with open(output_file) as f:
            data = json.load(f)
        assert "models" in data
        assert data["models"][0]["hazard_type"] == "earthquake"


# ========== Cache Command Tests ==========


class TestCacheCommands:
    """Test cache subcommands."""

    def test_cache_info(self, mock_cache_dir):
        """Test cache info command."""
        result = runner.invoke(app, ["cache", "info"])
        assert result.exit_code == 0
        assert "Cache Directory" in result.stdout
        assert "Total Models" in result.stdout

    def test_cache_refresh(self, mock_cache_dir):
        """Test cache refresh command."""
        result = runner.invoke(app, ["cache", "refresh"])
        assert result.exit_code == 0
        assert "refreshed" in result.stdout

    def test_cache_clear_no_confirm(self, mock_cache_dir):
        """Test cache clear without confirmation."""
        result = runner.invoke(app, ["cache", "clear"], input="n\n")
        assert result.exit_code == 0 or result.exit_code == 1
        assert "Cancelled" in result.stdout or "Aborted" in result.stdout

    def test_cache_clear_force(self, mock_cache_dir, sample_model_file):
        """Test cache clear with force flag."""
        # Add a model first
        runner.invoke(app, ["models", "add", str(sample_model_file), "--name", "to_clear"])

        # Clear cache
        result = runner.invoke(app, ["cache", "clear", "--force"])
        assert result.exit_code == 0
        assert "Cleared" in result.stdout


# ========== Simulation Command Tests ==========


class TestSimulationCommands:
    """Test simulation commands."""

    def test_simulate_model_not_found(self, mock_cache_dir):
        """Test simulation with non-existent model (requires 2 args now)."""
        result = runner.invoke(app, ["simulate", "nonexistent", "nonexistent_hazard"])
        # Exit code 1 for model not found (not 2 for missing args)
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_generate_model_not_found(self, mock_cache_dir):
        """Test scenario generation with non-existent model (requires 2 args now)."""
        result = runner.invoke(app, ["generate", "nonexistent", "nonexistent_hazard"])
        # Exit code 1 for model not found (not 2 for missing args)
        assert result.exit_code == 1
        assert "not found" in result.stdout


# ========== Server Command Tests ==========


class TestServerCommands:
    """Test server subcommands."""

    def test_server_mcp_help(self):
        """Test server mcp help."""
        result = runner.invoke(app, ["server", "mcp", "--help"])
        assert result.exit_code == 0


# ========== Integration Tests ==========


class TestCacheDirectoryFunctions:
    """Test cache directory utility functions."""

    def test_get_cache_directory_creates_dir(self, tmp_path, monkeypatch):
        """Test that get_cache_directory creates the directory."""
        import sys

        # Mock to use temp directory
        if sys.platform == "darwin":
            monkeypatch.setenv("HOME", str(tmp_path))
        else:
            monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

        # Import fresh to get new cache dir
        from erad.cli import get_cache_directory

        cache_dir = get_cache_directory()

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_load_save_metadata(self, mock_cache_dir):
        """Test loading and saving metadata."""
        from erad.cli import load_metadata, save_metadata

        # Initially empty
        metadata = load_metadata()
        assert metadata == {}

        # Save some metadata
        test_metadata = {"model1": {"description": "Test", "created_at": "2024-01-01"}}
        save_metadata(test_metadata)

        # Load and verify
        loaded = load_metadata()
        assert loaded == test_metadata
