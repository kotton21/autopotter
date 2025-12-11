from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    media_id: str
    path: str
    media_type: Literal["video", "image"]
    metadata: Dict[str, Optional[float | int | str]] = Field(default_factory=dict)

    def to_clean_dict(self, ids: bool = False) -> Dict[str, Any]:
        """Return a clean dict of the media item."""
        ret = {
            "path": self.path,
            "media_type": self.media_type,
            "metadata": self.metadata,
        }
        if ids:
            ret["media_id"] = self.media_id
        return ret


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
    image_qualities: List[str] = Field(default_factory=list)
    embedding_hints: List[str] = Field(default_factory=list)
    description: Optional[str] = None

    def to_clean_dict(self, ids: bool = False) -> Dict[str, Any]:
        """Return a clean dict of the media frame metadata."""
        
        ret = {
            # "image_path": self.image_path,
            "timestamp": self.timestamp,
            "shot_type": self.shot_type,
            "emotional_tone": self.emotional_tone,
            "use_case": self.use_case,
            "activities": self.activities,
            "materials": self.materials,
            "objects_detected": self.objects_detected,
            "image_qualities": self.image_qualities,
            "embedding_hints": self.embedding_hints,
            "description": self.description,
        }
        if ids:
            ret["frame_id"] = self.frame_id
            ret["parent_media_id"] = self.parent_media_id
        return ret

    def keyword_blob(self) -> str:
        """Return a flat string suitable for LIKE queries."""
        tokens: List[str] = []

        def _extend(value) -> None:
            if not value:
                return
            if isinstance(value, str):
                tokens.append(value)
            elif isinstance(value, (list, tuple, set)):
                for item in value:
                    if item:
                        tokens.append(str(item))
            else:
                tokens.append(str(value))

        _extend(self.shot_type)
        _extend(self.emotional_tone)
        _extend(self.use_case)
        _extend(self.activities)
        _extend(self.materials)
        _extend(self.objects_detected)
        _extend(self.image_qualities)
        _extend(self.embedding_hints)
        _extend(self.description)

        return " ".join(tokens).lower()


class FrameEmbedding(BaseModel):
    frame_id: str
    embedding: List[float]

