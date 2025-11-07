# Autopost Systemd Service Setup

This guide explains how to set up and manage the `autopost.service` systemd service on a Raspberry Pi.

## 1. Placing the Service File

1. Copy the `autopost.service` file to the systemd directory:
    ```bash
    sudo cp /path/to/autopost.service /etc/systemd/system/

2. If you are using a timer (e.g., autopost.timer), copy it as well:
    sudo cp /path/to/autopost.timer /etc/systemd/system/

3. Reload the systemd daemon to recognize the new service files:
    sudo systemctl daemon-reload

## 2. Managing the Service (if not using a timer)

Start the Service
To start the autopost.service immediately:

    sudo systemctl start autopost.service   

Stop the Service
To stop the autopost.service:

    sudo systemctl stop autopost.service

Restart the Service
To restart the autopost.service:

    sudo systemctl restart autopost.service

Enable the Service
To enable the service to start automatically on boot:

    sudo systemctl enable autopost.service

Disable the Service
To disable the service from starting on boot:

    sudo systemctl disable autopost.service

## 3. Managing the Timer (Optional)

If you are using a timer (autopost.timer) to run the service periodically:

Start the Timer
To start the timer:
    sudo systemctl start autopost.timer

systemctl
Stop the Timer
To stop the timer:
    sudo systemctl stop autopost.timer

Enable the Timer
To enable the timer to start automatically on boot:
    sudo systemctl enable autopost.timer

Disable the Timer
To disable the timer from starting on boot:
    sudo systemctl disable autopost.timer

Check Timer Status
To check the status of the timer:
    systemctl list-timers --all

## 4. Viewing Logs

To view the logs for the autopost.service, use the journalctl command:

    sudo journalctl -u autopost.service

If you specified a log file in the service file (e.g., /path/to/logs/autopost.log), you can also view the logs directly:
    
    cat /path/to/logs/autopost.log

## 5. Notes

Ensure that the paths in the autopost.service file (e.g., to the Python script, config file, and log file) are correct and accessible by the service.
If you make changes to the service or timer files, reload the systemd daemon:
Test the service manually before enabling it to ensure it works as expected.