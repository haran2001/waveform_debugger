"""Architect Agent - Parses any design spec into structured JSON."""

import os
from google.adk.agents import LlmAgent
from google.genai import types
from prompts.architect_prompt import ARCHITECT_SYSTEM_PROMPT

from dotenv import load_dotenv
load_dotenv()

MODEL = os.getenv("MODEL")

# Retry configuration for rate limiting
RETRY_CONFIG = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initialDelay=30.0,  # Wait 30 seconds before first retry
            maxDelay=120.0,     # Maximum delay between retries
            expBase=2.0,        # Exponential backoff base
            attempts=5,         # Try up to 5 times
        ),
    ),
)

architect_agent = LlmAgent(
    name="ArchitectAgent",
    model=MODEL,
    instruction=ARCHITECT_SYSTEM_PROMPT,
    description="Parses any design specification into structured JSON with functional requirements, interfaces, modules, timing, and PPA targets",
    output_key="architect_output",
    generate_content_config=RETRY_CONFIG,
)
