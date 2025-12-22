"""Simulation tools for running iverilog/vvp."""

import subprocess
import glob as glob_module
from pathlib import Path
from typing import Optional, List

# Directories
OUTPUT_DIR = Path(__file__).parent.parent / "output"
SIM_DIR = OUTPUT_DIR / "sim"


def run_iverilog_compile(
    verilog_files: List[str],
    output_file: str = "sim.vvp",
    include_dirs: Optional[List[str]] = None,
    defines: Optional[List[str]] = None,
    top_module: Optional[str] = None
) -> dict:
    """
    Compile Verilog/SystemVerilog files using Icarus Verilog.

    Args:
        verilog_files: List of Verilog file paths (relative to output dir, supports globs)
        output_file: Output VVP file name
        include_dirs: List of include directories
        defines: List of defines (e.g., ["DEBUG", "SIM"])
        top_module: Top module name for elaboration

    Returns:
        dict with compilation status and output
    """
    try:
        SIM_DIR.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = ["iverilog", "-g2012"]

        # Add include directories
        if include_dirs:
            for inc in include_dirs:
                inc_path = OUTPUT_DIR / inc if not Path(inc).is_absolute() else Path(inc)
                cmd.extend(["-I", str(inc_path)])
        else:
            # Default include RTL directory
            cmd.extend(["-I", str(OUTPUT_DIR / "rtl")])

        # Add defines
        if defines:
            for d in defines:
                cmd.extend(["-D", d])

        # Add top module
        if top_module:
            cmd.extend(["-s", top_module])

        # Output file
        cmd.extend(["-o", str(SIM_DIR / output_file)])

        # Expand and add source files
        expanded_files = []
        for vf in verilog_files:
            if "*" in vf:
                # Handle glob patterns
                pattern_path = str(OUTPUT_DIR / vf)
                matched_files = glob_module.glob(pattern_path)
                expanded_files.extend(matched_files)
            else:
                file_path = OUTPUT_DIR / vf if not Path(vf).is_absolute() else Path(vf)
                expanded_files.append(str(file_path))

        cmd.extend(expanded_files)

        # Run compilation
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        # Parse warnings and errors
        warnings = []
        errors = []
        for line in (result.stdout + result.stderr).split('\n'):
            line_lower = line.lower()
            if 'warning' in line_lower:
                warnings.append(line)
            elif 'error' in line_lower:
                errors.append(line)

        return {
            "status": "success" if result.returncode == 0 else "error",
            "return_code": result.returncode,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "warnings": warnings,
            "errors": errors,
            "output_file": str(SIM_DIR / output_file) if result.returncode == 0 else None,
            "files_compiled": expanded_files
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": "Compilation timed out after 120 seconds"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": "iverilog not found. Install with: brew install icarus-verilog"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def run_vvp_simulation(
    vvp_file: str = "sim.vvp",
    timeout_seconds: int = 300,
    plusargs: Optional[List[str]] = None
) -> dict:
    """
    Run VVP simulation.

    Args:
        vvp_file: Path to VVP file (relative to sim dir or absolute)
        timeout_seconds: Simulation timeout
        plusargs: List of plusargs for simulation

    Returns:
        dict with simulation status and output
    """
    try:
        # Resolve VVP file path
        if Path(vvp_file).is_absolute():
            vvp_path = Path(vvp_file)
        else:
            vvp_path = SIM_DIR / vvp_file

        if not vvp_path.exists():
            return {
                "status": "error",
                "error": f"VVP file not found: {vvp_path}"
            }

        cmd = ["vvp", str(vvp_path)]

        if plusargs:
            cmd.extend([f"+{arg}" for arg in plusargs])

        # Run simulation
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(SIM_DIR)
        )

        # Parse output for pass/fail
        output = result.stdout + result.stderr
        output_upper = output.upper()

        # Look for common pass/fail patterns
        test_passed = any(pattern in output_upper for pattern in [
            "TEST PASSED", "ALL TESTS PASSED", "PASS", "SUCCESS"
        ])
        test_failed = any(pattern in output_upper for pattern in [
            "TEST FAILED", "FAIL", "ERROR", "ASSERTION FAILED"
        ])

        # Determine overall status
        if result.returncode != 0:
            sim_status = "error"
        elif test_failed and not test_passed:
            sim_status = "failed"
        elif test_passed and not test_failed:
            sim_status = "passed"
        elif test_passed and test_failed:
            # Both patterns found - likely partial pass
            sim_status = "partial"
        else:
            sim_status = "completed"  # No explicit pass/fail found

        # Check for waveform file
        possible_vcd_files = list(SIM_DIR.glob("*.vcd"))
        waveform_file = str(possible_vcd_files[0]) if possible_vcd_files else None

        return {
            "status": sim_status,
            "return_code": result.returncode,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "test_passed": test_passed and not test_failed,
            "waveform_file": waveform_file
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "error": f"Simulation timed out after {timeout_seconds} seconds"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": "vvp not found. Install with: brew install icarus-verilog"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def check_iverilog_installed() -> dict:
    """
    Check if iverilog is installed and available.

    Returns:
        dict with installation status and version
    """
    try:
        result = subprocess.run(
            ["iverilog", "-V"],
            capture_output=True,
            text=True,
            timeout=10
        )

        version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown"

        # Get path
        which_result = subprocess.run(
            ["which", "iverilog"],
            capture_output=True,
            text=True
        )

        return {
            "status": "installed",
            "version": version_line,
            "path": which_result.stdout.strip()
        }
    except FileNotFoundError:
        return {
            "status": "not_installed",
            "error": "iverilog not found. Install with: brew install icarus-verilog"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
