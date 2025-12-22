# Generic Chip Design Multi-Agent System - Implementation Plan

## Overview

Build a **general-purpose** multi-agent chip design system using **Google ADK** that takes **any digital design specification** (SPI, FIFO, CRC, CPU, etc.) and produces **PPA-optimized** synthesis-ready RTL.

**Tools**: Google ADK, Icarus Verilog, Sky130 PDK, OpenLane

---

## Architecture

```
design_spec.txt (any design)
       │
       ▼
┌─────────────────┐
│ Architect Agent │ → Structured JSON spec (generic)
└────────┬────────┘
         │
         ▼ architect_output
┌─────────────────┐
│  Entity Agent   │ → Verilog module interfaces
└────────┬────────┘
         │
         │ entity_output
         │
         ├───────────────────────────┐
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│    RTL Agent    │         │    DV Agent     │  (ParallelAgent)
│                 │         │                 │
│ Inputs:         │         │ Inputs:         │
│ • architect_out │         │ • architect_out │
│ • entity_output │         │ • entity_output │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │ rtl_output                │ dv_output
         │                           │
         └─────────────┬─────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Verify Agent   │ → Run iverilog simulation
              └────────┬────────┘
                       │
                       ▼ verify_output
              ┌─────────────────┐
              │ Synthesis Agent │ → OpenLane config for Sky130
              └────────┬────────┘
                       │
                       ▼ synthesis_output
              ┌─────────────────┐
              │   PPA Config    │ → Power/Performance/Area optimized
              └─────────────────┘
```

### Data Flow Summary

```
┌──────────────┐
│ design_spec  │ (input text)
└──────┬───────┘
       │
       ▼
┌──────────────────┐     ┌──────────────────┐
│ architect_output │────▶│  entity_output   │
│ (JSON spec)      │     │ (Verilog stubs)  │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         │    ┌───────────────────┤
         │    │                   │
         ▼    ▼                   ▼
    ┌─────────────┐         ┌─────────────┐
    │ rtl_output  │         │ dv_output   │
    │ (full RTL)  │         │ (testbench) │
    └──────┬──────┘         └──────┬──────┘
           │                       │
           └───────────┬───────────┘
                       ▼
              ┌─────────────────┐
              │  verify_output  │
              │ (pass/fail)     │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │synthesis_output │
              │(OpenLane config)│
              └─────────────────┘
```

---

## Key Design Principle: Generic & PPA-Focused

The system is **design-agnostic**:
- Architect agent extracts structure from **any** natural language spec
- RTL agent implements **any** digital logic based on the structured spec
- Synthesis agent optimizes for **PPA targets** specified by user

**Example specs it can handle:**
- "8-bit SPI master with configurable clock divider"
- "Synchronous FIFO with depth 16, width 32"
- "CRC-32 calculator for Ethernet"
- "RV32I 5-stage pipeline CPU"
- "I2C slave controller"
- "UART with configurable baud rate"

---

## Project Structure

```
/Users/hari/Desktop/chipOS/chipAgent/
├── main.py                      # Main entry point & workflow orchestration
├── agents/
│   └── __init__.py
├── prompts/
│   ├── __init__.py
│   ├── architect_prompt.py      # Generic spec → JSON
│   ├── entity_prompt.py         # JSON → Verilog interfaces
│   ├── rtl_prompt.py            # Interfaces → Full RTL (any design)
│   ├── dv_prompt.py             # Interfaces → Testbenches
│   ├── verify_prompt.py         # Run simulation
│   └── synthesis_prompt.py      # Generate PPA-optimized config
├── tools/
│   ├── __init__.py
│   ├── file_tools.py            # write_file, read_file, copy_file
│   └── simulation_tools.py      # iverilog, vvp execution
├── config/
│   └── openlane_template.json   # Sky130 synthesis config template
├── output/                      # Generated artifacts
│   ├── rtl/
│   ├── tb/
│   ├── sim/
│   └── synth/
├── design_spec.txt              # User's design specification
└── requirements.txt
```

---

## Agent Definitions (Generic)

