#!/usr/bin/bash

# https://askubuntu.com/questions/252734/apt-get-mass-install-packages-from-a-file
# https://linuxsimply.com/linux-basics/package-management/package-installation/install-rpm-from-file/

# The $(something) construction runs the something command, inserting its output in the command line.
# The grep command will exclude any line beginning with a #, optionally allowing for whitespace before it.
# Then the tr command replaces newlines with spaces.

# Install
path=~/NaviAide/.venv
python3 -m venv $path
# Install apt packages
$(grep -vE "^\s*#" ./apt_packages.txt | sed -e 's/#.*//'  | tr "\n" " ") | xargs -r sudo apt -y install
# Install python packages
$(grep -vE "^\s*#" ./pyt_packages.txt | sed -e 's/#.*//'  | tr "\n" " ") | xargs -r $path/bin/pip3 -y install
