"""Verify Agent - Runs iverilog simulation and reports results."""

import os
from google.adk.agents import LlmAgent
from google.genai import types
from prompts.verify_prompt import VERIFY_SYSTEM_PROMPT
from tools.file_tools import read_file
from tools.simulation_tools import run_iverilog_compile, run_vvp_simulation

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

verify_agent = LlmAgent(
    name="VerifyAgent",
    model=MODEL,
    instruction=VERIFY_SYSTEM_PROMPT + """

=== CONTEXT FROM PREVIOUS AGENTS ===

RTL OUTPUT (files to compile):
{rtl_output}

TESTBENCH OUTPUT (testbenches to run):
{dv_output}
""",
    description="Compiles and runs simulation using Icarus Verilog, reports pass/fail status",
    tools=[run_iverilog_compile, run_vvp_simulation, read_file],
    output_key="verify_output",
    generate_content_config=RETRY_CONFIG,
)
