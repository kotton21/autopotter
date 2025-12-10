from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Set

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
        filter_existing_media: bool = True,
    ):
        self.config_manager = ConfigManager(config_path, overrides=overrides)
        self.config: Dict[str, object] = dict(self.config_manager.config)

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

        raw_folders = self.config.get("gcs_folders") or []
        if isinstance(raw_folders, (list, tuple, set)):
            self.media_folder_names = [str(folder) for folder in raw_folders]
        elif raw_folders:
            self.media_folder_names = [str(raw_folders)]
        else:
            self.media_folder_names = []

        self.progress_bar = 0
        self.progress_check = 0
        self.filter_existing_media = filter_existing_media
        self._existing_media_cache: Optional[List[Path]] = None


        database_path = Path(self.config.get("media_database_path", "media_frames.sqlite")).resolve()
        self.db = MediaDatabase(database_path)
        frames_per_call = int(self.config.get("gpt_frames_per_call", 10))
        self.metadata_analyzer = GPTMetadataAnalyzer(
            config_manager=self.config_manager,
            config=self.config,
            frames_per_call=frames_per_call,
        )
        self.embedding_service = EmbeddingService(
            api_key=self.config.get("openai_api_key"),
            model=self.config.get("embedding_model", "text-embedding-3-small"),
        )

    def run(self, limit_media: Optional[int] = None) -> Dict[str, object]:
        # Discover all candidate media paths based on the configured folders.
        media_paths = list(self._discover_media())
        processed_media = 0
        frames_indexed = 0

        for path in media_paths:
            if limit_media is not None and processed_media >= limit_media:
                break
            # Persist parent media metadata before drilling into frames.
            media_item = self._build_media_item(path)
            self.db.save_media_item(media_item)
            # Process the media into frames and accumulate counts.
            new_frames = self._process_media(path, media_item)
            processed_media += 1
            frames_indexed += new_frames
            
            self._check_progress(processed_media)

        # Ensure any buffered GPT metadata batches are written out.
        for metadata in self.metadata_analyzer.flush():
            self._persist_frame(metadata)

        summary: Dict[str, object] = {
            "media_processed": processed_media,
            "frames_indexed": frames_indexed,
        }
        usage = self.metadata_analyzer.get_usage_totals()
        if usage:
            summary["token_usage"] = usage

        return summary


    def _check_progress(self, processed_media: int) -> None:
        self.progress_check = self.progress_check + 1
        if (self.progress_bar % int(self.config.get("gpt_frames_per_call",10)) == 0 and 
                self.num_files_to_process is not None and 
                self.num_files_to_process > 0):
            progress = processed_media / self.num_files_to_process
            Logger.info(f" *****  Progress: {progress:.2%} *****\n")
            self.progress_bar = int(progress * 100)
            self.progress_check = 0

    def _clear_empty_media_items(self) -> None:
        """
        Clear media items that have no frames from the database.
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            DELETE FROM media_items WHERE media_id NOT IN (
                SELECT DISTINCT parent_media_id FROM frames
            )
        """)
        self.db.conn.commit()

    def _get_existing_media_filenames(self) -> List[Path]:
        """
        Return absolute Paths for media items already stored in the database.
        """
        if self._existing_media_cache is not None:
            return self._existing_media_cache

        filenames: List[Path] = []
        try:
            cursor = self.db.conn.cursor()
            # rows = cursor.execute("SELECT path FROM media_items").fetchall()
            rows = cursor.execute(
                """
                SELECT DISTINCT media_items.path
                FROM media_items
                JOIN frames ON frames.parent_media_id = media_items.media_id
                """
            ).fetchall()
            for row in rows:
                raw_path = row["path"]
                if not raw_path:
                    continue
                filenames.append(Path(raw_path).resolve())
        except Exception as exc:
            Logger.warning(f"Unable to load existing media filenames: {exc}")

        self._existing_media_cache = filenames
        return filenames

    def keyword_search(self, keyword: str, limit: int = 10) -> List[MediaFrameMetadata]:
        return self.db.search_by_keyword(keyword, limit=limit)

    def _discover_media(self) -> Iterable[Path]:
        seen: set[Path] = set()
        any_valid_directories = False


        media_directories: List[Path] = []
        for folder in self.media_folder_names:
            if not folder:
                continue
            folder_path = Path(folder)
            if not folder_path.is_absolute():
                folder_path = self.media_root / folder_path
            media_directories.append(folder_path.resolve())

        if not media_directories:
            media_directories = [self.media_root]

        # Deduplicate while preserving order
        media_directories: List[Path] = list(dict.fromkeys(media_directories))

        self._clear_empty_media_items()

        existing_paths: Set[Path] = set()
        if self.filter_existing_media:
            existing_paths = set(self._get_existing_media_filenames())

        # Count the number of files to process.
        self.num_files_to_process = 0
        for directory in media_directories:
            for path in directory.rglob("*"):
                if not path.is_file():
                    continue
                if (
                    self.supported_extensions
                    and path.suffix.lower().strip(".") not in self.supported_extensions
                ):
                    continue
                resolved = path.resolve()
                if self.filter_existing_media and resolved in existing_paths:
                    continue
                self.num_files_to_process += 1

        for directory in media_directories:
            if not directory.exists():
                Logger.warning(f"Media directory {directory} does not exist")
                continue

            any_valid_directories = True
            for path in directory.rglob("*"):
                if not path.is_file():
                    continue
                if (
                    self.supported_extensions
                    and path.suffix.lower().strip(".") not in self.supported_extensions
                ):
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                if self.filter_existing_media and resolved in existing_paths:
                    continue
                if is_image(path) or is_video(path):
                    seen.add(resolved)
                    yield path

        if not any_valid_directories:
            Logger.warning(
                "No valid media directories found based on configured gcs_folders."
            )

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
            orientation=media_item.metadata.get("orientation", ""),
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
                    orientation=media_item.metadata.get("orientation", ""),
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


    def _cluster_media_items(self, n_clusters: int = 4) -> Tuple[Dict[str, str], Dict[str, float], float]:
        clusters, cluster_tightness, inertia = self.db.cluster_media_items(
            n_clusters=n_clusters
        )
        if not clusters:
            print("[media-pipeline] No clusters generated (check avg embeddings).")
        else:
            # print cluster tightness and inertia
            if cluster_tightness:
                print("[media-pipeline] Cluster tightness (avg L2 distance to centroid):")
                for label in sorted(cluster_tightness.keys()):
                    print(f"  {label}: {cluster_tightness[label]:.4f}")
            print(f"[media-pipeline] Overall inertia: {inertia:.4f}")
            


            
            
            def print_cluster_assignments():
                media_ids = list(clusters.keys())
                media_paths = self.db.get_media_paths(media_ids)
                print("[media-pipeline] Cluster assignments:")
                sorted_assignments = sorted(
                    clusters.items(),
                    key=lambda item: (
                        item[1],
                        Path(media_paths.get(item[0], "")).name.lower(),
                    ),
                )
                for media_id, label in sorted_assignments:
                    path = media_paths.get(media_id, "")
                    filename = Path(path).name if path else "?"
                    print(f"  {label}  {filename}  ({media_id})")

            
            def _average_vectors(vectors: Sequence[List[float]]) -> Optional[List[float]]:
                if not vectors:
                    return None
                dimension = len(vectors[0])
                accumulator = [0.0] * dimension
                count = 0
                for vector in vectors:
                    if len(vector) != dimension:
                        Logger.warning(
                            "Skipping centroid contribution: embedding dimension mismatch."
                        )
                        continue
                    accumulator = [a + b for a, b in zip(accumulator, vector)]
                    count += 1
                if not count:
                    return None
                return [value / count for value in accumulator]

            def print_cluster_centroid_exemplars():
                print("[media-pipeline] Cluster centroid exemplars:")
                
                media_ids = list(clusters.keys())
                media_embeddings = self.db.get_media_avg_embeddings(media_ids)
                cluster_vectors: Dict[str, List[List[float]]] = defaultdict(list)
                for media_id, label in clusters.items():
                    embedding = media_embeddings.get(media_id)
                    if embedding:
                        cluster_vectors[label].append(embedding)

                for label in sorted(cluster_vectors.keys()):
                    centroid = _average_vectors(cluster_vectors[label])
                    if centroid is None:
                        print(f"  {label}  Unable to compute centroid (no valid embeddings).")
                        continue
                    closest = self.db.find_closest_frame_by_embedding(centroid)
                    if not closest:
                        print(f"  {label}  No frame embeddings available.")
                        continue
                    score, metadata = closest
                    metadata_payload = (
                        metadata.model_dump()
                        if hasattr(metadata, "model_dump")
                        else metadata.dict()
                    )
                    print(
                        f"{label}  centroid match score={score:.4f} frame_id={metadata.frame_id}"
                    )
                    print(f"    parent_media_id={metadata.parent_media_id}")
                    print(f"    image_path={metadata.image_path}")
                    print(f"    description={metadata.description}")
                    # print(f"    metadata={json.dumps(metadata_payload, indent=2)}")

            # print_cluster_assignments()
            print_cluster_tightness()
            # print_cluster_centroid_exemplars()

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
        "--build-db",
        action="store_true",
        default=False,
        help="Build the database.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of media items to process.",
    )
    # parser.add_argument(
    #     "--build-parent-embeddings",
    #     action="store_true",
    #     default=False,
    #     help="Build parent embeddings for media items.",
    # )
    parser.add_argument(
        "--cluster-media",
        action="store_true",
        default=False,
        help="Run k-means clustering over avg embeddings and print assignments.",
    )
    parser.add_argument(
        "--n-clusters",
        type=int,
        default=4,
        help="Optional Number of clusters to create.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        default=False,
        help="Delete the media database file and reset metadata_previous_response_id before building.",
    )
    
    return parser


