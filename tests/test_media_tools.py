from pathlib import Path

import pytest
from PIL import Image

from autopotter_tools.media_tools import (
    HAS_CV2,
    downsample_and_store,
    ensure_preview_path,
    frame_extractor,
    get_media_metadata,
)

TEST_IMAGE = Path("tests/test_images/timelapse_rv01.gcode_20250429_1524.jpg")
TEST_VIDEO = Path("tests/test_images/timelapse_rv01.gcode_20250429_1524.mp4")


def test_get_media_metadata_image():
    metadata = get_media_metadata(TEST_IMAGE)
    assert metadata["width"] > 0
    assert metadata["height"] > 0
    assert metadata["orientation"] in {"landscape", "portrait"}


def test_downsample_creates_parallel_preview(tmp_path):
    preview_root = tmp_path / "previews"
    preview_path = ensure_preview_path(Path(TEST_IMAGE.name), preview_root, suffix=".jpg")
    with Image.open(TEST_IMAGE) as img:
        stored = downsample_and_store(img, preview_path, max_px=64)

    assert stored.exists()
    assert stored.parent == preview_root


@pytest.mark.skipif(not HAS_CV2, reason="OpenCV not available in test environment")
def test_frame_extractor_returns_frame():
    frames = list(frame_extractor(TEST_VIDEO, interval_seconds=1.0, max_frames=1))
    assert len(frames) == 1
    image, timestamp = frames[0]
    assert image.width > 0
    assert timestamp >= 0.0

