"""
Benchmark suite for VCD parser - before/after compression comparison.

Run with:
    python -m benchmarks.benchmark_vcd

Metrics tracked:
    - Memory usage (peak and steady-state)
    - Parse time
    - Query time (get_value, get_transitions, find_signals)
    - File size (if saving compressed format)
"""

import os
import sys
import time
import tracemalloc
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vcd_parser import VCDParser


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""
    name: str
    parse_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    steady_memory_mb: float = 0.0
    query_times_ms: Dict[str, List[float]] = field(default_factory=dict)
    signal_count: int = 0
    change_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "parse_time_ms": round(self.parse_time_ms, 2),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "steady_memory_mb": round(self.steady_memory_mb, 2),
            "query_times_ms": {
                k: {
                    "mean": round(statistics.mean(v), 3),
                    "min": round(min(v), 3),
                    "max": round(max(v), 3),
                    "stdev": round(statistics.stdev(v), 3) if len(v) > 1 else 0
                }
                for k, v in self.query_times_ms.items()
            },
            "signal_count": self.signal_count,
            "change_count": self.change_count
        }


class VCDBenchmark:
    """Benchmark harness for VCD parser implementations."""

    def __init__(self, vcd_path: str):
        self.vcd_path = vcd_path
        self.vcd_size_mb = os.path.getsize(vcd_path) / (1024 * 1024)

    def run_benchmark(self, parser_class, name: str, num_queries: int = 100) -> BenchmarkResult:
        """Run full benchmark suite on a parser implementation."""
        result = BenchmarkResult(name=name)

        # Measure parse time and memory
        tracemalloc.start()

        start_time = time.perf_counter()
        parser = parser_class()
        parser.parse(self.vcd_path)
        end_time = time.perf_counter()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result.parse_time_ms = (end_time - start_time) * 1000
        result.peak_memory_mb = peak / (1024 * 1024)
        result.steady_memory_mb = current / (1024 * 1024)

        # Count signals and changes
        result.signal_count = len(parser.signals)
        result.change_count = sum(len(changes) for changes in parser.changes.values())

        # Get test signals and times
        signals = parser.list_signals()
        if not signals:
            print(f"Warning: No signals found in {self.vcd_path}")
            return result

        # Pick test signals (first, middle, last)
        test_signals = [
            signals[0],
            signals[len(signals) // 2],
            signals[-1]
        ]

        # Find time range from changes
        all_times = []
        for sig_id, changes in parser.changes.items():
            all_times.extend(c.time for c in changes)

        if not all_times:
            print("Warning: No value changes found")
            return result

        min_time, max_time = min(all_times), max(all_times)
        mid_time = (min_time + max_time) // 2

        # Benchmark: get_value
        result.query_times_ms["get_value"] = []
        for _ in range(num_queries):
            for sig in test_signals:
                start = time.perf_counter()
                parser.get_value_at_time(sig, mid_time)
                result.query_times_ms["get_value"].append(
                    (time.perf_counter() - start) * 1000
                )

        # Benchmark: get_transitions
        window_size = (max_time - min_time) // 10  # 10% of total time
        result.query_times_ms["get_transitions"] = []
        for _ in range(num_queries):
            for sig in test_signals:
                start = time.perf_counter()
                parser.get_transitions(sig, mid_time - window_size, mid_time + window_size)
                result.query_times_ms["get_transitions"].append(
                    (time.perf_counter() - start) * 1000
                )

        # Benchmark: find_signals
        result.query_times_ms["find_signals"] = []
        patterns = ["clk", "rst", "data", "full", "empty", "ptr"]
        for _ in range(num_queries):
            for pattern in patterns:
                start = time.perf_counter()
                parser.find_signals(pattern)
                result.query_times_ms["find_signals"].append(
                    (time.perf_counter() - start) * 1000
                )

        return result


def print_comparison(before: BenchmarkResult, after: BenchmarkResult):
    """Print side-by-side comparison of results."""

    def improvement(old, new):
        if old == 0:
            return "N/A"
        pct = ((old - new) / old) * 100
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct:.1f}%"

    print("\n" + "=" * 70)
    print(f"BENCHMARK COMPARISON: {before.name} vs {after.name}")
    print("=" * 70)

    print(f"\n{'Metric':<30} {'Before':>15} {'After':>15} {'Improvement':>12}")
    print("-" * 70)

    print(f"{'Parse Time (ms)':<30} {before.parse_time_ms:>15.2f} {after.parse_time_ms:>15.2f} {improvement(before.parse_time_ms, after.parse_time_ms):>12}")
    print(f"{'Peak Memory (MB)':<30} {before.peak_memory_mb:>15.2f} {after.peak_memory_mb:>15.2f} {improvement(before.peak_memory_mb, after.peak_memory_mb):>12}")
    print(f"{'Steady Memory (MB)':<30} {before.steady_memory_mb:>15.2f} {after.steady_memory_mb:>15.2f} {improvement(before.steady_memory_mb, after.steady_memory_mb):>12}")

    print(f"\n{'Query Times (mean ms)':<30}")
    print("-" * 70)

    for query_type in before.query_times_ms:
        before_mean = statistics.mean(before.query_times_ms[query_type])
        after_mean = statistics.mean(after.query_times_ms.get(query_type, [0]))
        print(f"  {query_type:<28} {before_mean:>15.4f} {after_mean:>15.4f} {improvement(before_mean, after_mean):>12}")

    print("\n" + "=" * 70)


