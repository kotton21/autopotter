from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, List

from autopotter_tools.media_models import MediaFrameMetadata, MediaItem
from autopotter_tools.simplelogger import Logger


class MediaDatabase:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        if self.db_path.parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS media_items (
                media_id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                media_type TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS frames (
                frame_id TEXT PRIMARY KEY,
                parent_media_id TEXT NOT NULL,
                timestamp REAL,
                image_path TEXT NOT NULL,
                metadata TEXT NOT NULL,
                keywords TEXT NOT NULL,
                FOREIGN KEY(parent_media_id) REFERENCES media_items(media_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                frame_id TEXT PRIMARY KEY,
                embedding TEXT NOT NULL,
                FOREIGN KEY(frame_id) REFERENCES frames(frame_id)
            )
            """
        )
        self.conn.commit()

    def save_media_item(self, media: MediaItem) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO media_items (media_id, path, media_type, metadata)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(media_id) DO UPDATE SET
                path=excluded.path,
                media_type=excluded.media_type,
                metadata=excluded.metadata
            """,
            (
                media.media_id,
                media.path,
                media.media_type,
                json.dumps(media.metadata),
            ),
        )
        self.conn.commit()

    def save_frame_metadata(self, frame: MediaFrameMetadata) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO frames (frame_id, parent_media_id, timestamp, image_path, metadata, keywords)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(frame_id) DO UPDATE SET
                parent_media_id=excluded.parent_media_id,
                timestamp=excluded.timestamp,
                image_path=excluded.image_path,
                metadata=excluded.metadata,
                keywords=excluded.keywords
            """,
            (
                frame.frame_id,
                frame.parent_media_id,
                frame.timestamp,
                frame.image_path,
                frame.model_dump_json() if hasattr(frame, "model_dump_json") else frame.json(),
                frame.keyword_blob(),
            ),
        )
        self.conn.commit()

    def save_embedding(self, frame_id: str, embedding: List[float]) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO embeddings (frame_id, embedding)
            VALUES (?, ?)
            ON CONFLICT(frame_id) DO UPDATE SET
                embedding=excluded.embedding
            """,
            (frame_id, json.dumps(embedding)),
        )
        self.conn.commit()

    def search_by_keyword(self, keyword: str, limit: int = 10) -> List[MediaFrameMetadata]:
        keyword_like = f"%{keyword.lower()}%"
        cursor = self.conn.cursor()
        rows = cursor.execute(
            """
            SELECT metadata FROM frames
            WHERE keywords LIKE ?
            ORDER BY timestamp ASC
            LIMIT ?
            """,
            (keyword_like, limit),
        ).fetchall()

        return [
            MediaFrameMetadata.model_validate_json(row["metadata"])
            if hasattr(MediaFrameMetadata, "model_validate_json")
            else MediaFrameMetadata.parse_raw(row["metadata"])
            for row in rows
        ]

    def count_frames(self) -> int:
        cursor = self.conn.cursor()
        value = cursor.execute("SELECT COUNT(*) FROM frames").fetchone()[0]
        return int(value)

    def list_media_ids(self) -> List[str]:
        cursor = self.conn.cursor()
        rows = cursor.execute("SELECT media_id FROM media_items").fetchall()
        return [row["media_id"] for row in rows]

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception as exc:  # pragma: no cover
            Logger.warning(f"Failed to close database: {exc}")

    def __enter__(self) -> "MediaDatabase":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def describe_stats(self) -> Dict[str, dict]:
        """Return basic stats about underlying sqlite file and tables."""
        import os

        info: Dict[str, dict] = {"tables": {}}
        if self.db_path and os.path.exists(self.db_path):
            info["path"] = str(self.db_path)
            info["size_bytes"] = os.path.getsize(self.db_path)
        else:  # pragma: no cover
            Logger.warning("Database path unavailable; skipping size metric.")

        cursor = self.conn.cursor()
        for table in ("media_items", "frames", "embeddings"):
            try:
                value = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                info["tables"][table] = int(value)
            except Exception as exc:  # pragma: no cover
                Logger.warning(f"Failed counting rows in {table}: {exc}")
        return info

