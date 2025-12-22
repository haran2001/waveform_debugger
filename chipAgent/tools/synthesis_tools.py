"""Synthesis tools for running OpenLane flow."""

import subprocess
import os
from pathlib import Path
from typing import Optional

# Directories
OUTPUT_DIR = Path(__file__).parent.parent / "output"
SYNTH_DIR = OUTPUT_DIR / "synth"


def run_openlane_synthesis(
    design_dir: Optional[str] = None,
    tag: Optional[str] = None,
    timeout_seconds: int = 1800,
    pdk: str = "sky130A",
    pdk_root: Optional[str] = None
) -> dict:
    """
    Run OpenLane synthesis flow using Docker.

    Args:
        design_dir: Path to design directory (default: output/synth)
        tag: Run tag name (default: run)
        timeout_seconds: Timeout for the flow (default: 30 minutes)
        pdk: PDK to use (default: sky130A)
        pdk_root: Path to PDK root directory (optional, uses env var if not set)

    Returns:
        dict with synthesis status and results
    """
    try:
        # Resolve design directory
        if design_dir:
            design_path = Path(design_dir) if Path(design_dir).is_absolute() else OUTPUT_DIR / design_dir
        else:
            design_path = SYNTH_DIR

        if not design_path.exists():
            return {
                "status": "error",
                "error": f"Design directory not found: {design_path}"
            }

        # Check for config.json
        config_file = design_path / "config.json"
        if not config_file.exists():
            return {
                "status": "error",
                "error": f"config.json not found in {design_path}"
            }

        # Check for source files
        src_dir = design_path / "src"
        if not src_dir.exists() or not list(src_dir.glob("*.v")):
            return {
                "status": "error",
                "error": f"No Verilog source files found in {src_dir}"
            }

        # Find PDK root
        pdk_path = pdk_root or os.environ.get("PDK_ROOT")

        # Check common PDK locations if not set
        if not pdk_path:
            common_locations = [
                Path.home() / ".volare" / "volare" / "sky130",
                Path.home() / "pdk",
                Path("/opt/pdk"),
                Path.home() / ".local" / "share" / "pdk",
            ]
            for loc in common_locations:
                if loc.exists():
                    pdk_path = str(loc.parent)
                    break

        if not pdk_path or not Path(pdk_path).exists():
            return {
                "status": "error",
                "error": "PDK not found. Install Sky130 PDK using: pip install volare && volare enable sky130 --pdk-root ~/pdk",
                "setup_instructions": [
                    "1. Install volare: pip install volare",
                    "2. Install Sky130 PDK: volare enable sky130 --pdk-root ~/pdk",
                    "3. Set PDK_ROOT environment variable: export PDK_ROOT=~/pdk",
                    "4. Re-run synthesis"
                ]
            }

        # Set tag
        run_tag = tag or "run"

        # Get design name from config
        import json
        with open(config_file) as f:
            config = json.load(f)
        design_name = config.get("DESIGN_NAME", "design")

        # Build Docker command for OpenLane
        docker_image = "ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69"

        # Mount paths - design goes to designs/<name>, PDK to /build/pdk
        design_mount = f"{design_path}:/openlane/designs/{design_name}"
        pdk_mount = f"{pdk_path}:/build/pdk"

        # Full Docker command
        cmd = [
            "docker", "run", "--rm",
            "-v", design_mount,
            "-v", pdk_mount,
            "-e", f"PDK={pdk}",
            docker_image,
            "flow.tcl",
            "-design", f"/openlane/designs/{design_name}",
            "-tag", run_tag,
        ]

        print(f"Running OpenLane: {' '.join(cmd)}")

        # Run OpenLane
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(design_path)
        )

        # Check for results
        runs_dir = design_path / "runs" / run_tag

        # Parse output for key metrics
        output = result.stdout + result.stderr

        # Look for synthesis results
        synthesis_results = {}
        if runs_dir.exists():
            # Check for reports
            reports_dir = runs_dir / "reports" / "synthesis"
            if reports_dir.exists():
                for report_file in reports_dir.glob("*.rpt"):
                    synthesis_results[report_file.stem] = str(report_file)

            # Check for netlist
            results_dir = runs_dir / "results" / "synthesis"
            if results_dir.exists():
                netlists = list(results_dir.glob("*.v"))
                if netlists:
                    synthesis_results["netlist"] = str(netlists[0])

        # Determine status
        if result.returncode == 0:
            status = "success"
        elif "error" in output.lower():
            status = "error"
        else:
            status = "failed"

        return {
            "status": status,
            "return_code": result.returncode,
            "command": " ".join(cmd),
            "stdout": result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,
            "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
            "run_directory": str(runs_dir) if runs_dir.exists() else None,
            "synthesis_results": synthesis_results,
            "design_directory": str(design_path)
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "error": f"OpenLane timed out after {timeout_seconds} seconds"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": "Docker not found. Install Docker to run OpenLane."
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def check_openlane_installed() -> dict:
    """
    Check if OpenLane Docker image is available.

    Returns:
        dict with installation status
    """
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}", "ghcr.io/the-openroad-project/openlane"],
            capture_output=True,
            text=True,
            timeout=30
        )

        images = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

        if images:
            return {
                "status": "installed",
                "images": images,
                "docker_available": True
            }
        else:
            return {
                "status": "not_installed",
                "error": "OpenLane Docker image not found. Pull with: docker pull ghcr.io/the-openroad-project/openlane",
                "docker_available": True
            }

    except FileNotFoundError:
        return {
            "status": "error",
            "error": "Docker not found. Install Docker first.",
            "docker_available": False
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def get_synthesis_reports(run_dir: str) -> dict:
    """
    Parse synthesis reports from an OpenLane run.

    Args:
        run_dir: Path to the OpenLane run directory

    Returns:
        dict with parsed report data
    """
    run_path = Path(run_dir)

    if not run_path.exists():
        return {"status": "error", "error": f"Run directory not found: {run_dir}"}

    reports = {}

    # Check synthesis reports
    synth_reports = run_path / "reports" / "synthesis"
    if synth_reports.exists():
        for rpt in synth_reports.glob("*.rpt"):
            try:
                content = rpt.read_text()
                reports[rpt.stem] = {
                    "path": str(rpt),
                    "content": content[:2000] if len(content) > 2000 else content
                }
            except Exception as e:
                reports[rpt.stem] = {"path": str(rpt), "error": str(e)}

    # Check for final summary
    final_summary = run_path / "reports" / "metrics.csv"
    if final_summary.exists():
        try:
            reports["metrics"] = {
                "path": str(final_summary),
                "content": final_summary.read_text()
            }
        except Exception as e:
            reports["metrics"] = {"error": str(e)}

    return {
        "status": "success",
        "reports": reports,
        "run_directory": str(run_path)
    }
