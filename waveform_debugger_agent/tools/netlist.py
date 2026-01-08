"""Netlist tracing tools for debug agent."""
from .netlist_graph import NetlistGraph

_graph = None


def load_netlist(json_path: str) -> str:
    """Load netlist for analysis."""
    global _graph
    _graph = NetlistGraph()
    _graph.load(json_path)
    return f"Loaded {len(_graph.modules)} modules"


def list_modules() -> list:
    """List all netlist modules."""
    if _graph is None:
        return []
    return _graph.list_modules()


def get_top_module() -> str:
    """Get top-level module."""
    if _graph is None:
        return None
    return _graph.get_top_module()


def get_human_readable_module(module_name: str) -> str:
    """Get human-readable module name."""
    if _graph is None:
        return module_name
    return _graph.get_human_readable_module(module_name)


def find_driver(module: str, signal: str) -> dict:
    """Find driver cell for signal."""
    if _graph is None:
        return {"error": "Netlist not loaded"}
    node = _graph.find_driver(module, signal)
    if node:
        return {
            "signal": node.signal_name,
            "driver_cell": node.driver_cell,
            "driver_type": node.driver_type,
            "src": node.src,
            "inputs": dict(node.inputs) if node.inputs else {}
        }
    return {"error": f"No driver found for {signal}"}


def backward_trace(module: str, signal: str, depth: int = 5) -> list:
    """Backward trace from signal through drivers."""
    if _graph is None:
        return []
    trace = _graph.backward_trace(module, signal, depth)
    return [{"signal": n.signal_name, "driver": n.driver_type, "src": n.src} for n in trace]


def get_fan_in(module: str, signal: str, depth: int = 5) -> list:
    """Get all signals in fan-in cone."""
    if _graph is None:
        return []
    return _graph.get_fan_in_signals(module, signal, depth)
