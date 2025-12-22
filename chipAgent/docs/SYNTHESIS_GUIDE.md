# Complete OpenLane Synthesis Guide for chipAgent

This document provides a comprehensive explanation of the RTL-to-GDSII synthesis flow using OpenLane with the Sky130 PDK.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites & Setup](#prerequisites--setup)
3. [Design Input Files](#design-input-files)
4. [OpenLane Configuration](#openlane-configuration)
5. [Synthesis Flow Steps](#synthesis-flow-steps)
6. [Output Files & Results](#output-files--results)
7. [Key Metrics Explained](#key-metrics-explained)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What is OpenLane?

OpenLane is an automated RTL-to-GDSII flow developed by Efabless. It integrates multiple open-source EDA tools to perform:

- **Synthesis** (Yosys) - RTL to gate-level netlist
- **Floorplanning** (OpenROAD) - Die/core area planning
- **Placement** (OpenROAD) - Cell placement optimization
- **Clock Tree Synthesis** (TritonCTS) - Clock distribution network
- **Routing** (TritonRoute) - Metal interconnect routing
- **Signoff** (Magic, Netgen) - DRC, LVS, parasitic extraction

### What is Sky130 PDK?

Sky130 is an open-source 130nm Process Design Kit from SkyWater Technology, containing:
- Standard cell libraries (sky130_fd_sc_hd, sky130_fd_sc_hs, sky130_fd_sc_lp)
- I/O cells
- SRAM macros
- Design rules and technology files

---

## Prerequisites & Setup

### 1. Install Docker

OpenLane runs inside a Docker container. Install Docker Desktop:

```bash
# macOS
brew install --cask docker

# Linux
sudo apt-get install docker.io
sudo usermod -aG docker $USER
```

### 2. Pull OpenLane Docker Image

```bash
docker pull ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69
```

### 3. Install Sky130 PDK using Volare

Volare is a PDK version manager:

```bash
# Install volare
pip install volare

# Install the compatible Sky130 PDK version
volare enable --pdk sky130 --pdk-root ~/pdk 0fe599b2afb6708d281543108caf8310912f54af

# Set environment variable (add to ~/.zshrc or ~/.bashrc)
export PDK_ROOT=~/pdk
```

**Important**: The PDK version must match the OpenLane version. The version `0fe599b2afb6708d281543108caf8310912f54af` is compatible with OpenLane `ff5509f65b17bfa4068d5336495ab1718987ff69`.

### 4. Verify Installation

```bash
# Check Docker image
docker images | grep openlane

# Check PDK installation
ls ~/pdk/sky130A
```

---

## Design Input Files

### Directory Structure

```
output/synth/
├── config.json          # OpenLane configuration
├── pin_order.cfg        # Pin placement constraints
└── src/
    └── sync_fifo.v      # RTL source files
```

### RTL Source (sync_fifo.v)

The input Verilog design - a synchronous FIFO:

```verilog
module sync_fifo #(
    parameter DATA_WIDTH = 32,
    parameter FIFO_DEPTH = 16
)(
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     wr_en,
    input  wire [DATA_WIDTH-1:0]    din,
    output reg                      full,
    input  wire                     rd_en,
    output reg  [DATA_WIDTH-1:0]    dout,
    output reg                      empty
);
    // ... implementation
endmodule
```

**Design Characteristics**:
- 32-bit data width
- 16-entry depth
- Asynchronous active-low reset
- Separate read/write interfaces

---

## OpenLane Configuration

### config.json

```json
{
    "DESIGN_NAME": "sync_fifo",
    "VERILOG_FILES": "dir::src/*.v",
    "CLOCK_PORT": "clk",
    "CLOCK_PERIOD": 10.0,

    "FP_CORE_UTIL": 50,
    "PL_TARGET_DENSITY": 0.55,

    "FP_PDN_VOFFSET": 7,
    "FP_PDN_HOFFSET": 7,
    "FP_PDN_SKIPTRIM": true,

    "FP_PIN_ORDER_CFG": "dir::pin_order.cfg",

    "SYNTH_STRATEGY": "AREA 0",
    "SYNTH_BUFFERING": 1,
    "SYNTH_SIZING": 1,
    "SYNTH_READ_BLACKBOX_LIB": 1,

    "PL_RESIZER_DESIGN_OPTIMIZATIONS": 1,
    "PL_RESIZER_TIMING_OPTIMIZATIONS": 1,
    "GLB_RESIZER_DESIGN_OPTIMIZATIONS": 1,
    "GLB_RESIZER_TIMING_OPTIMIZATIONS": 1,

    "ROUTING_CORES": 4,

    "RUN_KLAYOUT_XOR": false,
    "RUN_KLAYOUT_DRC": false,

    "pdk::sky130*": {
        "MAX_FANOUT_CONSTRAINT": 6,
        "scl::sky130_fd_sc_hd": {
            "CLOCK_PERIOD": 10.0
        }
    }
}
```

### Configuration Parameters Explained

| Parameter | Value | Description |
|-----------|-------|-------------|
| `DESIGN_NAME` | sync_fifo | Top module name |
| `CLOCK_PORT` | clk | Clock signal name |
| `CLOCK_PERIOD` | 10.0 ns | Target clock period (100 MHz) |
| `FP_CORE_UTIL` | 50% | Core utilization target |
| `PL_TARGET_DENSITY` | 0.55 | Placement density |
| `SYNTH_STRATEGY` | AREA 0 | Optimize for area |
| `ROUTING_CORES` | 4 | Parallel routing threads |

### Synthesis Strategy Options

| Strategy | Focus | Use Case |
|----------|-------|----------|
| `AREA 0` | Minimum area | Area-constrained designs |
| `AREA 1-3` | Area with timing | Balanced designs |
| `DELAY 0-4` | Minimum delay | Performance-critical designs |

---

## Synthesis Flow Steps

### Step 1: Linting (Verilator)

Checks RTL for syntax errors and warnings.

```
[INFO]: Running linter (Verilator)
[INFO]: 0 errors found by linter
[INFO]: 0 warnings found by linter
```

### Step 2: Synthesis (Yosys)

Converts RTL to gate-level netlist using Sky130 standard cells.

**Process**:
1. Parse Verilog → Abstract Syntax Tree
2. Elaborate → RTL representation
3. Optimize → Logic minimization
4. Technology mapping → Map to Sky130 cells

**Results**:
```
=== sync_fifo ===
   Number of cells:               2300
     sky130_fd_sc_hd__dfxtp_2      512   (D flip-flops)
     sky130_fd_sc_hd__mux2_2       512   (2:1 MUX for memory)
     sky130_fd_sc_hd__buf_1        810   (Buffers)
     sky130_fd_sc_hd__a22o_2       193   (AND-OR gates)
     sky130_fd_sc_hd__dfrtp_2       42   (Reset flip-flops)

   Chip area for module: 25184.15 µm²
```

### Step 3: Static Timing Analysis (OpenSTA)

Verifies timing constraints are met post-synthesis.

### Step 4: Floorplanning (OpenROAD)

Determines die area and core placement region.

```
[INFO]: Floorplanned with width 224.02 µm and height 223.04 µm
Die area: (0, 0) to (235.47, 246.19) µm
```

### Step 5: IO Placement

Places input/output pins on the die boundary according to `pin_order.cfg`.

### Step 6: Tap/Decap Insertion

Inserts:
- **Tap cells**: Provide substrate/well connections
- **Decap cells**: Power supply decoupling capacitors

### Step 7: Power Distribution Network (PDN)

Creates power (VPWR) and ground (VGND) routing grid.

### Step 8: Global Placement

Initial cell placement optimizing wire length.

### Step 9: Placement Optimization

Resizes cells and inserts buffers to meet timing.

### Step 10: Detailed Placement

Legalizes placement to manufacturing grid.

### Step 11: Clock Tree Synthesis (TritonCTS)

Builds balanced clock distribution network.

```
[INFO CTS-0010] Clock net "clk" has 554 sinks
[INFO CTS-0018] Created 57 clock buffers
[INFO CTS-0012] Minimum buffers in clock path: 3
[INFO CTS-0013] Maximum buffers in clock path: 3
```

**CTS creates**:
- H-tree topology for clock distribution
- Clock buffers to balance skew
- Equal path depth to all registers

### Step 12-18: Routing Optimization

Multiple iterations of:
- Global routing
- Timing optimization
- Design rule fixing

### Step 19: Global Routing (FastRoute)

Creates routing topology without detailed tracks.

### Step 20-23: Detailed Routing (TritonRoute)

Final metal layer routing.

```
Design:                   sync_fifo
Die area:                 (0, 0) to (235470, 246190) dbu
Number of components:     6647
Number of nets:           3035
```

**Metal Layer Usage**:
| Layer | Usage |
|-------|-------|
| li1 (local interconnect) | 111,329 shapes |
| met1 | 21,556 shapes |
| met2 | 502 shapes |
| met3 | 564 shapes |
| met4 | 182 shapes |
| met5 | 16 shapes |

### Step 24: Wire Length Check

Verifies no excessively long wires.

### Step 25-31: Parasitic Extraction & STA

Extracts RC parasitics (SPEF) and runs final timing analysis at:
- Slow corner (worst-case delay)
- Typical corner
- Fast corner (hold time check)

### Step 32: IR Drop Analysis

Analyzes voltage drop across power grid.

### Step 33-35: GDSII Generation (Magic)

Streams out final layout in GDSII format.

### Step 36-37: Powered Verilog

Generates Verilog netlist with power pins.

### Step 38: Layout vs. Schematic (LVS)

Verifies layout matches schematic (netlist).

```
LVS Summary:
Number of nets: 3037
Design is LVS clean.
```

### Step 39: Design Rule Check (DRC)

Verifies layout meets manufacturing rules.

```
Magic DRC Summary:
Total Magic DRC violations is 0
```

### Step 40-41: Antenna & ERC Checks

Final electrical rule checks.

---

## Output Files & Results

### Final Outputs Location

```
output/synth/runs/test_run/results/final/
├── gds/
│   └── sync_fifo.gds       # GDSII layout (tapeout file)
├── lef/
│   └── sync_fifo.lef       # Library Exchange Format
├── def/
│   └── sync_fifo.def       # Design Exchange Format
├── verilog/
│   ├── sync_fifo.v         # Gate-level netlist
│   └── sync_fifo.pnl.v     # Powered netlist
├── sdf/
│   └── sync_fifo.sdf       # Timing delays
├── spef/
│   └── sync_fifo.spef      # Parasitic data
├── spi/
│   └── sync_fifo.spi       # SPICE netlist
└── lib/
    └── sync_fifo.lib       # Timing library
```

### Key Reports

```
output/synth/runs/test_run/reports/
├── manufacturability.rpt   # DRC/LVS summary
├── metrics.csv             # All design metrics
└── signoff/
    └── 31-rcx_sta.rpt      # Final timing report
```

---

## Key Metrics Explained

### Final Metrics (from metrics.csv)

| Metric | Value | Description |
|--------|-------|-------------|
| **Die Area** | 0.058 mm² | Total chip area |
| **Core Area** | 49,965 µm² | Usable cell area |
| **Cell Count** | 2,300 (synth) / 6,647 (final) | Gates + physical cells |
| **Core Utilization** | 51.97% | Cell area / Core area |
| **Wire Length** | 76,424 µm | Total routing length |
| **Vias** | 18,338 | Layer-to-layer connections |
| **WNS** | 0.0 ns | Worst Negative Slack (timing met!) |
| **TNS** | 0.0 ns | Total Negative Slack |
| **Power** | 11.31 µW | Total power (typical corner) |

### Cell Breakdown

| Cell Type | Count | Purpose |
|-----------|-------|---------|
| Flip-flops (dfxtp) | 512 | Data storage (32×16 FIFO) |
| Reset FFs (dfrtp) | 42 | Pointer/control registers |
| MUX (mux2) | 512 | Memory read selection |
| Buffers (buf) | 810 | Signal buffering |
| Logic gates | ~400 | Combinational logic |
| Tap cells | 714 | Well connections |
| Fill cells | 1,113 | Gap filling |
| Decap cells | 1,818 | Decoupling capacitors |

### Physical Cells Added

| Cell Type | Count | Purpose |
|-----------|-------|---------|
| `sky130_ef_sc_hd__decap_12` | 1,818 | Decoupling capacitors |
| `sky130_fd_sc_hd__tapvpwrvgnd_1` | 714 | Substrate/well taps |
| `sky130_fd_sc_hd__fill_1/2` | 1,113 | Fill empty spaces |
| Clock buffers | 57 | Clock tree buffers |

---

## Troubleshooting

### Common Issues

#### 1. PDK Version Mismatch

```
[ERROR]: The version of open_pdks used in building the PDK does not match
```

**Solution**: Install the correct PDK version:
```bash
volare enable --pdk sky130 --pdk-root ~/pdk 0fe599b2afb6708d281543108caf8310912f54af
```

#### 2. PDK Not Found

```
[ERROR]: PDK is not specified
```

**Solution**: Set PDK_ROOT and mount correctly:
```bash
export PDK_ROOT=~/pdk
```

#### 3. Timing Violations

```
[WARNING]: There are setup violations in the design
```

**Solutions**:
- Increase `CLOCK_PERIOD`
- Change `SYNTH_STRATEGY` to `DELAY 0`
- Enable more optimization passes

#### 4. DRC Violations

**Solutions**:
- Reduce `FP_CORE_UTIL`
- Enable `RUN_KLAYOUT_DRC` for detailed checks
- Check antenna violations

#### 5. LVS Errors

**Common causes**:
- Floating pins
- Missing power connections
- Short circuits

---

## Running Synthesis

### Manual Docker Command

```bash
docker run --rm \
  -v /path/to/design:/openlane/designs/sync_fifo \
  -v ~/pdk:/build/pdk \
  -e PDK=sky130A \
  ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69 \
  flow.tcl -design /openlane/designs/sync_fifo -tag run
```

### Using chipAgent

```bash
# Set up environment
echo "PDK_ROOT=/Users/$USER/pdk" >> .env

# Run the full pipeline
python main.py
```

The synthesis agent will automatically:
1. Generate config.json
2. Create pin_order.cfg
3. Copy RTL files
4. Execute OpenLane
5. Report results

---

## Summary

The complete RTL-to-GDSII flow for the sync_fifo design:

1. **Input**: 100-line Verilog RTL
2. **Synthesis**: 2,300 standard cells
3. **Physical Design**: 6,647 total cells (including physical)
4. **Area**: 0.058 mm² die, 51.97% utilization
5. **Timing**: Met at 100 MHz (10 ns period)
6. **Quality**: 0 DRC violations, LVS clean
7. **Output**: Tapeout-ready GDSII

The design is ready for fabrication at SkyWater's 130nm foundry!
