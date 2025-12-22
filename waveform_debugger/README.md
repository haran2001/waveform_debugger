# Agentic Waveform Debugger

An agentic system for debugging RTL testbench failures by cross-referencing multiple data sources.

## Overview

This system combines structural netlist analysis with behavioral simulation data to automatically trace and identify root causes of testbench failures.

## Input Sources

| Source | Format | Purpose |
|--------|--------|---------|
| `connectivity.json` | Yosys JSON netlist | Structure (what's connected) |
| `*.vcd` | Value Change Dump | Behavior (what happened) |
| `*.v` source files | Verilog RTL | Intent (what was meant) |
| `README.md` / specs | Documentation | Requirements (what should happen) |

## Debugging Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER QUERY                                   │
│         "Test Case 2 fails - wfull never asserts"                   │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: UNDERSTAND INTENT                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  README/Spec │    │  FIFO_tb.v   │    │   FIFO.v     │          │
│  │              │    │              │    │              │          │
│  │ "wfull should│    │ Test Case 2: │    │ Port: wfull  │          │
│  │  assert when │───▶│ Fill FIFO to │───▶│ output, 1-bit│          │
│  │  FIFO full"  │    │ DEPTH+3      │    │              │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                                     │
│  Agent extracts: Expected behavior = wfull HIGH after 8 writes     │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 PHASE 2: OBSERVE BEHAVIOR (VCD)                     │
│                                                                     │
│  Agent parses VCD, queries specific signals:                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Time(ns)  │ winc │ wdata │ wfull │ wptr  │ wq2_rptr │      │    │
│  │───────────┼──────┼───────┼───────┼───────┼──────────│      │    │
│  │ 280       │  1   │ 0x45  │   0   │ 00000 │  00000   │      │    │
│  │ 290       │  1   │ 0x67  │   0   │ 00001 │  00000   │      │    │
│  │ ...       │  ... │  ...  │   0   │  ...  │  00000   │ ◄── STUCK│
│  │ 390       │  1   │ 0xAB  │   0   │ 01000 │  00000   │      │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  Agent detects: wfull stays 0, wptr increments, wq2_rptr stuck     │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 3: TRACE STRUCTURE (connectivity.json)           │
│                                                                     │
│  Agent performs backward trace from wfull:                          │
│                                                                     │
│  wfull ◄── $procdff$114 (Q)                                        │
│              │                                                      │
│              ▼                                                      │
│         wfull_val ◄── $eq (Y)                                      │
│                         │                                           │
│              ┌──────────┴──────────┐                               │
│              ▼                     ▼                                │
│         wgray_next           {~wq2_rptr[4:3],                      │
│              │                 wq2_rptr[2:0]}                       │
│              ▼                     │                                │
│         (from wbin_next)           ▼                                │
│                              wq2_rptr ◄── sync_r2w.q2              │
│                                              │                      │
│                                              ▼                      │
│                                         rptr (from rptr_empty)     │
│                                                                     │
│  Agent identifies: wq2_rptr is critical input, stuck at 00000      │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 4: CROSS-REFERENCE (VCD + Structure)             │
│                                                                     │
│  Agent checks related signals in VCD:                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Signal Path                │ Value │ Status                 │   │
│  │────────────────────────────┼───────┼────────────────────────│   │
│  │ rptr (rptr_empty output)   │ 00000 │ Never increments       │   │
│  │ sync_r2w.q1                │ 00000 │ Stuck                  │   │
│  │ sync_r2w.q2 (wq2_rptr)     │ 00000 │ Stuck                  │   │
│  │ rinc                       │   0   │ ◄── DISABLED in TC2!   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Agent correlates: rinc=0 means rptr frozen, sync passes 0s        │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 5: ROOT CAUSE ANALYSIS                           │
│                                                                     │
│  Agent reads wptr_full.v:40 (from connectivity.json src attr):      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ assign wfull_val = (wgray_next ==                           │   │
│  │                     {~wq2_rptr[ADDR_SIZE:ADDR_SIZE-1],      │   │
│  │                      wq2_rptr[ADDR_SIZE-2:0]});             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Agent analyzes:                                                    │
│  - wq2_rptr = 00000 (frozen because rinc=0 in Test Case 2)         │
│  - Expected comparison: wgray_next == {~00, 000} = 11000           │
│  - wgray_next reaches 01000 but never 11000                        │
│  - FIFO wraps at 8 entries, but full needs pointer diff = DEPTH    │
│                                                                     │
│  Wait... this is CORRECT behavior! Re-check spec...                │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 6: VERIFY AGAINST SPEC                           │
│                                                                     │
│  Agent re-reads FIFO_tb.v Test Case 2:                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ // TEST CASE 2: Write data to make FIFO full                │   │
│  │ rinc = 0;        // Disable reads                           │   │
│  │ winc = 1;                                                    │   │
│  │ for (i = 0; i < DEPTH + 3; ...) // Write 11 times           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Agent checks VCD timing more carefully:                            │
│  - wptr Gray sequence: 000→001→011→010→110→111→101→100→000...     │
│  - After 8 writes, wptr wraps to 00000                             │
│  - wq2_rptr still 00000 (correct, no reads)                        │
│  - Full condition: wgray_next == 11000 when wptr=01000 (write #9)  │
│                                                                     │
│  Re-check VCD at write #8-9... Found it!                           │
│  - wfull DOES assert at t=350ns                                    │
│  - Original observation was wrong - user looked at wrong timeframe │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT REPORT                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ FINDING: Test Case 2 is PASSING                             │   │
│  │                                                              │   │
│  │ Evidence:                                                    │   │
│  │ - wfull asserts at t=350ns after 8 writes                   │   │
│  │ - Writes 9-11 are correctly blocked (wfull=1)               │   │
│  │ - Gray code pointer comparison working as designed          │   │
│  │                                                              │   │
│  │ Trace path verified:                                         │   │
│  │ wfull ← wfull_val ← $eq ← wgray_next vs ~wq2_rptr[4:3]     │   │
│  │                                                              │   │
│  │ Source reference: wptr_full.v:40                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Agent Architecture

```python
class WaveformDebugAgent:
    def __init__(self):
        self.vcd_parser = VCDParser()           # Parse simulation data
        self.netlist = NetlistGraph()            # From connectivity.json
        self.source_reader = SourceReader()      # Read *.v files
        self.spec_reader = SpecReader()          # README/docs

    def debug(self, failing_signal: str, time_range: tuple):
        # 1. Understand intent
        expected = self.spec_reader.get_expected_behavior(failing_signal)
        tb_stimulus = self.source_reader.get_testbench_logic()

        # 2. Observe behavior
        actual_values = self.vcd_parser.get_signal_trace(
            failing_signal, time_range
        )

        # 3. Trace structure (backward from output)
        fan_in_cone = self.netlist.backward_trace(failing_signal)

        # 4. Cross-reference: check all fan-in signals in VCD
        suspicious_signals = []
        for signal in fan_in_cone:
            trace = self.vcd_parser.get_signal_trace(signal, time_range)
            if self.is_anomalous(trace, expected):
                suspicious_signals.append(signal)

        # 5. Root cause: find deepest suspicious signal
        root_cause = self.find_root_cause(suspicious_signals)

        # 6. Get source context
        src_location = self.netlist.get_source_location(root_cause)
        source_code = self.source_reader.read_lines(src_location)

        return DebugReport(
            root_cause=root_cause,
            evidence=actual_values,
            source_context=source_code,
            recommendation=self.generate_fix(root_cause)
        )
```

## Required Agent Capabilities

| Capability | Input Source | Purpose |
|------------|--------------|---------|
| **VCD Parsing** | `*.vcd` | Extract signal values at specific times |
| **Graph Traversal** | `connectivity.json` | Backward/forward cone tracing |
| **Source Lookup** | `*.v` files | Read RTL at specific lines (via `src` attr) |
| **Spec Matching** | `README.md` | Compare actual vs expected behavior |
| **Temporal Reasoning** | VCD + TB | Correlate stimulus timing with responses |
| **Hypothesis Testing** | All sources | "If X is stuck, what would cause that?" |

## How connectivity.json Enables Tracing

### Structure Overview

The Yosys JSON netlist contains:

| Section | Purpose |
|---------|---------|
| `modules` | All elaborated modules (parameterized instances resolved) |
| `ports` | Module I/O with direction and bit IDs |
| `cells` | Logic primitives ($and, $xor, $adff, $mux, $mem_v2, etc.) |
| `netnames` | Signal names mapped to bit IDs |
| `connections` | Port-to-bit mappings for each cell |
| `attributes.src` | Source file location (file:line.col) |

### Backward Trace Algorithm

```python
def backward_trace(netlist, signal_name, module_name):
    """
    Find all cells that drive a given signal.
    """
    module = netlist["modules"][module_name]

    # 1. Get bit IDs for the signal
    bit_ids = module["netnames"][signal_name]["bits"]

    # 2. Find cells with outputs connected to these bits
    drivers = []
    for cell_name, cell in module["cells"].items():
        for port, direction in cell["port_directions"].items():
            if direction == "output":
                connected_bits = cell["connections"][port]
                if any(bit in bit_ids for bit in connected_bits):
                    drivers.append({
                        "cell": cell_name,
                        "type": cell["type"],
                        "port": port,
                        "src": cell["attributes"].get("src", "unknown")
                    })

    return drivers
```

### Example: Tracing wfull in wptr_full module

```
Signal: wfull
Bit ID: [2]

Driver found:
  Cell: $procdff$114
  Type: $adff (async reset D flip-flop)
  Output port: Q → [2]
  Input port: D → [43] (wfull_val)
  Source: wptr_full.v:42.5-47.8

Next trace: wfull_val (bit 43)
  Cell: $eq$Verilog_Code/wptr_full.v:40$46
  Type: $eq (equality comparator)
  Output port: Y → [43]
  Input ports: A → wgray_next, B → modified wq2_rptr
  Source: wptr_full.v:40.25-40.96
```

## VCD Processing

### Signal Value Extraction

```python
def get_signal_at_time(vcd_data, signal_path, time_ns):
    """
    Get signal value at specific simulation time.
    """
    changes = vcd_data.get_signal_changes(signal_path)

    # Find most recent change before or at time_ns
    value = None
    for change_time, change_value in changes:
        if change_time <= time_ns:
            value = change_value
        else:
            break

    return value

def get_signal_transitions(vcd_data, signal_path, start_ns, end_ns):
    """
    Get all transitions in a time window.
    """
    changes = vcd_data.get_signal_changes(signal_path)
    return [
        (t, v) for t, v in changes
        if start_ns <= t <= end_ns
    ]
```

## Cross-Reference Strategy

The key insight is correlating information across sources:

```
connectivity.json says: wfull ← comparator ← wq2_rptr
VCD shows:              wq2_rptr = 00000 (stuck)
Testbench shows:        rinc = 0 during Test Case 2
RTL shows:              rptr only increments when rinc && !rempty

∴ Conclusion: wq2_rptr stuck is EXPECTED (not a bug)
```

## Limitations

| Gap | Description |
|-----|-------------|
| **No timing analysis** | Setup/hold violations not detectable |
| **No formal properties** | Assertions not captured in netlist |
| **Testbench not synthesized** | TB logic requires source parsing |
| **X-propagation differences** | Simulation vs silicon behavior may differ |

## Generating connectivity.json

```bash
yosys -p "read_verilog -sv Verilog_Code/*.v; prep -top FIFO; write_json connectivity.json"
```

## File Structure

```
Async_FIFO_Design/
├── connectivity.json          # Yosys netlist output
├── Verilog_Code/
│   ├── FIFO.v                # Top module
│   ├── FIFO_memory.v         # Dual-port RAM
│   ├── two_ff_sync.v         # 2-FF synchronizer
│   ├── rptr_empty.v          # Read pointer + empty flag
│   ├── wptr_full.v           # Write pointer + full flag
│   ├── FIFO_tb.v             # Testbench
│   └── fifo_wave.vcd         # Simulation waveform
└── waveform_debugger/
    └── README.md             # This file
```
