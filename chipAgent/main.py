"""
Generic Multi-Agent Chip Design System using Google ADK.

This system orchestrates multiple AI agents to automate digital design flow
from natural language specification to PPA-optimized synthesis configuration.

Supports any digital design: SPI, FIFO, CRC, processors, etc.
"""

import asyncio
import time
from pathlib import Path
from typing import Optional

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import the pipeline from agents
from agents.orchestrator import chip_design_pipeline
from tools.simulation_tools import check_iverilog_installed
from dotenv import load_dotenv

# Rate limiting configuration
RATE_LIMIT_RPM = 15  # Requests per minute (free tier limit)
RATE_LIMIT_WAIT_SECONDS = 60  # Wait time when rate limited

# =============================================================================
# Configuration
# =============================================================================

load_dotenv()


APP_NAME = "chip_design_system"
USER_ID = "designer"
SESSION_ID = "design_session"

# Project paths
PROJECT_ROOT = Path(__file__).parent
SPEC_FILE = PROJECT_ROOT / "design_spec.txt"


# =============================================================================
# Runner Functions
# =============================================================================

def load_design_spec(spec_path: Optional[Path] = None) -> str:
    """Load the design specification file."""
    path = spec_path or SPEC_FILE
    if not path.exists():
        raise FileNotFoundError(f"Design spec not found: {path}")
    with open(path, 'r') as f:
        return f.read()


async def run_design_flow(
    spec_path: Optional[Path] = None,
    session_id: Optional[str] = None
) -> dict:
    """
    Execute the complete chip design flow.

    Args:
        spec_path: Path to design specification file (default: design_spec.txt)
        session_id: Optional session ID for the run

    Returns:
        dict with final session state containing all agent outputs
    """

    # Check prerequisites
    iverilog_check = check_iverilog_installed()
    if iverilog_check["status"] != "installed":
        print(f"Warning: {iverilog_check.get('error', 'iverilog not found')}")
        print("Simulation step will fail. Install with: brew install icarus-verilog")
    else:
        print(f"Found iverilog: {iverilog_check['version']}")

    # Load design spec
    design_spec = load_design_spec(spec_path)
    print(f"\nLoaded design specification ({len(design_spec)} characters)")
    print("-" * 60)
    print(design_spec[:500] + "..." if len(design_spec) > 500 else design_spec)
    print("-" * 60)

    # Setup session service
    session_service = InMemorySessionService()

    # Create runner
    runner = Runner(
        agent=chip_design_pipeline,
        app_name=APP_NAME,
        session_service=session_service
    )

    # Session ID
    sid = session_id or SESSION_ID

    # Initialize session with design spec and default values for all agent outputs
    # Default values prevent pipeline crashes if an upstream agent fails to produce output
    default_not_run = '{"status": "not_run", "error": "Previous agent did not complete"}'
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=sid,
        state={
            "design_spec": design_spec,
            # Default values - will be overwritten when agents complete successfully
            "architect_output": default_not_run,
            "entity_output": default_not_run,
            "rtl_output": default_not_run,
            "dv_output": default_not_run,
            "verify_output": '{"status": "not_run", "verification_status": "NOT_RUN", "ready_for_synthesis": false}',
        }
    )

    # Build user message
    user_message = f"""
Please design a digital circuit based on the following specification:

---
{design_spec}
---

Execute the complete design flow:
1. Parse the specification into a structured JSON format
2. Generate Verilog module interfaces for all components
3. Implement the complete RTL
4. Create comprehensive testbenches
5. Run simulation to verify functionality
6. Generate synthesis configuration optimized for the design's requirements

Proceed through each step, using the appropriate tools to create files.
"""

    # Run the pipeline
    print("\n" + "=" * 60)
    print("Starting Chip Design Pipeline")
    print("=" * 60)

    # Create proper Content object for the message
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    )

    # Track API calls and timing for rate limiting
    api_call_count = 0
    api_calls_by_agent = {}
    api_call_timestamps = []  # Track timestamps for rate limiting

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=sid,
        new_message=user_content
    ):
        current_time = time.time()

        # Count API calls (model responses have role='model')
        if hasattr(event, 'content') and hasattr(event.content, 'role'):
            if event.content.role == 'model':
                api_call_count += 1
                api_call_timestamps.append(current_time)
                agent_name = getattr(event, 'author', 'unknown')
                api_calls_by_agent[agent_name] = api_calls_by_agent.get(agent_name, 0) + 1

                # Calculate current rate (calls in last 60 seconds)
                recent_calls = [t for t in api_call_timestamps if current_time - t < 60]
                rate = len(recent_calls)
                print(f"  [API Call #{api_call_count}, Rate: {rate}/min]", end="")

                # Add delay after EVERY API call to avoid rate limits
                # Free tier has strict limits - add 4s delay to spread out requests
                wait_time = 4
                print(f" (waiting {wait_time}s)", end="")
                await asyncio.sleep(wait_time)

        # Print progress updates
        if hasattr(event, 'author') and hasattr(event, 'content'):
            author = event.author
            event_content = str(event.content)[:200] if event.content else ""
            if event_content:
                print(f"\n[{author}]: {event_content}...")

    # Get final results from session state
    final_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=sid
    )

    print("\n" + "=" * 60)
    print("Design Flow Complete")
    print("=" * 60)

    # Print API call summary
    print(f"\n--- API Call Summary ---")
    print(f"Total API calls: {api_call_count}")
    for agent, count in sorted(api_calls_by_agent.items()):
        print(f"  {agent}: {count} calls")
    print("-" * 25)

    # Print summary
    state = final_session.state

    if "architect_output" in state:
        print("\n[Architect] Specification parsed successfully")

    if "entity_output" in state:
        print("[Entity] Module interfaces generated")

    if "rtl_output" in state:
        print("[RTL] Implementation complete")

    if "dv_output" in state:
        print("[DV] Testbenches generated")

    if "verify_output" in state:
        print("[Verify] Simulation completed")
        try:
            import json
            verify = state["verify_output"]
            if isinstance(verify, str):
                verify = json.loads(verify)
            status = verify.get("verification_status", "Unknown")
            print(f"         Status: {status}")
        except:
            pass

    if "synthesis_output" in state:
        print("[Synthesis] Configuration generated")

    return state


def main():
    """Main entry point."""
    import sys

    print("=" * 60)
    print("Generic Multi-Agent Chip Design System")
    print("Powered by Google ADK")
    print("=" * 60)

    # Optional: custom spec path from command line
    spec_path = None
    if len(sys.argv) > 1:
        spec_path = Path(sys.argv[1])
        print(f"Using specification: {spec_path}")

    try:
        result = asyncio.run(run_design_flow(spec_path=spec_path))
        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)
        print("\nOutput files are in: output/")
        print("  - RTL:       output/rtl/")
        print("  - Testbench: output/tb/")
        print("  - Simulation: output/sim/")
        print("  - Synthesis: output/synth/")
        return 0
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please create a design_spec.txt file with your design specification.")
        return 1
    except Exception as e:
        print(f"\nPipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
