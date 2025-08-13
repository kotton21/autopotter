import os
import argparse
import random
from google.cloud import storage
from datetime import datetime, timezone

class GCSClient:
    def __init__(self, api_key_path):
        self.client = storage.Client.from_service_account_json(api_key_path)

    def list_files(self, bucket_name, prefix=None):
        print(f"Listing files in {bucket_name}/{prefix}...")
        bucket = self.client.bucket(bucket_name)
        if prefix != None: 
            blobs = bucket.list_blobs(prefix=prefix)
        else: 
            blobs = bucket.list_blobs()
        file_list = [blob.name for blob in blobs]
        return file_list

    def upload_file(self, bucket_name, source_file_path, destination_blob_name):
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_path)
        print(f"Uploaded {source_file_path} to {bucket_name}/{destination_blob_name}")

    def upload_folder(self, bucket_name, source_folder, destination_folder_prefix=""):
        for root, _, files in os.walk(source_folder):
            for file in files:
                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, source_folder)
                destination_blob_name = os.path.join(destination_folder_prefix, relative_path).replace("\\", "/")
                self.upload_file(bucket_name, local_file_path, destination_blob_name)
        print(f"Uploaded folder {source_folder} to {bucket_name}/{destination_folder_prefix}")

    def get_most_recent_file_creation_time(self, bucket_name, prefix=None):
        print(f"Getting most recent file creation time in {bucket_name}/{prefix}...")
        bucket = self.client.bucket(bucket_name)
        if prefix:
            blobs = bucket.list_blobs(prefix=prefix)
        else:
            blobs = bucket.list_blobs()
        
        # Filter out folder blobs
        file_blobs = [blob for blob in blobs if not blob.name.endswith('/')]
        if not file_blobs:
            print("No files found.")
            return None
        # print([blob.name for blob in file_blobs])
        most_recent_blob = max(file_blobs, key=lambda blob: blob.time_created)
        print(f"The most recent file is: {most_recent_blob.name}")
        return most_recent_blob.time_created

    def upload_new_files(self, bucket_name, source_folder, destination_folder_prefix=""):
        most_recent_creation_time = self.get_most_recent_file_creation_time(bucket_name, destination_folder_prefix)
        print(f"Uploaded new files from {source_folder} to {bucket_name}/{destination_folder_prefix}")
        for root, _, files in os.walk(source_folder):
            for file in files:
                local_file_path = os.path.join(root, file)
                print("   Uploading File: ", local_file_path)
                file_time = datetime.fromtimestamp(os.path.getmtime(local_file_path)).astimezone(timezone.utc)
                print("   File Time: ", file_time, "\n   Most Recent Time: ", most_recent_creation_time)
                if most_recent_creation_time==None or file_time > most_recent_creation_time:
                    relative_path = os.path.relpath(local_file_path, source_folder)
                    destination_blob_name = os.path.join(destination_folder_prefix, relative_path).replace("\\", "/")
                    self.upload_file(bucket_name, local_file_path, destination_blob_name)
                    print("Done.")

    def get_available_videos(self, bucket_name="autopot1-printdump"):
        """Get list of available video files from video_uploads folder"""
        all_files = self.list_files(bucket_name, "video_uploads/")
        
        # Filter for video files only
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
        video_files = []
        
        for file_path in all_files:
            if any(file_path.lower().endswith(ext) for ext in video_extensions):
                # Get blob metadata for additional info
                blob = self.client.bucket(bucket_name).blob(file_path)
                
                # Reload blob to get full metadata
                blob.reload()
                
                # Handle None values for time fields
                created_time = blob.time_created if blob.time_created else blob.updated
                updated_time = blob.updated if blob.updated else created_time
                
                video_files.append({
                    'name': file_path,
                    'size': blob.size,
                    'created': created_time,
                    'updated': updated_time,
                    'public_url': f"https://storage.googleapis.com/{bucket_name}/{file_path}"
                })
        
        # Sort by creation time (newest first), filtering out None values
        video_files = [v for v in video_files if v['created'] is not None]
        video_files.sort(key=lambda x: x['created'], reverse=True)
        return video_files

    def select_next_video(self, bucket_name, uploaded_videos, log_file=None):
        """Select the next video to process based on upload history"""
        available_videos = self.get_available_videos(bucket_name)
        
        # Filter out already uploaded videos
        uploaded_video_names = [item["video"] for item in uploaded_videos]
        new_videos = [v for v in available_videos if v['name'] not in uploaded_video_names]
        
        if not new_videos:
            return None
        
        # Select the most recent new video
        selected_video = new_videos[0]
        
        # Optional: Check for minimum video quality/size
        if selected_video['size'] < 1024 * 1024:  # Less than 1MB
            if log_file:
                print(f"Warning: Selected video {selected_video['name']} is very small ({selected_video['size']} bytes)")
        
        return selected_video

    def get_audio_options(self, bucket_name="autopot1-printdump"):
        """Get list of available audio files from music_uploads folder"""
        all_files = self.list_files(bucket_name, "music_uploads/")
        
        # Filter for audio files only
        audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac']
        audio_files = []
        
        for file_path in all_files:
            if any(file_path.lower().endswith(ext) for ext in audio_extensions):
                blob = self.client.bucket(bucket_name).blob(file_path)
                
                # Reload blob to get full metadata
                blob.reload()
                
                audio_files.append({
                    'name': file_path,
                    'size': blob.size,
                    'created': blob.time_created,
                    'public_url': f"https://storage.googleapis.com/{bucket_name}/{file_path}"
                })
        
        return audio_files

    def select_random_audio(self, audio_options, exclude_recent=None):
        """Select a random audio file, optionally excluding recently used ones"""
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Cloud Storage operations")
    parser.add_argument("operation", choices=["list", "upload_file", "upload_folder", "get_most_recent_file_creation_time", "upload_new_files"], help="Operation to perform")
    parser.add_argument("--api_key_path", type=str, default=os.path.expanduser("~/Downloads/autopot-cloud-6cb17ee04664.json"), help="Path to the API key JSON file")
    parser.add_argument("--bucket_name", type=str, default="autopot1-printdump", help="Name of the GCS bucket")
    parser.add_argument("--source_file", type=str, help="Path to the source file for upload_file operation")
    parser.add_argument("--destination_blob", type=str, help="Destination blob name for upload_file operation")
    parser.add_argument("--source_folder", type=str, help="Path to the source folder for upload_folder operation")
    parser.add_argument("--destination_folder", type=str, default=None, help="Destination folder prefix for upload_folder operation")

    args = parser.parse_args()

    gcs_client = GCSClient(args.api_key_path)

    if args.operation == "list":
        print("Listing files...")
        # if not args.destination_folder:
        #     parser.error("list_files operation requires --destination_folder")
        file_list = gcs_client.list_files(args.bucket_name, args.destination_folder)
        print(f"Files in {args.bucket_name}/{args.destination_folder}:")
        for file in file_list:
            print(f"- {file}")
    elif args.operation == "upload_file":
        print("Uploading file...")
        if not args.source_file or not args.destination_blob:
            parser.error("upload_file operation requires --source_file and --destination_blob")
        gcs_client.upload_file(args.bucket_name, args.source_file, args.destination_blob)
    elif args.operation == "upload_folder":
        print("Uploading folder...")
        if not args.source_folder or not args.destination_folder:
            parser.error("upload_folder operation requires --source_folder and --destination_folder")
        gcs_client.upload_folder(args.bucket_name, args.source_folder, args.destination_folder)
    elif args.operation == "get_most_recent_file_creation_time":
        print("Getting most recent file creation time...")
        creation_time = gcs_client.get_most_recent_file_creation_time(args.bucket_name, args.destination_folder)
        print(f"The most recent file was created at: {creation_time}")
    elif args.operation == "upload_new_files":
        print("Uploading new files...")
        if not args.source_folder or not args.destination_folder:
            parser.error("upload_new_files operation requires --source_folder and --destination_folder")
        gcs_client.upload_new_files(args.bucket_name, args.source_folder, args.destination_folder)