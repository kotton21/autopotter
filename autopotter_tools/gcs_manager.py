#!/usr/bin/env python3
"""
Unified Google Cloud Storage Manager for Phase 2.
Combines inventory management and upload operations in a single interface.
"""

import os
import sys
import json
import random
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any
from google.cloud import storage

# Add the parent directory to Python path to import local modules
sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autopotter_tools.logger import get_logger
from config import get_config

class GCSManager:
    """
    Unified GCS manager that handles both inventory operations and upload operations.
    """
    
    def __init__(self, config_path: str = "autopost_config.enhanced.json"):
        self.config = get_config(config_path)
        self.logger = get_logger('gcs_manager')
        self.gcs_config = self.config.get_gcs_config()
        
        # Validate required configuration
        if not self.gcs_config.get('api_key_path'):
            raise ValueError("GCS API key path not configured")
        if not self.gcs_config.get('bucket'):
            raise ValueError("GCS bucket name not configured")
        
        # Initialize GCS client
        self.client = storage.Client.from_service_account_json(self.gcs_config['api_key_path'])
        self.bucket_name = self.gcs_config['bucket']
        self.bucket = self.client.bucket(self.bucket_name)
        
        # Configure folders to scan
        self.folders_to_scan = self.gcs_config.get('folders', None)
        
        self.logger.info(f"GCS Manager initialized for bucket: {self.bucket_name}")
    
    # ==================== INVENTORY OPERATIONS ====================
    
    def scan_folder(self, folder_prefix: str) -> List[Dict[str, Any]]:
        """
        Scan a specific folder and return basic file information.
        
        Args:
            folder_prefix: Folder prefix to scan (e.g., 'video_uploads/')
            
        Returns:
            List of file metadata dictionaries
        """
        self.logger.info(f"Scanning folder: {folder_prefix}")
        
        try:
            blobs = list(self.bucket.list_blobs(prefix=folder_prefix))
            files = []
            
            for blob in blobs:
                # Skip folder markers (blobs ending with /)
                if blob.name.endswith('/'):
                    continue
                
                # Get basic file info
                file_info = {
                    'name': blob.name,
                    'size_mb': round(blob.size / (1024 * 1024), 2) if blob.size else 0,
                    'public_url': f"https://storage.googleapis.com/{self.bucket_name}/{blob.name}",
                    'metadata': {}
                }
                
                # Add custom metadata (excluding goog-reserved fields)
                if blob.metadata:
                    for key, value in blob.metadata.items():
                        if not key.startswith('goog-reserved-'):
                            file_info['metadata'][key] = value
                
                files.append(file_info)
            
            self.logger.info(f"Found {len(files)} files in {folder_prefix}")
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to scan folder {folder_prefix}: {e}")
            return []
    
    def _categorize_file(self, filename: str) -> str:
        """
        Categorize a file based on its extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            Category string: 'videos', 'images', 'music', or 'other'
        """
        filename_lower = filename.lower()
        
        # Video file extensions
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        if any(filename_lower.endswith(ext) for ext in video_extensions):
            return 'videos'
        
        # Image file extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg']
        if any(filename_lower.endswith(ext) for ext in image_extensions):
            return 'images'
        
        # Music/Audio file extensions
        music_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma', '.aiff']
        if any(filename_lower.endswith(ext) for ext in music_extensions):
            return 'music'
        
        # Default to other for text, config, and unknown files
        return 'other'
    
    def generate_inventory(self, output_path: str = None) -> Dict[str, Any]:
        """
        Generate file inventory organized by folder with simplified file listings.
        
        Args:
            output_path: Optional path to save inventory JSON file
            
        Returns:
            Dictionary containing organized inventory data by folder
        """
        self.logger.info("Generating simplified GCS file inventory organized by folder")
        
        try:
            inventory_data = {
                'collection_info': {
                    'collected_at': datetime.now().isoformat(),
                    'source': 'gcs_manager',
                    'collection_version': '2.1'
                },
                'files_by_folder': {},
                'summary': {
                    'total_files': 0,
                    'total_size_mb': 0
                }
            }
            
            # Scan each configured folder
            for folder in self.folders_to_scan:
                try:
                    files = self.scan_folder(folder)
                    
                    if files:
                        # Create folder URL
                        folder_url = f"https://storage.googleapis.com/{self.bucket_name}/{folder}/"
                        
                        # Extract just the filenames (without folder prefix)
                        file_names = []
                        for file_info in files:
                            # Extract filename from full path (e.g., "video_uploads/file.mp4" -> "file.mp4")
                            filename = os.path.basename(file_info['name'])
                            file_names.append(filename)
                            
                            # Update summary counts
                            inventory_data['summary']['total_files'] += 1
                            inventory_data['summary']['total_size_mb'] += file_info.get('size_mb', 0)
                        
                        # Add folder to inventory
                        inventory_data['files_by_folder'][folder_url] = file_names
                    
                except Exception as e:
                    self.logger.error(f"Error scanning folder {folder}: {e}")
            
            # Round total size
            inventory_data['summary']['total_size_mb'] = round(inventory_data['summary']['total_size_mb'], 2)
            
            # Save to file if output path provided
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(inventory_data, f, indent=2)
                self.logger.info(f"File inventory saved to: {output_path}")
            
            self.logger.info("GCS file inventory generation completed")
            return inventory_data
            
        except Exception as e:
            self.logger.error(f"Failed to generate file inventory: {e}")
            raise
    
    # ==================== UPLOAD OPERATIONS ====================
    
    def upload_file(self, source_file_path: str, destination_blob_name: str) -> bool:
        """
        Upload a single file to GCS.
        
        Args:
            source_file_path: Path to the local file
            destination_blob_name: Destination blob name in GCS
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_path)
            self.logger.info(f"Uploaded {source_file_path} to {self.bucket_name}/{destination_blob_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to upload {source_file_path}: {e}")
            return False
    
    def upload_folder(self, source_folder: str, destination_folder_prefix: str = "") -> bool:
        """
        Upload an entire folder to GCS.
        
        Args:
            source_folder: Path to the local folder
            destination_folder_prefix: Destination folder prefix in GCS
            
        Returns:
            True if successful, False otherwise
        """
        try:
            for root, _, files in os.walk(source_folder):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_file_path, source_folder)
                    destination_blob_name = os.path.join(destination_folder_prefix, relative_path).replace("\\", "/")
                    if not self.upload_file(local_file_path, destination_blob_name):
                        return False
            
            self.logger.info(f"Uploaded folder {source_folder} to {self.bucket_name}/{destination_folder_prefix}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to upload folder {source_folder}: {e}")
            return False
    
    def get_most_recent_file_creation_time(self, prefix: str = None) -> datetime:
        """
        Get the most recent file creation time in a folder.
        
        Args:
            prefix: Folder prefix to check
            
        Returns:
            Most recent creation time or None if no files found
        """
        try:
            blobs = list(self.bucket.list_blobs(prefix=prefix))
            
            # Filter out folder blobs
            file_blobs = [blob for blob in blobs if not blob.name.endswith('/')]
            if not file_blobs:
                self.logger.info("No files found.")
                return None
            
            most_recent_blob = max(file_blobs, key=lambda blob: blob.time_created)
            self.logger.info(f"The most recent file is: {most_recent_blob.name}")
            return most_recent_blob.time_created
            
        except Exception as e:
            self.logger.error(f"Failed to get most recent file creation time: {e}")
            return None
    
    def upload_new_files(self, source_folder: str, destination_folder_prefix: str = "") -> bool:
        """
        Upload only new files that are newer than the most recent file in GCS.
        
        Args:
            source_folder: Path to the local folder
            destination_folder_prefix: Destination folder prefix in GCS
            
        Returns:
            True if successful, False otherwise
        """
        try:
            most_recent_creation_time = self.get_most_recent_file_creation_time(destination_folder_prefix)
            
            for root, _, files in os.walk(source_folder):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    file_time = datetime.fromtimestamp(os.path.getmtime(local_file_path)).astimezone(timezone.utc)
                    
                    if most_recent_creation_time is None or file_time > most_recent_creation_time:
                        relative_path = os.path.relpath(local_file_path, source_folder)
                        destination_blob_name = os.path.join(destination_folder_prefix, relative_path).replace("\\", "/")
                        if not self.upload_file(local_file_path, destination_blob_name):
                            return False
            
            self.logger.info(f"Uploaded new files from {source_folder} to {self.bucket_name}/{destination_folder_prefix}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload new files: {e}")
            return False
    
    # ==================== SELECTION OPERATIONS ====================
    
    def get_available_videos(self) -> List[Dict[str, Any]]:
        """
        Get list of available video files from video_uploads folder.
        
        Returns:
            List of video file dictionaries with metadata
        """
        try:
            all_files = self.scan_folder("video_uploads/")
            
            # Filter for video files only
            video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
            video_files = []
            
            for file_info in all_files:
                if any(file_info['name'].lower().endswith(ext) for ext in video_extensions):
                    # Get blob for additional metadata
                    blob = self.bucket.blob(file_info['name'])
                    blob.reload()
                    
                    # Handle None values for time fields
                    created_time = blob.time_created if blob.time_created else blob.updated
                    updated_time = blob.updated if blob.updated else created_time
                    
                    video_files.append({
                        'name': file_info['name'],
                        'size': blob.size,
                        'size_mb': file_info['size_mb'],
                        'created': created_time,
                        'updated': updated_time,
                        'public_url': file_info['public_url']
                    })
            
            # Sort by creation time (newest first), filtering out None values
            video_files = [v for v in video_files if v['created'] is not None]
            video_files.sort(key=lambda x: x['created'], reverse=True)
            
            return video_files
            
        except Exception as e:
            self.logger.error(f"Failed to get available videos: {e}")
            return []
    
    def select_next_video(self, uploaded_videos: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Select the next video to process based on upload history.
        
        Args:
            uploaded_videos: List of already uploaded videos
            
        Returns:
            Selected video dictionary or None if no new videos
        """
        try:
            available_videos = self.get_available_videos()
            
            # Filter out already uploaded videos
            uploaded_video_names = [item["video"] for item in uploaded_videos]
            new_videos = [v for v in available_videos if v['name'] not in uploaded_video_names]
            
            if not new_videos:
                return None
            
            # Select the most recent new video
            selected_video = new_videos[0]
            
            # Optional: Check for minimum video quality/size
            if selected_video['size'] < 1024 * 1024:  # Less than 1MB
                self.logger.warning(f"Selected video {selected_video['name']} is very small ({selected_video['size']} bytes)")
            
            return selected_video
            
        except Exception as e:
            self.logger.error(f"Failed to select next video: {e}")
            return None
    
    def get_audio_options(self) -> List[Dict[str, Any]]:
        """
        Get list of available audio files from music_uploads folder.
        
        Returns:
            List of audio file dictionaries with metadata
        """
        try:
            all_files = self.scan_folder("music_uploads/")
            
            # Filter for audio files only
            audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac']
            audio_files = []
            
            for file_info in all_files:
                if any(file_info['name'].lower().endswith(ext) for ext in audio_extensions):
                    # Get blob for additional metadata
                    blob = self.bucket.blob(file_info['name'])
                    blob.reload()
                    
                    audio_files.append({
                        'name': file_info['name'],
                        'size': blob.size,
                        'size_mb': file_info['size_mb'],
                        'created': blob.time_created,
                        'public_url': file_info['public_url']
                    })
            
            return audio_files
            
        except Exception as e:
            self.logger.error(f"Failed to get audio options: {e}")
            return []
    
    def select_random_audio(self, exclude_recent: int = None) -> Dict[str, Any]:
        """
        Select a random audio file, optionally excluding recently used ones.
        
        Args:
            exclude_recent: Number of most recent audio files to exclude
            
        Returns:
            Selected audio file dictionary or None if no audio available
        """
        try:
            audio_options = self.get_audio_options()
            
            if not audio_options:
                return None
                
            if exclude_recent and len(audio_options) > exclude_recent:
                # Exclude the N most recently used audio files
                available_audio = audio_options[exclude_recent:]
            else:
                available_audio = audio_options
            
            if not available_audio:
                return audio_options[0] if audio_options else None
            
            return random.choice(available_audio)
            
        except Exception as e:
            self.logger.error(f"Failed to select random audio: {e}")
            return None

