#!/usr/bin/env python3
"""Migrate a save to the current schema version."""

import argparse
import json
import logging
import sys
from pathlib import Path

from engine.state.migrations.registry import default_registry
from engine.state.migrations.runner import MigrationRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate a save directory to the latest schema version.")
    parser.add_argument("save_dir", type=Path, help="Path to the save directory")
    parser.add_argument("--copy-to", type=Path, help="Destination path for migrated save", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Only report what would happen")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    if not args.save_dir.is_dir():
        logging.error(f"Save directory {args.save_dir} does not exist")
        return 2
        
    state_path = args.save_dir / "state.json"
    if not state_path.exists():
        logging.error(f"No state.json found in {args.save_dir}")
        return 1
        
    try:
        state = json.loads(state_path.read_text())
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse state.json: {e}")
        return 1
        
    runner = MigrationRunner(default_registry)
    target_version = default_registry.get_max_version()
    
    try:
        migrated = runner.run_migrations(state, target_version)
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        return 1
        
    if migrated is state:
        logging.info(f"Save is already at target version {target_version}")
        if args.copy_to and not args.dry_run:
            import shutil
            shutil.copytree(args.save_dir, args.copy_to, dirs_exist_ok=True)
            logging.info(f"Copied save to {args.copy_to}")
        return 0
        
    if args.dry_run:
        logging.info("Dry run successful")
        return 0
        
    if not args.copy_to:
        logging.error("Migration required, but --copy-to not specified")
        return 1
        
    import shutil
    shutil.copytree(args.save_dir, args.copy_to, dirs_exist_ok=True)
    (args.copy_to / "state.json").write_text(json.dumps(migrated, indent=2))
    
    logging.info(f"Successfully migrated and saved to {args.copy_to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
