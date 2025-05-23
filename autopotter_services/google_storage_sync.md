# pip3 install gsutil #### no longer active!!!


curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-arm.tar.gz
tar -xf google-cloud-cli-linux-arm.tar.gz
./google-cloud-sdk/install.sh
./google-cloud-sdk/bin/gcloud init
./google-cloud-sdk/bin/gcloud auth login

# Example gsutil Command for Syncing a Local Folder: 
# Code

# gsutil rsync -d -r /path/to/local/folder gs://your-bucket-name/destination/folder
# Explanation of the command:
# -d: Handles directories recursively.
# -r: Recursively syncs subdirectories within the folder.
# /path/to/local/folder: The path to the local folder you want to synchronize.
# gs://your-bucket-name/destination/folder: The URI of the bucket and the destination folder. 

# --dry-run
gcloud storage rsync --dry-run --recursive /home/bayer3d/printer_data/timelapse gs://autopot1-printdump/video_uploads

# Copy the service file to the systemd directory
sudo cp gcloud_rsync.service /etc/systemd/system/

# Copy the timer file to the systemd directory
sudo cp gcloud_rsync.timer /etc/systemd/system/

# Reload the systemd daemon to recognize the new files
sudo systemctl daemon-reload

# Start the timer immediately
sudo systemctl start gcloud_rsync.timer

# Enable the timer to start on boot
sudo systemctl enable gcloud_rsync.timer