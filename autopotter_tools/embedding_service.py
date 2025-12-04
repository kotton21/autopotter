from __future__ import annotations

import os
from typing import List, Optional

from autopotter_tools.simplelogger import Logger

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - openai optional in tests
    OpenAI = None  # type: ignore


class EmbeddingService:
    """Small wrapper around OpenAI embeddings. Fails fast if requirements are missing."""

    def __init__(
        self,
        api_key: Optional[str],
        model: str = "text-embedding-3-small",
    ):
        if OpenAI is None:
            raise RuntimeError("openai package not installed; cannot build embeddings.")

        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise RuntimeError("OpenAI API key is required for embeddings.")

        self.model = model
        self.client = OpenAI(api_key=resolved_key)

    def build_embedding_text(self, metadata) -> str:
        """Flatten metadata into a short descriptive string."""
        parts = [
            metadata.shot_type or "",
            metadata.emotional_tone or "",
            metadata.use_case or "",
            " ".join(metadata.activities),
            " ".join(metadata.materials),
            " ".join(metadata.objects_detected),
            metadata.quality_notes or "",
            " ".join(metadata.embedding_hints),
        ]
        return " ".join(part for part in parts if part).strip()

    def embed(self, text: str) -> List[float]:
        if not text:
            text = "empty"

        response = self.client.embeddings.create(model=self.model, input=text)
        return list(response.data[0].embedding)

