#!/usr/bin/env python3
"""
Waveform Debugger - Cross-reference VCD with netlist for signal tracing.
"""

import argparse
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

# Add parent directory to path for imports when run as script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vcd_parser import VCDParser
from netlist_graph import NetlistGraph, TraceNode


@dataclass
class SignalSnapshot:
    """Signal value at a specific time."""
    name: str
    value: str
    time: int
    driver_type: Optional[str]
    src: Optional[str]


class WaveformDebugger:
    """Main debugger: cross-references VCD with netlist."""

    def __init__(self, vcd_path: str, netlist_path: str):
        self.vcd = VCDParser()
        self.netlist = NetlistGraph()

        print(f"Loading VCD: {vcd_path}")
        self.vcd.parse(vcd_path)
        print(f"  Found {len(self.vcd.signals)} signals")

        print(f"Loading netlist: {netlist_path}")
        self.netlist.load(netlist_path)
        print(f"  Found {len(self.netlist.modules)} modules")

    def debug_signal(self, signal_name: str, time: int,
                     module: Optional[str] = None,
                     trace_depth: int = 5) -> None:
        """Main debug function: trace backward and show fan-in values."""

        # Auto-detect module
        if module is None:
            module = self.netlist.get_top_module()
            if module is None:
                module = list(self.netlist.modules.keys())[0]

        module_display = self.netlist.get_human_readable_module(module)
        print(f"\n{'='*60}")
        print(f"Debugging '{signal_name}' at time {time} in '{module_display}'")
        print('='*60)

        # Get target value from VCD
        target_value = self.vcd.get_value_at_time(signal_name, time)
        if target_value is None:
            target_value = "NOT_FOUND_IN_VCD"

        print(f"\nTarget: {signal_name} = {target_value}")

        # Backward trace
        trace_path = self.netlist.backward_trace(module, signal_name, trace_depth)

        if trace_path:
            print(f"\nBackward trace ({len(trace_path)} nodes):")
            for node in trace_path:
                driver = node.driver_type or "INPUT"
                # Simplify source path
                src_short = node.src.split('/')[-1] if '/' in node.src else node.src
                print(f"  {node.signal_name:30} <- {driver:15} ({src_short})")
        else:
            print(f"\nNo trace found for '{signal_name}' in module '{module_display}'")
            print("Available modules:")
            for m in self.netlist.list_modules():
                hdl = self.netlist.get_human_readable_module(m)
                print(f"  {hdl}")
            return

        # Get fan-in signals
        fan_in_signals = self.netlist.get_fan_in_signals(module, signal_name, trace_depth)

        print(f"\nFan-in cone ({len(fan_in_signals)} signals):")
        print("-" * 50)

        # Cross-reference with VCD
        for sig_name in sorted(fan_in_signals):
            value = self.vcd.get_value_at_time(sig_name, time)
            val_str = value if value else "?"

            # Find driver info
            driver_type = None
            for node in trace_path:
                if node.signal_name == sig_name:
                    driver_type = node.driver_type
                    break

            driver_str = f"({driver_type})" if driver_type else ""
            print(f"  {sig_name:30} = {val_str:15} {driver_str}")

    def trace_transitions(self, signal_name: str,
                          start_time: int, end_time: int) -> None:
        """Show all transitions of a signal in a time range."""
        print(f"\n{'='*60}")
        print(f"Transitions for '{signal_name}' from {start_time} to {end_time}")
        print('='*60)

        transitions = self.vcd.get_transitions(signal_name, start_time, end_time)

        if not transitions:
            print(f"\nNo transitions found for '{signal_name}' in range")
            return

        print(f"\nFound {len(transitions)} transitions:")
        for t in transitions:
            print(f"  t={t.time:>10}: {t.value}")

    def list_available_signals(self) -> None:
        """List all signals in VCD."""
        print(f"\n{'='*60}")
        print("Available VCD Signals")
        print('='*60 + "\n")

        for name in sorted(self.vcd.list_signals()):
            signals = self.vcd.signals_by_name[name]
            for sig in signals:
                print(f"  {sig.path:50} ({sig.var_type}, {sig.width}-bit)")

    def list_netlist_info(self) -> None:
        """List netlist modules."""
        print(f"\n{'='*60}")
        print("Netlist Modules")
        print('='*60 + "\n")

        for module_name in self.netlist.list_modules():
            hdl_name = self.netlist.get_human_readable_module(module_name)
            signals = self.netlist.list_signals(module_name)
            cells = len(self.netlist.cells.get(module_name, {}))
            print(f"  {hdl_name:30} - {len(signals)} signals, {cells} cells")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Waveform Debugger - Trace signals and cross-reference values',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python debugger.py --signal wfull --time 325000
  python debugger.py --signal wfull --start 300000 --end 400000 --transitions
  python debugger.py --list-signals
  python debugger.py --list-modules
        """
    )

    # Default paths relative to project root
    default_vcd = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'Verilog_Code', 'fifo_wave.vcd'
    )
    default_netlist = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'connectivity.json'
    )

    parser.add_argument('--vcd', type=str, default=default_vcd,
                        help='Path to VCD file')
    parser.add_argument('--netlist', type=str, default=default_netlist,
                        help='Path to connectivity.json')
    parser.add_argument('--signal', '-s', type=str,
                        help='Signal name to debug')
    parser.add_argument('--time', '-t', type=int,
                        help='Simulation time to inspect')
    parser.add_argument('--start', type=int,
                        help='Start time for transition query')
    parser.add_argument('--end', type=int,
                        help='End time for transition query')
    parser.add_argument('--module', '-m', type=str,
                        help='Module name (auto-detected if not specified)')
    parser.add_argument('--depth', '-d', type=int, default=5,
                        help='Trace depth (default: 5)')
    parser.add_argument('--list-signals', action='store_true',
                        help='List all VCD signals')
    parser.add_argument('--list-modules', action='store_true',
                        help='List netlist modules')
    parser.add_argument('--transitions', action='store_true',
                        help='Show transitions instead of single value')

    args = parser.parse_args()

    # Check files exist
    if not os.path.exists(args.vcd):
        print(f"Error: VCD file not found: {args.vcd}")
        sys.exit(1)
    if not os.path.exists(args.netlist):
        print(f"Error: Netlist file not found: {args.netlist}")
        sys.exit(1)

    # Create debugger
    debugger = WaveformDebugger(args.vcd, args.netlist)

    # Handle commands
    if args.list_signals:
        debugger.list_available_signals()
    elif args.list_modules:
        debugger.list_netlist_info()
    elif args.transitions and args.signal and args.start is not None and args.end is not None:
        debugger.trace_transitions(args.signal, args.start, args.end)
    elif args.signal and args.time is not None:
        debugger.debug_signal(args.signal, args.time, args.module, args.depth)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
