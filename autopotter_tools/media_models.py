from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    media_id: str
    path: str
    media_type: Literal["video", "image"]
    metadata: Dict[str, Optional[float | int | str]] = Field(default_factory=dict)


class MediaFrameMetadata(BaseModel):
    frame_id: str
    parent_media_id: str
    timestamp: Optional[float]
    image_path: str

    shot_type: Optional[Literal[
        "macro", "closeup", "medium", "wide", "overhead", "hands_only"
    ]] = None
    emotional_tone: Optional[Literal[
        "calming", "energetic", "satisfying", "chaotic", "artistic"
    ]] = None
    use_case: Optional[Literal[
        "hook", "process_detail", "texture_shot", "reveal", "b_roll"
    ]] = None
    activities: List[str] = Field(default_factory=list)
    materials: List[str] = Field(default_factory=list)
    objects_detected: List[str] = Field(default_factory=list)
    quality_notes: Optional[str] = None
    embedding_hints: List[str] = Field(default_factory=list)

    def keyword_blob(self) -> str:
        """Return a flat string suitable for LIKE queries."""
        tokens: List[str] = []
        attrs = [
            self.shot_type,
            self.emotional_tone,
            self.use_case,
            self.quality_notes,
        ]
        tokens.extend([a for a in attrs if a])
        tokens.extend(self.activities)
        tokens.extend(self.materials)
        tokens.extend(self.objects_detected)
        tokens.extend(self.embedding_hints)
        return " ".join(tokens).lower()


class FrameEmbedding(BaseModel):
    frame_id: str
    embedding: List[float]

