"""
Historic hazard tools for ERAD MCP Server.
"""

import sqlite3

from loguru import logger
from mcp.server import MCPServer

from erad.models.hazard.wind import WindModel
from erad.models.hazard.earthquake import EarthQuakeModel
from erad.models.hazard.wild_fire import FireModel

from .state import state
from .helpers import get_historic_hazard_db


async def list_historic_hurricanes(year: int | None = None, limit: int = 50) -> dict:
    """List available historic hurricanes from the database.

    Args:
        year: Filter by year (optional).
        limit: Maximum number of results.

    Returns:
        JSON payload with the hurricane list, or an error payload.
    """
    try:
        db_path = get_historic_hazard_db()
        if not db_path.exists():
            return {"error": f"Historic hazard database not found at {db_path}"}

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info('historic_hurricanes')")
        columns = {row[1] for row in cursor.fetchall()}

        def pick_column(*candidates: str) -> str | None:
            for candidate in candidates:
                if candidate in columns:
                    return candidate
            return None

        sid_col = pick_column("SID", "SID ")
        name_col = pick_column("NAME", "NAME ")
        season_col = pick_column("SEASON", "SEASON ", "SEASON (Year)")

        if not sid_col or not name_col or not season_col:
            conn.close()
            return {
                "error": (
                    "historic_hurricanes schema is missing required columns. "
                    f"Found columns: {sorted(columns)}"
                )
            }

        query = (
            f'SELECT DISTINCT "{sid_col}" AS sid, "{name_col}" AS name, '
            f'"{season_col}" AS season FROM historic_hurricanes'
        )
        params = []

        if year:
            query += " WHERE season = ?"
            params.append(year)

        query += " ORDER BY season DESC, name LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        hurricanes = [{"sid": row[0], "name": row[1], "season": row[2]} for row in results]

        logger.info(f"Found {len(hurricanes)} historic hurricanes")

        return {"success": True, "count": len(hurricanes), "hurricanes": hurricanes}

    except Exception as e:
        logger.error(f"Error listing hurricanes: {e}")
        return {"error": str(e)}


async def list_historic_earthquakes(min_magnitude: float | None = None, limit: int = 50) -> dict:
    """List available historic earthquakes from the database.

    Args:
        min_magnitude: Minimum magnitude filter (optional).
        limit: Maximum number of results.

    Returns:
        JSON payload with the earthquake list, or an error payload.
    """
    try:
        db_path = get_historic_hazard_db()
        if not db_path.exists():
            return {"error": f"Historic hazard database not found at {db_path}"}

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = "SELECT earthquake_code, date, magnitude, latitude, longitude FROM historic_earthquakes"
        params = []

        if min_magnitude:
            query += " WHERE magnitude >= ?"
            params.append(min_magnitude)

        query += " ORDER BY magnitude DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        earthquakes = [
            {
                "earthquake_code": row[0],
                "date": row[1],
                "magnitude": row[2],
                "latitude": row[3],
                "longitude": row[4],
            }
            for row in results
        ]

        logger.info(f"Found {len(earthquakes)} historic earthquakes")

        return {"success": True, "count": len(earthquakes), "earthquakes": earthquakes}

    except Exception as e:
        logger.error(f"Error listing earthquakes: {e}")
        return {"error": str(e)}


async def list_historic_wildfires(year: int | None = None, limit: int = 50) -> dict:
    """List available historic wildfires from the database.

    Args:
        year: Filter by year (optional).
        limit: Maximum number of results.

    Returns:
        JSON payload with the wildfire list, or an error payload.
    """
    try:
        db_path = get_historic_hazard_db()
        if not db_path.exists():
            return {"error": f"Historic hazard database not found at {db_path}"}

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = "SELECT DISTINCT FIRE_NAME, FIRE_YEAR FROM historic_fires"
        params = []

        if year:
            query += " WHERE FIRE_YEAR = ?"
            params.append(year)

        query += " ORDER BY FIRE_YEAR DESC, FIRE_NAME LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        wildfires = [{"fire_name": row[0], "fire_year": row[1]} for row in results]

        logger.info(f"Found {len(wildfires)} historic wildfires")

        return {"success": True, "count": len(wildfires), "wildfires": wildfires}

    except Exception as e:
        logger.error(f"Error listing wildfires: {e}")
        return {"error": str(e)}


