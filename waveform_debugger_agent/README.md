# Waveform Debugger Agent

An AI-powered RTL debug agent using Google ADK that automatically analyzes failed testbench simulations by cross-referencing VCD waveforms with netlist connectivity.

## Overview

When a hardware simulation fails, debugging typically requires manually:
1. Finding the failing signal in waveforms
2. Tracing back through the design to find the root cause
3. Cross-referencing signal values at specific times

This agent automates that process using an LLM with specialized tools for VCD parsing and netlist analysis.

## Features

- **VCD Waveform Analysis**: Query signal values at any time, find transitions, search for signals
- **Netlist Connectivity Tracing**: Find drivers, trace backward through logic, get fan-in cones
- **Cross-Reference Analysis**: Combine waveform values with netlist structure
- **Automatic Root Cause Detection**: Identifies stuck signals, timing issues, CDC problems
- **Markdown Report Generation**: Produces detailed debug reports with findings

## Installation

```bash
cd waveform_debugger_agent
pip install -r requirements.txt
```

### Configuration

Create a `.env` file with your API credentials:

```bash
GEMINI_API_KEY="your-gemini-api-key"
MODEL="gemini-2.0-flash"
```

## Usage

### Basic Command

```bash
python main.py -f "wfull never asserted. Expected wfull=1 at t=325000"
```

### With Custom Files

```bash
python main.py \
  -f "rempty stuck at 1" \
  --vcd ../Async-FIFO/fifo_wave.vcd \
  --netlist ../Async-FIFO/async_fifo_connectivity.json
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-f, --failure` | Failure description (required) | - |
| `--vcd` | Path to VCD waveform file | `../Async-FIFO/fifo_wave.vcd` |
| `--netlist` | Path to Yosys JSON netlist | `../Async-FIFO/async_fifo_connectivity.json` |

## Project Structure

```
waveform_debugger_agent/
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
├── .env                    # API keys & model config
├── agents/
│   └── debugger.py         # Agent factory with tool bindings
├── prompts/
│   └── debugger.py         # System prompt for debug workflow
├── tools/
│   ├── vcd.py              # VCD analysis tools
│   ├── vcd_parser.py       # VCD file parser
│   ├── netlist.py          # Netlist analysis tools
│   ├── netlist_graph.py    # Yosys JSON netlist parser
│   └── crossref.py         # Cross-reference tools
├── hooks/
│   └── testbench.py        # Simulation auto-trigger
└── output/
    └── reports/            # Generated debug reports
```

## Available Tools

### VCD Analysis

| Tool | Description |
|------|-------------|
| `list_signals()` | List all signals in the VCD |
| `find_signals(pattern)` | Find signals matching a pattern |
| `get_value(signal, time)` | Get signal value at specific time |
| `get_transitions(signal, start, end)` | Get all value changes in time window |

### Netlist Analysis

| Tool | Description |
|------|-------------|
| `list_modules()` | List all modules in the design |
| `find_driver(module, signal)` | Find what cell drives a signal |
| `backward_trace(module, signal, depth)` | Trace backward through driver chain |
| `get_fan_in(module, signal, depth)` | Get all signals affecting target |

### Cross-Reference

| Tool | Description |
|------|-------------|
| `debug_signal(signal, time, depth)` | Full analysis: trace + all values at time |
| `write_report(content, filename)` | Write markdown debug report |

## Agent Workflow

The agent follows an iterative debug process:

```
1. Quick Triage
   └─> Parse failure message, identify signal/time/expected value

2. Observe
   └─> Check signal states and transitions at failure time

3. Trace Root Cause
   └─> Find driver chain, cross-reference with VCD values

4. Report
   └─> Generate markdown report with findings and fixes
```

## Common Root Causes Detected

- Stuck input signal (not toggling)
- Missing or incorrect reset
- Clock domain crossing issues
- Wrong comparison logic
- Testbench timing issues (sampling too early/late)

## Programmatic Usage

```python
import asyncio
from agents.debugger import create_debug_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def debug():
    agent = create_debug_agent(
        vcd_path="path/to/sim.vcd",
        netlist_path="path/to/connectivity.json"
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="debug", session_service=session_service)
    session = await session_service.create_session(app_name="debug", user_id="cli")

    async for event in runner.run_async(
        user_id="cli",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Debug this: wfull never asserted at t=325000")]
        )
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)

asyncio.run(debug())
```

## Auto-Trigger on Simulation Failure

The agent can automatically trigger when simulations fail:

```python
from hooks.testbench import run_simulation_with_debug

result = await run_simulation_with_debug(
    vvp_file="./fifo_wave",
    vcd_path="./fifo_wave.vcd",
    netlist_path="./async_fifo_connectivity.json"
)

if not result["simulation_passed"]:
    print("Failure:", result["failure"]["failure_message"])
    print("Debug Report:", result["debug_report"])
```

Detects patterns: `$fatal`, `FAIL:`, `ERROR:`, `assertion failed:`, `Test FAILED:`

## Input File Requirements

### VCD File

Standard Value Change Dump format from simulation:

```bash
# Generate with Icarus Verilog
iverilog -o sim *.v
vvp sim  # Produces waveform.vcd
```

### Netlist JSON

Yosys JSON connectivity format:

```bash
yosys -p "read_verilog *.v; prep -top TOP_MODULE; write_json connectivity.json"
```

See [generate_connectivity.md](../Assets/generate_connectivity.md) for detailed instructions.

## Dependencies

```
google-adk>=1.0.0       # Google Agent Development Kit
google-genai>=1.0.0     # Google Generative AI API
python-dotenv>=1.0.0    # Environment variable loading
```

## Example Output

The agent generates reports in `output/reports/report.md`:

```markdown
## Debug Report: wfull Signal Analysis

### Summary
The wfull signal correctly asserts at t=325000. The testbench samples
on posedge before the flip-flop updates.

### Signal Trace
- wfull driven by $dff at wptr_full.v:42
- wfull_val (next-state logic) = 1 at t=315000
- wfull captures value at t=325000

### Root Cause
Testbench timing issue - sampling on same edge as flip-flop update.

### Recommended Fix
Sample wfull on negedge wclk or add #1 delay after posedge.
```

## License

MIT


Failure: "wfull never asserted, data overflow"

Agent should:
1. find_signals("wfull") → locate wfull
2. get_value("wfull", time_of_overflow) → sees 0 when should be 1
3. backward_trace("wptr_full", "wfull") → traces to wfull_val
4. find_driver("wptr_full", "wfull_val") → sees comparison logic
5. Identify: "wfull_val comparison missing MSB inversion"

Root cause: wptr_full.v:40 - full detection logic
