# Simple Plan: Waveform Debugger Prototype

## Goal
Build a minimal Python prototype that uses ONLY:
1. `connectivity.json` (Yosys netlist) → structural backward tracing
2. `fifo_wave.vcd` → behavioral signal values

Given a signal name and time, trace backward to show values of all signals in the fan-in cone.

---

## File Structure

```
waveform_debugger/
├── vcd_parser.py      # VCD parsing and signal value extraction
├── netlist_graph.py   # connectivity.json parsing and backward tracing
└── debugger.py        # Main CLI + cross-reference logic
```

---

## 1. vcd_parser.py

**Purpose:** Parse VCD file, extract signal values at specific times

```python
class VCDSignal:      # id, name, width, path
class ValueChange:    # time, value
class VCDParser:
    def parse(vcd_path)
    def get_value_at_time(signal_name, time) → str
    def get_transitions(signal_name, start, end) → List[ValueChange]
    def list_signals() → List[str]
```

**Algorithm:**
1. Parse header: `$scope`/`$upscope` for hierarchy, `$var` for signal defs
2. Parse values: `#timestamp`, `0!`/`1!` (scalar), `b1010 X` (vector)
3. Query: find last change <= query time

---

## 2. netlist_graph.py

**Purpose:** Parse connectivity.json, build driver graph, backward trace

```python
class CellInfo:       # name, type, ports, connections, src
class SignalInfo:     # name, bits, is_port, direction
class TraceNode:      # signal, driver_cell, driver_type, inputs, src
class NetlistGraph:
    def load(json_path)
    def find_driver(module, signal) → TraceNode
    def backward_trace(module, signal, depth) → List[TraceNode]
    def get_fan_in_signals(module, signal, depth) → List[str]
```

**Key data structures:**
- `bit_to_signal[module][bit_id]` → signal name
- `bit_to_driver[module][bit_id]` → CellInfo

**Algorithm:**
1. Load JSON, process ports/netnames/cells
2. Build bit_to_driver map from output ports
3. BFS: signal → driver → input ports → input signals → repeat

---

## 3. debugger.py

**Purpose:** Main CLI, cross-reference VCD with netlist

```python
class WaveformDebugger:
    def __init__(vcd_path, netlist_path)
    def debug_signal(signal, time, module, depth) → DebugReport
    def trace_transitions(signal, start, end)
    def list_available_signals()
```

**CLI:**
```bash
python debugger.py --signal wfull --time 325000
python debugger.py --list-signals
python debugger.py --signal wfull --start 300000 --end 400000 --transitions
```

---

## Cross-Reference Algorithm

```
1. vcd.get_value_at_time(signal, time)     → target value
2. netlist.backward_trace(module, signal)   → trace path
3. Collect all fan-in signal names
4. For each: vcd.get_value_at_time(sig, time)
5. Output: target + fan-in values + trace path
```

---

## Example Output

```
$ python debugger.py --signal wfull --time 325000

=== Debugging 'wfull' at time 325000 ===

Target: wfull = 1

Backward trace:
  wfull <- $adff (wptr_full.v:42)
  wfull_val <- $eq (wptr_full.v:40)
  wgray_next <- $xor (wptr_full.v:31)

Fan-in values:
  wfull         = 1
  wfull_val     = 1
  wgray_next    = b1000
  wq2_rptr      = b100
  winc          = 1
```

---

## Excluded (keep simple)

- No source file reader
- No GUI
- No cross-module tracing
- No AI/LLM
- No unit tests (yet)