### 1. Architect Agent
- **Purpose**: Parse ANY natural language spec into structured JSON
- **Input**: Raw `design_spec.txt`
- **Output Key**: `architect_output`
- **Output Format** (Generic JSON):
```json
{
  "design_name": "spi_master",
  "design_type": "communication_interface",
  "description": "8-bit SPI master controller",
  "parameters": {
    "DATA_WIDTH": 8,
    "CLK_DIV_WIDTH": 8
  },
  "interfaces": {
    "clock_reset": ["clk", "rst_n"],
    "control": ["start", "busy", "done"],
    "data": ["tx_data", "rx_data"],
    "spi": ["sclk", "mosi", "miso", "cs_n"]
  },
  "modules": [
    {"name": "spi_master_top", "type": "top"},
    {"name": "spi_shift_reg", "type": "datapath"},
    {"name": "spi_ctrl", "type": "control"}
  ],
  "functional_requirements": [
    "Generate SPI clock from system clock",
    "Support configurable clock divider",
    "Shift out data MSB first",
    "Capture input data on rising edge"
  ],
  "timing_constraints": {
    "target_frequency_mhz": 100,
    "spi_max_frequency_mhz": 10
  },
  "ppa_targets": {
    "priority": "area",
    "max_area_um2": null,
    "max_power_mw": null,
    "min_frequency_mhz": 50
  }
}
```

### 2. Entity Agent
- **Purpose**: Generate Verilog module interfaces for ANY design
- **Input**: `{architect_output}`
- **Output Key**: `entity_output`
- **Tools**: `write_file`

### 3. RTL Agent
- **Purpose**: Implement complete RTL for ANY digital logic
- **Input**:
  - `{architect_output}` - Full spec with functional requirements, timing, PPA
  - `{entity_output}` - Module interfaces and port definitions
- **Output Key**: `rtl_output`
- **Tools**: `write_file`, `read_file`
- **Guidelines**: Synthesizable Verilog-2001, no latches, parameterized
- **Note**: Needs architect spec to understand WHAT to implement, not just interfaces

### 4. DV Agent
- **Purpose**: Generate testbenches for ANY design
- **Input**:
  - `{architect_output}` - Functional requirements (what to test)
  - `{entity_output}` - Module interfaces (ports to drive/monitor)
- **Output Key**: `dv_output`
- **Tools**: `write_file`
- **Output**: Self-checking directed tests, iverilog compatible
- **Note**: Needs architect spec to know what behaviors to verify

### 5. Verify Agent
- **Purpose**: Run simulation, report pass/fail
- **Input**: `{rtl_output}`, `{dv_output}`
- **Output Key**: `verify_output`
- **Tools**: `run_iverilog_compile`, `run_vvp_simulation`, `read_file`

### 6. Synthesis Agent (PPA-Focused)
- **Purpose**: Generate OpenLane config optimized for PPA targets
- **Input**: `{rtl_output}`, `{verify_output}`, `{architect_output}`
- **Output Key**: `synthesis_output`
- **Tools**: `write_file`, `read_file`, `copy_file`
- **PPA Optimization Strategy**:
  - **Area priority**: Higher utilization, smaller cells
  - **Performance priority**: Aggressive timing, faster cells
  - **Power priority**: Lower utilization, power-optimized cells

---

## PPA Optimization Strategy

The Synthesis Agent generates **PPA-aware** OpenLane config:

| PPA Priority | SYNTH_STRATEGY | FP_CORE_UTIL | CLOCK_PERIOD | Cell Library |
|--------------|----------------|--------------|--------------|--------------|
| Area | "AREA 0" | 60-70% | Relaxed | sky130_fd_sc_hd |
| Performance | "DELAY 0" | 40-50% | Aggressive | sky130_fd_sc_hs |
| Power | "AREA 2" | 35-45% | Moderate | sky130_fd_sc_lp |
| Balanced | "AREA 0" | 50% | Target freq | sky130_fd_sc_hd |

The config template supports PPA targets from architect output:
```json
{
    "DESIGN_NAME": "{{design_name}}",
    "VERILOG_FILES": "dir::src/*.v",
    "CLOCK_PERIOD": "{{calculated_from_target_freq}}",
    "SYNTH_STRATEGY": "{{based_on_ppa_priority}}",
    "FP_CORE_UTIL": "{{based_on_ppa_priority}}",
    "PL_TARGET_DENSITY": "{{based_on_ppa_priority}}"
}
```

---

## Workflow Composition (Google ADK)

