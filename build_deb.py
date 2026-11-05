#!/usr/bin/env python3
"""
Build script for creating .deb package using dpkg-buildpackage
"""
import subprocess
import sys
import os
from pathlib import Path

def run_cmd(cmd, cwd=None, check=True):
    """Run command and return result"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result

def main():
    project_dir = Path(__file__).parent
    debian_dir = project_dir / "debian"
    
    # Check if we're in the right directory
    if not (project_dir / "pyproject.toml").exists():
        print("Error: pyproject.toml not found. Run from project root.")
        return 1
    
    # Check for required tools
    for tool in ["dpkg-buildpackage", "debhelper", "dh-python"]:
        result = subprocess.run(["which", tool], capture_output=True)
        if result.returncode != 0:
            print(f"Warning: {tool} not found. Install with: sudo apt install {tool}")
    
    print("Building .deb package...")
    
    try:
        # Build source package
        run_cmd("dpkg-buildpackage -us -uc -b", cwd=project_dir)
        
        # List generated packages
        print("\nGenerated packages:")
        for deb in project_dir.parent.glob("*.deb"):
            print(f"  {deb.name}")
        
        # Show package info
        for deb in project_dir.parent.glob("*.deb"):
            run_cmd(f"dpkg-deb -I {deb}", check=False)
            
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())