async def load_historic_hurricane(hazard_system_id: str, hurricane_sid: str) -> dict:
    """Load a historic hurricane and add to hazard system.

    Args:
        hazard_system_id: ID of hazard system to add to.
        hurricane_sid: Hurricane SID (e.g., '2017228N14314').

    Returns:
        JSON payload with the loaded track points, or an error payload.
    """
    try:
        if hazard_system_id not in state.hazard_systems:
            return {"error": f"Hazard system not found: {hazard_system_id}"}

        hazard_system = state.hazard_systems[hazard_system_id]

        logger.info(f"Loading hurricane {hurricane_sid}")
        wind_track = WindModel.from_hurricane_sid(hurricane_sid)
        if not wind_track:
            return {"error": f"No hurricane track points found for {hurricane_sid}"}

        for wind_model in wind_track:
            hazard_system.add_component(wind_model)

        latest = wind_track[-1]

        return {
            "success": True,
            "hurricane_sid": hurricane_sid,
            "points_loaded": len(wind_track),
            "timestamp": latest.timestamp.isoformat(),
            "max_wind_speed": str(latest.max_wind_speed),
            "message": f"Hurricane {hurricane_sid} added to hazard system {hazard_system_id}",
        }

    except Exception as e:
        logger.error(f"Error loading hurricane: {e}")
        return {"error": str(e)}


async def load_historic_earthquake(hazard_system_id: str, earthquake_code: str) -> dict:
    """Load a historic earthquake and add to hazard system.

    Args:
        hazard_system_id: ID of hazard system to add to.
        earthquake_code: Earthquake code (e.g., 'ISCGEM851547').

    Returns:
        JSON payload with the loaded earthquake, or an error payload.
    """
    try:
        if hazard_system_id not in state.hazard_systems:
            return {"error": f"Hazard system not found: {hazard_system_id}"}

        hazard_system = state.hazard_systems[hazard_system_id]

        logger.info(f"Loading earthquake {earthquake_code}")
        earthquake_model = EarthQuakeModel.from_earthquake_code(earthquake_code)
        hazard_system.add_component(earthquake_model)

        return {
            "success": True,
            "earthquake_code": earthquake_code,
            "timestamp": earthquake_model.timestamp.isoformat(),
            "magnitude": earthquake_model.magnitude,
            "message": f"Earthquake {earthquake_code} added to hazard system {hazard_system_id}",
        }

    except Exception as e:
        logger.error(f"Error loading earthquake: {e}")
        return {"error": str(e)}


async def load_historic_wildfire(hazard_system_id: str, wildfire_name: str) -> dict:
    """Load a historic wildfire and add to hazard system.

    Args:
        hazard_system_id: ID of hazard system to add to.
        wildfire_name: Wildfire name (e.g., 'GREAT LAKES FIRE').

    Returns:
        JSON payload with the loaded wildfire, or an error payload.
    """
    try:
        if hazard_system_id not in state.hazard_systems:
            return {"error": f"Hazard system not found: {hazard_system_id}"}

        hazard_system = state.hazard_systems[hazard_system_id]

        logger.info(f"Loading wildfire {wildfire_name}")
        fire_model = FireModel.from_wildfire_name(wildfire_name)
        hazard_system.add_component(fire_model)

        return {
            "success": True,
            "wildfire_name": wildfire_name,
            "timestamp": fire_model.timestamp.isoformat(),
            "message": f"Wildfire {wildfire_name} added to hazard system {hazard_system_id}",
        }

    except Exception as e:
        logger.error(f"Error loading wildfire: {e}")
        return {"error": str(e)}


def register(mcp: MCPServer) -> None:
    """Register historic hazard tools with the MCP server."""
    mcp.tool()(list_historic_hurricanes)
    mcp.tool()(list_historic_earthquakes)
    mcp.tool()(list_historic_wildfires)
    mcp.tool()(load_historic_hurricane)
    mcp.tool()(load_historic_earthquake)
    mcp.tool()(load_historic_wildfire)
