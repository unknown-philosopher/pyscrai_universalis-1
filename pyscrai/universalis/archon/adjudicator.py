"""
Archon Adjudicator - The omniscient referee of PyScrAI Universalis.

This module contains the LangGraph-based adjudication logic that:
1. Processes actor perceptions and generates intents
2. Adjudicates actions and resolves conflicts
3. Updates world state based on outcomes
"""

import os
from typing import TypedDict, List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph, END

from pyscrai.data.schemas.models import WorldState
from pyscrai.universalis.archon.interface import ArchonInterface, AdjudicationResult
from pyscrai.utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


class AgentState(TypedDict):
    """State passed through the LangGraph workflow."""
    world_state: WorldState
    actor_intents: List[str]
    archon_summary: str
    rationales: List[Dict[str, Any]]


class Archon(ArchonInterface):
    """
    The Archon - omniscient referee of the simulation.
    
    Implements the ArchonInterface and provides LangGraph-based
    adjudication logic.
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        enable_tracing: bool = True
    ):
        """
        Initialize the Archon.
        
        Args:
            model_name: LLM model to use (defaults to env var)
            temperature: LLM temperature setting
            enable_tracing: Enable Langfuse tracing
        """
        # LLM Configuration
        self._api_key = os.getenv("OPENROUTER_API_KEY")
        self._base_url = os.getenv("OPENROUTER_BASE_URL")
        self._model_name = model_name or os.getenv("MODEL_NAME", "xiaomi/mimo-v2-flash:free")
        
        # Initialize the LLM
        self.llm = ChatOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            model=self._model_name,
            temperature=temperature
        )
        
        # Langfuse handler for tracing
        self.langfuse_handler = CallbackHandler() if enable_tracing else None
        
        # Build the LangGraph workflow
        self._workflow = self._build_workflow()
        self._compiled_graph = self._workflow.compile()
        
        logger.info(f"Archon initialized with model: {self._model_name}")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("perception", self._actor_perception_node)
        workflow.add_node("adjudication", self._archon_adjudication_node)
        
        workflow.set_entry_point("perception")
        workflow.add_edge("perception", "adjudication")
        workflow.add_edge("adjudication", END)
        
        return workflow
    
    def _actor_perception_node(self, state: AgentState) -> AgentState:
        """
        Node 1: Actor Perception.
        
        Each actor perceives the world and generates their intent.
        """
        logger.info("--- NODE: ACTORS PERCEIVING ---")
        
        world = state["world_state"]
        env = world.environment
        all_intents = []
        
        # Loop through all actors in the simulation
        for actor_id, actor in world.actors.items():
            # Build Context Strings
            recent_events = "\n- ".join(env.global_events[-3:]) if env.global_events else "None"
            asset_list = ", ".join(actor.assets) if actor.assets else "None"
            objectives_list = "\n- ".join(actor.objectives) if actor.objectives else "None"
            
            # Construct the Prompt
            prompt_content = (
                f"You are {actor.role} (ID: {actor_id}).\n"
                f"Description: {actor.description}\n"
                f"Objectives:\n- {objectives_list}\n"
                f"Assets under command: {asset_list}\n\n"
                f"Current Situation:\n"
                f"- Cycle: {env.cycle}\n"
                f"- Time: {env.time}\n"
                f"- Weather: {env.weather}\n"
                f"- Recent Events:\n- {recent_events}\n\n"
                "Based on your role and the situation, what is your strategic intent for this cycle? "
                "Be concise. Refer to your assets by name if moving them."
            )
            
            try:
                # Invoke LLM
                config = {"callbacks": [self.langfuse_handler]} if self.langfuse_handler else {}
                response = self.llm.invoke(
                    [HumanMessage(content=prompt_content)],
                    config=config
                )
                
                intent_str = f"{actor_id}: {response.content}"
                all_intents.append(intent_str)
                logger.info(f"   > {actor_id} decided: {response.content[:50]}...")
                
            except Exception as e:
                error_msg = f"{actor_id} failed to act: {str(e)}"
                all_intents.append(error_msg)
                logger.error(error_msg)
        
        state["actor_intents"] = all_intents
        return state
    
    def _archon_adjudication_node(self, state: AgentState) -> AgentState:
        """
        Node 2: Archon Adjudication.
        
        The Archon reviews all intents and determines outcomes.
        """
        logger.info("--- NODE: ARCHON ADJUDICATING ---")
        
        current_state = state["world_state"]
        intents = "\n".join(state["actor_intents"])
        
        # Construct the Prompt for the Archon
        system_prompt = (
            "You are the Archon, the omniscient referee of a simulation. "
            "Your goal is to adjudicate actor actions and simulate environmental shifts (Gaia). "
            "Analyze the current state and the actor intents. "
            "Output a concise summary of what happens next."
        )
        
        user_prompt = (
            f"Current Cycle: {current_state.environment.cycle}\n"
            f"Current Weather: {current_state.environment.weather}\n"
            f"Recent Events: {current_state.environment.global_events[-3:] if current_state.environment.global_events else 'None'}\n\n"
            f"Actor Intents:\n{intents}\n\n"
            "Adjudicate the result of this cycle:"
        )
        
        # Invoke the LLM with Langfuse Tracing
        try:
            config = {"callbacks": [self.langfuse_handler]} if self.langfuse_handler else {}
            response = self.llm.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
                config=config
            )
            summary = response.content
        except Exception as e:
            summary = f"Archon Error: {str(e)}"
            logger.error(summary)
        
        # Update the World State (Ground Truth)
        state["world_state"].environment.global_events.append(summary)
        state["archon_summary"] = summary
        
        # Store rationale for traceability
        rationale = {
            "cycle": current_state.environment.cycle,
            "intents": state["actor_intents"],
            "summary": summary,
            "reasoning": "LLM-based adjudication"
        }
        state["rationales"] = state.get("rationales", []) + [rationale]
        
        return state
    
    def run_cycle(self, world_state: WorldState) -> Dict[str, Any]:
        """
        Run a full perception-adjudication cycle.
        
        Args:
            world_state: Current world state
        
        Returns:
            Dict with updated world_state and archon_summary
        """
        brain_input = {
            "world_state": world_state, 
            "actor_intents": [], 
            "archon_summary": "",
            "rationales": []
        }
        
        # Execute the graph
        final_output = self._compiled_graph.invoke(brain_input)
        
        return {
            "world_state": final_output["world_state"],
            "archon_summary": final_output.get("archon_summary", "No summary provided"),
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
        
        Args:
            world_state: Current world state
            actor_intents: List of actor intent strings
        
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
    ) -> Dict[str, Any]:
        """
        Check if an intent is feasible given the world state.
        
        This is a placeholder that will be enhanced with the FeasibilityEngine.
        
        Args:
            intent: The intent to check
            world_state: Current world state
        
        Returns:
            Dict with feasibility assessment
        """
        # Placeholder - will be implemented with FeasibilityEngine
        return {
            "feasible": True,
            "constraints_checked": [],
            "violations": []
        }
    
    def generate_rationale(self, result: AdjudicationResult) -> str:
        """
        Generate a human-readable rationale for an adjudication result.
        
        Args:
            result: The adjudication result
        
        Returns:
            Human-readable rationale string
        """
        return result.summary


# Create a compiled simulation brain for backward compatibility
def create_simulation_brain(archon: Optional[Archon] = None) -> Any:
    """
    Create a simulation brain (compiled LangGraph).
    
    Args:
        archon: Optional Archon instance (creates new one if not provided)
    
    Returns:
        Compiled LangGraph workflow
    """
    if archon is None:
        archon = Archon()
    return archon._compiled_graph

