#!/usr/bin/bash

# Start script w elevated privileges
if [ "$EUID" -ne 0 ]; then
	echo "Please run using \`sudo\` as a prefix"
	exit 2
fi

PATHTOSERVICE="/lib/systemd/system/navi.service"

echo "Writing to $PATHTOSERVICE"
echo ""

# Write service entry to file [PATHTOSERVICE]
cat << writeend > $PATHTOSERVICE
[Unit]
Description=Navigation Aide

[Service]
Type=idle
ExecStart=/home/sass/NaviAide/PROJECT_MAIN.py

[Install]
WantedBy=multi-user.target
writeend

# Setting permissions for service
echo "Setting permissions for navi.service"
echo ""
sudo chmod 644 $PATHTOSERVICE

# List, enable and start the service
echo "Starting service"
echo ""
sudo systemctl daemon-reload
sudo systemctl enable navi.service
sudo systemctl start navi.service

# Show that the service is enabled
sudo systemctl status navi.service
