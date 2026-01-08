# RTL Block Diagram Generator

An MCP server for generating interactive, hierarchical block diagrams from large RTL designs.

## Problem Statement

Generate high-level block diagrams for large RTL designs (like the 61-file, 54-module SparseAccelerator) that:
- Abstract away language-specific details (Verilog/VHDL/SystemVerilog)
- Show hardware components (registers, muxes, ALUs, memories) at a readable level
- Allow RTL engineers to quickly understand design architecture
- Scale to thousands of lines of code

## Solution: Agent + Memory System

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RTL Diagram Generator                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Phase 1    │───▶│   Phase 2    │───▶│   Phase 3    │       │
│  │  Discovery   │    │   Analysis   │    │  Rendering   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ File Scanner │    │  LLM Agent   │    │ DOT Generator│       │
│  │ + Hierarchy  │    │  (Claude)    │    │ + Viz.js HTML│       │
│  │   Builder    │    │              │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              Intermediate JSON Schema               │        │
│  │                  (Persistent Memory)                │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Discovery (Deterministic)

**Goal**: Build initial file/module inventory without LLM

### Steps:
1. Scan directory for `*.v`, `*.sv`, `*.vhd` files
2. Extract module names using regex patterns
3. Build preliminary hierarchy from instantiation patterns
4. Calculate file sizes and complexity metrics

### Output: `discovery.json`
```json
{
  "project": "mx_accelerator",
  "files": [
    {"path": "vegeta_tpu_top.sv", "lines": 93, "modules": ["vegeta_tpu_top"]}
  ],
  "module_count": 54,
  "total_lines": 7902
}
```

---

## Phase 2: Analysis (LLM Agent + Iterative Memory)

**Goal**: Deep understanding of each module's hardware implementation

### Iteration Strategy:
```
For each module (or batch of related modules):
  1. Read RTL source
  2. Prompt LLM to extract hardware components
  3. Update intermediate JSON
  4. Validate consistency with already-analyzed modules
```

### Intermediate Data Structure: `rtl_model.json`

```json
{
  "version": "1.0",
  "project": "mx_accelerator",
  "generated_at": "2025-01-15T10:30:00Z",

  "modules": {
    "vegeta_tpu_top": {
      "file": "VEGETA_TPU/vegeta/vegeta_tpu_top.sv",
      "type": "top",
      "description": "Top-level TPU wrapper with instruction FIFO",

      "ports": {
        "inputs": [
          {"name": "clk", "width": 1, "type": "clock"},
          {"name": "rst_n", "width": 1, "type": "reset"},
          {"name": "instruction", "width": 64, "type": "data"}
        ],
        "outputs": [
          {"name": "done", "width": 1, "type": "control"},
          {"name": "result", "width": 256, "type": "data"}
        ]
      },

      "components": [
        {
          "id": "inst_fifo",
          "type": "fifo",
          "module": "instruction_fifo",
          "params": {"DEPTH": 16, "WIDTH": 64},
          "position_hint": "input_stage"
        },
        {
          "id": "tpu_core",
          "type": "submodule",
          "module": "vegeta_tpu_core",
          "position_hint": "center"
        },
        {
          "id": "runtime_counter",
          "type": "counter",
          "width": 32,
          "position_hint": "auxiliary"
        }
      ],

      "connections": [
        {"from": "instruction", "to": "inst_fifo.din", "type": "data"},
        {"from": "inst_fifo.dout", "to": "tpu_core.instruction", "type": "data"},
        {"from": "tpu_core.done", "to": "done", "type": "control"}
      ],

      "internal_signals": [
        {"name": "fifo_empty", "width": 1, "type": "control"},
        {"name": "fifo_full", "width": 1, "type": "control"}
      ]
    },

    "vegeta_mac": {
      "file": "accelerator/compute/vegeta_mac.sv",
      "type": "leaf",
      "description": "Multiply-accumulate unit for BFloat16",

      "components": [
        {"id": "multiplier", "type": "multiplier", "precision": "bfp16"},
        {"id": "accumulator", "type": "adder", "precision": "bfp32"},
        {"id": "acc_reg", "type": "register", "width": 32}
      ],

      "connections": [
        {"from": "a", "to": "multiplier.a", "type": "data"},
        {"from": "b", "to": "multiplier.b", "type": "data"},
        {"from": "multiplier.product", "to": "accumulator.a", "type": "data"},
        {"from": "acc_reg.q", "to": "accumulator.b", "type": "data"},
        {"from": "accumulator.sum", "to": "acc_reg.d", "type": "data"}
      ]
    }
  },

  "hierarchy": {
    "vegeta_tpu_top": {
      "children": ["vegeta_tpu_core", "instruction_fifo"],
      "vegeta_tpu_core": {
        "children": ["vegeta_compute_top", "weight_buffer", "unified_buffer"]
      }
    }
  },

  "component_types": {
    "register": {"shape": "box3d", "color": "#C8E6C9"},
    "fifo": {"shape": "box3d", "color": "#BBDEFB"},
    "multiplier": {"shape": "box", "color": "#FFE0B2"},
    "adder": {"shape": "box", "color": "#FFE0B2"},
    "mux": {"shape": "trapezium", "color": "#E1F5FE"},
    "counter": {"shape": "box", "color": "#F5F5F5"},
    "fsm": {"shape": "component", "color": "#E1BEE7"},
    "memory": {"shape": "box3d", "color": "#FFF59D"},
    "submodule": {"shape": "box", "color": "#ECEFF1"}
  },

  "clusters": [
    {"id": "compute", "label": "Compute Unit", "modules": ["vegeta_compute_top", "vegeta_pe", "vegeta_mac"]},
    {"id": "control", "label": "Control", "modules": ["control_coordinator", "matrix_multiply_control"]},
    {"id": "memory", "label": "Memory Subsystem", "modules": ["weight_buffer", "unified_buffer", "register_file"]}
  ]
}
```

