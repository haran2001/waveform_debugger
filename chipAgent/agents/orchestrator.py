"""
Orchestrator - Composes agents into the chip design pipeline.

This module defines the workflow composition using SequentialAgent and ParallelAgent
to orchestrate the complete chip design flow from spec to synthesis.
"""

from google.adk.agents import SequentialAgent, ParallelAgent

from agents.architect import architect_agent
from agents.entity import entity_agent
from agents.rtl import rtl_agent
from agents.dv import dv_agent
from agents.verify import verify_agent
from agents.synthesis import synthesis_agent


# Parallel execution disabled to avoid rate limiting on free tier API
# To re-enable, uncomment ParallelAgent and use it in place of rtl_agent, dv_agent
# parallel_rtl_dv = ParallelAgent(
#     name="ParallelRTLAndDV",
#     sub_agents=[rtl_agent, dv_agent],
#     description="Generates RTL implementation and testbenches in parallel"
# )

# Main sequential pipeline (runs RTL and DV sequentially to avoid rate limits)
chip_design_pipeline = SequentialAgent(
    name="ChipDesignPipeline",
    sub_agents=[
        architect_agent,    # Step 1: Parse spec into structured JSON
        entity_agent,       # Step 2: Create module interfaces
        rtl_agent,          # Step 3: Generate RTL implementation
        dv_agent,           # Step 4: Generate testbenches
        verify_agent,       # Step 5: Run simulation
        synthesis_agent     # Step 6: Generate synthesis config
    ],
    description="Complete chip design pipeline from spec to synthesis"
)
