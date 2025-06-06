#!/bin/bash

# Script to execute other scripts with parameters

# Change to the autopotter/scripts directory
cd "$(dirname "$0")" || { echo "Error: Failed to change directory to autopotter/scripts."; exit 1; }

# Confirm the current directory
current_dir=$(pwd)
echo "Running from directory: $current_dir"


# Check if at least one argument is provided (the script to execute)
if [ -z "$1" ]; then
  echo "Usage: $0 <script_to_execute> [parameters...]"
  exit 1
fi

script_to_execute="$1"
shift # Remove the script name from the arguments list

# Check if the script to execute exists
if [ ! -f "$script_to_execute" ]; then
  echo "Error: Script '$script_to_execute' not found."
  exit 1
fi

# Execute the script with bash, even if it's not marked as executable
bash "./$script_to_execute" "$@"

# Check the exit status of the executed script (optional)
exit_status=$?
if [ "$exit_status" -ne 0 ]; then
  echo "Error: Script '$script_to_execute' exited with status $exit_status."
fi

exit $exit_status