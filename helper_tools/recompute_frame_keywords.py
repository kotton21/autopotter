#!/usr/bin/env python3
"""
Recompute the `keywords` column for all frames from their stored metadata.

Dry-run processes only the first row, shows before/after, and does not commit.
"""

import argparse
import sqlite3
from pathlib import Path

from autopotter_tools.media_models import MediaFrameMetadata
from autopotter_tools.simplelogger import Logger


def _metadata_to_keyword_blob(meta_raw: str) -> str:
    """Deserialize frame metadata and compute its keyword blob."""
    meta = (
        MediaFrameMetadata.model_validate_json(meta_raw)
        if hasattr(MediaFrameMetadata, "model_validate_json")
        else MediaFrameMetadata.parse_raw(meta_raw)
    )
    return meta.keyword_blob()


def recompute_keywords(db_path: Path, dry_run: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    rows = cursor.execute(
        "SELECT frame_id, metadata, keywords FROM frames ORDER BY frame_id"
    ).fetchall()

    if not rows:
        print("No frames found.")
        conn.close()
        return

    updated = 0

    if dry_run:
        row = rows[0]
        new_blob = _metadata_to_keyword_blob(row["metadata"])
        print("Dry run: showing first row only (no commit).")
        print(f"frame_id: {row['frame_id']}")
        print(f"keywords (old): {row['keywords']}")
        print(f"keywords (new): {new_blob}")
        conn.rollback()
        conn.close()
        return

    for row in rows:
        new_blob = _metadata_to_keyword_blob(row["metadata"])
        if new_blob != row["keywords"]:
            cursor.execute(
                "UPDATE frames SET keywords = ? WHERE frame_id = ?",
                (new_blob, row["frame_id"]),
            )
            updated += 1

    conn.commit()
    conn.close()
    print(f"Done. Frames processed: {len(rows)}, updated: {updated}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute keywords column for frames from stored metadata."
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        required=True,
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process only the first row, print before/after, do not commit.",
    )
    args = parser.parse_args()

    recompute_keywords(Path(args.db_path), dry_run=args.dry_run)


if __name__ == "__main__":
    main()

