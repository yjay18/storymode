"""Command-line runner for campaign validation."""

import argparse
import json
import sys
from pathlib import Path

from engine.validation.balance import validate_balance
from engine.validation.campaign_files import validate_campaign_files
from engine.validation.graphs import validate_graphs
from engine.validation.references import index_campaign_entities, validate_references


def validate_directory(campaign_dir: Path) -> int:
    """Validate a campaign directory and print diagnostics."""
    file_contents = {}
    
    # Read all JSON files in the directory
    for file_path in campaign_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_contents[file_path.name] = f.read()
        except OSError as e:
            print(f"[{file_path.name}] Read error: {e}")
            return 1
            
    pack, diagnostics = validate_campaign_files(file_contents)
    
    if pack is not None:
        # Phase 2: References
        index, ref_diags = index_campaign_entities(pack)
        diagnostics.extend(ref_diags)
        
        # Only proceed to deep reference validation if no duplicate IDs
        if not ref_diags:
            diagnostics.extend(validate_references(pack, index))
            
        # Phase 3: Graphs
        diagnostics.extend(validate_graphs(pack))
        
        # Phase 4: Balance
        diagnostics.extend(validate_balance(pack))
        
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
