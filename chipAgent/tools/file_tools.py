"""File operation tools for the chip design agents."""

import os
import shutil
from pathlib import Path
from typing import Optional, List

# Base output directory
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def write_file(filepath: str, content: str) -> dict:
    """
    Write content to a file, creating directories as needed.

    Args:
        filepath: Relative path from output directory (e.g., "rtl/module.v")
        content: The content to write to the file

    Returns:
        dict with status and filepath
    """
    try:
        full_path = OUTPUT_DIR / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'w') as f:
            f.write(content)

        return {
            "status": "success",
            "filepath": str(full_path),
            "bytes_written": len(content)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def read_file(filepath: str) -> dict:
    """
    Read content from a file.

    Args:
        filepath: Path to the file (absolute or relative to output dir)

    Returns:
        dict with status and content
    """
    try:
        # Handle both absolute and relative paths
        if os.path.isabs(filepath):
            full_path = Path(filepath)
        else:
            full_path = OUTPUT_DIR / filepath

        with open(full_path, 'r') as f:
            content = f.read()

        return {
            "status": "success",
            "filepath": str(full_path),
            "content": content
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"File not found: {filepath}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def copy_file(source: str, destination: str) -> dict:
    """
    Copy a file from source to destination.

    Args:
        source: Source file path (absolute or relative to output dir)
        destination: Destination file path (relative to output dir)

    Returns:
        dict with status
    """
    try:
        if os.path.isabs(source):
            src_path = Path(source)
        else:
            src_path = OUTPUT_DIR / source

        dst_path = OUTPUT_DIR / destination
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(src_path, dst_path)

        return {
            "status": "success",
            "source": str(src_path),
            "destination": str(dst_path)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def list_files(directory: str = "", pattern: str = "*") -> dict:
    """
    List files in a directory matching a pattern.

    Args:
        directory: Directory path relative to output dir (empty for output dir root)
        pattern: Glob pattern (default: "*")

    Returns:
        dict with file list
    """
    try:
        if directory:
            dir_path = OUTPUT_DIR / directory
        else:
            dir_path = OUTPUT_DIR

        files = list(dir_path.glob(pattern))

        return {
            "status": "success",
            "directory": str(dir_path),
            "files": [str(f.relative_to(OUTPUT_DIR)) for f in files if f.is_file()]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
