"""Cross-reference tools combining VCD and netlist analysis."""
import os
from . import vcd, netlist


def debug_signal(signal: str, time: int, depth: int = 5) -> dict:
    """Full cross-reference: trace + values at time."""
    module = netlist.get_top_module()
    if not module:
        modules = netlist.list_modules()
        module = modules[0] if modules else None

    if not module:
        return {"error": "No modules found in netlist"}

    value = vcd.get_value(signal, time)
    trace = netlist.backward_trace(module, signal, depth)
    fan_in = netlist.get_fan_in(module, signal, depth)

    # Cross-reference fan-in with VCD values
    fan_in_values = {}
    for sig in fan_in:
        val = vcd.get_value(sig, time)
        fan_in_values[sig] = val.get("value") if val else "?"

    return {
        "signal": signal,
        "time": time,
        "module": netlist.get_human_readable_module(module),
        "value": value.get("value"),
        "trace": trace,
        "fan_in_values": fan_in_values
    }


def write_report(content: str, filename: str = "report.md") -> str:
    """Write debug report to file."""
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'reports')
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, 'w') as f:
        f.write(content)
    return f"Report written to {path}"
