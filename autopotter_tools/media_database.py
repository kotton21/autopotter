from __future__ import annotations

import importlib
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from autopotter_tools.media_models import MediaFrameMetadata, MediaItem
from autopotter_tools.simplelogger import Logger


class MediaDatabase:
    """
    MediaDatabase is a SQLite database that stores media items and frames, and their embeddings.
    """

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

    def search_by_embedding(
        self, query_embedding: List[float], limit: int = 10
    ) -> List[Tuple[float, MediaFrameMetadata]]:
        cursor = self.conn.cursor()
        rows = cursor.execute(
            """
            SELECT frames.metadata, embeddings.embedding
            FROM frames
            JOIN embeddings ON frames.frame_id = embeddings.frame_id
            """
        ).fetchall()

        scored: List[Tuple[float, MediaFrameMetadata]] = []
        for row in rows:
            metadata = (
                MediaFrameMetadata.model_validate_json(row["metadata"])
                if hasattr(MediaFrameMetadata, "model_validate_json")
                else MediaFrameMetadata.parse_raw(row["metadata"])
            )
            embedding = json.loads(row["embedding"])
            score = self._cosine_similarity(query_embedding, embedding)
            scored.append((score, metadata))

        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:limit]

    def find_closest_frame_by_embedding(
        self, query_embedding: List[float]
    ) -> Optional[Tuple[float, MediaFrameMetadata]]:
        """
        Return the single closest frame to the supplied embedding, or None if no embeddings exist.
        """

        if not query_embedding:
            return None

        matches = self.search_by_embedding(query_embedding, limit=1)
        return matches[0] if matches else None

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

    def get_db_size_and_rowcounts(self) -> Dict[str, dict]:
        """Return basic numberical stats about underlying sqlite file and tables."""
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

    def print_db_schema(self) -> None:
        """ Prints the database schema to the console. """
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_list")
        print("\n\nDatabase Schema:")
        for table in cursor.fetchall():
            table_name = table["name"]
            if table_name.startswith("sqlite_"):
                continue
            escaped_table = table_name.replace("'", "''")
            print(f"Table: {table_name}")

            cursor.execute(f"PRAGMA table_info('{escaped_table}')")
            for column in cursor.fetchall():
                print(f"  Column: {column['name']} ({column['type']})")

            cursor.execute(f"PRAGMA index_list('{escaped_table}')")
            for index in cursor.fetchall():
                print(f"  Index: {index['name']} unique={bool(index['unique'])}")
        print("\n\n")

    def compute_all_parrent_embeddings(self) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute("PRAGMA table_info('media_items')")
            columns = {row["name"] for row in cursor.fetchall()}
            if "avg_embedding" not in columns:
                cursor.execute(
                    """
                    ALTER TABLE media_items
                    ADD COLUMN avg_embedding TEXT
                    """
                )
                self.conn.commit()

            cursor.execute("UPDATE media_items SET avg_embedding = NULL")

            rows = cursor.execute(
                """
                SELECT f.parent_media_id, e.embedding
                FROM frames f
                INNER JOIN embeddings e ON f.frame_id = e.frame_id
                """
            ).fetchall()

            sum_vectors: Dict[str, List[float]] = {}
            counts: Dict[str, int] = defaultdict(int)

            for row in rows:
                parent_id = row["parent_media_id"]
                raw_embedding = row["embedding"]
                if not raw_embedding:
                    Logger.warning(
                        f"Skipping parent {parent_id}: empty child embedding payload."
                    )
                    continue

                try:
                    embedding = json.loads(raw_embedding)
                except json.JSONDecodeError:
                    Logger.warning(
                        f"Skipping parent {parent_id}: invalid child embedding JSON."
                    )
                    continue

                if not isinstance(embedding, list) or not embedding:
                    Logger.warning(
                        f"Skipping parent {parent_id}: child embedding missing values."
                    )
                    continue

                if parent_id not in sum_vectors:
                    sum_vectors[parent_id] = [0.0] * len(embedding)
                elif len(sum_vectors[parent_id]) != len(embedding):
                    Logger.warning(
                        f"Skipping frame for {parent_id}: embedding dimension mismatch."
                    )
                    continue

                sum_vectors[parent_id] = [
                    current + value
                    for current, value in zip(sum_vectors[parent_id], embedding)
                ]
                counts[parent_id] += 1

            updates: List[Tuple[str, str]] = []
            for parent_id, summed in sum_vectors.items():
                count = counts[parent_id]
                if not count:
                    continue
                avg_embedding = [value / count for value in summed]
                updates.append((json.dumps(avg_embedding), parent_id))

            if updates:
                cursor.executemany(
                    """
                    UPDATE media_items
                    SET avg_embedding = ?
                    WHERE media_id = ?
                    """,
                    updates,
                )
            self.conn.commit()
        except Exception as exc:
            Logger.error(f"Error computing all parent embeddings: {exc}")
            self.conn.rollback()
            raise exc

    def get_media_paths(self, media_ids: Sequence[str]) -> Dict[str, str]:
        if not media_ids:
            return {}

        cursor = self.conn.cursor()
        placeholders = ",".join("?" for _ in media_ids)
        rows = cursor.execute(
            f"""
            SELECT media_id, path
            FROM media_items
            WHERE media_id IN ({placeholders})
            """,
            tuple(media_ids),
        ).fetchall()

        return {row["media_id"]: row["path"] for row in rows}

    def get_media_avg_embeddings(self, media_ids: Sequence[str]) -> Dict[str, List[float]]:
        if not media_ids:
            return {}

        cursor = self.conn.cursor()
        placeholders = ",".join("?" for _ in media_ids)
        rows = cursor.execute(
            f"""
            SELECT media_id, avg_embedding
            FROM media_items
            WHERE media_id IN ({placeholders})
            """,
            tuple(media_ids),
        ).fetchall()

        embeddings: Dict[str, List[float]] = {}
        for row in rows:
            raw_embedding = row["avg_embedding"]
            if not raw_embedding:
                continue
            try:
                embedding = json.loads(raw_embedding)
            except json.JSONDecodeError:
                Logger.warning(
                    f"Skipping avg embedding for {row['media_id']}: invalid JSON payload."
                )
                continue
            if not isinstance(embedding, list) or not embedding:
                Logger.warning(
                    f"Skipping avg embedding for {row['media_id']}: missing values."
                )
                continue
            embeddings[row["media_id"]] = embedding

        return embeddings

    def cluster_media_items(
        self, n_clusters: int = 4, random_state: int = 42
    ) -> Tuple[Dict[str, str], Dict[str, float], float]:
        """
        Cluster media items by running KMeans over their avg_embedding vectors.

        Args:
            n_clusters: Desired number of clusters (will be capped by available rows).
            random_state: Seed to keep clustering deterministic between runs.

        Returns:
            Mapping of media_id -> cluster label (e.g. "cluster_0").
        """

        try:
            np = importlib.import_module("numpy")
            sklearn_cluster = importlib.import_module("sklearn.cluster")
            KMeansCls = getattr(sklearn_cluster, "KMeans")
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "cluster_media_items requires numpy and scikit-learn to be installed."
            ) from exc

        cursor = self.conn.cursor()
        rows = cursor.execute(
            """
            SELECT media_id, avg_embedding
            FROM media_items
            WHERE avg_embedding IS NOT NULL
            """
        ).fetchall()

        media_ids: List[str] = []
        vectors: List[List[float]] = []
        vector_dim: int | None = None

        for row in rows:
            raw_embedding = row["avg_embedding"]
            if not raw_embedding:
                continue
            try:
                embedding = json.loads(raw_embedding)
            except json.JSONDecodeError:
                Logger.warning(f"Skipping invalid embedding for {row['media_id']}")
                continue

            if not isinstance(embedding, list) or not embedding:
                Logger.warning(f"Skipping empty embedding for {row['media_id']}")
                continue

            if vector_dim is None:
                vector_dim = len(embedding)
            elif len(embedding) != vector_dim:
                Logger.warning(
                    f"Skipping embedding for {row['media_id']} due to mismatched dimension."
                )
                continue

            media_ids.append(row["media_id"])
            vectors.append(embedding)

        if not vectors:
            Logger.warning("No avg_embedding rows available for clustering.")
            return {}, {}, 0.0

        effective_clusters = min(n_clusters, len(vectors))
        if effective_clusters < 1:
            Logger.warning("Not enough embeddings to form clusters.")
            return {}, {}, 0.0

        matrix = np.vstack(vectors)
        kmeans = KMeansCls(
            n_clusters=effective_clusters,
            init="k-means++",
            random_state=random_state,
            n_init=10,
        )
        kmeans.fit(matrix)

        labels = kmeans.labels_.tolist()
        clusters = {
            media_id: f"cluster_{label}"
            for media_id, label in zip(media_ids, labels)
        }

        cluster_vectors: Dict[int, List[List[float]]] = defaultdict(list)
        for vector, label in zip(vectors, labels):
            cluster_vectors[label].append(vector)

        cluster_tightness: Dict[str, float] = {}
        for label, group_vectors in cluster_vectors.items():
            centroid = kmeans.cluster_centers_[label]
            if not group_vectors:
                continue
            distances = [
                float(np.linalg.norm(np.array(vector) - centroid))
                for vector in group_vectors
            ]
            if distances:
                cluster_tightness[f"cluster_{label}"] = float(
                    sum(distances) / len(distances)
                )

        inertia = float(getattr(kmeans, "inertia_", 0.0))
        return clusters, cluster_tightness, inertia

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)

