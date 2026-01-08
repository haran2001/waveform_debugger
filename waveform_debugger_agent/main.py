"""Entry point for debug agent."""
import asyncio
import argparse
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.debugger import create_debug_agent


async def debug_failure(
    failure_description: str,
    vcd_path: str,
    netlist_path: str
) -> str:
    """Run debug agent on a failure."""

    agent = create_debug_agent(vcd_path, netlist_path)
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="debug", session_service=session_service)

    session = await session_service.create_session(app_name="debug", user_id="cli")

    final_response = ""
    async for event in runner.run_async(
        user_id="cli",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=failure_description)]
        )
    ):
        if event.is_final_response():
            final_response = event.content.parts[0].text

    return final_response


def main():
    parser = argparse.ArgumentParser(
        description="Debug failed testbenches using AI agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -f "wfull never asserted. Expected wfull=1 at t=325000"
  python main.py -f "rempty stuck at 1" --vcd ../Async-FIFO/fifo_wave.vcd
        """
    )
    parser.add_argument("--failure", "-f", type=str, required=True,
                        help="Failure description or message")
    parser.add_argument("--vcd", type=str,
                        default="../Async-FIFO/fifo_wave_bug.vcd",
                        help="Path to VCD file")
    parser.add_argument("--netlist", type=str,
                        default="../Async-FIFO/async_fifo_connectivity.json",
                        help="Path to async_fifo_connectivity.json")

    args = parser.parse_args()

    # Resolve paths relative to script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vcd_path = os.path.join(script_dir, args.vcd) if not os.path.isabs(args.vcd) else args.vcd
    netlist_path = os.path.join(script_dir, args.netlist) if not os.path.isabs(args.netlist) else args.netlist

    # Check files exist
    if not os.path.exists(vcd_path):
        print(f"Error: VCD file not found: {vcd_path}")
        sys.exit(1)
    if not os.path.exists(netlist_path):
        print(f"Error: Netlist file not found: {netlist_path}")
        sys.exit(1)

    print(f"Loading VCD: {vcd_path}")
    print(f"Loading netlist: {netlist_path}")
    print(f"\nDebugging: {args.failure}\n")
    print("-" * 60)

    result = asyncio.run(debug_failure(args.failure, vcd_path, netlist_path))
    print(result)


if __name__ == "__main__":
    main()
