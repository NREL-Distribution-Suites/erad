"""Run the ERAD MCP server via ``python -m erad.mcp``.

The ``erad-mcp`` console script (``erad.mcp:main``) and ``python -m erad.mcp``
both enter through :func:`erad.mcp.server.main`.
"""

from erad.mcp.server import main

if __name__ == "__main__":
    main()
