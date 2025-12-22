"""
Dashboard module - Visualization components for PyScrAI Universalis.

This module contains:
- viewport: Unified viewport with resolution toggle
- macro_view: Macro resolution components (graphs, heatmaps, reports)
- micro_view: Micro resolution components (agent inspection, memory visualizer)
- components: Shared UI components (map, timeline, etc.)
"""

from pyscrai.forge.dashboard.viewport import (
    UnifiedViewport,
    ViewResolution,
    ViewportState,
    create_viewport
)
from pyscrai.forge.dashboard.macro_view import (
    MacroViewRenderer,
    MacroMetrics,
    create_macro_view
)
from pyscrai.forge.dashboard.micro_view import (
    MicroViewRenderer,
    AgentProfile,
    create_micro_view
)
from pyscrai.forge.dashboard.components import (
    MapComponent,
    TimelineComponent,
    EventLogComponent,
    StatusBarComponent,
    create_map_component,
    create_timeline_component,
    create_event_log_component,
    create_status_bar_component
)

__all__ = [
    # Viewport
    "UnifiedViewport",
    "ViewResolution",
    "ViewportState",
    "create_viewport",
    # Macro view
    "MacroViewRenderer",
    "MacroMetrics",
    "create_macro_view",
    # Micro view
    "MicroViewRenderer",
    "AgentProfile",
    "create_micro_view",
    # Components
    "MapComponent",
    "TimelineComponent",
    "EventLogComponent",
    "StatusBarComponent",
    "create_map_component",
    "create_timeline_component",
    "create_event_log_component",
    "create_status_bar_component",
]
