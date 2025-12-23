"""Debug agent using Google ADK."""
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from prompts.debugger import DEBUG_AGENT_PROMPT
from tools import vcd, netlist, crossref
from dotenv import load_dotenv
import os

load_dotenv()

MODEL=os.getenv("MODEL")

def create_debug_agent(vcd_path: str, netlist_path: str) -> Agent:
    """Create debug agent with tools bound to specific files."""

    # Initialize tools with file paths
    vcd.load_vcd(vcd_path)
    netlist.load_netlist(netlist_path)

    # Wrap functions as FunctionTools
    function_tools = [
        # VCD tools
        FunctionTool(vcd.list_signals),
        FunctionTool(vcd.find_signals),
        FunctionTool(vcd.get_value),
        FunctionTool(vcd.get_transitions),
        # Netlist tools
        FunctionTool(netlist.list_modules),
        FunctionTool(netlist.find_driver),
        FunctionTool(netlist.backward_trace),
        FunctionTool(netlist.get_fan_in),
        # Cross-reference tools
        FunctionTool(crossref.debug_signal),
        FunctionTool(crossref.write_report),
    ]

    return Agent(
        name="waveform_debugger",
        model=MODEL,
        instruction=DEBUG_AGENT_PROMPT,
        tools=function_tools,
    )
