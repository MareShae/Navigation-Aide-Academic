#!/usr/bin/bash

# Start script w elevated privileges
if [ "$EUID" -ne 0 ]; then
	echo "Please run using \`sudo\` as a prefix"
	exit 2
fi

# Stop the service
sudo systemctl stop navi.service

# Remove the service file
PATHTOSERVICE="/lib/systemd/system/navi.service"
sudo rm -rf $PATHTOSERVICE

# Reload the service list
sudo systemctl daemon-reload

