#!/bin/bash

# Note that this cannot execute commands which require superuser privileges.

# Navigate to the autopotter directory
cd ~/autopotter || { echo "Directory ~/autopotter not found!"; exit 1; }

# Pull updates from the git repository
echo "Pulling updates from the git repository..."
git pull origin main || { echo "Failed to pull updates from the repository!"; exit 1; }


echo "Updates pulled successfully!"
