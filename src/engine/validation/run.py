"""Command-line runner for campaign validation."""

import argparse
import json
import sys
from pathlib import Path

from engine.campaign import load_campaign


def validate_directory(campaign_dir: Path) -> int:
    """Validate a campaign directory and print diagnostics."""
    pack, diagnostics = load_campaign(campaign_dir)
        
    if not diagnostics:
        print("Validation successful: 0 diagnostics.")
        return 0
        
    print(f"Validation failed: {len(diagnostics)} diagnostics found.")
    for d in sorted(diagnostics):
        print(f"[{d.file}] {d.code} at {d.json_pointer}: {d.message}")
        
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a campaign pack directory.")
    parser.add_argument("directory", type=Path, help="Path to campaign directory")
    args = parser.parse_args()
    
    if not args.directory.is_dir():
        print(f"Error: Directory '{args.directory}' does not exist.")
        sys.exit(1)
        
    sys.exit(validate_directory(args.directory))


if __name__ == "__main__":
    main()
