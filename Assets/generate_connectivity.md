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
