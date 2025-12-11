from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Tuple
import json

from config import ConfigManager


def load_db_path(config_path: Path) -> Path:
    cfg = ConfigManager(str(config_path)).config
    raw = (
        cfg.get("agentdraft_metadata_database")
        or cfg.get("dbbuilder_media_database_path")
        or "media_frames.sqlite"
    )
    db_path = Path(raw)
    if not db_path.is_absolute():
        db_path = (config_path.parent / db_path).resolve()
    return db_path


def strip_paths(
    db_path: Path, *, dry_run_limit: Optional[int] = None
) -> Tuple[int, int, int, list[str]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    rows_items = cursor.execute("SELECT media_id, path FROM media_items").fetchall()
    updates_items = []
    previews: list[str] = []
    for row in rows_items:
        raw_path = row["path"] or ""
        path_obj = Path(raw_path)
        parts = path_obj.parts
        new_path = Path(parts[-2], parts[-1]).as_posix() if len(parts) >= 2 else path_obj.name
        if new_path != raw_path:
            updates_items.append((new_path, row["media_id"]))
            if dry_run_limit is not None and len(previews) < dry_run_limit:
                previews.append(f"{raw_path} -> {new_path}")

    # Frames table uses image_path column.
    rows_frames = cursor.execute("SELECT frame_id, image_path, metadata FROM frames").fetchall()
    updates_frames = []
    for row in rows_frames:
        raw_path = row["image_path"] or ""
        path_obj = Path(raw_path)
        parts = path_obj.parts
        new_path = Path(parts[-2], parts[-1]).as_posix() if len(parts) >= 2 else path_obj.name
        meta_raw = row["metadata"] or ""
        meta_new = meta_raw
        try:
            meta_obj = json.loads(meta_raw)
            meta_img = meta_obj.get("image_path")
            if meta_img:
                meta_obj["image_path"] = Path(meta_img).name if len(Path(meta_img).parts) < 2 else Path(meta_img).parts[-2] + "/" + Path(meta_img).name
                meta_new = json.dumps(meta_obj)
        except Exception:
            # keep original metadata if parsing fails
            meta_new = meta_raw

        if new_path != raw_path or meta_new != meta_raw:
            updates_frames.append((new_path, meta_new, row["frame_id"]))
            if dry_run_limit is not None and len(previews) < dry_run_limit:
                previews.append(f"{raw_path} -> {new_path}")

    if (updates_items or updates_frames) and dry_run_limit is None:
        cursor.executemany(
            "UPDATE media_items SET path = ? WHERE media_id = ?",
            updates_items,
        )
        cursor.executemany(
            "UPDATE frames SET image_path = ?, metadata = ? WHERE frame_id = ?",
            updates_frames,
        )
        conn.commit()

    return len(rows_items), len(updates_items), len(updates_frames), previews


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Strip directory prefixes from media_items.path entries."
    )
    parser.add_argument(
        "--config",
        default="autopost_config.database.json",
        help="Path to config file that points to the target database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not modify the database; print the first 10 path changes.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    db_path = load_db_path(config_path)

    total_items, changed_items, changed_frames, previews = strip_paths(
        db_path, dry_run_limit=(10 if args.dry_run else None)
    )
    if args.dry_run:
        print(
            "[strip_media_item_paths] DRY RUN "
            f"items_processed={total_items} items_update={changed_items} "
            f"frames_update={changed_frames}"
        )
        for preview in previews:
            print(f"  {preview}")
    else:
        print(
            "[strip_media_item_paths] "
            f"items_processed={total_items} items_updated={changed_items} "
            f"frames_updated={changed_frames} db={db_path}"
        )


if __name__ == "__main__":
    main()

