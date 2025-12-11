from __future__ import annotations

import base64
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

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
        """Return metadata rows for a single frame request."""
        raise NotImplementedError

    def flush(self) -> List[MediaFrameMetadata]:
        """Return any buffered results that still need to be emitted."""
        return []

    def get_usage_totals(self) -> Dict[str, int]:
        """Return aggregate token usage information, if available."""
        return {}

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
        """Configure GPT metadata analysis, batching, and prompt instructions."""
        self.config_manager = config_manager
        self.frames_per_call = max(1, frames_per_call)
        self.buffer: List[FrameAnalysisRequest] = []
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_image_tokens: int = 0

        previous_response_id = config.get("dbbuilder_previous_response_id")
        model = config.get("metadata_gpt_model") or config.get("gpt_model")
        use_prev = bool(config.get("dbbuilder_use_previous_response_id", False))
        if GPTAPI is None:
            raise RuntimeError(
                "GPTAPI is unavailable. Install OpenAI dependencies to use GPT metadata analysis."
            )
        try:
            # Initialize GPT client with optional response-id reuse for threading.
            self.gpt_client = GPTAPI(
                model=model,
                use_previous_response_id=use_prev,
                previous_response_id=previous_response_id,
            )
        except Exception as exc:
            raise RuntimeError(
                "Failed to initialize GPT client for metadata analysis."
            ) from exc
        self.prompt_context = str(
            config.get("dbbuilder_prompt_instructions") or DEFAULT_PROMPT_INSTRUCTIONS
        )
        self.dev_instructions = str(
            config.get("dbbuilder_system_prompt") or DEFAULT_SYSTEM_INSTRUCTIONS
        ) + "\n" + str( 
            config.get("dbbuilder_campaign_specific_analysis_prompt") or ""
        ).strip()
        Logger.info("Initialized GPTMetadataAnalyzer in GPT mode")

    def submit(self, request: FrameAnalysisRequest) -> List[MediaFrameMetadata]:
        """Queue a frame for GPT processing and emit when the batch fills."""
        self.buffer.append(request)
        if len(self.buffer) >= self.frames_per_call:
            return self._process_buffer()
        return []

    def flush(self) -> List[MediaFrameMetadata]:
        """Force processing of partially filled batches."""
        if not self.buffer:
            return []
        return self._process_buffer()

    def _process_buffer(self) -> List[MediaFrameMetadata]:
        """Send queued frames to GPT and convert the structured response."""
        batch = self.buffer
        self.buffer = []
        # Build the JSON payload that becomes part of the prompt for each frame.
        payload = [
            {
                "frame_id": req.frame_id,
                "parent_media_id": req.parent_media_id,
                "image_path": str(req.preview_path),
                "timestamp": req.timestamp,
            }
            for req in batch
        ]

        # Alternate instruction text and encoded images to satisfy the multimodal API shape.
        content_blocks: List[Dict[str, object]] = [
            {"type": "input_text", "text": self.prompt_context}
        ]
        image_stats: List[Dict[str, object]] = []
        for descriptor in payload:
            # Provide structured JSON describing the frame for textual context.
            content_blocks.append(
                {
                    "type": "input_text",
                    "text": f"Frame request:\n{json.dumps(descriptor, indent=2)}",
                }
            )
            image_url, byte_size = self._encode_image(Path(descriptor["image_path"]))
            # Follow each description with the actual image data URL.
            content_blocks.append(
                {
                    "type": "input_image",
                    "image_url": image_url,
                }
            )
            # Track bytes for logging/observability of image payload sizes.
            image_stats.append(
                {"frame_id": descriptor["frame_id"], "bytes": byte_size}
            )

        try:
            response = self.gpt_client.prompt(
                user_instructions=content_blocks,
                developer_instructions=self.dev_instructions,
                text_format=FramesMetadataBatch,
            )
            results = response.output_parsed.frames  # type: ignore[attr-defined]

            usage = getattr(response, "usage", None)
            image_tokens = "?"
            if usage:
                input_tokens = getattr(usage, "input_tokens", 0) or 0
                output_tokens = getattr(usage, "output_tokens", 0) or 0
                self.total_input_tokens += int(input_tokens)
                self.total_output_tokens += int(output_tokens)

                if hasattr(usage, "input_tokens_details"):
                    image_tokens_value = getattr(
                        usage.input_tokens_details, "image_tokens", 0
                    ) or 0
                    self.total_image_tokens += int(image_tokens_value)
                    image_tokens = image_tokens_value
                else:
                    image_tokens = "?"
            # Track image token spend for observability on GPT usage.
            Logger.info(
                "Analyzed %s frames (%s bytes) -> image_tokens=%s"
                % (
                    len(image_stats),
                    sum(item["bytes"] for item in image_stats),
                    image_tokens,
                )
            )

            if self.gpt_client.previous_response_id:
                self.config_manager.set(
                    "dbbuilder_previous_response_id",
                    self.gpt_client.previous_response_id,
                )
            return results
        except Exception as exc:  # pragma: no cover
            Logger.error(f"GPT metadata analysis failed: {exc}")
            raise

    def _encode_image(self, path: Path) -> Tuple[str, int]:
        """Return a data URL and byte length for embedding the preview in GPT prompts."""
        raw = path.read_bytes()
        mime_type, _ = mimetypes.guess_type(path.name)
        mime_type = mime_type or "image/jpeg"
        # data: URLs let us send the binary inline without an external host.
        encoded = base64.b64encode(raw).decode("utf-8")
        data_url = f"data:{mime_type};base64,{encoded}"
        return data_url, len(raw)

    def get_usage_totals(self) -> Dict[str, int]:
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "image_tokens": self.total_image_tokens,
        }

