#!/usr/bin/env python3
"""Lightweight, pythonic helpers for interacting with Google Cloud Storage."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from google.cloud import storage

try:
    from simplelogger import Logger
except ImportError:
    from autopotter_tools.simplelogger import Logger

from config import get_config

VIDEO_EXTENSIONS = (
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
)
AUDIO_EXTENSIONS = (
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".wma",
    ".aiff",
)
RESERVED_METADATA_PREFIX = "goog-reserved-"
VIDEO_FOLDER = "video_uploads/"
AUDIO_FOLDER = "music_uploads/"


@dataclass(frozen=True)
class FileRecord:
    """Simple representation of a blob we care about."""

    name: str
    size_bytes: int
    public_url: str
    metadata: Dict[str, str]
    created: Optional[datetime]
    updated: Optional[datetime]

    @property
    def size_mb(self) -> float:
        if not self.size_bytes:
            return 0.0
        return round(self.size_bytes / (1024 * 1024), 2)


class GCSManager:
    """Small, dependency-injected wrapper around a Google Cloud Storage bucket."""

    def __init__(
        self,
        config_path: str = "autopost_config.enhanced.json",
        *,
        storage_client: Optional[storage.Client] = None,
        bucket=None,
    ) -> None:
        self.config = get_config(config_path)

        self.api_key_path = self._require_setting("gcs_api_key_path")
        self.bucket_name = self._require_setting("gcs_bucket")
        folders = self.config.get("gcs_folders", [])
        normalized_folders = (
            self._normalize_folder_prefix(folder) for folder in (folders or [])
        )
        self.folders_to_scan = tuple(filter(None, normalized_folders))

        if bucket is not None:
            self.client = storage_client
            self.bucket = bucket
        else:
            self.client = storage_client or storage.Client.from_service_account_json(self.api_key_path)
            self.bucket = self.client.bucket(self.bucket_name)

        Logger.info(f"GCS Manager initialized for bucket: {self.bucket_name}")

    # -------------------- Inventory helpers -------------------- #
    def scan_folder(self, folder_prefix: str, *, extensions: Optional[Sequence[str]] = None) -> List[FileRecord]:
        """Return all blob records in a folder, optionally filtered by extension."""
        Logger.info(f"Scanning folder: {folder_prefix}")

        try:
            blobs = list(self.bucket.list_blobs(prefix=folder_prefix))
        except Exception as exc:  # pragma: no cover - defensive logging
            Logger.error(f"Failed to list blobs for {folder_prefix}: {exc}")
            return []

        records: List[FileRecord] = []
        normalized_extensions = tuple(ext.lower() for ext in extensions) if extensions else None

        for blob in blobs:
            if blob.name.endswith("/"):
                continue

            if normalized_extensions and not blob.name.lower().endswith(normalized_extensions):
                continue

            metadata = self._extract_metadata(getattr(blob, "metadata", None))
            record = FileRecord(
                name=blob.name,
                size_bytes=int(getattr(blob, "size", 0) or 0),
                public_url=self._public_url(blob.name),
                metadata=metadata,
                created=getattr(blob, "time_created", None),
                updated=getattr(blob, "updated", None),
            )
            records.append(record)

        Logger.info(f"Found {len(records)} files in {folder_prefix}")
        return records

    def generate_inventory(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Produce a light-weight inventory grouped by folder."""
        Logger.info("Generating GCS inventory...")
        inventory: Dict[str, Any] = {
            "collection_info": {
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "source": "gcs_manager",
                "collection_version": "3.0",
            },
            "files_by_folder": {},
            "summary": {"total_files": 0, "total_size_mb": 0.0},
        }

        if not self.folders_to_scan:
            Logger.warning("No folders configured; returning empty inventory")
            return inventory

        for folder in self.folders_to_scan:
            files = self.scan_folder(folder)
            if not files:
                continue

            folder_url = self._folder_url(folder)
            filenames = [Path(record.name).name for record in files]

            inventory["files_by_folder"][folder_url] = filenames
            inventory["summary"]["total_files"] += len(files)
            inventory["summary"]["total_size_mb"] += sum(record.size_mb for record in files)

        inventory["summary"]["total_size_mb"] = round(inventory["summary"]["total_size_mb"], 2)

        if output_path:
            Path(output_path).write_text(json.dumps(inventory, indent=2), encoding="utf-8")
            Logger.info(f"Inventory saved to {output_path}")

        return inventory

    # -------------------- Upload helpers -------------------- #
    def upload_file(self, source_file_path: str, destination_blob_name: str) -> bool:
        """Upload a single file to the configured bucket."""
        source_path = Path(source_file_path)
        if not source_path.is_file():
            Logger.error(f"Source file does not exist: {source_path}")
            return False

        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(str(source_path))
            Logger.info(f"Uploaded {source_path} to {self.bucket_name}/{destination_blob_name}")
            return True
        except Exception as exc:  # pragma: no cover - network failure
            Logger.error(f"Failed to upload {source_path}: {exc}")
            return False

    def upload_folder(self, source_folder: str, destination_folder_prefix: str = "") -> bool:
        """Upload a directory tree to the bucket."""
        source_path = Path(source_folder)
        if not source_path.is_dir():
            Logger.error(f"Source folder does not exist: {source_path}")
            return False

        for file_path in self._iter_local_files(source_path):
            relative = file_path.relative_to(source_path)
            destination = self._destination_name(destination_folder_prefix, relative)
            if not self.upload_file(str(file_path), destination):
                return False

        Logger.info(f"Uploaded folder {source_path} to {self.bucket_name}/{destination_folder_prefix}")
        return True

    def get_most_recent_file_creation_time(self, prefix: Optional[str] = None) -> Optional[datetime]:
        """Return the newest blob creation/update time for a prefix."""
        newest_time: Optional[datetime] = None
        try:
            for blob in self.bucket.list_blobs(prefix=prefix):
                if blob.name.endswith("/"):
                    continue
                blob_time = getattr(blob, "time_created", None) or getattr(blob, "updated", None)
                if blob_time is None:
                    continue
                if newest_time is None or blob_time > newest_time:
                    newest_time = blob_time
        except Exception as exc:  # pragma: no cover - defensive logging
            Logger.error(f"Failed to inspect blobs for prefix {prefix}: {exc}")
            return None

        if newest_time is None:
            Logger.info("No files found.")
        else:
            Logger.info(f"Newest file timestamp for prefix '{prefix}': {newest_time.isoformat()}")

        return newest_time

    def upload_new_files(self, source_folder: str, destination_folder_prefix: str = "") -> bool:
        """Upload files that are newer than what currently exists in the bucket."""
        source_path = Path(source_folder)
        if not source_path.is_dir():
            Logger.error(f"Source folder does not exist: {source_path}")
            return False

        newest_remote_time = self.get_most_recent_file_creation_time(destination_folder_prefix)

        for file_path in self._iter_local_files(source_path):
            modified_time = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if newest_remote_time and modified_time <= newest_remote_time:
                continue
            relative = file_path.relative_to(source_path)
            destination = self._destination_name(destination_folder_prefix, relative)
            if not self.upload_file(str(file_path), destination):
                return False

        Logger.info(f"Uploaded new files from {source_path} to {self.bucket_name}/{destination_folder_prefix}")
        return True

    # -------------------- Selection helpers -------------------- #
    def get_available_videos(self) -> List[Dict[str, Any]]:
        """Return sorted video metadata dictionaries."""
        records = self.scan_folder(VIDEO_FOLDER, extensions=VIDEO_EXTENSIONS)
        payloads = [self._record_payload(record) for record in records if record.created]
        payloads.sort(key=lambda item: item["created"], reverse=True)
        return payloads

    def select_next_video(self, uploaded_videos: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Return the newest video that has not yet been uploaded."""
        uploaded_names = {item.get("video") for item in uploaded_videos}
        for video in self.get_available_videos():
            if video["name"] not in uploaded_names:
                if video["size"] < 1024 * 1024:
                    Logger.warning(f"Selected video {video['name']} is very small ({video['size']} bytes)")
                return video
        return None

    def get_audio_options(self) -> List[Dict[str, Any]]:
        """Return metadata for all audio files."""
        records = self.scan_folder(AUDIO_FOLDER, extensions=AUDIO_EXTENSIONS)
        return [self._record_payload(record) for record in records]

    def select_random_audio(self, exclude_recent: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Pick a random audio track, optionally skipping the most recent ones."""
        audio_options = self.get_audio_options()
        if not audio_options:
            return None

        if exclude_recent and len(audio_options) > exclude_recent:
            available_audio = audio_options[exclude_recent:]
        else:
            available_audio = audio_options

        if not available_audio:
            return audio_options[0]

        return random.choice(available_audio)

    # -------------------- Internals -------------------- #
    def _require_setting(self, key: str) -> str:
        value = self.config.get(key)
        if not value:
            raise ValueError(f"GCS setting '{key}' is required")
        return value

    @staticmethod
    def _extract_metadata(metadata: Optional[Dict[str, str]]) -> Dict[str, str]:
        if not metadata:
            return {}
        return {k: v for k, v in metadata.items() if not k.startswith(RESERVED_METADATA_PREFIX)}

    def _public_url(self, blob_name: str) -> str:
        sanitized = blob_name.lstrip("/")
        return f"https://storage.googleapis.com/{self.bucket_name}/{sanitized}"

    def _folder_url(self, folder: str) -> str:
        base = folder if folder.endswith("/") else f"{folder}/"
        return self._public_url(base)

    @staticmethod
    def _iter_local_files(base_path: Path) -> Iterator[Path]:
        for path in base_path.rglob("*"):
            if path.is_file():
                yield path

    @staticmethod
    def _destination_name(prefix: str, relative_path: Path) -> str:
        clean_prefix = prefix.strip().strip("/")
        relative = relative_path.as_posix()
        return f"{clean_prefix}/{relative}" if clean_prefix else relative

    @staticmethod
    def _record_payload(record: FileRecord) -> Dict[str, Any]:
        return {
            "name": record.name,
            "size": record.size_bytes,
            "size_mb": record.size_mb,
            "created": record.created,
            "updated": record.updated or record.created,
            "public_url": record.public_url,
            "metadata": record.metadata,
        }

    @staticmethod
    def _normalize_folder_prefix(folder: str) -> str:
        value = (folder or "").strip()
        if not value:
            return value
        return value if value.endswith("/") else f"{value}/"


def main() -> None:
    """Simple CLI for ad-hoc operations."""
    parser = argparse.ArgumentParser(description="Google Cloud Storage helper")
    parser.add_argument(
        "operation",
        choices=["inventory", "upload_file", "upload_folder", "upload_new_files", "get_videos", "get_audio"],
    )
    parser.add_argument("--config", default="autopost_config.enhanced.json")
    parser.add_argument("--output", default="gcs_inventory_result.json")
    parser.add_argument("--source_file")
    parser.add_argument("--destination_blob")
    parser.add_argument("--source_folder")
    parser.add_argument("--destination_folder", default="")

    args = parser.parse_args()
    manager = GCSManager(args.config)

    if args.operation == "inventory":
        inventory = manager.generate_inventory(args.output)
        print(json.dumps(inventory, indent=2))
    elif args.operation == "upload_file":
        if not args.source_file or not args.destination_blob:
            parser.error("--source_file and --destination_blob are required")
        manager.upload_file(args.source_file, args.destination_blob)
    elif args.operation == "upload_folder":
        if not args.source_folder:
            parser.error("--source_folder is required")
        manager.upload_folder(args.source_folder, args.destination_folder or "")
    elif args.operation == "upload_new_files":
        if not args.source_folder:
            parser.error("--source_folder is required")
        manager.upload_new_files(args.source_folder, args.destination_folder or "")
    elif args.operation == "get_videos":
        print(json.dumps(manager.get_available_videos(), indent=2, default=str))
    elif args.operation == "get_audio":
        print(json.dumps(manager.get_audio_options(), indent=2, default=str))


if __name__ == "__main__":  # pragma: no cover - manual entry point
    main()