### Key Schema Elements

| Element | Purpose |
|---------|---------|
| `modules` | Per-module hardware breakdown |
| `components` | Extracted hardware elements (regs, muxes, ALUs) |
| `connections` | Signal flow between components |
| `hierarchy` | Module instantiation tree |
| `component_types` | Visual styling for DOT generation |
| `clusters` | Logical groupings for diagram layout |

---

## Phase 3: Rendering

### What to Reuse from rtlviz:

1. **HTML Template** (`server.py:154-257`)
   - Viz.js CDN integration
   - Zoom controls
   - SVG download
   - Modern CSS styling

2. **DOT Conventions** (`PROMPT.md`)
   - Shape standards (box3d=registers, diamond=comparators)
   - Edge styling (solid=data, dashed=control)
   - Clustering with subgraphs
   - `rankdir=LR`, `splines=ortho`

3. **MCP Server Pattern** for IDE integration

### DOT Generation from JSON

```python
def json_to_dot(model: dict, view_level: str = "top") -> str:
    """
    Generate DOT from intermediate JSON.

    view_level options:
    - "top": Only top-level modules and their connections
    - "module:vegeta_tpu_core": Expand specific module internals
    - "cluster:compute": Show all modules in compute cluster
    """
    dot = ['digraph RTL {', 'rankdir=LR;', 'splines=ortho;']

    # Add clusters
    for cluster in model['clusters']:
        dot.append(f'subgraph cluster_{cluster["id"]} {{')
        dot.append(f'label="{cluster["label"]}";')
        # Add modules in cluster
        dot.append('}')

    # Add nodes for each component
    for mod_name, mod in model['modules'].items():
        for comp in mod['components']:
            shape = model['component_types'][comp['type']]['shape']
            color = model['component_types'][comp['type']]['color']
            dot.append(f'{comp["id"]} [label="{comp["id"]}", shape={shape}, fillcolor="{color}"];')

    # Add edges
    for mod_name, mod in model['modules'].items():
        for conn in mod['connections']:
            style = 'dashed, color="#1565C0"' if conn['type'] == 'control' else ''
            dot.append(f'{conn["from"]} -> {conn["to"]} [{style}];')

    dot.append('}')
    return '\n'.join(dot)
```

---

## View Levels for Large Designs

| Level | Shows | Use Case |
|-------|-------|----------|
| **Top** | Only top-level module + immediate children | Initial overview |
| **Subsystem** | All modules in a cluster (e.g., "Compute") | Focus on one area |
| **Module** | Internal components of single module | Deep dive |
| **Full** | Everything (may be overwhelming) | Complete reference |

---

## Configuration

| Decision | Choice |
|----------|--------|
| **Analysis Strategy** | Batch by hierarchy (parent + children together) |
| **Output Type** | Hierarchical drill-down (interactive HTML) |
| **Storage Location** | Project directory (`.rtl_model/`) |
| **Integration** | MCP Server (for IDE integration with Claude Code) |

---

## MCP Server Structure

```
rtl_diagram_server/
├── __init__.py
├── server.py              # MCP server (modeled after rtlviz)
├── discovery.py           # Phase 1: File scanning + hierarchy
├── analyzer.py            # Phase 2: LLM batch analysis
├── prompts/
│   └── extract_hardware.md
├── schema.py              # JSON schema + validation
├── dot_generator.py       # JSON → DOT with view levels
├── html_renderer.py       # Interactive drill-down HTML
└── assets/
    └── PROMPT.md          # User documentation
```

### MCP Tools Exposed

| Tool | Description |
|------|-------------|
| `analyze_rtl` | Scan directory, run LLM analysis, save to `.rtl_model/` |
| `render_diagram` | Generate interactive HTML from model |
| `get_module_info` | Query specific module from model |
| `list_modules` | List all modules with hierarchy |

