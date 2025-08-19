"""
Autopotter Tools Package

A collection of tools for managing GPT interactions, Instagram APIs, and other automation tasks.
"""

# Import and expose main functions/classes for easier access
from .logger import get_logger
from .gpt_thread_manager import GPTThreadManager
from .gpt_responses_manager import GPTResponsesManager
from .gptassistant_api import GPTAssistant
from .instagram_api import InstagramConfig, InstagramVideoUploader
from .json2video_api import Json2VideoConfig, Json2VideoAPI
from .gcs_manager import GCSManager
from .instagram_analytics import InstagramAnalyticsManager
from .googlestorage_api import GCSClient

__all__ = [
    'get_logger',
    'GPTThreadManager', 
    'GPTResponsesManager',
    'GPTAssistant',
    'InstagramConfig',
    'InstagramVideoUploader',
    'Json2VideoConfig',
    'Json2VideoAPI',
    'GCSManager',
    'InstagramAnalyticsManager',
    'GCSClient'
]

__version__ = "1.0.0"
