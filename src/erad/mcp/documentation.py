"""
Documentation search tools for ERAD MCP Server.
"""

from pathlib import Path

from loguru import logger


async def search_documentation_tool(args: dict) -> dict:
    """Search documentation."""
    query = args["query"].lower()

    try:
        docs_dir = Path(__file__).parent.parent.parent.parent / "docs"
        results = []

        if not docs_dir.exists():
            return {"error": "Documentation directory not found"}

        # Search markdown files
        for md_file in docs_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if query in content.lower():
                    # Get context around match
                    lines = content.split("\n")
                    matching_lines = [i for i, line in enumerate(lines) if query in line.lower()]

                    snippets = []
                    for line_num in matching_lines[:3]:  # First 3 matches
                        start = max(0, line_num - 2)
                        end = min(len(lines), line_num + 3)
                        snippet = "\n".join(lines[start:end])
                        snippets.append(snippet)

                    results.append(
                        {
                            "file": str(md_file.relative_to(docs_dir)),
                            "match_count": len(matching_lines),
                            "snippets": snippets,
                        }
                    )
            except Exception as e:
                logger.warning(f"Error reading {md_file}: {e}")
                continue

        return {"success": True, "query": query, "result_count": len(results), "results": results}

    except Exception as e:
        logger.error(f"Error searching documentation: {e}")
        return {"error": str(e)}
