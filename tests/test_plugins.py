"""
Tests for ERAD plugin discovery.
"""

import pytest

from erad.plugins import (
    clear_plugin_cache,
    discover_plugins,
    get_plugin,
    list_plugins,
)
from erad.mcp.plugins import get_plugin as mcp_get_plugin
from erad.mcp.plugins import list_plugins as mcp_list_plugins


@pytest.fixture(autouse=True)
def _reset_plugin_cache():
    """Clear the discovery cache before and after each test."""
    clear_plugin_cache()
    yield
    clear_plugin_cache()


class TestDiscovery:
    """Test the core discover_plugins / get_plugin / list_plugins functions."""

    def test_discover_plugins_no_plugins_installed(self):
        """Discovery returns {} without raising when no plugins are installed."""
        assert discover_plugins() == {}

    def test_discover_plugins_skips_broken_entry_points(self, monkeypatch):
        """A broken entry point must not kill discovery."""

        class _BrokenEP:
            name = "broken"
            value = "no_such_module:register"

            def load(self):
                raise ImportError("cannot import no_such_module")

        class _RaisingRegisterEP:
            name = "explodes"
            value = "os:register"

            def load(self):
                import os

                # os has no 'register' attribute -> AttributeError on getattr
                return getattr(os, "register")

        monkeypatch.setattr(
            "erad.plugins.entry_points", lambda **kwargs: [_BrokenEP(), _RaisingRegisterEP()]
        )

        assert discover_plugins() == {}

    def test_discover_plugins_collects_working_entry_point(self, monkeypatch):
        """A working entry point is collected under its metadata name."""

        def _register():
            return {
                "name": "fake",
                "version": "1.0.0",
                "description": "a fake plugin",
                "hazard_types": ["wind"],
                "requires": ["some_engine_that_is_not_installed"],
            }

        class _FakeEP:
            name = "fake"
            value = "fake_module:register"

            def load(self):
                return _register

        monkeypatch.setattr("erad.plugins.entry_points", lambda **kwargs: [_FakeEP()])

        plugins = discover_plugins()
        assert "fake" in plugins
        assert plugins["fake"]["version"] == "1.0.0"

        # get_plugin resolves by name
        assert get_plugin("fake") == plugins["fake"]
        assert get_plugin("missing") is None

        # list_plugins reports metadata plus an availability flag
        listed = list_plugins()
        assert listed[0]["name"] == "fake"
        assert listed[0]["available"] is False  # required engine not importable

    def test_working_entry_point_available_when_engine_present(self, monkeypatch):
        """available is True when every module in requires is importable."""

        def _register():
            return {
                "name": "fake2",
                "version": "1.0.0",
                "description": "a fake plugin",
                "hazard_types": ["earthquake"],
                "requires": ["json"],  # stdlib, always importable
            }

        class _FakeEP:
            name = "fake2"
            value = "fake2_module:register"

            def load(self):
                return _register

        monkeypatch.setattr("erad.plugins.entry_points", lambda **kwargs: [_FakeEP()])

        listed = list_plugins()
        assert listed[0]["name"] == "fake2"
        assert listed[0]["available"] is True


class TestMcpPluginTools:
    """Test the MCP plugin tools via direct function calls."""

    @pytest.mark.asyncio
    async def test_list_plugins_tool_shape(self):
        """list_plugins returns {'plugins': [...]}."""
        result = await mcp_list_plugins()
        assert "plugins" in result
        assert isinstance(result["plugins"], list)

    @pytest.mark.asyncio
    async def test_get_plugin_tool_missing(self):
        """get_plugin returns an error payload for an unknown plugin."""
        result = await mcp_get_plugin("no_such_plugin")
        assert result == {"error": "plugin not found: no_such_plugin"}

    @pytest.mark.asyncio
    async def test_get_plugin_tool_found(self, monkeypatch):
        """get_plugin returns metadata for a discovered plugin."""
        from erad.mcp.plugins import get_plugin as _mcp_get_plugin

        def _register():
            return {
                "name": "fake",
                "version": "1.0.0",
                "description": "a fake plugin",
                "hazard_types": ["wind"],
                "requires": [],
            }

        class _FakeEP:
            name = "fake"
            value = "fake_module:register"

            def load(self):
                return _register

        monkeypatch.setattr("erad.plugins.entry_points", lambda **kwargs: [_FakeEP()])

        result = await _mcp_get_plugin("fake")
        assert result["plugin"]["name"] == "fake"
        assert result["plugin"]["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_plugins_resource_returns_json(self):
        """The erad://plugins resource returns a JSON payload with a plugins key."""
        import json

        from erad.mcp.server import create_server

        server = create_server()
        contents = await server.read_resource("erad://plugins")
        text = contents[0].content
        payload = json.loads(text)
        assert "plugins" in payload
        assert isinstance(payload["plugins"], list)
