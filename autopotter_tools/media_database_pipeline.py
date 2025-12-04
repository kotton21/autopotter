from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

try:  # pragma: no cover - pillow should be available but guard for lint
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

from autopotter_tools.embedding_service import EmbeddingService
from autopotter_tools.media_database import MediaDatabase
from autopotter_tools.media_models import MediaFrameMetadata, MediaItem
from autopotter_tools.media_tools import (
    downsample_and_store,
    ensure_preview_path,
    estimate_clip_span,
    frame_extractor,
    get_media_metadata,
    is_image,
    is_video,
    safe_media_id,
)
from autopotter_tools.metadata_analyzer import (
    FrameAnalysisRequest,
    GPTMetadataAnalyzer,
    SimpleMetadataAnalyzer,
)
from autopotter_tools.simplelogger import Logger
from config import ConfigManager


class MediaDatabasePipeline:
    """
    Executes build steps 1-6 from media_understanding_build_plan.md.

    args:
        config_path: path to the config file
        overrides: optional override values to the config
    """

    def __init__(
        self,
        config_path: str = "autopost_config.database.json",
        overrides: Optional[Dict[str, object]] = None,
    ):
        self.config_manager = ConfigManager(config_path)
        self.config: Dict[str, object] = dict(self.config_manager.config)
        if overrides: # used for tests to override specific config values...???
            self.config.update(overrides)

        self.media_root = Path(self.config["media_library_dir"]).resolve()
        self.preview_root = Path(self.config["media_preview_dir"]).resolve()
        self.preview_root.mkdir(parents=True, exist_ok=True)

        self.downsample_px = int(self.config.get("downsample_max_px", 320))
        self.frame_interval = float(self.config.get("frame_interval_seconds", 2.0))
        self.max_frames_per_media = int(self.config.get("max_frames_per_media", 5))
        raw_exts = self.config.get("media_supported_extensions", [])
        self.supported_extensions = {
            str(ext).lower().lstrip(".") for ext in raw_exts
        } if raw_exts else set()

        database_path = Path(self.config.get("media_database_path", "media_frames.sqlite"))
        self.db = MediaDatabase(database_path)
        analyzer_mode = str(self.config.get("metadata_analyzer_mode", "simple")).lower()
        if analyzer_mode == "gpt":
            frames_per_call = int(self.config.get("gpt_frames_per_call", 10))
            self.metadata_analyzer = GPTMetadataAnalyzer(
                config_manager=self.config_manager,
                config=self.config,
                frames_per_call=frames_per_call,
            )
        else:
            self.metadata_analyzer = SimpleMetadataAnalyzer()
        self.embedding_service = EmbeddingService(
            api_key=self.config.get("openai_api_key"),
            model=self.config.get("embedding_model", "text-embedding-3-small"),
        )

    def run(self, limit_media: Optional[int] = None) -> Dict[str, int]:
        media_paths = list(self._discover_media())
        processed_media = 0
        frames_indexed = 0

        for path in media_paths:
            if limit_media is not None and processed_media >= limit_media:
                break
            media_item = self._build_media_item(path)
            self.db.save_media_item(media_item)
            new_frames = self._process_media(path, media_item)
            processed_media += 1
            frames_indexed += new_frames

        for metadata in self.metadata_analyzer.flush():
            self._persist_frame(metadata)

        return {"media_processed": processed_media, "frames_indexed": frames_indexed}

    def keyword_search(self, keyword: str, limit: int = 10) -> List[MediaFrameMetadata]:
        return self.db.search_by_keyword(keyword, limit=limit)

    def _discover_media(self) -> Iterable[Path]:
        if not self.media_root.exists():
            Logger.warning(f"Media directory {self.media_root} does not exist")
            return []
        for path in self.media_root.rglob("*"):
            if not path.is_file():
                continue
            if self.supported_extensions and path.suffix.lower().strip(".") not in self.supported_extensions:
                continue
            if is_image(path) or is_video(path):
                yield path

    def _build_media_item(self, path: Path) -> MediaItem:
        media_type = "image" if is_image(path) else "video"
        metadata = get_media_metadata(path)
        media_id = safe_media_id(path.relative_to(self.media_root))
        return MediaItem(
            media_id=media_id,
            path=str(path),
            media_type=media_type,
            metadata=metadata,
        )

    def _process_media(self, path: Path, media_item: MediaItem) -> int:
        if media_item.media_type == "image":
            self._process_image(path, media_item)
            return 1
        return self._process_video(path, media_item)

    def _process_image(self, path: Path, media_item: MediaItem) -> None:
        preview_rel = path.relative_to(self.media_root)
        preview_path = ensure_preview_path(preview_rel, self.preview_root, suffix=".jpg")

        if Image is None:
            raise RuntimeError("Pillow is required for image processing.")
        with Image.open(path) as img:
            downsample_and_store(img, preview_path, max_px=self.downsample_px)

        frame_id = f"{media_item.media_id}:img"
        request = FrameAnalysisRequest(
            frame_id=frame_id,
            parent_media_id=media_item.media_id,
            timestamp=0.0,
            preview_path=preview_path,
            orientation=media_item.metadata.get("orientation", "landscape"),
            filename_tokens=self._filename_tokens(path),
        )
        self._handle_analysis_request(request)

    def _process_video(self, path: Path, media_item: MediaItem) -> int:
        relative = path.relative_to(self.media_root)
        timestamps: List[float] = []
        frame_count = 0

        iterator = frame_extractor(
            path,
            interval_seconds=self.frame_interval,
            max_frames=self.max_frames_per_media,
        )

        try:
            for index, (image, timestamp) in enumerate(iterator):
                frame_rel = relative.parent / f"{relative.stem}_frame{index:04d}.jpg"
                preview_path = ensure_preview_path(frame_rel, self.preview_root)
                downsample_and_store(image, preview_path, max_px=self.downsample_px)

                frame_id = f"{media_item.media_id}:f{index:04d}"
                request = FrameAnalysisRequest(
                    frame_id=frame_id,
                    parent_media_id=media_item.media_id,
                    timestamp=timestamp,
                    preview_path=preview_path,
                    orientation=media_item.metadata.get("orientation", "landscape"),
                    filename_tokens=self._filename_tokens(path),
                )
                self._handle_analysis_request(request)
                timestamps.append(timestamp if timestamp is not None else 0.0)
                frame_count += 1
        except RuntimeError as exc:
            Logger.warning(f"Skipping video {path}: {exc}")
            return frame_count

        if timestamps:
            media_item.metadata["preview_span"] = estimate_clip_span(timestamps)
            self.db.save_media_item(media_item)

        return frame_count

    def _handle_analysis_request(self, request: FrameAnalysisRequest) -> None:
        completed = self.metadata_analyzer.submit(request)
        for metadata in completed:
            self._persist_frame(metadata)

    def _persist_frame(self, metadata: MediaFrameMetadata) -> None:
        self.db.save_frame_metadata(metadata)
        embedding_text = self.embedding_service.build_embedding_text(metadata)
        embedding = self.embedding_service.embed(embedding_text)
        self.db.save_embedding(metadata.frame_id, embedding)

    @staticmethod
    def _filename_tokens(path: Path) -> Sequence[str]:
        return path.stem.replace("-", "_").split("_")


