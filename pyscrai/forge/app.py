"""
Forge App - FastAPI server for PyScrAI Universalis.

This module provides the REST API layer for controlling the simulation
and querying world state.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import uvicorn

from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


def create_app(
    title: str = "PyScrAI Universalis Engine",
    version: str = "0.2.0",
    description: str = "Agnostic Linguistic Simulation Engine"
) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        title: API title
        version: API version
        description: API description
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        version=version,
        description=description
    )
    
    # Add CORS middleware for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Store engine reference (to be set later)
    app.state.engine = None
    
    @app.get("/")
    async def root() -> Dict[str, str]:
        """Health check endpoint."""
        return {"message": "PyScrAI Universalis Engine is Pulsing"}
    
    @app.get("/health")
    async def health() -> Dict[str, Any]:
        """Detailed health check."""
        engine_status = "attached" if app.state.engine else "not attached"
        return {
            "status": "healthy",
            "engine": engine_status,
            "version": version
        }
    
    @app.post("/simulation/tick")
    async def run_tick() -> Dict[str, Any]:
        """
        Manually trigger a full Perception-Action-Adjudication cycle.
        
        Returns:
            Dict with cycle number, status, and summary
        """
        if not app.state.engine:
            raise HTTPException(
                status_code=503, 
                detail="Simulation engine not initialized"
            )
        
        try:
            result = app.state.engine.step()
            return result
        except Exception as e:
            logger.error(f"Error during tick: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/state")
    async def get_state() -> Dict[str, Any]:
        """
        Fetch the latest ground truth from the MongoDB ledger.
        
        Returns:
            Current world state or error message
        """
        if not app.state.engine:
            raise HTTPException(
                status_code=503, 
                detail="Simulation engine not initialized"
            )
        
        world_state = app.state.engine.get_current_state()
        if world_state:
            return world_state.model_dump()
        return {"error": "No state found in ledger"}
    
    @app.get("/simulation/info")
    async def get_simulation_info() -> Dict[str, Any]:
        """
        Get information about the current simulation.
        
        Returns:
            Simulation metadata
        """
        if not app.state.engine:
            raise HTTPException(
                status_code=503, 
                detail="Simulation engine not initialized"
            )
        
        return {
            "simulation_id": app.state.engine.sim_id,
            "current_cycle": app.state.engine.steps,
            "archon_attached": app.state.engine.archon is not None
        }
    
    @app.post("/simulation/reset")
    async def reset_simulation() -> Dict[str, str]:
        """
        Reset the simulation to cycle 0.
        
        Note: This does not clear the database, just resets the cycle counter.
        """
        if not app.state.engine:
            raise HTTPException(
                status_code=503, 
                detail="Simulation engine not initialized"
            )
        
        app.state.engine.reset()
        return {"message": "Simulation reset to cycle 0"}
    
    return app


def attach_engine(app: FastAPI, engine: Any) -> None:
    """
    Attach a simulation engine to the FastAPI app.
    
    Args:
        app: FastAPI application instance
        engine: SimulationEngine instance
    """
    app.state.engine = engine
    logger.info(f"Engine {engine.sim_id} attached to Forge")


def run_server(
    app: FastAPI,
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False
) -> None:
    """
    Run the FastAPI server.
    
    Args:
        app: FastAPI application instance
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
    """
    uvicorn.run(app, host=host, port=port, reload=reload)


# Create default app instance
app = create_app()

