"""Entity Agent - Generates Verilog module interfaces from structured spec."""

import os
from google.adk.agents import LlmAgent
from google.genai import types
from prompts.entity_prompt import ENTITY_SYSTEM_PROMPT
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

entity_agent = LlmAgent(
    name="EntityAgent",
    model=MODEL,
    instruction=ENTITY_SYSTEM_PROMPT + "\n\nArchitect Specification:\n{architect_output}",
    description="Generates Verilog module interfaces from structured spec",
    tools=[write_file],
    output_key="entity_output",
    generate_content_config=RETRY_CONFIG,
)
