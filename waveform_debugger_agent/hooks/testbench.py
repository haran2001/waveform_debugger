"""Hook to auto-trigger debug agent on simulation failure."""
import subprocess
import re
import os

from google.genai import types


def parse_simulation_output(output: str) -> dict | None:
    """Parse simulation output for failure info."""

    # Match common failure patterns
    patterns = [
        r'\$fatal.*?:(.*)',           # $fatal messages
        r'FAIL.*?:(.*)',              # FAIL: messages
        r'ERROR.*?:(.*)',             # ERROR: messages
        r'assertion failed.*?:(.*)',  # assertion failures
        r'Test FAILED:(.*)',          # Test FAILED:
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return {
                "failure_message": match.group(1).strip(),
                "full_output": output
            }

    return None


def extract_time_from_output(output: str) -> int | None:
    """Extract simulation time from output."""
    # Match patterns like "time=325000" or "@ 325000" or "t=325000"
    match = re.search(r'(?:time=|@ |t=)(\d+)', output)
    if match:
        return int(match.group(1))
    return None


async def run_simulation_with_debug(
    vvp_file: str,
    vcd_path: str,
    netlist_path: str,
    auto_debug: bool = True
) -> dict:
    """Run simulation and auto-trigger debug on failure."""

    # Run VVP simulation
    result = subprocess.run(
        ['vvp', vvp_file],
        capture_output=True,
        text=True,
        timeout=60
    )

    output = result.stdout + result.stderr
    failure = parse_simulation_output(output)

    if failure and auto_debug:
        from agents.debugger import create_debug_agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        # Create and run debug agent
        agent = create_debug_agent(vcd_path, netlist_path)
        session_service = InMemorySessionService()
        runner = Runner(agent=agent, app_name="debug", session_service=session_service)

        session = await session_service.create_session(app_name="debug", user_id="auto")

        # Build failure context
        time = extract_time_from_output(output)
        failure_msg = failure["failure_message"]
        if time:
            failure_msg += f"\nSimulation time: {time}"

        # Run debug agent
        async for event in runner.run_async(
            user_id="auto",
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=f"Debug this failure:\n{failure_msg}")]
            )
        ):
            if event.is_final_response():
                return {
                    "simulation_passed": False,
                    "failure": failure,
                    "debug_report": event.content.parts[0].text
                }

    return {
        "simulation_passed": failure is None,
        "output": output
    }
