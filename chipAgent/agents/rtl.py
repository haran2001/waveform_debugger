"""RTL Agent - Implements complete synthesizable Verilog RTL."""

import os
from google.adk.agents import LlmAgent
from google.genai import types
from prompts.rtl_prompt import RTL_SYSTEM_PROMPT
from tools.file_tools import write_file, read_file

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

rtl_agent = LlmAgent(
    name="RTLAgent",
    model=MODEL,
    instruction=RTL_SYSTEM_PROMPT + """

=== CONTEXT FROM PREVIOUS AGENTS ===

ARCHITECT SPECIFICATION (functional requirements, parameters, timing):
{architect_output}

MODULE INTERFACES (ports and structure):
{entity_output}
""",
    description="Implements complete synthesizable Verilog RTL for any digital design",
    tools=[write_file, read_file],
    output_key="rtl_output",
    generate_content_config=RETRY_CONFIG,
)
