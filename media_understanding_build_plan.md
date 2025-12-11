# Media Understanding System — Build Plan Summary

A full pipeline for extracting, analyzing, embedding, storing, and searching visual metadata from your media library.

This system analyzes your entire media library by extracting key frames from videos, downsampling images, tagging each frame with GPT-generated metadata, generating semantic embeddings, storing everything in a searchable database, and exposing search tools that allow an AI agent to intelligently select clips, build sequences, and generate fully automated video edits. It gives Autopot.ter a structured, visual understanding of your content so it can behave like a lightweight video editor with actual awareness of what’s in your footage.

1. Media Tools Library: Core image and video helper functions for periodic video frame extraction, image downsampling, or duration calculation for multiple frames. Any downstream image/video tools should be here.

2. Core Data Models: Pydantic schemas that describe media items, frames, and embeddings.

3. Embedding Generator: Builds semantic embeddings from metadata so the system can search by meaning, not just keywords.

4. Vector & Metadata Database: Stores frame metadata, embeddings, and media relationships for fast retrieval and similarity search.

5. Database Gneration Pipeline: Captures frames for gpt analysis, Sends batches of preview images to GPT and returns structured tags, builds database, generates embeddings for future search function

6. Keyword Search: Filters frames using textual metadata fields like shot type or detected objects.

7. Semantic Embedding Search: Finds visually and conceptually similar frames using embedding similarity.

    Notes: It's clear that the embedding needs more info. Include the gcs library notes into the data so that filenames can be used. Is parent data included?? Would this data distract the model from it's purpose???

    Need to develope some kind of readable summary of the database: How? Have gpt summarize the text content of the database so that it can create search parameters with some confidence. How??? Cluster all the parent embeddings then ouput the closest actual frame item as a description?

    

    ***⚠️ change the batching so that images are sent in batches, but videos are sent one at a time?? Should request some summary of what the video is about in addition to the frame notes? Or, change my structure so that there is no frame... just metadata blobs for images, and metadata blobs for videos... How do I want search to work? I think that defines the structure!!!***

     ✅ organize the rest of the files into the sync folder, then execute.. perhaps, come up with a scheme to only add new media, not redo old media. 

    ✅ Next Step: sync db, then build toolset
    
    ✅ There's a problem. The filenames are.. bad again in the db. 

    ⚠️ GPT seems to often search for the acronyms like pot series names... re-tokenize the filename to include...
    ⚠️ Database doesn't include the video duration????!!!!
    ⚠️ Need to re-write all the prompts with search in mind. Possibly add in direct media_id search as well. Or everything from a given parent? (could tell it to keyword search the parent_id...)
    ⚠️ So there's 



Next 2 phases. build toolset for the ageng, then give the agent the ability to call the search tools on the database in order to generate it's videos. 
 