def _build_cli(parser=None):
    import argparse

    parser = parser or argparse.ArgumentParser(
        description="Build the media metadata + embedding database."
    )
    parser.add_argument(
        "--config",
        default="autopost_config.database.json",
        help="Path to database-specific config JSON.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap of how many media files to process.",
    )
    parser.add_argument(
        "--overrides",
        type=str,
        default=None,
        help="JSON string of config overrides (e.g. '{\"media_library_dir\": \"~/Media\"}').",
    )
    parser.add_argument(
        "--keyword",
        type=str,
        default=None,
        help="Optional keyword search to run after building.",
    )
    return parser


def main():
    parser = _build_cli()
    args = parser.parse_args()

    overrides: Optional[Dict[str, object]] = None
    if args.overrides:
        import json
        overrides = json.loads(args.overrides)

    pipeline = MediaDatabasePipeline(config_path=args.config, overrides=overrides)
    summary = pipeline.run(limit_media=args.limit)
    print(f"[media-pipeline] build complete: {summary}")
    stats = pipeline.db.describe_stats()
    print(f"[media-pipeline] db_stats={stats}")

    if args.keyword:
        results = pipeline.keyword_search(args.keyword)
        print(f"[media-pipeline] keyword '{args.keyword}' hits={len(results)}")
        for frame in results[:5]:
            print("  --- search result ---")
            print(frame.model_dump_json() if hasattr(frame, "model_dump_json") else frame.json())


if __name__ == "__main__":
    main()

