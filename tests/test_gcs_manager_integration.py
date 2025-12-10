#!/usr/bin/env python3
"""Integration test for the refactored GCSManager.

This script:
1. Loads the real autopost configuration.
2. Generates a fresh GCS inventory, persisting it to disk.
3. Re-opens the saved file and prints summary statistics.

Run it only in environments where valid Google Cloud credentials and network
access are available.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from autopotter_tools.gcs_manager import GCSManager  # noqa: E402
from autopotter_tools.simplelogger import Logger  # noqa: E402


def build_inventory(config_path: Path, output_path: Path) -> dict:
    """Create the inventory file on disk and return the in-memory payload."""
    manager = GCSManager(str(config_path))
    inventory = manager.generate_inventory(str(output_path))
    Logger.info(f"Inventory written to {output_path}")
    return inventory


def print_stats(inventory: dict) -> None:
    """Emit basic statistics for the generated inventory."""
    summary = inventory.get("summary", {})
    total_files = summary.get("total_files", 0)
    total_size = summary.get("total_size_mb", 0)
    collected_at = inventory.get("collection_info", {}).get("collected_at", "unknown timestamp")

    print("\n=== GCS Inventory Summary ===")
    print(f"Collected at: {collected_at}")
    print(f"Total files : {total_files}")
    print(f"Total size  : {total_size} MB")

    print("\nFolders:")
    files_by_folder = inventory.get("files_by_folder", {})
    for folder_url, files in sorted(files_by_folder.items()):
        print(f"  - {folder_url} -> {len(files)} files")

    print("=============================\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Integration test for GCSManager inventory generation.")
    parser.add_argument(
        "--config",
        default="autopost_config.enhanced.json",
        help="Path to the autopost configuration JSON file.",
    )
    parser.add_argument(
        "--output",
        default="tests/gcs_inventory_integration_test.json",
        help="Where to write the generated inventory JSON.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    if not config_path.is_file():
        Logger.error(f"Config file not found: {config_path}")
        return 1

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        build_inventory(config_path, output_path)
        inventory_from_disk = json.loads(output_path.read_text(encoding="utf-8"))
        print_stats(inventory_from_disk)
    except Exception as exc:  # pragma: no cover - integration/logging focused
        Logger.error(f"Integration test failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())



