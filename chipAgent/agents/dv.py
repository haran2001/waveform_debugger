"""DV Agent - Generates SystemVerilog testbenches with directed tests."""

import os
from google.adk.agents import LlmAgent
from google.genai import types
from prompts.dv_prompt import DV_SYSTEM_PROMPT
from tools.file_tools import write_file

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

dv_agent = LlmAgent(
    name="DVAgent",
    model=MODEL,
    instruction=DV_SYSTEM_PROMPT + """

=== CONTEXT FROM PREVIOUS AGENTS ===

ARCHITECT SPECIFICATION (functional requirements to verify):
{architect_output}

MODULE INTERFACES (ports to drive/monitor):
{entity_output}
""",
    description="Generates SystemVerilog testbenches with directed tests for any digital design",
    tools=[write_file],
    output_key="dv_output",
    generate_content_config=RETRY_CONFIG,
)