```python
# Parallel RTL + DV generation (independent tasks)
parallel_rtl_dv = ParallelAgent(
    name="ParallelRTLAndDV",
    sub_agents=[rtl_agent, dv_agent]
)

# Main sequential pipeline
chip_design_pipeline = SequentialAgent(
    name="ChipDesignPipeline",
    sub_agents=[
        architect_agent,    # Step 1: Parse any spec
        entity_agent,       # Step 2: Create interfaces
        parallel_rtl_dv,    # Step 3: RTL + DV in parallel
        verify_agent,       # Step 4: Simulate
        synthesis_agent     # Step 5: PPA-optimized config
    ]
)
```

---

## Files Created

| File | Purpose |
|------|---------|
| `main.py` | Entry point, generic agent definitions, workflow |
| `tools/file_tools.py` | `write_file`, `read_file`, `copy_file`, `list_files` |
| `tools/simulation_tools.py` | `run_iverilog_compile`, `run_vvp_simulation` |
| `tools/__init__.py` | Tool exports |
| `prompts/architect_prompt.py` | **Generic** spec parsing prompt |
| `prompts/entity_prompt.py` | **Generic** interface generation |
| `prompts/rtl_prompt.py` | **Generic** RTL implementation |
| `prompts/dv_prompt.py` | **Generic** testbench generation |
| `prompts/verify_prompt.py` | Simulation execution |
| `prompts/synthesis_prompt.py` | **PPA-aware** synthesis config |
| `prompts/__init__.py` | Prompt exports |
| `agents/__init__.py` | Agent exports |
| `config/openlane_template.json` | Parameterized Sky130 config |
| `requirements.txt` | `google-adk>=1.0.0` |

---

## Generic Prompt Design Principles

All prompts follow these principles:

1. **No hardcoded design types** - Prompts work with any digital logic
2. **Extract from spec** - All design details come from user's spec
3. **Parameterized** - All widths, depths, etc. are parameters
4. **PPA-aware** - Consider area/power/performance tradeoffs
5. **Synthesizable** - Generate clean, synthesis-ready Verilog

Example RTL prompt excerpt:
```
You are an expert Verilog RTL designer.

Given ANY digital design specification, implement complete, synthesizable RTL.

The architect has provided a structured specification in {architect_output}.
Use this to understand:
- What modules to implement
- What interfaces they have
- What functionality is required
- What parameters to support

Generate synthesizable Verilog-2001 that:
- Is parameterized for reusability
- Has no latches (complete case/if statements)
- Uses non-blocking for sequential, blocking for combinational
- Meets the timing constraints specified
```

---

## Sample OpenLane Config (PPA-Parameterized)

```json
{
    "DESIGN_NAME": "{{design_name}}",
    "VERILOG_FILES": "dir::src/*.v",
    "CLOCK_PORT": "clk",
    "CLOCK_PERIOD": 10,

    "FP_CORE_UTIL": 50,
    "PL_TARGET_DENSITY": 0.55,

    "SYNTH_STRATEGY": "AREA 0",
    "SYNTH_BUFFERING": 1,
    "SYNTH_SIZING": 1,

    "pdk::sky130*": {
        "scl::sky130_fd_sc_hd": {
            "CLOCK_PERIOD": 10
        },
        "scl::sky130_fd_sc_hs": {
            "CLOCK_PERIOD": 8
        },
        "scl::sky130_fd_sc_lp": {
            "CLOCK_PERIOD": 15
        }
    }
}
```

---

## Usage

```bash
# Install dependencies
pip install -r requirements.txt
brew install icarus-verilog

# Set Google API key
export GOOGLE_API_KEY="your-api-key"

# Run with default spec (design_spec.txt)
python main.py

# Run with custom spec
python main.py /path/to/my_spec.txt
```

---

## Data Flow

```
Session State Keys:
┌──────────────────┬─────────────────────────────────────┐
│ Key              │ Content                             │
├──────────────────┼─────────────────────────────────────┤
│ design_spec      │ Raw specification text (input)      │
│ architect_output │ Structured JSON spec                │
│ entity_output    │ Module interfaces + file paths      │
│ rtl_output       │ RTL implementation summary          │
│ dv_output        │ Testbench summary                   │
│ verify_output    │ Simulation results (pass/fail)      │
│ synthesis_output │ OpenLane config summary             │
└──────────────────┴─────────────────────────────────────┘
```