def run_benchmarks(vcd_path: str, output_json: str = None):
    """Run benchmarks and optionally save results to JSON."""

    print(f"VCD File: {vcd_path}")
    print(f"File Size: {os.path.getsize(vcd_path) / 1024:.2f} KB")

    benchmark = VCDBenchmark(vcd_path)

    # Run baseline benchmark
    print("\nRunning baseline (uncompressed) benchmark...")
    baseline_result = benchmark.run_benchmark(VCDParser, "Baseline (Uncompressed)")

    print(f"  Signals: {baseline_result.signal_count}")
    print(f"  Value changes: {baseline_result.change_count}")
    print(f"  Parse time: {baseline_result.parse_time_ms:.2f} ms")
    print(f"  Memory: {baseline_result.steady_memory_mb:.2f} MB")

    # Try to import compressed parser (if implemented)
    compressed_result = None
    try:
        from tools.vcd_parser_compressed import CompressedVCDParser
        print("\nRunning compressed benchmark...")
        compressed_result = benchmark.run_benchmark(CompressedVCDParser, "Compressed (FSST)")
        print_comparison(baseline_result, compressed_result)
    except ImportError:
        print("\nCompressed parser not yet implemented.")
        print("Create tools/vcd_parser_compressed.py to enable comparison.")

    # Save results
    if output_json:
        results = {
            "vcd_file": vcd_path,
            "vcd_size_mb": benchmark.vcd_size_mb,
            "baseline": baseline_result.to_dict(),
        }
        if compressed_result:
            results["compressed"] = compressed_result.to_dict()

        with open(output_json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_json}")

    return baseline_result, compressed_result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark VCD parser implementations")
    parser.add_argument("--vcd", type=str,
                        default="../Async-FIFO/fifo_wave.vcd",
                        help="Path to VCD file")
    parser.add_argument("--output", type=str,
                        default="benchmarks/results.json",
                        help="Output JSON file for results")
    parser.add_argument("--queries", type=int, default=100,
                        help="Number of queries per benchmark")

    args = parser.parse_args()

    # Resolve path
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vcd_path = os.path.join(script_dir, args.vcd) if not os.path.isabs(args.vcd) else args.vcd

    if not os.path.exists(vcd_path):
        print(f"Error: VCD file not found: {vcd_path}")
        sys.exit(1)

    output_path = os.path.join(script_dir, args.output) if not os.path.isabs(args.output) else args.output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    run_benchmarks(vcd_path, output_path)
