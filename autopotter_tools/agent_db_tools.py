from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import random

from autopotter_tools.embedding_service import EmbeddingService
from autopotter_tools.gcs_manager import GCSManager
from autopotter_tools.media_database import MediaDatabase
from autopotter_tools.media_models import MediaFrameMetadata
from autopotter_tools.simplelogger import Logger
from config import ConfigManager


def _strip_image_path(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove image_path if present to keep responses lighter."""
    if isinstance(data, dict):
        data.pop("image_path", None)
    return data


class AgentDBTools:
    """
    Lightweight helper that exposes agent-friendly tools for media search.

    The constructor validates that the configured SQLite database is present
    locally, pulling it from GCS if needed.
    """

    def __init__(self, config_path: str = "autopost_config.enhanced.json") -> None:
        self.config_path = config_path
        self.config = ConfigManager(config_path)
        self._raw_db_setting = (
            self.config.get("agentdraft_metadata_database"))
        if not self._raw_db_setting:
            raise ValueError(
                "agentdraft_metadata_database is required."
            )

        self.db_path = self._resolve_db_path(self._raw_db_setting)
        self._db: Optional[MediaDatabase] = None
        self._embedder: Optional[EmbeddingService] = None

        # Validate or fetch the database immediately.
        self.check_get_db()

    def _resolve_db_path(self, configured_path: str) -> Path:
        """Resolve the configured DB path relative to the config file when needed."""
        candidate = Path(configured_path).expanduser()
        if candidate.is_absolute():
            return candidate

        config_dir = Path(self.config_path).expanduser().parent
        try:
            return (config_dir / candidate).resolve()
        except FileNotFoundError:
            # resolve() can raise if parent dirs are missing on some platforms
            return (config_dir / candidate)

    def _gcs_object_path(self) -> str:
        """Return the GCS blob path for the configured database."""
        # Use the configured value as the blob path, stripping any leading slash.
        return Path(self._raw_db_setting).as_posix().lstrip("/")

    def check_get_db(self) -> Path:
        """
        Ensure the SQLite database exists locally. Download from GCS if missing.
        Raises FileNotFoundError/RuntimeError on failure.
        """
        if self.db_path.exists():
            Logger.info(f"Using local database at {self.db_path}")
        else:
            Logger.info(
                "[agent_db_tools] Database not found locally; attempting GCS download..."
            )
            self._download_db_from_gcs()

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Media metadata database not available at {self.db_path}"
            )

        if self._db is None:
            self._db = MediaDatabase(self.db_path)

        return self.db_path

    def _download_db_from_gcs(self) -> None:
        """Download the configured database from GCS to the local path."""
        gcs_blob_path = self._gcs_object_path()
        try:
            manager = GCSManager(self.config_path)
        except Exception as exc:
            raise RuntimeError(
                "Failed to initialize GCSManager while fetching metadata DB."
            ) from exc

        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            blob = manager.bucket.blob(gcs_blob_path)
            if not blob.exists():
                raise FileNotFoundError(
                    f"GCS object '{gcs_blob_path}' not found in bucket {manager.bucket.name}"
                )
            blob.download_to_filename(str(self.db_path))
            Logger.info(
                f"[agent_db_tools] Downloaded database from gs://{manager.bucket.name}/{gcs_blob_path}"
            )
        except Exception as exc:
            Logger.error(f"[agent_db_tools] Failed to fetch database: {exc}")
            raise

    def _ensure_db(self) -> MediaDatabase:
        """Lazily initialize and return the media database handle."""
        if self._db is None:
            self.check_get_db()
        return self._db  # type: ignore[return-value]

    def _ensure_embedder(self) -> EmbeddingService:
        """Lazily initialize and return the embedding service."""
        if self._embedder is None:
            self._embedder = EmbeddingService(
                api_key=self.config.get("openai_api_key"),
                model=self.config.get("dbbuilder_embedding_model", "text-embedding-3-small"),
            )
        return self._embedder

    def search_keyword(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Keyword search over frame metadata."""
        if not keyword:
            raise ValueError("keyword is required.")

        # Get frame, and parent path and metadata!
        db = self._ensure_db()
        search_results = db.search_by_keyword(keyword, limit=limit)
        
        results = [item.to_clean_dict(ids=True) for item in search_results]
        for item in results:
            item.pop("image_path", None) # should absolutely not include the frame image path!!!
            item.pop("frame_id", None)
            parent_media_id = item.pop("parent_media_id", None)
            parent_media = db.get_media_item(parent_media_id)
            if parent_media:
                item["parent_media"] = parent_media.to_clean_dict()
        return results
        

    def search_mult_keywords_rand(self, keywords: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Keywords search over frame metadata."""
        if not keywords:
            raise ValueError("keyword is required.")

        terms = [term.strip() for term in keywords.split() if term.strip()]
        if not terms:
            raise ValueError("keyword is required.")

        db = self._ensure_db()
        aggregated = []
        seen_ids = set[Any]()

        for term in terms:
            hits = db.search_by_keyword(term, limit=limit)
            for item in hits:
                frame_id = getattr(item, "frame_id", None)
                if frame_id and frame_id in seen_ids:
                    continue
                if frame_id:
                    seen_ids.add(frame_id)
                aggregated.append(item)

        random.shuffle(aggregated)
        return [_strip_image_path(db.to_dict(item)) for item in aggregated[:limit]]

    def search_semantic(
        self, text: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Semantic similarity search using OpenAI embeddings."""
        if not text:
            raise ValueError("text is required for semantic search.")

        embedder = self._ensure_embedder()
        vector = embedder.embed(text)
        db = self._ensure_db()
        scored = db.search_by_embedding(vector, limit=limit)

        results = [(sim,item.to_clean_dict(ids=True)) for sim,item in scored]
        for _,item in results:
            item.pop("image_path", None) # should absolutely not include the frame image path!!!
            parent_media_id = item.pop("parent_media_id", None)
            parent_media = db.get_media_item(parent_media_id)
            if parent_media:
                item["parent_media"] = parent_media.to_clean_dict()
        # return results
        
        return [
            {
                "similarity": similarity,
                "frame": item,
            }
            for similarity, item in results
        ]

    @staticmethod
    def get_agent_tool_defs() -> List[Dict[str, Any]]:
        """Return tool definitions formatted for the Responses API (toolcalling)."""
        schema = [
            {
                "type": "function",
                "name": "search_keyword",
                "description": "Find media frames by keyword(s) across indexed metadata fields. This function searches a word, or exact phrase. Use it for single words, or short phrases.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "single keyword or exact phrase"},
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return.",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 10,
                        },
                    },
                    "required": ["keyword"],
                },
            },
            {
                "type": "function",
                "name": "search_semantic",
                "description": "Semantic similarity search using OpenAI embeddings over media frames. This function gives ranked results based on similarity of the search text. It can be used for one word, or as many words as you like.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Natural language description to embed and search."},
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return.",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 10,
                        },
                    },
                    "required": ["text"],
                },
            },
            # {
            #     "type": "function",
            #     "name": "validate_json2video_config",
            #     "description": "Validation of a json2video config string.",
            #     "parameters": {
            #         "type": "object",
            #         "properties": {
            #             "json2video_config_str": {"type": "string", "description": "The json2video config string to validate."},
            #         },
            #         "required": ["text"],
            #     },
            # },
        ]
        return schema


# Convenience export for callers that just need the tool schema.
TOOLS: List[Dict[str, Any]] = AgentDBTools.get_agent_tool_defs()

