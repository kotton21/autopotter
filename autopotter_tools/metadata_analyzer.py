from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence

from pydantic import BaseModel

try:  # pragma: no cover - optional dependency for tests
    from autopotter_tools.gpt_api import GPTAPI
except Exception:  # pylint: disable=broad-except
    GPTAPI = None  # type: ignore

from autopotter_tools.media_models import MediaFrameMetadata
from autopotter_tools.simplelogger import Logger

if TYPE_CHECKING:  # pragma: no cover
    from config import ConfigManager


@dataclass
class FrameAnalysisRequest:
    frame_id: str
    parent_media_id: str
    timestamp: Optional[float]
    preview_path: Path
    orientation: str
    filename_tokens: Sequence[str]


class FramesMetadataBatch(BaseModel):
    frames: List[MediaFrameMetadata]


class BaseMetadataAnalyzer:
    def submit(self, request: FrameAnalysisRequest) -> List[MediaFrameMetadata]:
        raise NotImplementedError

    def flush(self) -> List[MediaFrameMetadata]:
        return []


class SimpleMetadataAnalyzer(BaseMetadataAnalyzer):
    """
    Lightweight stand-in for GPT metadata extraction.
    Uses filename cues + orientation hints to populate MediaFrameMetadata fields.
    """

    MATERIAL_KEYWORDS = {
        "clay": "clay",
        "porcelain": "porcelain",
        "terra": "terracotta",
        "timelapse": "timelapse",
        "rv": "rv_series",
    }

    ACTIVITY_KEYWORDS = {
        "timelapse": "timelapse",
        "print": "3d_printing",
        "gcode": "gcode_render",
        "process": "process_detail",
        "reveal": "reveal",
    }

    def submit(self, request: FrameAnalysisRequest) -> List[MediaFrameMetadata]:
        metadata = self._describe_frame(request)
        return [metadata]

    def _describe_frame(self, request: FrameAnalysisRequest) -> MediaFrameMetadata:
        shot_type = self._infer_shot_type(request.orientation)
        activities = self._collect_keywords(request.filename_tokens, self.ACTIVITY_KEYWORDS)
        materials = self._collect_keywords(request.filename_tokens, self.MATERIAL_KEYWORDS)

        use_case = None
        if "timelapse" in activities:
            use_case = "process_detail"
        elif request.timestamp is not None and request.timestamp < 1.0:
            use_case = "hook"

        quality_notes = "Auto-generated metadata from filename heuristics."

        embedding_hints: List[str] = [
            shot_type or "",
            use_case or "",
            request.orientation,
        ]
        embedding_hints.extend(activities)
        embedding_hints.extend(materials)

        return MediaFrameMetadata(
            frame_id=request.frame_id,
            parent_media_id=request.parent_media_id,
            timestamp=request.timestamp,
            image_path=str(request.preview_path),
            shot_type=shot_type,
            emotional_tone="artistic" if "timelapse" in activities else "calming",
            use_case=use_case,
            activities=activities,
            materials=materials,
            objects_detected=[],
            quality_notes=quality_notes,
            embedding_hints=[hint for hint in embedding_hints if hint],
        )

    @staticmethod
    def _infer_shot_type(orientation: str) -> str:
        if orientation == "portrait":
            return "closeup"
        return "wide"

    @staticmethod
    def _collect_keywords(tokens: Sequence[str], vocabulary: Dict[str, str]) -> List[str]:
        collected: List[str] = []
        for token in tokens:
            normalized = re.sub(r"[^a-z0-9]+", "", token.lower())
            if not normalized:
                continue
            for pattern, label in vocabulary.items():
                if pattern in normalized:
                    collected.append(label)
        return sorted(set(collected))


DEFAULT_SYSTEM_INSTRUCTIONS = dedent(
    """
    You are an assistant that analyzes pottery-making images and returns structured
    metadata using the MediaFrameMetadata schema. Only respond with valid JSON that fits
    the schema provided. Respect the enumerated values for shot_type, emotional_tone, and use_case.
    """
).strip()

