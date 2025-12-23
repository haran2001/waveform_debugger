"""VCD parsing tools for debug agent."""
import sys
import os

# Add waveform_debugger to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waveform_debugger'))
from vcd_parser import VCDParser

_parser = None


def load_vcd(vcd_path: str) -> str:
    """Load VCD file for analysis."""
    global _parser
    _parser = VCDParser()
    _parser.parse(vcd_path)
    return f"Loaded {len(_parser.signals)} signals"


def list_signals() -> list:
    """List all available VCD signals."""
    if _parser is None:
        return []
    return _parser.list_signals()


def find_signals(pattern: str) -> list:
    """Find signals matching pattern."""
    if _parser is None:
        return []
    signals = _parser.find_signals(pattern)
    return [{"name": s.name, "path": s.path, "width": s.width} for s in signals]


def get_value(signal: str, time: int) -> dict:
    """Get signal value at specific time."""
    if _parser is None:
        return {"signal": signal, "time": time, "value": None, "error": "VCD not loaded"}
    value = _parser.get_value_at_time(signal, time)
    return {"signal": signal, "time": time, "value": value}


def get_transitions(signal: str, start: int, end: int) -> list:
    """Get all transitions in time window."""
    if _parser is None:
        return []
    transitions = _parser.get_transitions(signal, start, end)
    return [{"time": t.time, "value": t.value} for t in transitions]
