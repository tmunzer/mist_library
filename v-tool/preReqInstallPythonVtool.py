#!/usr/bin/env python3
"""
===============================================================================
Pre-Requisites Installation Script for Upgrade Management Script
===============================================================================
Version: 1.0
Date: February 13, 2025
Author: SV

Description:
------------
This script installs the following required Python packages for the Upgrade Management 
Script:
  - requests    (Used for making HTTP requests to the API)
  - pandas      (Used for data manipulation and Excel file operations)
  - openpyxl    (Used for reading and writing Excel files)

Standard library modules used in this script:
  - os          (For operating system interactions)
  - sys         (For accessing system-specific parameters and functions)
  - subprocess  (For invoking pip3 via the command line)

Prerequisites:
--------------
- Python 3.6 or higher must be installed.
- This script uses pip3 to install required packages.
- To run the script, use:
    python3 preReqInstallPython.py

Usage:
------
Run the script from the command line to automatically install the required packages:
    python3 preReqInstallPython.py

===============================================================================
"""

import subprocess
import sys

# List of required packages to install via pip3
packages = [
    "requests",
    "pandas",
    "openpyxl"
]

def install_package(package):
    """
    Installs the given package using pip3.
    """
    print(f"Installing {package} ...")
    try:
        # Use python3 -m pip install ... to ensure pip3 is used
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"[SUCCESS] {package} installed successfully.\n")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install {package}. Error: {e}")
        sys.exit(1)

def main():
    """
    Main function to install all required packages.
    """
    print("Starting installation of required packages...\n")
    for pkg in packages:
        install_package(pkg)
    print("All required packages have been installed successfully.")

if __name__ == "__main__":
    main()
