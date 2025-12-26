"""
waveform_debugger/netlist_graph.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json


@dataclass
class CellInfo:
    """Information about a cell in the netlist."""
    name: str
    cell_type: str
    module: str
    port_directions: Dict[str, str]
    connections: Dict[str, List[Any]]
    src: str


@dataclass
class SignalInfo:
    """Information about a signal in the netlist."""
    name: str
    module: str
    bits: List[int]
    src: str
    is_port: bool = False
    direction: str = ""


@dataclass
class TraceNode:
    """A node in the backward trace tree."""
    signal_name: str
    module: str
    driver_cell: Optional[str]
    driver_type: Optional[str]
    driver_port: Optional[str]
    src: str
    inputs: Dict[str, List[int]] = field(default_factory=dict)


class NetlistGraph:
    """Graph representation of Yosys JSON netlist."""

    def __init__(self):
        self.modules: Dict[str, Dict] = {}
        self.cells: Dict[str, Dict[str, CellInfo]] = {}
        self.signals: Dict[str, Dict[str, SignalInfo]] = {}
        self.bit_to_signal: Dict[str, Dict[int, str]] = {}
        self.bit_to_driver: Dict[str, Dict[int, CellInfo]] = {}

    def load(self, json_path: str) -> None:
        """Load and parse connectivity.json."""
        with open(json_path, 'r') as f:
            data = json.load(f)

        self.modules = data.get('modules', {})

        for module_name, module_data in self.modules.items():
            self._process_module(module_name, module_data)

    def _process_module(self, module_name: str, module_data: Dict) -> None:
        """Process a single module's cells and signals."""
        self.cells[module_name] = {}
        self.signals[module_name] = {}
        self.bit_to_signal[module_name] = {}
        self.bit_to_driver[module_name] = {}

        # Process ports
        for port_name, port_data in module_data.get('ports', {}).items():
            bits = port_data.get('bits', [])
            direction = port_data.get('direction', '')

            sig_info = SignalInfo(
                name=port_name,
                module=module_name,
                bits=[b for b in bits if isinstance(b, int)],
                src=module_data.get('attributes', {}).get('src', 'unknown'),
                is_port=True,
                direction=direction
            )
            self.signals[module_name][port_name] = sig_info

            for bit in sig_info.bits:
                self.bit_to_signal[module_name][bit] = port_name

        # Process netnames
        for net_name, net_data in module_data.get('netnames', {}).items():
            bits = net_data.get('bits', [])
            src = net_data.get('attributes', {}).get('src', 'unknown')

            sig_info = SignalInfo(
                name=net_name,
                module=module_name,
                bits=[b for b in bits if isinstance(b, int)],
                src=src
            )

            if net_name not in self.signals[module_name]:
                self.signals[module_name][net_name] = sig_info

            for bit in sig_info.bits:
                self.bit_to_signal[module_name][bit] = net_name

        # Process cells and build driver map
        for cell_name, cell_data in module_data.get('cells', {}).items():
            port_dirs = cell_data.get('port_directions', {})
            connections = cell_data.get('connections', {})
            src = cell_data.get('attributes', {}).get('src', 'unknown')

            cell_info = CellInfo(
                name=cell_name,
                cell_type=cell_data.get('type', 'unknown'),
                module=module_name,
                port_directions=port_dirs,
                connections=connections,
                src=src
            )
            self.cells[module_name][cell_name] = cell_info

            # Map output bits to driver
            for port, direction in port_dirs.items():
                if direction == 'output':
                    bits = connections.get(port, [])
                    for bit in bits:
                        if isinstance(bit, int):
                            self.bit_to_driver[module_name][bit] = cell_info

    def get_signal_bits(self, module: str, signal_name: str) -> List[int]:
        """Get bit IDs for a signal."""
        if module not in self.signals:
            return []
        if signal_name not in self.signals[module]:
            return []
        return self.signals[module][signal_name].bits

    def find_driver(self, module: str, signal_name: str) -> Optional[TraceNode]:
        """Find the cell that drives a given signal."""
        bits = self.get_signal_bits(module, signal_name)
        if not bits:
            return None

        first_bit = bits[0]
        driver = self.bit_to_driver[module].get(first_bit)

        if driver is None:
            sig_info = self.signals[module].get(signal_name)
            if sig_info and sig_info.is_port and sig_info.direction == 'input':
                return TraceNode(
                    signal_name=signal_name,
                    module=module,
                    driver_cell=None,
                    driver_type='INPUT_PORT',
                    driver_port=None,
                    src=sig_info.src
                )
            return None

        # Find which port drives this bit
        driver_port = None
        for port, direction in driver.port_directions.items():
            if direction == 'output':
                if first_bit in driver.connections.get(port, []):
                    driver_port = port
                    break

        # Collect input connections
        inputs = {}
        for port, direction in driver.port_directions.items():
            if direction == 'input':
                inputs[port] = [b for b in driver.connections.get(port, [])
                                if isinstance(b, int)]

        return TraceNode(
            signal_name=signal_name,
            module=module,
            driver_cell=driver.name,
            driver_type=driver.cell_type,
            driver_port=driver_port,
            src=driver.src,
            inputs=inputs
        )

    def backward_trace(self, module: str, signal_name: str,
                       max_depth: int = 10) -> List[TraceNode]:
        """Perform backward trace from a signal."""
        result = []
        visited = set()
        queue = [(signal_name, 0)]

        while queue:
            current_signal, depth = queue.pop(0)

            if current_signal in visited or depth > max_depth:
                continue
            visited.add(current_signal)

            trace_node = self.find_driver(module, current_signal)
            if trace_node is None:
                continue

            result.append(trace_node)

            if trace_node.inputs:
                for port, bits in trace_node.inputs.items():
                    for bit in bits:
                        input_signal = self.bit_to_signal[module].get(bit)
                        if input_signal and input_signal not in visited:
                            queue.append((input_signal, depth + 1))

        return result

    def get_fan_in_signals(self, module: str, signal_name: str,
                           max_depth: int = 10) -> List[str]:
        """Get all signal names in the fan-in cone."""
        trace = self.backward_trace(module, signal_name, max_depth)
        signals = set()

        for node in trace:
            signals.add(node.signal_name)
            for port, bits in node.inputs.items():
                for bit in bits:
                    sig = self.bit_to_signal[module].get(bit)
                    if sig:
                        signals.add(sig)

        return list(signals)

    def list_modules(self) -> List[str]:
        """List all module names."""
        return list(self.modules.keys())

    def list_signals(self, module: str) -> List[str]:
        """List all signal names in a module."""
        if module not in self.signals:
            return []
        return list(self.signals[module].keys())

    def get_top_module(self) -> Optional[str]:
        """Find the top module."""
        for module_name, module_data in self.modules.items():
            attrs = module_data.get('attributes', {})
            if 'top' in attrs:
                return module_name
        return None

    def get_human_readable_module(self, module_name: str) -> str:
        """Get human-readable module name from hdlname attribute."""
        if module_name in self.modules:
            attrs = self.modules[module_name].get('attributes', {})
            return attrs.get('hdlname', module_name)
        return module_name