DEFAULT_PROMPT_INSTRUCTIONS = dedent(
    """
    Analyze each frame preview and populate every field in MediaFrameMetadata.
    Allowed shot_type values: ["macro","closeup","medium","wide","overhead","hands_only"].
    Allowed emotional_tone: ["calming","energetic","satisfying","chaotic","artistic"].
    Allowed use_case: ["hook","process_detail","texture_shot","reveal","b_roll"].
    Use filename tokens as hints for activities/materials and guess if uncertain.
    """
).strip()


class GPTMetadataAnalyzer(BaseMetadataAnalyzer):
    """
    Uses GPT via GPTAPI to analyze frames in batches and return MediaFrameMetadata objects.
    """

    def __init__(
        self,
        *,
        config_manager: "ConfigManager",
        config: Dict[str, object],
        frames_per_call: int = 10,
    ):
        self.config_manager = config_manager
        self.frames_per_call = max(1, frames_per_call)
        self.buffer: List[FrameAnalysisRequest] = []

        previous_response_id = config.get("metadata_previous_response_id")
        model = config.get("gpt_model")
        use_prev = bool(config.get("gpt_use_previous_response_id", False))
        if GPTAPI is None:
            raise RuntimeError(
                "GPTAPI is unavailable. Install OpenAI dependencies to use GPT metadata analysis."
            )
        self.gpt_client = GPTAPI(
            model=model,
            use_previous_response_id=use_prev,
            previous_response_id=previous_response_id,
        )
        self.prompt_context = str(
            config.get("metadata_prompt_instructions") or DEFAULT_PROMPT_INSTRUCTIONS
        )
        self.dev_instructions = str(
            config.get("metadata_system_prompt") or DEFAULT_SYSTEM_INSTRUCTIONS
        )
        Logger.info("Initialized GPTMetadataAnalyzer in GPT mode")

    def submit(self, request: FrameAnalysisRequest) -> List[MediaFrameMetadata]:
        self.buffer.append(request)
        if len(self.buffer) >= self.frames_per_call:
            return self._process_buffer()
        return []

    def flush(self) -> List[MediaFrameMetadata]:
        if not self.buffer:
            return []
        return self._process_buffer()

    def _process_buffer(self) -> List[MediaFrameMetadata]:
        batch = self.buffer
        self.buffer = []
        payload = [
            {
                "frame_id": req.frame_id,
                "parent_media_id": req.parent_media_id,
                "image_path": str(req.preview_path),
                "timestamp": req.timestamp,
                "orientation": req.orientation,
                "filename_tokens": list(req.filename_tokens),
            }
            for req in batch
        ]

        prompt = dedent(
            f"""
            {self.prompt_context}

            Frames JSON:
            {json.dumps(payload, indent=2)}
            """
        ).strip()

        try:
            response = self.gpt_client.prompt(
                user_instructions=prompt,
                developer_instructions=self.dev_instructions,
                text_format=FramesMetadataBatch,
            )
            results = response.output_parsed.frames  # type: ignore[attr-defined]
            if self.gpt_client.previous_response_id:
                self.config_manager.set(
                    "metadata_previous_response_id",
                    self.gpt_client.previous_response_id,
                )
            return results
        except Exception as exc:  # pragma: no cover - fallback path
            Logger.error(f"GPT metadata analysis failed: {exc}. Falling back to heuristic analyzer.")
            fallback = SimpleMetadataAnalyzer()
            flattened: List[MediaFrameMetadata] = []
            for request in payload:
                frame_request = FrameAnalysisRequest(
                    frame_id=request["frame_id"],
                    parent_media_id=request["parent_media_id"],
                    timestamp=request["timestamp"],
                    preview_path=Path(request["image_path"]),
                    orientation=request["orientation"],
                    filename_tokens=request["filename_tokens"],
                )
                flattened.extend(fallback.submit(frame_request))
            return flattened

