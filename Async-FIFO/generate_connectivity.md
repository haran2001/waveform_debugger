# Generating connectivity.json with Yosys

## Prerequisites

Install Yosys (open-source synthesis tool):

```bash
# macOS
brew install yosys

# Ubuntu/Debian
sudo apt install yosys

# From source
git clone https://github.com/YosysHQ/yosys.git
cd yosys && make && sudo make install
```

## Basic Command

```bash
yosys -p "read_verilog Verilog_Code/*.v; prep -top FIFO; write_json connectivity.json"
yosys -p "read_verilog Async-FIFO/*.v; prep -top FIFO; write_json async_fifo_connectivity.json"
```

## Step-by-Step Breakdown

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `read_verilog Verilog_Code/*.v` | Load all Verilog source files |
| 2 | `prep -top FIFO` | Elaborate design with FIFO as top module |
| 3 | `write_json connectivity.json` | Export netlist to JSON format |

## Interactive Mode

For more control, run Yosys interactively:

```bash
yosys
```

Then execute commands one by one:

```tcl
# Read Verilog files
read_verilog Verilog_Code/FIFO.v
read_verilog Verilog_Code/FIFO_memory.v
read_verilog Verilog_Code/rptr_empty.v
read_verilog Verilog_Code/wptr_full.v
read_verilog Verilog_Code/two_ff_sync.v

# Elaborate and prepare
prep -top FIFO

# Optional: view hierarchy
hierarchy -check

# Export to JSON
write_json connectivity.json
```

## Output Structure

The generated JSON contains:

```json
{
  "creator": "Yosys 0.60",
  "modules": {
    "FIFO": {
      "ports": { ... },      // I/O ports with directions
      "cells": { ... },      // Instantiated submodules
      "netnames": { ... }    // Internal signals
    },
    "FIFO_memory": { ... },
    "rptr_empty": { ... },
    "wptr_full": { ... },
    "two_ff_sync": { ... }
  }
}
```

## Key Fields

- **ports**: Module I/O with `direction` (input/output) and `bits` (wire indices)
- **cells**: Submodule instances with `type`, `port_directions`, and `connections`
- **netnames**: Signal names mapped to bit indices, with `src` pointing to Verilog source location

## Troubleshooting

### Missing modules
Ensure all required files are included in `read_verilog`.

### Wrong top module
Specify the correct top with `-top <module_name>`.

### Syntax errors
Run `read_verilog -sv` for SystemVerilog syntax support.

---

# Running Async-FIFO Testbench

## Available Testbenches

| File | Purpose |
|------|---------|
| `FIFO_tb.v` | Basic functional tests |
| `FIFO_tb_wave.v` | Tests with VCD waveform output |

## Using Icarus Verilog (iverilog)

### Compile and run with VCD output

```bash
cd /Users/hari/Desktop/waveform_debugger/Async-FIFO

# Compile all Verilog files with the waveform testbench
iverilog -o fifo_wave FIFO.v FIFO_memory.v rptr_empty.v wptr_full.v two_ff_sync.v FIFO_tb_wave.v

# Run simulation (generates fifo_wave.vcd)
vvp fifo_wave
```

### View waveforms (optional)

```bash
# Using GTKWave
gtkwave fifo_wave.vcd
```

### Using the Basic Testbench

```bash
# Compile with basic testbench
iverilog -o fifo_test FIFO.v FIFO_memory.v rptr_empty.v wptr_full.v two_ff_sync.v FIFO_tb.v

# Run
vvp fifo_test
```

## What the Waveform Testbench Does

| Test | Description |
|------|-------------|
| **TEST 1** | Write 10 random values while simultaneously reading (`rinc=1`) |
| **TEST 2** | Fill the FIFO (write DEPTH+3 values with `winc=1`, `rinc=0`) - triggers `wfull` |
| **TEST 3** | Empty the FIFO (read DEPTH+3 times with `rinc=1`, `winc=0`) - triggers `rempty` |

## Quick Run (Pre-compiled)

If binaries already exist:

```bash
vvp /Users/hari/Desktop/waveform_debugger/Async-FIFO/fifo_wave
```
