"""
Forge module - UI/API layer for PyScrAI Universalis.

This module provides the NiceGUI-based user interface for controlling
and visualizing simulations with real-time map updates.
"""

from pyscrai.forge.ui import (
    create_app,
    run_app,
)

__all__ = [
    'create_app',
    'run_app',
]

