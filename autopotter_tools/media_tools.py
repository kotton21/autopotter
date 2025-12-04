from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

try:  # pragma: no cover - import guard exercised in tests
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore

from PIL import Image, ImageOps

from autopotter_tools.simplelogger import Logger
HAS_CV2 = cv2 is not None


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def safe_media_id(path: Path) -> str:
    """Create a stable identifier for a given path."""
    normalized = str(path.resolve())
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    return digest[:12]


def frame_extractor(
    video_path: Path,
    interval_seconds: float = 2.0,
    max_frames: Optional[int] = None,
) -> Iterator[Tuple[Image.Image, float]]:
    """
    Yield PIL Frames and timestamps for a video using cv2 for portability.
    """
    if cv2 is None:
        raise RuntimeError("OpenCV is required for video frame extraction.")
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Unable to open video {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = max(int(fps * interval_seconds), 1)
    frame_index = 0
    produced = 0

    while True:
        ok, frame = capture.read()
        if not ok:
            break

        if frame_index % frame_interval == 0:
            timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            yield image, timestamp

            produced += 1
            if max_frames and produced >= max_frames:
                break

        frame_index += 1

    capture.release()


def downsample_and_store(
    image: Image.Image,
    preview_path: Path,
    max_px: int = 320,
) -> Path:
    """Resize the largest side to max_px and save as JPEG."""
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    image = ImageOps.exif_transpose(image)
    image.thumbnail((max_px, max_px))
    image.convert("RGB").save(preview_path, format="JPEG", quality=90)
    return preview_path


def ensure_preview_path(
    source_relative: Path,
    preview_root: Path,
    suffix: Optional[str] = None,
) -> Path:
    """Return the preview path under preview_root mirroring relative structure."""
    preview_root.mkdir(parents=True, exist_ok=True)
    relative = source_relative
    if suffix:
        relative = relative.with_suffix(suffix)
    return preview_root / relative


def get_media_metadata(path: Path) -> Dict[str, float | int | str]:
    if is_image(path):
        with Image.open(path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "orientation": "landscape" if img.width >= img.height else "portrait",
            }

    if cv2 is None:
        Logger.warning("OpenCV missing; returning minimal metadata for video.")
        return {
            "width": 0,
            "height": 0,
            "duration": 0.0,
            "fps": 0.0,
            "frame_count": 0,
        }

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Unable to open media {path}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    width = capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0.0
    height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0.0
    duration = frame_count / fps if fps else 0.0
    capture.release()
    return {
        "fps": round(fps, 2),
        "frame_count": int(frame_count),
        "duration": round(duration, 2),
        "width": int(width),
        "height": int(height),
    }


def estimate_clip_span(timestamps: Sequence[float]) -> float:
    """Compute span between first and last timestamp."""
    if not timestamps:
        return 0.0
    if len(timestamps) == 1:
        return 1.0
    start = min(timestamps)
    end = max(timestamps)
    return round(end - start, 2) or 1.0

