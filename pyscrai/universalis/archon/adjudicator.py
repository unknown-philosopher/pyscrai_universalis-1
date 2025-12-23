"""
Archon Adjudicator - The omniscient referee of PyScrAI Universalis.

This module contains the LangGraph-based adjudication logic that:
1. Orchestrates Agent Perception (delegating to Agent classes)
2. Checks Feasibility using DuckDB spatial queries
3. Adjudicates outcomes and Updates world state
4. Supports interrupts for "God Mode" control
"""

import os
from typing import TypedDict, List, Dict, Any, Optional, Union
from datetime import datetime
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from pyscrai.data.schemas.models import WorldState, ResolutionType, Actor
from pyscrai.universalis.archon.interface import (
    ArchonInterface, 
    AdjudicationResult, 
    FeasibilityReport
)
from pyscrai.universalis.archon.feasibility import FeasibilityEngine
from pyscrai.universalis.archon.spatial_constraints import SpatialConstraintChecker
from pyscrai.universalis.agents.macro_agent import MacroAgent, create_macro_agent
from pyscrai.universalis.agents.micro_agent import MicroAgent, create_micro_agent
from pyscrai.universalis.state.duckdb_manager import get_state_manager
from pyscrai.universalis.memory.stream import MemoryStream
from pyscrai.config import get_config
from pyscrai.utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# Try to import langfuse
try:
    from langfuse.langchain import CallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logger.debug("Langfuse not available, tracing disabled")


class AgentState(TypedDict):
    """State passed through the LangGraph workflow."""
    world_state: WorldState
    actor_intents: Dict[str, str]  # Map actor_id -> intent string
    actor_errors: Dict[str, str]  # Map actor_id -> error message
    feasibility_reports: Dict[str, FeasibilityReport]  # Map actor_id -> report
    perception_context: Dict[str, Dict[str, Any]]  # Map actor_id -> perception data
    archon_summary: str
    rationales: List[Dict[str, Any]]
    interrupted: bool  # For God Mode support


