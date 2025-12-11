import shutil
import types
from pathlib import Path
from typing import List

import pytest

from autopotter_tools import embedding_service
from autopotter_tools.media_database_pipeline import MediaDatabasePipeline
from autopotter_tools.media_models import MediaFrameMetadata


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch):
    class _FakeEmbeddings:
        @staticmethod
        def create(model, input):
            return types.SimpleNamespace(
                data=[types.SimpleNamespace(embedding=[0.0, 0.0, 0.0])]
            )

    class _FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.embeddings = _FakeEmbeddings()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(embedding_service, "OpenAI", _FakeClient)


@pytest.fixture(autouse=True)
def fake_metadata_analyzer(monkeypatch):
    class _FakeAnalyzer:
        def __init__(self, *args, **kwargs):
            self._buffer: List[MediaFrameMetadata] = []

        def submit(self, request):
            metadata = MediaFrameMetadata(
                frame_id=request.frame_id,
                parent_media_id=request.parent_media_id,
                timestamp=request.timestamp,
                image_path=str(request.preview_path),
                shot_type="closeup",
                emotional_tone="calming",
                use_case="process_detail",
                activities=["timelapse"],
                materials=["clay"],
                objects_detected=["printer"],
                image_qualities=["synthetic metadata"],
                embedding_hints=["synthetic"],
                description="synthetic description",
            )
            return [metadata]

        def flush(self):
            data = self._buffer
            self._buffer = []
            return data

        def get_usage_totals(self):
            return {}

    monkeypatch.setattr(
        "autopotter_tools.media_database_pipeline.GPTMetadataAnalyzer",
        _FakeAnalyzer,
    )


def _print_pipeline_debug(pipeline: MediaDatabasePipeline, keyword: str = "timelapse") -> None:
    """Utility to display DB stats + sample keyword results when tests run."""
    frame_count = pipeline.db.count_frames()
    print(f"[media_pipeline] frame_count={frame_count}")

    results = pipeline.keyword_search(keyword)
    print(f"[media_pipeline] keyword='{keyword}' hits={len(results)}")
    for frame in results[:5]:
        print(
            f"  - {frame.frame_id} @ {frame.image_path} "
            f"activities={frame.activities} use_case={frame.use_case}"
        )


def test_pipeline_indexes_media_and_supports_keyword_search(tmp_path):
    media_root = tmp_path / "media"
    preview_root = tmp_path / "media_previews"
    db_path = tmp_path / "frames.sqlite"
    shutil.copytree("tests/test_images", media_root)

    pipeline = MediaDatabasePipeline(
        overrides={
            "dbbuilder_media_library_dir": str(media_root),
            "dbbuilder_media_preview_dir": str(preview_root),
            "dbbuilder_media_database_path": str(db_path),
            "dbbuilder_max_frames_per_media": 1,
            "dbbuilder_media_supported_extensions": ["jpg", "mp4"],
            "gcs_folders": ["."],
        }
    )

    summary = pipeline.run(limit_media=3)
    assert summary["media_processed"] >= 3
    assert summary["frames_indexed"] > 0
    assert preview_root.exists()

    results = pipeline.keyword_search("timelapse")
    assert results, "Expected at least one keyword search result"
    assert all(Path(r.image_path).exists() for r in results)

    _print_pipeline_debug(pipeline, keyword="timelapse")

    pipeline.db.close()

