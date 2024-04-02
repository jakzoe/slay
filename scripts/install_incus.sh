#!/bin/bash

USER_NAME=$(whoami)

# disable sudo timeout
while true; do sudo -v; sleep 60; done &

sudo pacman -S --needed --noconfirm git wget

# to be able to add USB devices when using a VM:
sudo pacman -S --needed --noconfirm qemu-hw-usb-host
# to be able to attach to VGA output of a VM
sudo pacman -S --needed --noconfirm virt-viewer

sudo pacman -S --needed --noconfirm incus
sudo systemctl enable incus.socket
sudo systemctl enable incus-user.socket

# start all containers unprivileged by default
echo "root:1000000:1000000000" | sudo tee -a /etc/subuid /etc/subgid
echo "$USER_NAME:1000000:1000000000" | sudo tee -a /etc/subuid /etc/subgid

incus admin init --minimal
# allow $USER_NAME to access incus when utilizing e.g. sudo or doas
sudo usermod -aG incus $USER_NAME
# The newgrp step is needed in any terminal that interacts with Incus until you restart your user session.
newgrp incus

# sudo usermod -aG incus-admin $USER_NAME
# newgrp incus-admin

# grant all containers full network access (instances started by root)
sudo ufw allow in on incusbr0
sudo ufw route allow in on incusbr0
sudo ufw route allow out on incusbr0

# (instances started by user with uid 1000)
sudo ufw allow in on incusbr-1000
sudo ufw route allow in on incusbr-1000
sudo ufw route allow out on incusbr-1000
# for more fine grained options: see wiki

# kill the sudo -v job
jobs
kill %1