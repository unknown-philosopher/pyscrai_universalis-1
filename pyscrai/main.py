"""
PyScrAI Universalis - Main Bootloader

This is the entry point for the PyScrAI Universalis simulation engine.
It initializes all three layers of the Triad:
- Architect: Design-time tools (seeding, validation)
- Universalis: Run-time simulation engine
- Forge: UI/API layer

Usage:
    python -m pyscrai.main [--seed] [--host HOST] [--port PORT]
"""

import argparse
import os
from dotenv import load_dotenv

from pyscrai.universalis.engine import SimulationEngine
from pyscrai.universalis.archon.adjudicator import Archon
from pyscrai.forge.app import create_app, attach_engine, run_server
from pyscrai.architect.seeder import seed_simulation
from pyscrai.utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger("pyscrai.main")


def initialize_simulation(
    sim_id: str = "Alpha_Scenario",
    seed_db: bool = False
) -> SimulationEngine:
    """
    Initialize the simulation engine with Archon.
    
    Args:
        sim_id: Simulation identifier
        seed_db: Whether to seed the database first
    
    Returns:
        Configured SimulationEngine instance
    """
    logger.info(f"Initializing PyScrAI Universalis - Simulation: {sim_id}")
    
    # Optionally seed the database
    if seed_db:
        logger.info("Seeding database...")
        seed_simulation(simulation_id=sim_id)
    
    # Initialize the Archon (cognitive adjudicator)
    logger.info("Initializing Archon...")
    archon = Archon()
    
    # Initialize the simulation engine
    logger.info("Initializing Simulation Engine...")
    engine = SimulationEngine(sim_id=sim_id)
    engine.attach_archon(archon)
    
    logger.info(f"Simulation {sim_id} ready at Cycle {engine.steps}")
    return engine


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PyScrAI Universalis - Agnostic Linguistic Simulation Engine"
    )
    parser.add_argument(
        "--sim-id",
        default=os.getenv("SIMULATION_ID", "Alpha_Scenario"),
        help="Simulation identifier"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed the database before starting"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind the API server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to bind the API server"
    )
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Initialize engine without starting the API server"
    )
    
    args = parser.parse_args()
    
    # Initialize the simulation
    engine = initialize_simulation(
        sim_id=args.sim_id,
        seed_db=args.seed
    )
    
    if not args.no_server:
        # Create and configure the Forge (API)
        logger.info("Creating Forge (API layer)...")
        app = create_app()
        attach_engine(app, engine)
        
        # Start the server
        logger.info(f"Starting server at {args.host}:{args.port}")
        run_server(app, host=args.host, port=args.port)
    else:
        logger.info("Engine initialized without API server (--no-server flag)")
        return engine


if __name__ == "__main__":
    main()

