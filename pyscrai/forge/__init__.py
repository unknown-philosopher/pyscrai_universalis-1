"""
Forge module - UI/API layer for PyScrAI Universalis.

This module contains:
- app: FastAPI server and REST endpoints
- dashboard: Visualization components (macro/micro views)
- map: Map rendering and layer management
"""

from pyscrai.forge.app import create_app, attach_engine, run_server

__all__ = [
    "create_app",
    "attach_engine",
    "run_server",
]
