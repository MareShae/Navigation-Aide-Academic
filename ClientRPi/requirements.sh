#!/usr/bin/bash

# https://askubuntu.com/questions/252734/apt-get-mass-install-packages-from-a-file
# https://linuxsimply.com/linux-basics/package-management/package-installation/install-rpm-from-file/

# The $(something) construction runs the something command, inserting its output in the command line.
# The grep command will exclude any line beginning with a #, optionally allowing for whitespace before it.
# Then the tr command replaces newlines with spaces.

# Install system packages
echo "[Installing System Packages]"
# required for sounddevice
sudo apt -y install portaudio19-dev
sudo apt update && sudo apt upgrade -y
echo ""


# New venv
echo "[Creating Py Virtual Environment]"
NAVI_VENV=./venv
if [ ! -d "$NAVI_VENV" ]; then
    echo "New py venv at $NAVI_VENV"
    python3.9 -m venv $NAVI_VENV
else
    echo "Skipping creation of virtual environment"
fi
echo ""


# Install python packages
echo "[Installing Python Packages]"
$NAVI_VENV/bin/pip3 install --upgrade pip
$NAVI_VENV/bin/pip3 install -r ./requirements.txt
$NAVI_VENV/bin/pip3 install numpy --upgrade
echo ""

echo "[Cleaning Up Installation]"
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get dist-upgrade -y
sudo apt autoremove -y
