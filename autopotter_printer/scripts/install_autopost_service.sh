#!/bin/bash

# Define paths
SERVICE_FILE="/home/bayer3d/autopotter/autopotter_services/autopost.service"
TIMER_FILE="/home/bayer3d/autopotter/autopotter_services/autopost.timer"
SYSTEMD_DIR="/etc/systemd/system"

# Copy service and timer files to systemd directory
echo "Copying autopost.service to $SYSTEMD_DIR..."
sudo cp "$SERVICE_FILE" "$SYSTEMD_DIR"

echo "Copying autopost.timer to $SYSTEMD_DIR..."
sudo cp "$TIMER_FILE" "$SYSTEMD_DIR"

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Restart and enable the autopost timer
echo "Restarting autopost.timer..."
sudo systemctl restart autopost.timer

echo "Enabling autopost.timer to start on boot..."
sudo systemctl enable autopost.timer

echo "Autopost service and timer installed and started successfully!"