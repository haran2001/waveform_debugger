"""Synthesis Agent - Generates PPA-optimized OpenLane configuration."""

import os
from google.adk.agents import LlmAgent
from google.genai import types
from prompts.synthesis_prompt import SYNTHESIS_SYSTEM_PROMPT
from tools.file_tools import write_file, read_file, copy_file, list_files
from tools.synthesis_tools import run_openlane_synthesis, check_openlane_installed, get_synthesis_reports

from dotenv import load_dotenv
load_dotenv()

MODEL = os.getenv("MODEL")

# Retry configuration for rate limiting
RETRY_CONFIG = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initialDelay=30.0,
            maxDelay=120.0,
            expBase=2.0,
            attempts=5,
        ),
    ),
)

synthesis_agent = LlmAgent(
    name="SynthesisAgent",
    model=MODEL,
    instruction=SYNTHESIS_SYSTEM_PROMPT + """

=== CONTEXT FROM PREVIOUS AGENTS ===

ARCHITECT SPECIFICATION (design requirements and PPA targets):
{architect_output}

RTL OUTPUT (implemented modules):
{rtl_output}

VERIFICATION RESULTS (must check ready_for_synthesis):
{verify_output}
""",
    description="Generates PPA-optimized OpenLane synthesis configuration for Sky130 PDK",
    tools=[write_file, read_file, copy_file, list_files, run_openlane_synthesis, check_openlane_installed, get_synthesis_reports],
    output_key="synthesis_output",
    generate_content_config=RETRY_CONFIG,
)