def main():
    parser = _build_cli()
    args = parser.parse_args()

    # if not args.build_db and not args.build_parent_embeddings and not args.cluster_media:
    #     parser.print_help()
    #     return

    config_path = Path(args.config).resolve()
    if args.clean:
        config_manager = ConfigManager(str(config_path))
        db_value = config_manager.config.get(
            "media_database_path", "media_frames.sqlite"
        )
        db_path = Path(db_value)
        if not db_path.is_absolute():
            db_path = (config_path.parent / db_path).resolve()
        else:
            db_path = db_path.resolve()

        if db_path.exists():
            db_path.unlink()
            print(f"[media-pipeline] Removed existing database at {db_path}")
        else:
            print(f"[media-pipeline] No existing database to remove at {db_path}")
        config_manager.set("metadata_previous_response_id", None)
        print("[media-pipeline] Cleared metadata_previous_response_id in config.")

    pipeline = MediaDatabasePipeline(config_path=str(config_path), filter_existing_media=not args.clean)

    if args.build_db:
        stats = pipeline.db.get_db_size_and_rowcounts()
        print(f"[media-pipeline] db_stats_before={stats}")

        summary = pipeline.run(limit_media=args.limit)

        print(f"[media-pipeline] build complete: {summary}")
        stats = pipeline.db.get_db_size_and_rowcounts()
        print(f"[media-pipeline] db_stats_after={stats}")
        
        token_usage = summary.get("token_usage")
        if token_usage:
            print(f"[media-pipeline] token_usage={token_usage}")
        pipeline.db.print_db_schema() 

    # if args.build_parent_embeddings:
        pipeline.db.compute_all_parrent_embeddings()
        pipeline.db.print_db_schema() 

    if args.cluster_media:
        pipeline._cluster_media_items(args.n_clusters)

if __name__ == "__main__":
    main()

