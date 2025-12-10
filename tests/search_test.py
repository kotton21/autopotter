import argparse
import json
from pathlib import Path

from autopotter_tools.embedding_service import EmbeddingService
from autopotter_tools.media_database import MediaDatabase
from config import ConfigManager


def pretty_print(
    db: MediaDatabase,
    frame,
    extra: dict | None = None,
    verbose: bool = True,
    hit_index: int | None = None,
):
    data = frame.model_dump() if hasattr(frame, "model_dump") else frame.dict()
    data["parent_media"] = _load_parent_media(db, frame.parent_media_id)
    embedding = _load_embedding(db, frame.frame_id)
    data["embedding_length"] = len(embedding) if embedding else 0
    if extra:
        data.update(extra)
    prefix = f"\n[hit {hit_index}]" if hit_index is not None else "\n"
    if verbose:
        print(prefix)
        print(json.dumps(data, indent=2))
        return
    filename = Path(frame.image_path).name
    minimal = {
        "image_filename": filename,
        "image_qualities": data.get("image_qualities"),
        "description": data.get("description"),
    }
    print(prefix)
    print(json.dumps(minimal, indent=2))


def run_keyword(db: MediaDatabase, keyword: str, limit: int, verbose: bool):
    results = db.search_by_keyword(keyword, limit=limit)
    for idx, frame in enumerate(results, start=1):
        pretty_print(db, frame, verbose=verbose, hit_index=idx)
    print(f"[search-test] keyword='{keyword}' hits={len(results)}")
    print_db_stats(db)


def run_semantic(
    db: MediaDatabase, config: dict, query: str, limit: int, verbose: bool
):
    embedder = EmbeddingService(
        api_key=config.get("openai_api_key"),
        model=config.get("embedding_model", "text-embedding-3-small"),
    )
    vector = embedder.embed(query)
    results = db.search_by_embedding(vector, limit=limit)
    for idx, (score, frame) in enumerate(results, start=1):
        pretty_print(
            db, frame, {"similarity": score}, verbose=verbose, hit_index=idx
        )
    print(f"[search-test] semantic query='{query}' hits={len(results)}")
    print_db_stats(db)


def _load_parent_media(db: MediaDatabase, media_id: str):
    cursor = db.conn.cursor()
    row = cursor.execute(
        "SELECT media_id, path, metadata FROM media_items WHERE media_id=?",
        (media_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "media_id": row["media_id"],
        "path": row["path"],
        "metadata": json.loads(row["metadata"]),
    }


def _load_embedding(db: MediaDatabase, frame_id: str):
    cursor = db.conn.cursor()
    row = cursor.execute(
        "SELECT embedding FROM embeddings WHERE frame_id=?", (frame_id,)
    ).fetchone()
    if not row:
        return None
    return json.loads(row["embedding"])


def print_db_stats(db: MediaDatabase):
    stats = db.get_db_size_and_rowcounts()
    print(f"[search-test] db_stats={stats}")


def main():
    parser = argparse.ArgumentParser(description="Ad-hoc search tester for media DB.")
    parser.add_argument(
        "--config",
        default="autopost_config.database.json",
        help="Path to config file for DB paths and keys.",
    )
    parser.add_argument("--keyword", type=str, help="Keyword to search for.")
    parser.add_argument("--semantic", type=str, help="Semantic query text.")
    parser.add_argument(
        "--limit", type=int, default=5, help="Maximum number of results to print."
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print full metadata (default) or, if false, only filenames plus image qualities/description.",
    )
    args = parser.parse_args()

    config = ConfigManager(args.config).config
    db_path = Path(config.get("media_database_path", "media_frames.sqlite"))
    db = MediaDatabase(db_path)

    if not args.keyword and not args.semantic:
        raise SystemExit("Provide --keyword or --semantic (or both).")

    if args.keyword:
        run_keyword(db, args.keyword, args.limit, args.verbose)
    if args.semantic:
        run_semantic(db, config, args.semantic, args.limit, args.verbose)


if __name__ == "__main__":
    main()

