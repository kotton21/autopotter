from __future__ import annotations

import argparse
from pathlib import Path
import json

from autopotter_tools.media_tools import (
    downsample_and_store,
    ensure_preview_path,
    get_media_metadata,
    is_image,
)
from autopotter_tools.media_database_pipeline import FrameAnalysisRequest
from autopotter_tools.metadata_analyzer import GPTMetadataAnalyzer
from config import ConfigManager


def analyze_single_frame(config_path: str, media_path: Path) -> None:
    config_manager = ConfigManager(
        config_path,
        overrides={
            "metadata_previous_response_id": None,
            # "campaign_specific_analysis_prompt": "analyze this 3d printed pottery image",
        },
    )
    config = dict(config_manager.config)

    media_path = media_path.resolve()
    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")
    if not is_image(media_path):
        raise ValueError("This script only supports image files.")

    script_root = Path(__file__).resolve().parent
    preview_root = script_root / "single_frame_previews"
    preview_rel = media_path.name
    preview_path = ensure_preview_path(Path(preview_rel), preview_root, suffix=".jpg")

    from PIL import Image

    with Image.open(media_path) as img:
        downsample_and_store(img, preview_path, max_px=int(config.get("downsample_max_px", 320)))

    metadata = get_media_metadata(media_path)

    analyzer = GPTMetadataAnalyzer(
        config_manager=config_manager,
        config=config,
        frames_per_call=1,
    )

    request = FrameAnalysisRequest(
        frame_id="single_frame",
        parent_media_id="single_media",
        timestamp=0.0,
        preview_path=preview_path,
        orientation=metadata.get("orientation", ""),
        filename_tokens=media_path.stem.replace("-", "_").split("_"),
    )

    results = analyzer.submit(request) + analyzer.flush()
    if not results:
        print("No metadata returned.")
        return

    print(f"Preview stored at: {preview_path}")
    for item in results:
        payload = item.model_dump() if hasattr(item, "model_dump") else item.dict()
        print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a single image without touching the DB.")
    parser.add_argument("--config", default="autopost_config.database.json", help="Path to config file.")
    parser.add_argument("media_path", type=Path, help="Path to a single image file.")
    args = parser.parse_args()
    analyze_single_frame(args.config, args.media_path)


if __name__ == "__main__":
    main()

