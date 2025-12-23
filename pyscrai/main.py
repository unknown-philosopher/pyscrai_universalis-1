"""
PyScrAI Universalis (GeoScrAI) - Main Entry Point

This is the entry point for the simulation engine.
It initializes all three layers of the Triad:
- Architect: Design-time tools (seeding, validation)
- Universalis: Run-time simulation engine
- Forge: NiceGUI-based UI layer

Usage:
    python -m pyscrai.main [--seed] [--host HOST] [--port PORT] [--no-ui]
"""

import argparse
import asyncio
import os
from dotenv import load_dotenv

from pyscrai.config import get_config
from pyscrai.utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger("pyscrai.main")


def seed_database(sim_id: str) -> None:
    """
    Seed the DuckDB database with initial scenario.
    
    Args:
        sim_id: Simulation identifier
    """
    from pyscrai.architect.seeder import seed_simulation
    from pyscrai.architect.schema_init import init_database
    
    logger.info(f"Initializing database...")
    init_database()
    
    logger.info(f"Seeding database for {sim_id}...")
    seed_simulation(simulation_id=sim_id)
    logger.info("Database seeded successfully!")


def initialize_simulation(
    sim_id: str,
    seed_db: bool = False
):
    """
    Initialize the simulation engine with Archon.
    
    Args:
        sim_id: Simulation identifier
        seed_db: Whether to seed the database first
    
    Returns:
        Configured SimulationEngine instance
    """
    from pyscrai.universalis.engine import SimulationEngine
    from pyscrai.universalis.archon.adjudicator import Archon
    
    logger.info(f"Initializing PyScrAI Universalis - Simulation: {sim_id}")
    
    # Optionally seed the database
    if seed_db:
        seed_database(sim_id)
    
    # Initialize the Archon (cognitive adjudicator)
    logger.info("Initializing Archon...")
    archon = Archon(simulation_id=sim_id)
    
    # Initialize the simulation engine
    logger.info("Initializing Simulation Engine...")
    engine = SimulationEngine(sim_id=sim_id)
    engine.attach_archon(archon)
    
    logger.info(f"Simulation {sim_id} ready at Cycle {engine.steps}")
    return engine


def run_ui(host: str, port: int) -> None:
    """
    Run the NiceGUI-based user interface.
    
    Args:
        host: Host to bind to
        port: Port to bind to
    """
    from pyscrai.forge.ui import create_app, run_app
    
    logger.info(f"Starting GeoScrAI UI at http://{host}:{port}")
    create_app()
    run_app(host=host, port=port)


async def run_headless(sim_id: str, cycles: int = 10) -> None:
    """
    Run the simulation in headless mode (no UI).
    
    Args:
        sim_id: Simulation identifier
        cycles: Number of cycles to run
    """
    engine = initialize_simulation(sim_id, seed_db=True)
    
    logger.info(f"Running {cycles} cycles in headless mode...")
    
    for i in range(cycles):
        result = await engine.async_step()
        logger.info(f"Cycle {result['cycle']}: {result['status']} - {result['summary'][:100]}...")
    
    logger.info("Headless simulation complete!")
    engine.shutdown()


def main():
    """Main entry point."""
    config = get_config()
    
    parser = argparse.ArgumentParser(
        description="GeoScrAI / PyScrAI Universalis - Spatial Linguistic Simulation Engine"
    )
    parser.add_argument(
        "--sim-id",
        default=config.simulation.simulation_id,
        help="Simulation identifier"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed the database before starting"
    )
    parser.add_argument(
        "--host",
        default=config.ui.host,
        help="Host to bind the UI server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.ui.port,
        help="Port to bind the UI server"
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Run in headless mode (no UI)"
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=10,
        help="Number of cycles to run in headless mode"
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Only seed the database, then exit"
    )
    
    args = parser.parse_args()
    
    # Seed only mode
    if args.seed_only:
        seed_database(args.sim_id)
        return
    
    # Seed if requested
    if args.seed:
        seed_database(args.sim_id)
    
    # Run in headless mode or with UI
    if args.no_ui:
        asyncio.run(run_headless(args.sim_id, args.cycles))
    else:
        run_ui(args.host, args.port)


if __name__ == "__main__":
    main()
