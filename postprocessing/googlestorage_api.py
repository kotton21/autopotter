import os
import argparse
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