### MCP Resources

| Resource | Description |
|----------|-------------|
| `rtl://model` | Current project's JSON model |
| `rtl://prompt` | Hardware extraction prompt template |

---

## Interactive HTML Features

```javascript
// Drill-down behavior
function onModuleClick(moduleId) {
  // Expand module to show internal components
  // Re-render DOT with expanded view
  // Animate transition
}

// Navigation
// - Click module → expand internals
// - Click background → collapse to parent
// - Breadcrumb trail for navigation history
// - Search box for finding modules
```

---

## Storage Structure

```
project_root/
├── .rtl_model/
│   ├── discovery.json     # File inventory
│   ├── model.json         # Full hardware model
│   ├── analysis_log.json  # LLM analysis history
│   └── diagrams/
│       ├── top_level.html
│       ├── compute_subsystem.html
│       └── interactive.html  # Main drill-down view
└── RTL sources...
```

---

## Implementation Steps

### Step 1: Create MCP Server Skeleton
- Copy rtlviz server.py pattern
- Define tools: `analyze_rtl`, `render_diagram`
- Define resources: `rtl://model`, `rtl://prompt`

### Step 2: Build Discovery Module
- Regex-based module extraction
- Instantiation graph builder
- Hierarchy tree construction

### Step 3: Build Analyzer with Batch Strategy
- Group modules by hierarchy (parent + direct children)
- Run LLM analysis per batch
- Merge results into model.json
- Track analysis progress

### Step 4: Build DOT Generator with View Levels
- Top-level view (modules as boxes)
- Expanded view (show internals)
- Generate DOT dynamically based on expansion state

### Step 5: Build Interactive HTML Renderer
- Client-side state for expanded modules
- Click handlers for drill-down
- Breadcrumb navigation
- Re-render on expansion changes

### Step 6: IDE Integration
- Add to Claude Code MCP settings
- Test with `/mcp` command
- Document usage

---

## What Can Be Reused from rtlviz

| Component | Reusability | Notes |
|-----------|-------------|-------|
| HTML template | HIGH | Viz.js + zoom + download |
| DOT styling conventions | HIGH | Shapes, colors, clustering |
| MCP server skeleton | MEDIUM | If IDE integration needed |
| PROMPT.md structure | MEDIUM | Adapt for component extraction |
| Telemetry | LOW | Optional |

---

## Estimated Effort

| Phase | Complexity | Files |
|-------|------------|-------|
| Discovery | Low | 1 file, ~100 LOC |
| Schema Definition | Low | 1 file, ~50 LOC |
| LLM Analyzer | Medium | 2 files, ~300 LOC |
| DOT Generator | Medium | 1 file, ~200 LOC |
| HTML Renderer (Interactive) | Medium | 1 file, ~300 LOC |
| MCP Server | Low (reuse pattern) | 1 file, ~150 LOC |
| **Total** | | ~1100 LOC |

---

## LLM Prompt Template

```markdown
# prompts/extract_hardware.md

You are analyzing RTL code to extract hardware components.

## Module: {module_name}
## Source:
{source_code}

## Task:
Extract the following in JSON format:

1. **Component Types**: Identify registers, muxes, ALUs, memories, FSMs, counters
2. **Connections**: How signals flow between components
3. **Port Classification**: Which ports are data vs control vs clock/reset
4. **Brief Description**: One sentence describing the module's function

## Output Format:
{
  "description": "...",
  "components": [...],
  "connections": [...],
  "ports": {...}
}

Focus on HARDWARE abstraction, not code syntax.
```

---

## Discovery Module

```python
# discovery.py
def scan_rtl_directory(path: str) -> dict:
    """Scan for RTL files and extract basic module info."""
    pass

def extract_module_names(file_path: str) -> list[str]:
    """Regex extraction of module declarations."""
    pass

def build_instantiation_graph(files: list) -> dict:
    """Find module instantiations to build hierarchy."""
    pass
```

---

## Analysis Agent

```python
# analyzer.py
class RTLAnalyzer:
    def __init__(self, model_path: str):
        self.model = load_or_create_model(model_path)

    async def analyze_module(self, module_name: str, source: str) -> dict:
        """Use LLM to extract hardware components."""
        prompt = self.build_prompt(module_name, source)
        response = await call_llm(prompt)
        return parse_hardware_extraction(response)

    def update_model(self, module_name: str, analysis: dict):
        """Merge new analysis into persistent model."""
        self.model['modules'][module_name] = analysis
        self.save_model()

    async def analyze_all(self, batch_size: int = 5):
        """Iterate through all modules with batching."""
        for batch in self.get_module_batches(batch_size):
            results = await asyncio.gather(*[
                self.analyze_module(m.name, m.source) for m in batch
            ])
            for m, r in zip(batch, results):
                self.update_model(m.name, r)
```