class Archon(ArchonInterface):
    """
    The Archon - omniscient referee of the simulation.
    
    Orchestrates agent perception, feasibility checking, and adjudication
    using LangGraph workflow. Uses DuckDB for spatial constraint checking.
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        enable_tracing: bool = True,
        simulation_id: Optional[str] = None
    ):
        """
        Initialize the Archon.
        
        Args:
            model_name: LLM model to use (defaults to env var)
            temperature: LLM temperature setting
            enable_tracing: Enable Langfuse tracing
            simulation_id: Simulation ID for spatial queries
        """
        config = get_config()
        
        # LLM Configuration
        self._api_key = config.llm.api_key or os.getenv("OPENROUTER_API_KEY")
        self._base_url = config.llm.base_url or os.getenv("OPENROUTER_BASE_URL")
        self._model_name = model_name or config.llm.model_name
        self._simulation_id = simulation_id or config.simulation.simulation_id
        
        # Initialize the LLM
        self.llm = ChatOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            model=self._model_name,
            temperature=temperature
        )
        
        # Langfuse handler for tracing
        self.langfuse_handler = None
        if enable_tracing and LANGFUSE_AVAILABLE:
            try:
                self.langfuse_handler = CallbackHandler()
            except Exception as e:
                logger.warning(f"Langfuse tracing not available: {e}")
        
        # Initialize Logic Engines
        self.feasibility_engine = FeasibilityEngine(simulation_id=self._simulation_id)
        self.spatial_checker = SpatialConstraintChecker(simulation_id=self._simulation_id)
        
        # Memory References (Injected by Engine)
        self.memory_bank = None  # Will be MemoryBank (LanceDBMemoryBank or ChromaDBMemoryBank)
        self.memory_stream: Optional[MemoryStream] = None
        
        # Agent Cache (preserves state across cycles)
        self._agent_cache: Dict[str, Union[MacroAgent, MicroAgent]] = {}
        
        # Build the Graph
        self._workflow = self._build_workflow()
        self._compiled_graph = self._workflow.compile()
        
        logger.info(f"Archon initialized with model: {self._model_name}")

    def set_memory_systems(
        self, 
        memory_bank, 
        memory_stream: MemoryStream
    ) -> None:
        """
        Receive memory instances from the Engine.
        
        Args:
            memory_bank: LanceDB or ChromaDB-backed associative memory
            memory_stream: Chronological event log
        """
        self.memory_bank = memory_bank
        self.memory_stream = memory_stream
        logger.info("Archon connected to Memory Bank and Stream")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with interrupt support."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("perception", self._actor_perception_node)
        workflow.add_node("feasibility", self._feasibility_check_node)
        workflow.add_node("adjudication", self._archon_adjudication_node)
        
        # Set entry point and edges
        workflow.set_entry_point("perception")
        workflow.add_edge("perception", "feasibility")
        workflow.add_edge("feasibility", "adjudication")
        workflow.add_edge("adjudication", END)
        
        return workflow
    
    def _get_or_create_agent(
        self, 
        actor_id: str, 
        actor_data: Actor
    ) -> Union[MacroAgent, MicroAgent]:
        """
        Get cached agent instance or create new one.
        
        Preserves agent state (relationships, internal state) across cycles.
        
        Args:
            actor_id: Unique actor identifier
            actor_data: Actor model data
        
        Returns:
            Agent instance (MacroAgent or MicroAgent)
        """
        if actor_id not in self._agent_cache:
            # Determine resolution with defensive check
            resolution = getattr(actor_data, 'resolution', ResolutionType.MACRO)
            
            if resolution == ResolutionType.MICRO:
                agent = create_micro_agent(
                    actor_data,
                    memory_bank=self.memory_bank,
                    memory_stream=self.memory_stream
                )
            else:
                agent = create_macro_agent(
                    actor_data,
                    memory_bank=self.memory_bank
                )
            
            self._agent_cache[actor_id] = agent
            logger.debug(f"Created new {resolution.value} agent for {actor_id}")
        
        return self._agent_cache[actor_id]
    
    def _generate_perception_sphere(
        self,
        actor: Actor,
        world_state: WorldState
    ) -> Dict[str, Any]:
        """
        Generate spatial perception context for an actor using DuckDB.
        
        This creates a "perception sphere" around the actor's location,
        finding nearby entities and terrain features.
        
        Args:
            actor: The actor to generate perception for
            world_state: Current world state
        
        Returns:
            Dict with perception data (nearby entities, terrain, etc.)
        """
        perception = {
            "nearby_actors": [],
            "nearby_assets": [],
            "terrain": None,
            "controlled_assets": []
        }
        
        # Get actor location
        if actor.location:
            lon, lat = actor.location.lon, actor.location.lat
            
            try:
                # Get nearby entities using DuckDB spatial query
                state_manager = get_state_manager(self._simulation_id)
                config = get_config()
                radius = config.simulation.perception_radius_degrees
                
                nearby = state_manager.get_entities_within_distance(
                    center_lon=lon,
                    center_lat=lat,
                    distance_degrees=radius
                )
                
                for entity in nearby:
                    if entity['entity_type'] == 'actor' and entity['id'] != actor.actor_id:
                        perception['nearby_actors'].append({
                            'id': entity['id'],
                            'name': entity['name'],
                            'distance': entity['distance'],
                            'distance_km': entity['distance'] * 111  # Approx conversion
                        })
                    elif entity['entity_type'] == 'asset':
                        perception['nearby_assets'].append({
                            'id': entity['id'],
                            'name': entity['name'],
                            'distance': entity['distance'],
                            'status': entity['status']
                        })
                
                # Get terrain at location
                terrain = state_manager.get_terrain_at_point(lon, lat)
                if terrain:
                    perception['terrain'] = {
                        'type': terrain['terrain_type'],
                        'name': terrain['name'],
                        'movement_cost': terrain['movement_cost'],
                        'passable': terrain['passable']
                    }
                    
            except Exception as e:
                logger.warning(f"Could not generate perception sphere: {e}")
        
        # Add controlled assets from world state
        for asset_id in actor.assets:
            if asset_id in world_state.assets:
                asset = world_state.assets[asset_id]
                perception['controlled_assets'].append({
                    'id': asset_id,
                    'name': asset.name,
                    'type': asset.asset_type,
                    'status': asset.status,
                    'location': asset.location
                })
        
        return perception
    
    def _actor_perception_node(self, state: AgentState) -> AgentState:
        """
        Node 1: Actor Perception.
        
        Delegates to Agent Classes to generate intents using Memory & Personality.
        Uses spatial perception sphere for context.
        """
        logger.info("--- NODE: ACTORS PERCEIVING ---")
        
        world = state["world_state"]
        actor_intents: Dict[str, str] = {}
        actor_errors: Dict[str, str] = {}
        perception_context: Dict[str, Dict[str, Any]] = {}
        
        for actor_id, actor_data in world.actors.items():
            try:
                # 1. Generate perception sphere using spatial queries
                perception = self._generate_perception_sphere(actor_data, world)
                perception_context[actor_id] = perception
                
                # 2. Get or create agent instance (cached for state preservation)
                agent = self._get_or_create_agent(actor_id, actor_data)
                
                # 3. Agent "Thinks" (Uses Memory + LLM + Perception)
                intent_obj = agent.generate_intent(world, context=perception)
                
                # 4. Store result
                actor_intents[actor_id] = intent_obj.content
                logger.info(f"   > {actor_id} intent: {intent_obj.content[:50]}...")
                
            except Exception as e:
                error_msg = f"Error in agent {actor_id}: {str(e)}"
                actor_errors[actor_id] = error_msg
                logger.error(error_msg, exc_info=True)
        
        state["actor_intents"] = actor_intents
        state["actor_errors"] = actor_errors
        state["perception_context"] = perception_context
        return state

    def _feasibility_check_node(self, state: AgentState) -> AgentState:
        """
        Node 2: Feasibility Check.
        
        Filters hallucinations using physics/budget constraints.
        Uses DuckDB spatial queries for movement validation.
        """
        logger.info("--- NODE: FEASIBILITY CHECK ---")
        world = state["world_state"]
        reports: Dict[str, FeasibilityReport] = {}
        
        for actor_id, intent_text in state["actor_intents"].items():
            # Skip feasibility check if actor had an error
            if actor_id in state.get("actor_errors", {}):
                continue
            
            # Run the feasibility engine (now includes spatial checks)
            report = self.feasibility_engine.check_feasibility(
                intent=intent_text,
                world_state=world,
                actor_id=actor_id
            )
            reports[actor_id] = report
            
            if not report.feasible:
                logger.warning(
                    f"   ! {actor_id} Intent Infeasible: "
                    f"{[v.get('message', '') for v in report.violations]}"
                )
        
        state["feasibility_reports"] = reports
        return state
    
    def _archon_adjudication_node(self, state: AgentState) -> AgentState:
        """
        Node 3: Archon Adjudication.
        
        Resolves conflicts and updates world state.
        """
        logger.info("--- NODE: ARCHON ADJUDICATING ---")
        
        current_state = state["world_state"]
        
        # Construct summary string including feasibility warnings and errors
        intent_summary_lines = []
        
        # Add successful intents with perception context
        for aid, text in state["actor_intents"].items():
            report = state["feasibility_reports"].get(aid)
            perception = state.get("perception_context", {}).get(aid, {})
            
            # Build context string
            context_parts = []
            if perception.get('terrain'):
                context_parts.append(f"terrain: {perception['terrain']['type']}")
            if perception.get('nearby_actors'):
                nearby = ", ".join([a['name'] for a in perception['nearby_actors'][:3]])
                context_parts.append(f"nearby actors: {nearby}")
            
            context_str = f" [{', '.join(context_parts)}]" if context_parts else ""
            
            if report and not report.feasible:
                violations = "; ".join([v.get('message', '') for v in report.violations])
                intent_summary_lines.append(
                    f"{aid}{context_str}: ATTEMPTED '{text}' BUT FAILED due to: {violations}"
                )
            else:
                intent_summary_lines.append(f"{aid}{context_str}: {text}")
        
        # Add errors
        for aid, error_msg in state.get("actor_errors", {}).items():
            intent_summary_lines.append(f"{aid}: ERROR - {error_msg}")
        
        intents_block = "\n".join(intent_summary_lines)
        
        # System Prompt
        system_prompt = (
            "You are the Archon, the omniscient referee of a simulation. "
            "Adjudicate the cycle based on Actor Intents, Feasibility Reports, and Spatial Context. "
            "1. If an action failed feasibility (blocked by terrain, distance, etc.), describe the failure. "
            "2. If an actor had an error, note it but continue with other actors. "
            "3. Consider spatial relationships and terrain when describing outcomes. "
            "4. Update the Global Events log. "
            "5. Describe any environmental shifts (weather, etc)."
        )
        
        user_prompt = (
            f"Cycle: {current_state.environment.cycle}\n"
            f"Weather: {current_state.environment.weather}\n"
            f"Recent Events: {current_state.environment.global_events[-3:] if current_state.environment.global_events else 'None'}\n\n"
            f"ACTOR ACTIONS:\n{intents_block}\n\n"
            "Generate the Adjudication Result:"
        )
        
        try:
            config = {"callbacks": [self.langfuse_handler]} if self.langfuse_handler else {}
            response = self.llm.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
                config=config
            )
            summary = response.content
        except Exception as e:
            summary = f"Archon Error: {str(e)}"
            logger.error(summary, exc_info=True)
        
        # Update World State (create new list to avoid mutation issues)
        new_events = list(current_state.environment.global_events) + [summary]
        state["world_state"].environment.global_events = new_events
        state["archon_summary"] = summary
        
        # Store in Memory Stream for traceability
        if self.memory_stream:
            self.memory_stream.add_adjudication(
                content=summary,
                cycle=current_state.environment.cycle,
                metadata={
                    "intents": state["actor_intents"],
                    "feasibility_reports": {
                        k: v.to_dict() for k, v in state["feasibility_reports"].items()
                    },
                    "perception_context": state.get("perception_context", {}),
                    "errors": state.get("actor_errors", {})
                }
            )
        
        # Store rationale for traceability
        rationale = {
            "cycle": current_state.environment.cycle,
            "intents": state["actor_intents"],
            "feasibility_reports": {
                k: v.to_dict() for k, v in state["feasibility_reports"].items()
            },
            "perception_context": state.get("perception_context", {}),
            "errors": state.get("actor_errors", {}),
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        state["rationales"] = state.get("rationales", []) + [rationale]
        
        return state
    
    def run_cycle(self, world_state: WorldState) -> Dict[str, Any]:
        """
        Run the full graph cycle.
        
        Args:
            world_state: Current world state
        
        Returns:
            Dict with updated world_state, archon_summary, and rationales
        """
        brain_input: AgentState = {
            "world_state": world_state, 
            "actor_intents": {}, 
            "actor_errors": {},
            "feasibility_reports": {},
            "perception_context": {},
            "archon_summary": "",
            "rationales": [],
            "interrupted": False
        }
        
        final_output = self._compiled_graph.invoke(brain_input)
        
        return {
            "world_state": final_output["world_state"],
            "archon_summary": final_output.get("archon_summary", ""),
            "rationales": final_output.get("rationales", [])
        }

    # ArchonInterface implementation
    
    def adjudicate(
        self, 
        world_state: WorldState, 
        actor_intents: List[str]
    ) -> AdjudicationResult:
        """
        Adjudicate actor intents and return the result.
        
        Note: This interface method accepts pre-generated intents, but
        the internal implementation generates intents via agents.
        For now, we ignore the provided intents and use agent generation.
        
        Args:
            world_state: Current world state
            actor_intents: List of actor intent strings (ignored - agents generate their own)
        
        Returns:
            AdjudicationResult with updated state and rationale
        """
        result = self.run_cycle(world_state)
        
        return AdjudicationResult(
            world_state=result["world_state"],
            summary=result["archon_summary"],
            rationales=result["rationales"],
            success=True
        )
    
    def check_feasibility(
        self, 
        intent: str, 
        world_state: WorldState
    ) -> FeasibilityReport:
        """
        Check if an intent is feasible given the world state.
        
        Args:
            intent: The intent to check
            world_state: Current world state
        
        Returns:
            FeasibilityReport with assessment details
        """
        return self.feasibility_engine.check_feasibility(
            intent=intent,
            world_state=world_state
        )
    
    def generate_rationale(self, result: AdjudicationResult) -> str:
        """
        Generate a human-readable rationale for an adjudication result.
        
        Args:
            result: The adjudication result
        
        Returns:
            Human-readable rationale string
        """
        return result.summary
    
    def clear_agent_cache(self) -> None:
        """
        Clear the agent cache.
        
        Useful for resetting agent state or when actors are removed.
        """
        self._agent_cache.clear()
        logger.info("Agent cache cleared")