First: 
agent_db_tools:
TOOLS = [ the list of callable tools for the model. use the example function definition defined here https://platform.openai.com/docs/guides/function-calling ]
 - check_get_db: checks local file system for a sqlite db with a path/name provided by the the config file "agent_metadata_database". Retraives it from gcs using the same path, if it doesn't exist locally. Fails hard if it can't accomplish. This should run on class init.
 - search_keyword(keyword, limit): runs the keyword search to provide results to the agent
 - search_semantic(text, limit): runs the semantic search to provide results to the agent
 - get_agent_tool_defs -> List : Produces a list of tools for the agent, as specified here: https://platform.openai.com/docs/guides/function-calling

 Seccond: modify enhanced_autodraft to allow the ai to make tool calls (specifically the ones surfaced by agent_db_tools)in a loop (maximum of 3 loops speced by config).

 All new config parameters should be prefixed with "agentdraft_". create the first phase, but ask if any clarification is needed. Keep it as simple and straightforward as possible to accoplish the goal

      Later: validate Databse frames (count, and have parent)
      

8. ✅ Clip Lookup Resolver: Maps a frame back to its original media file and exact timestamp for precise clip extraction. Maps groups of frames from the same file to a timestamp and duration.

9. AI Tool Interface: Exposes DB search and metadata functions as tools that the AI agent can call during video generation. Tell gpt that if searches don't produce good results, try again. Can loop... I think I should just give it the keyword search, the semantic search tool, and a tool for getting everything for a given video (so it can see where to start/stop) and see what it generates!!

    Keep major logic in my pipeline, give openai tools which my stuff cant do:

    ***Searches***
    - Keyword search
    - Semantic Search
    - Filename Search.. (use keyword search on the fileid??)
    
    ***Tools***
    - JSON Validator
    
    ***Expected Output***
    - Run search or tool
    - Done: with loops, jsonvalidated, switch back to my pipeline for vid creation


10. System Testing & Ops: Automated tests plus orchestration scripts that validate the pipeline end-to-end and keep preview assets in sync with the media library.




# Build:

## PHASE 1 — Media Tools Library

### 1.1 Frame Extraction Utilities
```python
def frame_extractor(interval_seconds=2.0):
    '''ffmpeg frame grabs with timestamp'''
```
- Yield `(image, timestamp, parent_media_id)` tuples.

### 1.2 Downsampling & Preview Writers
```python
def downsample_and_store(image, max_px=256, storage="local") -> str:
    '''Resize, encode PNG/JPEG, persist to previews/, return image_path.'''
```
- Share logic for both extracted frames and standalone images so downstream code sees uniform previews.
- Support local disk and GCS storage adapters with checksum + dedupe baked in.

### 1.2 Downsampling & Preview Writers
```python
def get_metadata(file) -> str:
    '''get the image or video metadata for a given media file'''
```
- Get the metadata for a given media file. Output dict, including duration, resolution, orientation, or other relevant metadata

### 1.4 Library Tests
- Add pytest coverage for extractor, downsampler, and metadata


## PHASE 2 — Core Data Models

### 2.1 Media Item (videos or images)
```python
class MediaItem(BaseModel):
    media_id: str
    path: str
    media_type: Literal["video", "image"]
    metadata: dict
```

### 2.2 Frame Metadata (per extracted image)
```python
class MediaFrameMetadata(BaseModel):
    frame_id: str
    parent_media_id: str
    timestamp: Optional[float]
    image_path: str

    shot_type: Optional[Literal[
        "macro", "closeup", "medium", "wide", "overhead", "hands_only"
    ]]
    emotional_tone: Optional[Literal[
        "calming", "energetic", "satisfying", "chaotic", "artistic"
    ]]
    use_case: Optional[Literal[
        "hook", "process_detail", "texture_shot", "reveal", "b_roll"
    ]]
    activities: List[str] = []
    materials: List[str] = []
    objects_detected: List[str] = []
    image_qualities: List[str] = []
    embedding_hints: List[str] = []
    description: Optional[str]
```

### 2.3 Frame Embedding
```python
class FrameEmbedding(BaseModel):
    frame_id: str
    embedding: List[float]
```

## PHASE 3 — Embedding Generator

### 3.1 Convert Metadata to Text for Embeddings
```python
def build_embedding_text(meta: MediaFrameMetadata) -> str:
    '''Use metadata + embedding_hints to create a short description.'''
```

### 3.2 Compute Embeddings
```python
def compute_frame_embedding(text: str) -> List[float]:
    '''Call OpenAI embedding API.'''
```

### 3.3 Store Embeddings
```python
def save_embedding(db, frame_id, embedding):
    '''Insert into pgvector or local vector DB.'''
```

## PHASE 4 — Vector & Metadata Database

### 4.1 Save Frame Metadata
```python
def save_frame_metadata(db, metadata: MediaFrameMetadata):
    '''Insert/update metadata entry.'''
```

### 4.2 Link Media Item to Frames
```python
def link_frame_to_media(db, frame_id, parent_media_id, timestamp):
    '''Create relationships for retrieval.'''
```

### 4.3 Save Media Item
```python
def save_media_item(db, media: MediaItem):
    '''Insert/update top-level video/image metadata.'''
```

## PHASE 5 — Database Generation Pipeline

### 5.1 Scan & Register Media
```python
def scan_media_library(directory_path) -> List[MediaItem]:
    '''Discover videos/images, assign media_ids, extract basic metadata.'''
```
- Store discovered items immediately via `save_media_item` to keep the catalog fresh.
- Attach hashes + modification timestamps so incremental rescans skip unchanged assets.

### 5.2 Extract & Downsample Previews
```python
def extract_frames(video_path, interval_seconds=2.0) -> List[Tuple[Image, float]]:
    '''Returns (frame_image, timestamp) pairs.'''

def downsample_image(image, max_size=256) -> Image:
    '''Resize for GPT and embedding efficiency.'''

def prepare_media_for_analysis(media_item) -> List[str]:
    '''Save downsampled PNG/JPEG previews to disk/GCS, return file paths.'''
```
- Use the Media Tools Library helpers for cadence control, duration estimation, and storage adapters.
- Persist preview paths on `MediaFrameMetadata.image_path` so GPT + embedding jobs operate on identical bytes.

### 5.3 GPT Metadata Analysis
```python
def analyze_images_with_gpt(image_paths: List[str]) -> List[MediaFrameMetadata]:
    '''Send images to OpenAI with prompt, parse into model objects.'''
```
- Prompt enumerates allowed tag values to keep outputs schema-conformant.
- Batch requests to respect rate limits and reuse cached descriptions when previews already exist.

### 5.4 Embed & Persist
```python
def run_database_generation(media_root: Path, db):
    '''Orchestrate scan -> preview -> GPT -> embedding -> storage.'''
```
- For each frame metadata result, call `build_embedding_text`, `compute_frame_embedding`, `save_frame_metadata`, `save_embedding`, and `link_frame_to_media`.
- Track job progress in a lightweight queue (e.g., sqlite table) so partial runs can resume safely.

> _Note: Phase numbering mirrors the high-level summary. Phase 6 is intentionally left undefined until a new capability is added to the roadmap._

## PHASE 7 — Keyword Search
```python
def search_media_by_keyword(db, query: str) -> List[MediaFrameMetadata]:
    '''Filter by tags or metadata fields.'''
```
- Supports filtering by shot type, materials, activities, emotional tone, etc.
- Add pagination + sorting (timestamp, quality notes) to make UI tooling snappy.

## PHASE 8 — Semantic Embedding Search
```python
def search_media_by_embedding(db, nl_query: str, n=10) -> List[MediaFrameMetadata]:
    '''Convert natural language query -> embedding -> cosine similarity -> top N frames.'''
```
- Accept optional filters (media type, duration range) to constrain results.
- Return both metadata + similarity scores for downstream ranking.

## PHASE 9 — Clip Lookup Resolver
```python
def get_source_clip_location(frame_id) -> Tuple[media_path, timestamp]:
    '''Locate original media for JSON2Video slicing.'''
```
- When multiple selected frames share a media_id, aggregate timestamps using `estimate_clip_span` to form clip requests.
- Integrate with ffmpeg/JSON2Video to emit final time ranges for Autopotter’s editor.
- 
### 1.3 Duration Aggregation Helpers in Image Media Library
```python
def estimate_clip_span(frames: List[Tuple[float, float]]) -> float:
    '''Given timestamps or fps hints, compute representative segment duration.'''
```
- Convert grouped frames into clip length estimates for timeline-aware editing tools.


## PHASE 10 — AI Tool Interface
- Wrap keyword + embedding search plus clip lookup as callable tools (OpenAI responses, LangChain tools, etc.).
- Include safety checks (max frames per call, allowed directories) so the agent cannot exfiltrate arbitrary files.
- Provide structured responses (JSON with frame_ids, timestamps, preview URLs) that downstream planners can chain.
- Surface usage metrics back into ops dashboards for observability.

## PHASE 11 — System Testing & Ops
- Pytest suites for Media Tools Library, GPT parsing, embedding text builder, and DB accessors.
- Integration script `python scripts/run_media_pipeline.py --source ~/Potter/autopot1-sync` to exercise Phase 5 end-to-end.