#!/usr/bin/env python3
"""Lightweight tests for the refactored GCSManager module."""

import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

# Provide a lightweight stub for google.cloud.storage so the tests do not require
# the real dependency. Only the attribute accessed by the module needs to exist.
fake_google = types.ModuleType("google")
fake_cloud = types.ModuleType("google.cloud")
fake_storage = types.ModuleType("google.cloud.storage")
fake_storage.Client = MagicMock
fake_cloud.storage = fake_storage
fake_google.cloud = fake_cloud
sys.modules.setdefault("google", fake_google)
sys.modules.setdefault("google.cloud", fake_cloud)
sys.modules["google.cloud.storage"] = fake_storage

from autopotter_tools.gcs_manager import GCSManager  # noqa: E402


class _StubBlob:
    """Minimal stand-in for google.cloud.storage.Blob."""

    def __init__(self, name: str, size: int = 0, metadata=None, created=None, updated=None) -> None:
        self.name = name
        self.size = size
        self.metadata = metadata or {}
        self.time_created = created
        self.updated = updated

    def reload(self) -> None:  # pragma: no cover - compatibility stub
        return None


class TestGCSManager(unittest.TestCase):
    """Covers inventory, upload, and selection helpers without hitting GCS."""

    def setUp(self) -> None:
        self.bucket = MagicMock()
        self.config_patch = patch("autopotter_tools.gcs_manager.get_config")
        self.mock_get_config = self.config_patch.start()
        self.config_values = {
            "gcs_api_key_path": "/tmp/key.json",
            "gcs_bucket": "autopotter",
            "gcs_folders": [],
        }

        class _ConfigStub:
            def __init__(self, store):
                self.store = store

            def get(self, key, default=None):
                return self.store.get(key, default)

        self.config_stub = _ConfigStub(self.config_values)
        self.mock_get_config.return_value = self.config_stub
        self._set_folders([])

    def tearDown(self) -> None:
        self.config_patch.stop()

    def _set_folders(self, folders: List[str]) -> None:
        self.config_values["gcs_folders"] = folders

    def _make_manager(self) -> GCSManager:
        return GCSManager("dummy-config.json", bucket=self.bucket)

    def test_generate_inventory_compiles_summary(self) -> None:
        self._set_folders(["video_uploads/"])
        clip_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        blobs = [
            _StubBlob("video_uploads/clip.mp4", size=2 * 1024 * 1024, metadata={"foo": "bar"}, created=clip_time),
            _StubBlob("video_uploads/note.txt", size=512),
        ]

        def list_blobs(prefix=None, **_):
            return blobs if prefix == "video_uploads/" else []

        self.bucket.list_blobs.side_effect = list_blobs
        manager = self._make_manager()

        inventory = manager.generate_inventory()
        self.assertEqual(inventory["summary"]["total_files"], 2)
        self.assertAlmostEqual(inventory["summary"]["total_size_mb"], 2.0, places=1)
        self.assertEqual(len(inventory["files_by_folder"]), 1)
        folder_files = next(iter(inventory["files_by_folder"].values()))
        self.assertIn("clip.mp4", folder_files)

    def test_select_next_video_skips_uploaded_names(self) -> None:
        manager = self._make_manager()
        now = datetime.now(timezone.utc)
        manager.get_available_videos = MagicMock(
            return_value=[
                {"name": "video_uploads/new.mp4", "size": 5_000_000, "size_mb": 5, "created": now, "updated": now, "public_url": "url"},
                {"name": "video_uploads/older.mp4", "size": 4_000_000, "size_mb": 4, "created": now, "updated": now, "public_url": "url2"},
            ]
        )

        choice = manager.select_next_video([{"video": "video_uploads/new.mp4"}])
        self.assertIsNotNone(choice)
        self.assertEqual(choice["name"], "video_uploads/older.mp4")

    def test_select_random_audio_respects_exclusion(self) -> None:
        manager = self._make_manager()
        audio_options = [
            {"name": "music_uploads/a.mp3"},
            {"name": "music_uploads/b.mp3"},
            {"name": "music_uploads/c.mp3"},
        ]
        manager.get_audio_options = MagicMock(return_value=audio_options)

        with patch("autopotter_tools.gcs_manager.random.choice", side_effect=lambda seq: seq[0]) as mock_choice:
            selection = manager.select_random_audio(exclude_recent=1)

        self.assertIsNotNone(selection)
        self.assertEqual(selection["name"], "music_uploads/b.mp3")
        self.assertEqual(mock_choice.call_count, 1)
        available = mock_choice.call_args[0][0]
        self.assertEqual([item["name"] for item in available], ["music_uploads/b.mp3", "music_uploads/c.mp3"])

    def test_upload_folder_uses_relative_paths(self) -> None:
        manager = self._make_manager()
        upload_calls = []
        manager.upload_file = MagicMock(side_effect=lambda src, dest: upload_calls.append((src, dest)) or True)

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "root.txt").write_text("root", encoding="utf-8")
            nested_dir = root / "nested"
            nested_dir.mkdir()
            (nested_dir / "child.txt").write_text("child", encoding="utf-8")

            success = manager.upload_folder(str(root), "dest")

        self.assertTrue(success)
        destinations = {dest for _, dest in upload_calls}
        self.assertSetEqual(destinations, {"dest/root.txt", "dest/nested/child.txt"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

