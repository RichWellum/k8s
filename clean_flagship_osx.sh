#!/bin/bash
# Installs flagship

# set -x

sudo -v

# Delete old version
echo Remove old flagship
cd
brew uninstall --force gnu-sed
brew reinstall gnu-sed --with-default-names
flagship -s
flagship -r
sudo rm -rf /opt/flagship
rm -rf ~/.flagship
rm -rf ~/flagship

# Clone k8s and flagship - k8s because has some k8s cleanup and osh that can
# run on top of flagship
echo Clone repos - passwords may be needed
# git clone https://github.com/RichWellum/k8s.git
git clone https://github.com/v1k0d3n/flagship.git ${HOME}/flagship \
    && sudo mv ${HOME}/flagship /opt/ && cd /opt/flagship

flagship -i
