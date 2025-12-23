"""
NiceGUI App - Unified event loop UI for PyScrAI Universalis.

This module provides the main user interface using NiceGUI,
running on the same event loop as the simulation for real-time
updates without polling.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from nicegui import ui, app
from nicegui.events import ValueChangeEventArguments

from pyscrai.universalis.engine import SimulationEngine
from pyscrai.universalis.archon.adjudicator import Archon
from pyscrai.architect.seeder import seed_simulation, get_seeded_simulations
from pyscrai.config import get_config
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)

# Global state
_engine: Optional[SimulationEngine] = None
_simulation_task: Optional[asyncio.Task] = None


class SimulationUI:
    """
    Main simulation UI component.
    
    Provides controls for starting/stopping simulation, viewing world state,
    and interacting with the map.
    """
    
    def __init__(self):
        """Initialize the UI components."""
        self.engine: Optional[SimulationEngine] = None
        self.config = get_config()
        
        # UI state
        self.current_cycle = 0
        self.is_running = False
        self.is_paused = False
        self.events_log: List[str] = []
        
        # UI element references
        self.cycle_label = None
        self.status_label = None
        self.map_component = None
        self.events_container = None
        self.actors_container = None
        self.assets_container = None
    
    def build(self) -> None:
        """Build the main UI layout."""
        # Apply dark theme
        ui.dark_mode().enable()
        
        # Custom CSS
        ui.add_css('''
            .simulation-card {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border: 1px solid #0f3460;
            }
            .event-item {
                border-left: 3px solid #e94560;
                padding-left: 8px;
                margin: 4px 0;
            }
            .control-btn {
                min-width: 120px;
            }
        ''')
        
        with ui.header().classes('items-center justify-between bg-slate-900'):
            ui.label('GeoScrAI Universalis').classes('text-2xl font-bold text-cyan-400')
            with ui.row().classes('items-center gap-4'):
                self.cycle_label = ui.label('Cycle: 0').classes('text-lg')
                self.status_label = ui.label('Status: Idle').classes('text-lg text-gray-400')
        
        with ui.row().classes('w-full h-full gap-4 p-4'):
            # Left panel - Controls and Info
            with ui.column().classes('w-1/4 gap-4'):
                self._build_control_panel()
                self._build_actors_panel()
                self._build_assets_panel()
            
            # Center - Map
            with ui.column().classes('w-1/2 gap-4'):
                self._build_map_panel()
            
            # Right panel - Events and Memory
            with ui.column().classes('w-1/4 gap-4'):
                self._build_events_panel()
    
    def _build_control_panel(self) -> None:
        """Build the simulation control panel."""
        with ui.card().classes('w-full simulation-card'):
            ui.label('Simulation Control').classes('text-xl font-bold text-cyan-300 mb-4')
            
            # Simulation selector
            with ui.row().classes('w-full items-center gap-2 mb-4'):
                ui.label('Simulation:')
                simulations = get_seeded_simulations() or ['Alpha_Scenario']
                self.sim_select = ui.select(
                    simulations,
                    value=self.config.simulation.simulation_id
                ).classes('flex-grow')
            
            # Control buttons
            with ui.row().classes('w-full gap-2 flex-wrap'):
                ui.button('Initialize', on_click=self._on_initialize).classes('control-btn bg-blue-600')
                ui.button('Seed DB', on_click=self._on_seed).classes('control-btn bg-purple-600')
            
            with ui.row().classes('w-full gap-2 flex-wrap mt-2'):
                self.start_btn = ui.button('Start', on_click=self._on_start).classes('control-btn bg-green-600')
                self.pause_btn = ui.button('Pause', on_click=self._on_pause).classes('control-btn bg-yellow-600')
                self.step_btn = ui.button('Step', on_click=self._on_step).classes('control-btn bg-cyan-600')
                self.stop_btn = ui.button('Stop', on_click=self._on_stop).classes('control-btn bg-red-600')
            
            # Speed control
            with ui.row().classes('w-full items-center gap-2 mt-4'):
                ui.label('Tick Interval:')
                self.speed_slider = ui.slider(
                    min=100, max=5000, value=1000, step=100
                ).classes('flex-grow')
                self.speed_label = ui.label('1000ms')
            
            self.speed_slider.on('update:model-value', 
                lambda e: self.speed_label.set_text(f'{int(e.args)}ms'))
    
    def _build_actors_panel(self) -> None:
        """Build the actors info panel."""
        with ui.card().classes('w-full simulation-card'):
            ui.label('Actors').classes('text-xl font-bold text-cyan-300 mb-4')
            self.actors_container = ui.column().classes('w-full gap-2')
    
    def _build_assets_panel(self) -> None:
        """Build the assets info panel."""
        with ui.card().classes('w-full simulation-card'):
            ui.label('Assets').classes('text-xl font-bold text-cyan-300 mb-4')
            self.assets_container = ui.column().classes('w-full gap-2')
    
    def _build_map_panel(self) -> None:
        """Build the map visualization panel."""
        with ui.card().classes('w-full h-full simulation-card'):
            ui.label('World Map').classes('text-xl font-bold text-cyan-300 mb-4')
            
            # Leaflet map
            self.map_component = ui.leaflet(
                center=(34.05, -118.25),  # LA coordinates
                zoom=10
            ).classes('w-full h-96')
            
            # Map controls
            with ui.row().classes('w-full gap-2 mt-2'):
                ui.button('Center on Actors', on_click=self._center_on_actors).classes('text-sm')
                ui.button('Show Terrain', on_click=self._toggle_terrain).classes('text-sm')
    
    def _build_events_panel(self) -> None:
        """Build the events log panel."""
        with ui.card().classes('w-full simulation-card h-full'):
            ui.label('Events Log').classes('text-xl font-bold text-cyan-300 mb-4')
            self.events_container = ui.column().classes('w-full gap-1 overflow-y-auto max-h-96')
    
    # Event handlers
    
    async def _on_initialize(self) -> None:
        """Initialize the simulation engine."""
        try:
            sim_id = self.sim_select.value
            
            ui.notify(f'Initializing simulation: {sim_id}...', type='info')
            
            # Create Archon
            archon = Archon(simulation_id=sim_id)
            
            # Create Engine
            self.engine = SimulationEngine(sim_id=sim_id)
            self.engine.attach_archon(archon)
            
            # Update UI
            self.current_cycle = self.engine.steps
            self.cycle_label.set_text(f'Cycle: {self.current_cycle}')
            self.status_label.set_text('Status: Initialized')
            
            # Load world state
            await self._refresh_state()
            
            ui.notify(f'Simulation {sim_id} initialized!', type='positive')
            
        except Exception as e:
            logger.error(f"Initialization error: {e}", exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
    
    async def _on_seed(self) -> None:
        """Seed the database."""
        try:
            sim_id = self.sim_select.value
            ui.notify(f'Seeding database for {sim_id}...', type='info')
            
            seed_simulation(simulation_id=sim_id)
            
            ui.notify(f'Database seeded for {sim_id}!', type='positive')
            
            # Refresh simulation list
            simulations = get_seeded_simulations() or ['Alpha_Scenario']
            self.sim_select.options = simulations
            
        except Exception as e:
            logger.error(f"Seeding error: {e}", exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
    
    async def _on_start(self) -> None:
        """Start the simulation loop."""
        if not self.engine:
            ui.notify('Please initialize first!', type='warning')
            return
        
        if self.is_running:
            return
        
        self.is_running = True
        self.is_paused = False
        self.status_label.set_text('Status: Running')
        
        # Start simulation loop
        global _simulation_task
        _simulation_task = asyncio.create_task(self._run_simulation_loop())
    
    async def _on_pause(self) -> None:
        """Pause/Resume the simulation."""
        if not self.engine:
            return
        
        if self.is_paused:
            self.engine.resume()
            self.is_paused = False
            self.status_label.set_text('Status: Running')
            self.pause_btn.set_text('Pause')
        else:
            self.engine.pause()
            self.is_paused = True
            self.status_label.set_text('Status: Paused (God Mode)')
            self.pause_btn.set_text('Resume')
    
    async def _on_step(self) -> None:
        """Execute a single simulation step."""
        if not self.engine:
            ui.notify('Please initialize first!', type='warning')
            return
        
        try:
            result = await self.engine.async_step()
            self.current_cycle = result['cycle']
            self.cycle_label.set_text(f'Cycle: {self.current_cycle}')
            
            # Add to events log
            self._add_event(f"Cycle {result['cycle']}: {result['summary'][:100]}...")
            
            await self._refresh_state()
            
        except Exception as e:
            logger.error(f"Step error: {e}", exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
    
    async def _on_stop(self) -> None:
        """Stop the simulation."""
        if self.engine:
            self.engine.stop()
        
        self.is_running = False
        self.is_paused = False
        self.status_label.set_text('Status: Stopped')
        
        global _simulation_task
        if _simulation_task:
            _simulation_task.cancel()
            _simulation_task = None
    
    async def _run_simulation_loop(self) -> None:
        """Run the simulation loop."""
        try:
            while self.is_running and self.engine:
                if not self.is_paused:
                    result = await self.engine.async_step()
                    self.current_cycle = result['cycle']
                    self.cycle_label.set_text(f'Cycle: {self.current_cycle}')
                    
                    # Add to events log
                    self._add_event(f"Cycle {result['cycle']}: {result['summary'][:100]}...")
                    
                    await self._refresh_state()
                
                # Wait for tick interval
                interval_ms = self.speed_slider.value
                await asyncio.sleep(interval_ms / 1000.0)
                
        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled")
        except Exception as e:
            logger.error(f"Simulation loop error: {e}", exc_info=True)
            self.is_running = False
            self.status_label.set_text(f'Status: Error - {e}')
    
    async def _refresh_state(self) -> None:
        """Refresh UI with current world state."""
        if not self.engine:
            return
        
        world_state = self.engine.get_current_state()
        if not world_state:
            return
        
        # Update actors panel
        self.actors_container.clear()
        with self.actors_container:
            for actor_id, actor in world_state.actors.items():
                with ui.row().classes('w-full items-center justify-between bg-slate-800 p-2 rounded'):
                    ui.label(actor.role).classes('font-bold')
                    ui.badge(actor.status, color='green' if actor.status == 'active' else 'gray')
        
        # Update assets panel
        self.assets_container.clear()
        with self.assets_container:
            for asset_id, asset in world_state.assets.items():
                with ui.row().classes('w-full items-center justify-between bg-slate-800 p-2 rounded'):
                    ui.label(asset.name).classes('font-bold')
                    ui.badge(asset.status, color='green' if asset.status == 'active' else 'yellow')
        
        # Update map markers
        self._update_map_markers(world_state)
    
    def _update_map_markers(self, world_state) -> None:
        """Update map markers for actors and assets."""
        if not self.map_component:
            return
        
        # Clear existing markers (simplified - in real app, track and update)
        # For now, we'll just add markers
        
        # Add actor markers
        for actor_id, actor in world_state.actors.items():
            if actor.location:
                self.map_component.marker(
                    latlng=(actor.location.lat, actor.location.lon)
                )
        
        # Add asset markers
        for asset_id, asset in world_state.assets.items():
            if asset.location and 'lat' in asset.location and 'lon' in asset.location:
                self.map_component.marker(
                    latlng=(asset.location['lat'], asset.location['lon'])
                )
    
    def _add_event(self, event: str) -> None:
        """Add an event to the log."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.events_log.append(f"[{timestamp}] {event}")
        
        # Keep last 50 events
        if len(self.events_log) > 50:
            self.events_log = self.events_log[-50:]
        
        # Update UI
        self.events_container.clear()
        with self.events_container:
            for evt in reversed(self.events_log[-20:]):
                ui.label(evt).classes('event-item text-sm text-gray-300')
    
    def _center_on_actors(self) -> None:
        """Center map on actor locations."""
        if not self.engine:
            return
        
        world_state = self.engine.get_current_state()
        if world_state and world_state.actors:
            # Find center of all actor locations
            lats = []
            lons = []
            for actor in world_state.actors.values():
                if actor.location:
                    lats.append(actor.location.lat)
                    lons.append(actor.location.lon)
            
            if lats and lons:
                center_lat = sum(lats) / len(lats)
                center_lon = sum(lons) / len(lons)
                self.map_component.set_center((center_lat, center_lon))
    
    def _toggle_terrain(self) -> None:
        """Toggle terrain overlay."""
        # Placeholder for terrain visualization
        ui.notify('Terrain toggle not yet implemented', type='info')


def create_app() -> SimulationUI:
    """
    Create and configure the NiceGUI application.
    
    Returns:
        SimulationUI instance
    """
    simulation_ui = SimulationUI()
    
    @ui.page('/')
    def main_page():
        simulation_ui.build()
    
    return simulation_ui


def run_app(
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: bool = False
) -> None:
    """
    Run the NiceGUI application.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
    """
    config = get_config()
    
    host = host or config.ui.host
    port = port or config.ui.port
    reload = reload or config.ui.reload
    
    logger.info(f"Starting GeoScrAI UI at http://{host}:{port}")
    
    ui.run(
        host=host,
        port=port,
        title=config.ui.title,
        reload=reload,
        dark=config.ui.dark_mode
    )

