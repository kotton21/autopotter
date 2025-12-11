import requests
import json
import time
import os
from datetime import datetime
from pathlib import Path
import tempfile
import copy
from typing import Any

import sys
from pathlib import Path

# Add the parent directory to Python path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager

# Try importing logger from autopotter_tools first, fallback to local import
try:
    from autopotter_tools.simplelogger import Logger
except ImportError:
    from simplelogger import Logger


class Json2VideoAPI:
    """
    Minimal client for the json2video API
    Only implements the methods required by autopotter_workflow.py
    """
    
    def __init__(self, config_path="autopost_config.enhanced.json"):
        self.config_manager = ConfigManager(config_path)
        
        # Initialize API settings from config
        self.api_key = self.config_manager.config["json2video_api_key"]
        self.base_url = self.config_manager.config["json2video_base_url"]
        self.timeout = self.config_manager.config["json2video_timeout"]
        self.gcs_bucket = self.config_manager.config.get("gcs_bucket", "").strip()
        self.gcs_folders = tuple(self.config_manager.config.get("gcs_folders", []) or [])
        self.gcs_draft_folder = self.config_manager.config.get("gcs_draft_folder", "")
        
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        # Validate API key
        if not self.api_key or self.api_key.startswith("${"):
            error_msg = "Please set your json2video API key in the config file"
            Logger.error(error_msg)
            raise ValueError(error_msg)
        
        Logger.info(f"Json2VideoAPI initialized with base URL: {self.base_url}")

    # -------------------- Config helpers -------------------- #
    def _bucket_base_url(self) -> str:
        """Return the HTTPS base URL for the configured GCS bucket."""
        bucket = self.gcs_bucket.lstrip("/").rstrip("/")
        if not bucket:
            raise ValueError("gcs_bucket is required to resolve media paths")
        return f"https://storage.googleapis.com/{bucket}/"

    def _to_bucket_url(self, src: str) -> str:
        """
        Convert a local/relative path into a public GCS URL. If the value already
        looks like an http(s) URL, leave it untouched.
        """
        if not isinstance(src, str):
            return src

        lowered = src.lower()
        if lowered.startswith("http://") or lowered.startswith("https://"):
            return src

        if lowered.startswith("gs://"):
            without_scheme = src[5:]
            if "/" in without_scheme:
                bucket, path = without_scheme.split("/", 1)
                return f"https://storage.googleapis.com/{bucket.rstrip('/')}/{path.lstrip('/')}"
            return f"https://storage.googleapis.com/{without_scheme}"

        base_url = self._bucket_base_url()

        # If the path already contains one of the configured folder names, preserve that
        parts = Path(src).parts
        candidate_prefixes = list(self.gcs_folders) + ([self.gcs_draft_folder] if self.gcs_draft_folder else [])
        for idx, part in enumerate(parts):
            if part in candidate_prefixes:
                rel = Path(*parts[idx:]).as_posix()
                return f"{base_url}{rel.lstrip('/')}"

        # Fallback: keep the last two path components to avoid collisions
        if parts:
            rel = Path(*parts[-2:]).as_posix() if len(parts) >= 2 else parts[-1]
            return f"{base_url}{rel.lstrip('/')}"

        return base_url

    # def _sanitize_config(self, video_config: dict) -> dict:
    #     """
    #     Convert loose configs to the allowed template shape from resources/json2video_templates.md:
    #       top-level: quality, draft, scenes, elements, resolution, fps
    #       scenes: comment, elements
    #       elements: type, src, position, muted, resize, cache, duration, seek,
    #         fade-in, fade-out, volume, text, voice, model, style, settings,
    #         height, x, y, start, end, comment

    #     Also maps legacy keys like canvas/audio/clips/overlays into template scenes/elements.
    #     """
    #     if not isinstance(video_config, dict):
    #         return video_config

    #     allowed_top = {"quality", "draft", "scenes", "elements", "resolution", "fps"}
    #     allowed_scene = {"comment", "elements", "duration"}
    #     allowed_element = {
    #         "type",
    #         "src",
    #         "position",
    #         "muted",
    #         "resize",
    #         "cache",
    #         "duration",
    #         "seek",
    #         "fade-in",
    #         "fade-out",
    #         "volume",
    #         "text",
    #         "voice",
    #         "model",
    #         "style",
    #         "settings",
    #         "height",
    #         "x",
    #         "y",
    #         "start",
    #         "end",
    #         "comment",
    #     }

    #     removed: list[str] = []

    #     def _filter_element(element: dict) -> dict:
    #         filtered = {}
    #         for k, v in element.items():
    #             if k in allowed_element:
    #                 filtered[k] = v
    #             else:
    #                 removed.append(k)
    #         return filtered

    #     def _build_audio_elements(raw_audio: Any) -> list[dict]:
    #         if not isinstance(raw_audio, list):
    #             return []
    #         elements = []
    #         for item in raw_audio:
    #             if not isinstance(item, dict):
    #                 continue
    #             src = item.get("src")
    #             if not src:
    #                 continue
    #             elements.append(
    #                 _filter_element(
    #                     {
    #                         "type": "audio",
    #                         "src": src,
    #                         "seek": item.get("start", item.get("seek", 0)),
    #                         "fade-in": item.get("fade-in", 0.5),
    #                         "fade-out": item.get("fade-out", 0.5),
    #                         "volume": item.get("volume", 0.3),
    #                         "duration": item.get("duration", -2),
    #                     }
    #                 )
    #             )
    #         return elements

    #     def _build_text_elements(raw_overlays: Any) -> list[dict]:
    #         if not isinstance(raw_overlays, list):
    #             return []
    #         elements = []
    #         for ov in raw_overlays:
    #             if not isinstance(ov, dict):
    #                 continue
    #             if ov.get("type") != "text":
    #                 continue
    #             el = {
    #                 "type": "text",
    #                 "text": ov.get("text"),
    #                 "position": "custom",
    #                 "x": ov.get("position", {}).get("x") if isinstance(ov.get("position"), dict) else 0,
    #                 "y": ov.get("position", {}).get("y") if isinstance(ov.get("position"), dict) else 0,
    #                 "style": ov.get("style"),
    #             }
    #             elements.append(_filter_element(el))
    #         return elements

    #     def _ensure_scene_duration(scene: dict) -> dict:
    #         if "duration" in scene:
    #             try:
    #                 scene["duration"] = max(0.5, float(scene.get("duration", 0) or 0))
    #                 return scene
    #             except Exception:
    #                 removed.append("duration")
    #                 scene.pop("duration", None)
    #         # infer duration from elements if possible
    #         durations = []
    #         for el in scene.get("elements", []) or []:
    #             if isinstance(el, dict) and "duration" in el:
    #                 try:
    #                     durations.append(float(el.get("duration", 0) or 0))
    #                 except Exception:
    #                     continue
    #         if durations:
    #             scene["duration"] = max(0.5, sum(durations))
    #         else:
    #             scene["duration"] = 3.0
    #         return scene

    #     def _clip_to_scene(clip: dict) -> dict:
    #         clip_type = clip.get("type", "image")
    #         src = clip.get("src")
    #         base_el = {
    #             "type": "video" if clip_type == "video" else "image",
    #             "src": src,
    #             "duration": max(0.5, float(clip.get("duration", 3) or 0)),
    #             "resize": "cover",
    #             "position": "center-center",
    #         }
    #         if clip_type == "video":
    #             base_el["muted"] = clip.get("muted", True)

    #         elements = [_filter_element(base_el)]
    #         elements.extend(_build_text_elements(clip.get("overlays")))

    #         comment = clip.get("comment") or (Path(src).stem if src else "scene")
    #         scene = {
    #             "comment": comment,
    #             "elements": elements,
    #         }
    #         return _ensure_scene_duration(scene)

    #     # Start with defaults required by template
    #     canonical = {
    #         "quality": video_config.get("quality", "high"),
    #         "draft": video_config.get("draft", False),
    #         "scenes": [],
    #         "elements": [],
    #         "resolution": video_config.get("resolution", "instagram-story"),
    #         "fps": video_config.get("fps", 25),
    #     }

    #     # Map audio -> global elements
    #     canonical["elements"].extend(_build_audio_elements(video_config.get("audio")))

    #     # Use provided scenes if already template-shaped; otherwise build from clips
    #     if isinstance(video_config.get("scenes"), list) and video_config["scenes"]:
    #         for scene in video_config["scenes"]:
    #             if not isinstance(scene, dict):
    #                 continue
    #             filtered_scene = {}
    #             for k in allowed_scene:
    #                 if k not in scene:
    #                     continue
    #                 if k == "elements":
    #                     filtered_scene[k] = [_filter_element(e) for e in scene.get("elements", [])]
    #                 elif k == "duration":
    #                     try:
    #                         filtered_scene[k] = max(0.5, float(scene.get("duration", 0) or 0))
    #                     except Exception:
    #                         removed.append("duration")
    #                 else:
    #                     filtered_scene[k] = scene[k]
    #             canonical["scenes"].append(_ensure_scene_duration(filtered_scene))
    #     elif isinstance(video_config.get("clips"), list):
    #         for clip in video_config["clips"]:
    #             if isinstance(clip, dict):
    #                 canonical["scenes"].append(_clip_to_scene(clip))

    #     # Fallback: if no scenes but we have elements with media, build one scene
    #     if not canonical["scenes"] and isinstance(video_config.get("elements"), list):
    #         media_elements = [
    #             el
    #             for el in video_config["elements"]
    #             if isinstance(el, dict) and el.get("type") in ("image", "video") and el.get("src")
    #         ]
    #         if media_elements:
    #             scene_elements = []
    #             for el in media_elements:
    #                 duration = max(0.5, float(el.get("duration", 3) or 0))
    #                 scene_elements.append(
    #                     _filter_element(
    #                         {
    #                             "type": el.get("type"),
    #                             "src": el.get("src"),
    #                             "duration": duration,
    #                             "resize": el.get("resize", "cover"),
    #                             "position": el.get("position", "center-center"),
    #                             "muted": el.get("muted", True) if el.get("type") == "video" else None,
    #                         }
    #                     )
    #                 )
    #             canonical["scenes"].append({"comment": "auto-scene", "elements": scene_elements})

    #     # Ensure we have at least one scene with positive duration elements
    #     if not canonical["scenes"]:
    #         raise ValueError("No scenes available after sanitization; cannot build movie")

    #     # Final filter to ensure only allowed keys remain
    #     final_cleaned = {}
    #     for k, v in canonical.items():
    #         if k not in allowed_top:
    #             removed.append(k)
    #             continue
    #         final_cleaned[k] = v

    #     if removed:
    #         Logger.info(f"[json2video] Removed unsupported field(s): {sorted(set(removed))}")
    #     return final_cleaned

    def resolve_media_paths(self, video_config: dict) -> dict:
        """
        Walk a json2video config and convert any 'src' fields to fully-qualified
        GCS URLs. Returns a new config dict.
        """
        replacements = []

        def _walk(node):
            if isinstance(node, dict):
                updated = {}
                for key, value in node.items():
                    if key == "src":
                        new_value = self._to_bucket_url(value)
                        if new_value != value:
                            replacements.append((value, new_value))
                        updated[key] = new_value
                    else:
                        updated[key] = _walk(value)
                return updated
            if isinstance(node, list):
                return [_walk(item) for item in node]
            return node

        resolved = _walk(video_config)
        if replacements:
            for old, new in replacements:
                Logger.info(f"[json2video] Resolved media path: {old} -> {new}")
        else:
            Logger.info("[json2video] No media paths required resolution.")
        return resolved
        
    def test_connection(self):
        """Test the connection to the json2video API"""
        try:
            Logger.info("Testing connection to json2video API...")
            
            url = f"{self.base_url}/movies"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                Logger.info("API connection successful")
                return True
            elif response.status_code == 401:
                Logger.error("API key authentication failed")
                return False
            elif response.status_code == 403:
                Logger.error("API access forbidden - check API key permissions")
                return False
            else:
                Logger.warning(f"Unexpected response: {response.status_code}")
                return False
                
        except Exception as e:
            Logger.error(f"Connection test failed: {e}")
            return False
    
    def create_video(self, video_config):
        """Create a video using json2video API"""
        try:
            url = f"{self.base_url}/movies"
            Logger.info("Creating video with API...")

            sanitized_config = video_config # = self._sanitize_config(video_config)
            prepared_config = self.resolve_media_paths(sanitized_config)
            
            response = requests.post(url, headers=self.headers, json=prepared_config)
            response.raise_for_status()
            
            result = response.json()
            project_id = result.get('project')
            
            if not project_id:
                error_msg = "No project ID in API response"
                Logger.error(error_msg)
                raise Exception(error_msg)
            
            Logger.info(f"Video creation initiated. Project ID: {project_id}")
            
            # Return with 'id' field for compatibility
            result['id'] = project_id
            return result
            
        except Exception as e:
            Logger.error(f"Error creating video: {e}")
            raise
    
    def wait_for_completion(self, project_id):
        """Wait for video creation to complete"""
        start_time = time.time()
        Logger.info(f"Waiting for project {project_id} to complete...")
        
        # Note: We don't validate project existence upfront because newly created projects
        # might not immediately appear in the API response. We'll check during the first status check.
        
        while time.time() - start_time < self.timeout:
            try:
                status_info = self.get_project_status(project_id)
                
                # Extract status from response
                if 'movie' in status_info:
                    movie_info = status_info['movie']
                    status = movie_info.get('status', 'unknown')
                    success = movie_info.get('success', False)
                else:
                    status = status_info.get('status', 'unknown')
                    success = status_info.get('success', False)
                
                if status == 'done' or success:
                    Logger.info(f"Project {project_id} completed successfully!")
                    
                    # Log the finished video URL
                    if 'movie' in status_info:
                        movie_info = status_info['movie']
                        video_url = movie_info.get('url')
                        if video_url:
                            Logger.info(f"Finished video URL: {video_url}")
                        else:
                            Logger.warning("No video URL found in response")
                    else:
                        video_url = status_info.get('url')
                        if video_url:
                            Logger.info(f"Finished video URL: {video_url}")
                        else:
                            Logger.warning("No video URL found in response")
                    
                    return status_info
                elif status == 'error':
                    # Get more details about the error if available
                    error_msg = "Video creation failed"
                    if 'movie' in status_info:
                        movie_info = status_info['movie']
                        if 'error' in movie_info:
                            error_msg = f"Video creation failed: {movie_info['error']}"
                        elif 'message' in movie_info:
                            error_msg = f"Video creation failed: {movie_info['message']}"
                    Logger.error(error_msg)
                    raise Exception(error_msg)
                elif status in ['pending', 'processing', 'running']:
                    Logger.debug(f"Still {status}... waiting 10 seconds")
                    time.sleep(10)
                elif status == 'not_found_yet':
                    Logger.debug(f"Project {project_id} not found yet (may be newly created), waiting 10 seconds")
                    time.sleep(10)
                else:
                    Logger.warning(f"Unknown status: {status}, waiting 10 seconds")
                    time.sleep(10)
                    
            except Exception as e:
                Logger.error(f"Error checking status: {e}")
                # If we get an error during status check, it likely means the project failed
                # Don't continue waiting, raise the exception to stop the process
                raise Exception(f"Video creation failed with error: {e}")
        
        error_msg = f"Video creation timed out after {self.timeout} seconds"
        Logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_project_status(self, project_id):
        """Get the current status of a video creation project"""
        try:
            url = f"{self.base_url}/movies"
            params = {"project": project_id}
            
            Logger.debug(f"Getting project status for {project_id}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            # Look for the specific project in the response
            if 'movies' in result and isinstance(result['movies'], list):
                for movie in result['movies']:
                    if movie.get('project') == project_id:
                        return movie
            
            # If we can't find the specific project, return the full response
            return result
            
        except Exception as e:
            Logger.error(f"Error getting project status: {e}")
            raise
    
    def download_video(self, project_id, output_path=None):
        """Download the completed video"""
        try:
            # Get project info first
            status_info = self.get_project_status(project_id)
            
            # Extract download URL
            if 'movie' in status_info:
                movie_info = status_info['movie']
                download_url = movie_info.get('url')
            else:
                download_url = status_info.get('url')
            
            if not download_url:
                error_msg = "No download URL found in project status"
                Logger.error(error_msg)
                raise Exception(error_msg)
            
            # Determine output path
            if not output_path:
                filename = f"json2video_{project_id}.mp4"
                output_path = os.path.join(tempfile.gettempdir(), filename)
            
            # Download the video
            Logger.info(f"Downloading video to: {output_path}")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            Logger.info(f"Video downloaded successfully to: {output_path}")
            return output_path
            
        except Exception as e:
            Logger.error(f"Error downloading video: {e}")
            raise


    def validate_json2video_config_simple(self, video_config_str: str):
        """Simple validate a json2video config. Put all errors and warnings into a dict and return it."""
        errors = []
        warnings = []
        validated = True

        try:   
            video_config = json.loads(video_config_str.strip())
        except Exception as e:
            errors.append(f"Error parsing video_config: {e.message}")
            return {"validated": False, "errors": errors, "warnings": warnings}
        if not video_config:
            errors.append("video_config is required")
        if not isinstance(video_config, dict):
            errors.append("video_config must be a dict")

        from typing import Optional, List, Literal
        movie_template = {
            "quality": Literal["high"],
            "draft": Literal[False],
            "scenes": List[dict],
            "elements": Optional[List[dict]],
            "resolution": Literal["instagram-story"],
            "fps": Literal[25],
        }

        def _check_against_template(config, template):
            for key, value in template.items():
                if key not in config:
                    errors.append(f"key {key} is required in video_config")
                elif type(value) == Literal:
                    if config[key] not in value:
                        errors.append(f"key {key} has value {config[key]} but should be in {value}")
            return errors, warnings

        movie_errors, movie_warnings = _check_against_template(video_config, movie_template)
        errors.extend(movie_errors)
        warnings.extend(movie_warnings)
        

        if len(errors) > 0:
            validated = False            
        return {"validated": validated, "errors": errors, "warnings": warnings}

    def validate_json2video_config_pydantic(self, video_config_str: str) -> dict:
        """
        Validate a json2video config using Pydantic with extra='forbid'.
        Returns a dict with validated(bool), errors(list), warnings(list).
        """
        errors: list[str] = []
        # warnings: list[str] = []

        try:
            raw_config = json.loads(video_config_str.strip())
        except Exception as e:
            errors.append(f"Error parsing video_config: {getattr(e, 'msg', str(e))}")
            return {"validated": False, "errors": errors}

        from typing import List, Optional, Literal
        from pydantic import BaseModel, Field, ValidationError, ConfigDict

        class J2VElement(BaseModel):
            # model_config = ConfigDict(extra="forbid")
            type: Literal["audio", "voice", "text", "video", "image"]
            src: Optional[str] = None
            position: Optional[str] = Field(default=None)
            muted: Optional[bool] = None
            resize: Optional[str] = None
            cache: Optional[bool] = None
            duration: Optional[float] = None
            seek: Optional[float] = None
            fade_in: Optional[float] = Field(default=None, alias="fade-in")
            fade_out: Optional[float] = Field(default=None, alias="fade-out")
            volume: Optional[float] = None
            text: Optional[str] = None
            voice: Optional[str] = None
            model: Optional[str] = None
            style: Optional[str | dict] = None
            settings: Optional[dict] = None
            height: Optional[int] = None
            x: Optional[float] = None
            y: Optional[float] = None
            start: Optional[float] = None
            end: Optional[float] = None
            comment: Optional[str] = None

        class J2VScene(BaseModel):
            model_config = ConfigDict(extra="forbid")
            comment: Optional[str] = None
            duration: Optional[float] = None
            elements: List[J2VElement]

        class J2VMovie(BaseModel):
            model_config = ConfigDict(extra="forbid")
            quality: Literal["high"]
            draft: Literal[False]
            scenes: List[J2VScene]
            elements: Optional[List[J2VElement]] = None
            resolution: Literal["instagram-story"]
            fps: Literal[25]

        try:
            J2VMovie.model_validate(raw_config)
            return {"validated": True}
        except ValidationError as ve:
            for err in ve.errors():
                loc = ".".join(str(p) for p in err.get("loc", []))
                msg = err.get("msg", "validation error")
                errors.append(f"{loc}: {msg}")
            return {"validated": False, "errors": errors}


    # def validate_json2video_config(self, video_config):
    #     """Validate a json2video config"""
    #     errors = []
    #     warnings = []

    #     from typing import Dict, List, Literal, Optional

    #     movie_template = {
    #         "quality": "high",
    #         "draft": False,
    #         "scenes": [],
    #         "elements": [],
    #         "resolution": "instagram-story",
    #         "fps": 25,
    #     }

    #     movie_element_template = {
    #         "type": Literal["audio", "voice", "text"],
    #     }

    #     movie_scene_template = {
    #         "elements": [],
    #     }

    #     scene_element_template = {
    #         "type": Literal["video", "image"],
    #     }


    #     audio_element_template_json = json.dumps("""{
    #         "type": "audio",
    #         "src": "",
    #         "seek": 50,
    #         "fade-in": 0.5,
    #         "volume": 0.3,
    #     }""")

    #     voice_element_template_json = json.dumps("""{
    #         "type": "voice",
    #         "text": "",
    #         "voice": "en-US-JennyNeural",
    #         "model": "azure",
    #         "volume": 1,
    #     }""")



    #     return ""
        
        


def main():
    """Simple test function"""
    try:
        api = Json2VideoAPI()
        if api.test_connection():
            Logger.info("Connection test passed")
        else:
            Logger.error("Connection test failed")
    except Exception as e:
        Logger.error(f"Error: {e}")


if __name__ == "__main__":
    main()
