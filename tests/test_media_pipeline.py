import shutil
import types
from pathlib import Path

import pytest

from autopotter_tools import embedding_service
from autopotter_tools.media_database_pipeline import MediaDatabasePipeline


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
            "media_library_dir": str(media_root),
            "media_preview_dir": str(preview_root),
            "media_database_path": str(db_path),
            "max_frames_per_media": 1,
            "media_supported_extensions": ["jpg", "mp4"],
            "metadata_analyzer_mode": "simple",
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