def main():
    """Test the unified GCS Manager with inventory functionality."""
    parser = argparse.ArgumentParser(description="Unified Google Cloud Storage operations")
    parser.add_argument("operation", choices=["inventory", "upload_file", "upload_folder", "upload_new_files", "get_videos", "get_audio"], 
                       help="Operation to perform")
    parser.add_argument("--config", type=str, default="autopost_config.enhanced.json", help="Path to config file")
    parser.add_argument("--output", type=str, default="gcs_inventory_result.json", help="Output file for inventory")
    parser.add_argument("--source_file", type=str, help="Path to source file for upload operations")
    parser.add_argument("--destination_blob", type=str, help="Destination blob name for upload operations")
    parser.add_argument("--source_folder", type=str, help="Path to source folder for upload operations")
    parser.add_argument("--destination_folder", type=str, help="Destination folder prefix for upload operations")
    
    args = parser.parse_args()
    
    try:
        # Initialize the manager
        gcs_manager = GCSManager(args.config)
        
        if args.operation == "inventory":
            print("🔍 Generating GCS inventory organized by file type...")
            inventory_data = gcs_manager.generate_inventory(args.output)
            print("✅ GCS inventory generated successfully!")
            print(f"📊 Total files: {inventory_data['summary']['total_files']}")
            print(f"💾 Total size: {inventory_data['summary']['total_size_mb']:.2f} MB")
            print(f"📁 Output saved to: {args.output}")
            
            # Display breakdown by folder
            print("\n📁 File breakdown by folder:")
            for folder_url, files in inventory_data['files_by_folder'].items():
                folder_name = folder_url.split('/')[-2] if folder_url.endswith('/') else folder_url.split('/')[-1]
                print(f"  📁 {folder_name}: {len(files)} files")
            
            # Show sample files from each folder
            print("\n📁 Sample files by folder:")
            for folder_url, files in inventory_data['files_by_folder'].items():
                folder_name = folder_url.split('/')[-2] if folder_url.endswith('/') else folder_url.split('/')[-1]
                print(f"  📁 {folder_name} ({len(files)} files):")
                for filename in files[:3]:  # Show first 3 files
                    print(f"    - {filename}")
                if len(files) > 3:
                    print(f"    ... and {len(files) - 3} more files")
                print()
            
        elif args.operation == "upload_file":
            if not args.source_file or not args.destination_blob:
                parser.error("upload_file operation requires --source_file and --destination_blob")
            print(f"📤 Uploading {args.source_file}...")
            success = gcs_manager.upload_file(args.source_file, args.destination_blob)
            if success:
                print("✅ File uploaded successfully!")
            else:
                print("❌ File upload failed!")
                
        elif args.operation == "upload_folder":
            if not args.source_folder or not args.destination_folder:
                parser.error("upload_folder operation requires --source_folder and --destination_folder")
            print(f"📁 Uploading folder {args.source_folder}...")
            success = gcs_manager.upload_folder(args.source_folder, args.destination_folder)
            if success:
                print("✅ Folder uploaded successfully!")
            else:
                print("❌ Folder upload failed!")
                
        elif args.operation == "upload_new_files":
            if not args.source_folder or not args.destination_folder:
                parser.error("upload_new_files operation requires --source_folder and --destination_folder")
            print(f"🆕 Uploading new files from {args.source_folder}...")
            success = gcs_manager.upload_new_files(args.source_folder, args.destination_folder)
            if success:
                print("✅ New files uploaded successfully!")
            else:
                print("❌ New files upload failed!")
                
        elif args.operation == "get_videos":
            print("🎥 Getting available videos...")
            videos = gcs_manager.get_available_videos()
            print(f"✅ Found {len(videos)} videos")
            for video in videos[:5]:  # Show first 5
                print(f"  - {video['name']} ({video['size_mb']:.2f} MB)")
                
        elif args.operation == "get_audio":
            print("🎵 Getting available audio...")
            audio_files = gcs_manager.get_audio_options()
            print(f"✅ Found {len(audio_files)} audio files")
            for audio in audio_files[:5]:  # Show first 5
                print(f"  - {audio['name']} ({audio['size_mb']:.2f} MB)")
        
    except Exception as e:
        print(f"❌ Operation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
