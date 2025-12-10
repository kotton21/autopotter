from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Tuple

from config import ConfigManager


def load_db_path(config_path: Path) -> Path:
    cfg = ConfigManager(str(config_path)).config
    raw = cfg.get("media_database_path", "media_frames.sqlite")
    db_path = Path(raw)
    if not db_path.is_absolute():
        db_path = (config_path.parent / db_path).resolve()
    return db_path


def strip_paths(db_path: Path, *, dry_run_limit: Optional[int] = None) -> Tuple[int, int, list[str]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    rows = cursor.execute("SELECT media_id, path FROM media_items").fetchall()
    updates = []
    previews: list[str] = []
    for row in rows:
        raw_path = row["path"] or ""
        path_obj = Path(raw_path)
        parts = path_obj.parts
        new_path = Path(parts[-2], parts[-1]).as_posix() if len(parts) >= 2 else path_obj.name
        if new_path != raw_path:
            updates.append((new_path, row["media_id"]))
            if dry_run_limit is not None and len(previews) < dry_run_limit:
                previews.append(f"{raw_path} -> {new_path}")

    if updates and dry_run_limit is None:
        cursor.executemany(
            "UPDATE media_items SET path = ? WHERE media_id = ?",
            updates,
        )
        conn.commit()

    return len(rows), len(updates), previews


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

    total, changed, previews = strip_paths(
        db_path, dry_run_limit=(10 if args.dry_run else None)
    )
    if args.dry_run:
        print(f"[strip_media_item_paths] DRY RUN processed={total} would_update={changed}")
        for preview in previews:
            print(f"  {preview}")
    else:
        print(
            f"[strip_media_item_paths] processed={total} updated={changed} db={db_path}"
        )


if __name__ == "__main__":
    main()

