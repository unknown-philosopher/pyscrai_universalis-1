"""
State Management for PyScrAI Universalis.

This module provides DuckDB-based state management with spatial query support.
"""

from pyscrai.universalis.state.duckdb_manager import (
    DuckDBStateManager,
    get_state_manager,
)

__all__ = [
    'DuckDBStateManager',
    'get_state_manager',
]

