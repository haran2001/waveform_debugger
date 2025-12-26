"""
VCD Parser - Extract signal values from Value Change Dump files.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import re


@dataclass
class VCDSignal:
    """Represents a signal definition from VCD."""
    id: str              # Single char like '!', '"', '#'
    name: str            # Signal name like 'wfull'
    width: int           # Bit width
    path: str            # Full hierarchical path
    var_type: str        # 'wire', 'reg', etc.


@dataclass
class ValueChange:
    """A single value change event."""
    time: int            # Timestamp in timescale units
    value: str           # Value string ('0', '1', 'x', 'b1010', etc.)


class VCDParser:
    """Minimal VCD parser for signal value extraction."""

    def __init__(self):
        self.signals: Dict[str, VCDSignal] = {}          # id -> signal
        self.signals_by_path: Dict[str, VCDSignal] = {}  # path -> signal
        self.signals_by_name: Dict[str, List[VCDSignal]] = {}  # name -> [signals]
        self.changes: Dict[str, List[ValueChange]] = {}  # id -> changes
        self.timescale: str = "1ps"
        self._scope_stack: List[str] = []

    def parse(self, vcd_path: str) -> None:
        """Parse entire VCD file."""
        with open(vcd_path, 'r') as f:
            content = f.read()

        self._parse_header(content)
        self._parse_values(content)

    def _parse_header(self, content: str) -> None:
        """Parse signal definitions from VCD header."""
        lines = content.split('\n')

        for line in lines:
            line = line.strip()

            if line.startswith('$enddefinitions'):
                break

            if line.startswith('$scope'):
                match = re.match(r'\$scope\s+\w+\s+(\w+)\s+\$end', line)
                if match:
                    self._scope_stack.append(match.group(1))

            elif line.startswith('$upscope'):
                if self._scope_stack:
                    self._scope_stack.pop()

            elif line.startswith('$var'):
                # $var TYPE WIDTH ID NAME [MSB:LSB] $end
                match = re.match(
                    r'\$var\s+(\w+)\s+(\d+)\s+(.)\s+(\w+)(?:\s+\[\d+:\d+\])?\s+\$end',
                    line
                )
                if match:
                    var_type, width, sig_id, name = match.groups()
                    path = '.'.join(self._scope_stack + [name])

                    signal = VCDSignal(
                        id=sig_id,
                        name=name,
                        width=int(width),
                        path=path,
                        var_type=var_type
                    )

                    self.signals[sig_id] = signal
                    self.signals_by_path[path] = signal

                    if name not in self.signals_by_name:
                        self.signals_by_name[name] = []
                    self.signals_by_name[name].append(signal)

                    self.changes[sig_id] = []

    def _parse_values(self, content: str) -> None:
        """Parse value changes after $enddefinitions."""
        idx = content.find('$enddefinitions')
        if idx == -1:
            return

        value_section = content[idx:]
        current_time = 0

        for line in value_section.split('\n'):
            line = line.strip()

            if not line or line.startswith('$'):
                continue

            # Timestamp: #12345
            if line.startswith('#'):
                try:
                    current_time = int(line[1:])
                except ValueError:
                    pass
                continue

            # Scalar value: 0! or 1! or x!
            if len(line) >= 2 and line[0] in '01xXzZ':
                value = line[0]
                sig_id = line[1]
                if sig_id in self.changes:
                    self.changes[sig_id].append(
                        ValueChange(time=current_time, value=value)
                    )
                continue

            # Vector value: b1010 X
            if line.startswith('b') or line.startswith('B'):
                parts = line.split()
                if len(parts) == 2:
                    value = parts[0]
                    sig_id = parts[1]
                    if sig_id in self.changes:
                        self.changes[sig_id].append(
                            ValueChange(time=current_time, value=value)
                        )

    def get_value_at_time(self, signal_name: str, time: int) -> Optional[str]:
        """Get signal value at a specific time."""
        if signal_name not in self.signals_by_name:
            return None

        signal = self.signals_by_name[signal_name][0]
        changes = self.changes.get(signal.id, [])

        value = None
        for change in changes:
            if change.time <= time:
                value = change.value
            else:
                break

        return value

    def get_value_at_time_by_path(self, path: str, time: int) -> Optional[str]:
        """Get signal value using full hierarchical path."""
        if path not in self.signals_by_path:
            return None

        signal = self.signals_by_path[path]
        changes = self.changes.get(signal.id, [])

        value = None
        for change in changes:
            if change.time <= time:
                value = change.value
            else:
                break

        return value

    def get_transitions(self, signal_name: str,
                        start_time: int, end_time: int) -> List[ValueChange]:
        """Get all value changes in a time window."""
        if signal_name not in self.signals_by_name:
            return []

        signal = self.signals_by_name[signal_name][0]
        changes = self.changes.get(signal.id, [])

        return [c for c in changes if start_time <= c.time <= end_time]

    def list_signals(self) -> List[str]:
        """List all signal names."""
        return list(self.signals_by_name.keys())

    def find_signals(self, pattern: str) -> List[VCDSignal]:
        """Find signals matching a pattern."""
        results = []
        for name, signals in self.signals_by_name.items():
            if pattern.lower() in name.lower():
                results.extend(signals)
        return results