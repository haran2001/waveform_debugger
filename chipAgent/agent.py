"""
ChipAgent - Entry point for ADK web server
This exposes the orchestrator as the root agent for the application.
"""

from agents.orchestrator import chip_design_pipeline

# Expose the pipeline as root_agent for ADK web server
root_agent = chip_design_pipeline
