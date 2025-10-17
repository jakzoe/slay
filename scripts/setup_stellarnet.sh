#!/bin/bash
# setting up Incus (Arch Linux)
# bash setup_incus.sh

CONTAINER_NAME="arch-vm-stellarnet"
# has to be absolute
INSTALL_PATH="/home/user/slay/myproject"

DRIVER_URL=""
# one is only allowed to download and use the driver after signing a Software License Agreement
source secrets.txt

mkdir -p $INSTALL_PATH/stellarnet/stellarnet_driverLibs

# download the driver
wget "$DRIVER_URL/stellarnet_driverLibs/stellarnet_driver3.cpython-310-x86_64-linux-gnu.so" -O  $INSTALL_PATH/stellarnet/stellarnet_driverLibs/stellarnet_driver3.cpython-310-x86_64-linux-gnu.so

# disable sudo timeout
while true; do sudo -v; sleep 60; done &

# download an image of a container (Ubuntu) from https://images.linuxcontainers.org/
# (incus image list images:)

#sudo incus launch images:ubuntu/23.10/cloud $CONTAINER_NAME
#sudo incus launch images:ubuntu/22.04/desktop $CONTAINER_NAME --vm -c security.secureboot=false -c limits.cpu=4 -c limits.memory=8GiB --console=vga
sudo incus launch images:archlinux/desktop-gnome $CONTAINER_NAME --vm -c security.secureboot=false -c limits.cpu=4 -c limits.memory=8GiB --console=vga
sudo incus exec $CONTAINER_NAME -- bash /home/archlinux/firstboot.sh

#sudo incus exec $CONTAINER_NAME -- apt-get update
#sudo incus exec $CONTAINER_NAME -- apt-get upgrade
sudo incus exec $CONTAINER_NAME -- pacman -Syu --noconfirm
sudo incus snapshot create $CONTAINER_NAME clean

 
cd $INSTALL_PATH || exit
git clone https://github.com/jakzoe/slay
git clone https://github.com/jakzoe/slay

# add project-dir as bind-mount
# when using a virtual machine, fs-options such as noexec on the source do not have any effect
# however, when using a container, they still apply (due to the same kernel)
sudo incus config device add $CONTAINER_NAME slay-dir disk source=$INSTALL_PATH/slay path=/home/slay shift=true
# the source has to be world-readable when idmapped (shift=true) is not supported
#sudo chmod -R 777 $INSTALL_PATH/slay


## add devices

# devices are mainly identified using a pair of hexadecimal numbers, like 04b3:3108.
#- The 4 first hexadecimal digits are the Vendor ID (04b3 = IBM).
#- The 4 last hexadecimal digits are the Device ID (3108 = ThinkPad 800dpi Optical Travel Mouse).
# more information: 
lsusb
usb-devices

# add the spectrometer
sudo incus config device add $CONTAINER_NAME spectro usb vendorid=04b4 productid=8613
# allow read/write-access
sudo incus exec $CONTAINER_NAME --  bash -c "echo 'SUBSYSTEMS==\"usb\", ATTRS{idVendor}==\"04b4\", ATTRS{idProduct}==\"8613\" GROUP=\"uucp\", MODE=\"0666\"' > /etc/udev/rules.d/50-spectro.rules"

# apparently, the spectrometer's library changes the device to "0bd7:a012 Andrew Pargeter & Associates USB2EPP"
sudo incus config device add $CONTAINER_NAME changed_spectro usb vendorid=0bd7 productid=a012
# allow read/write-access
sudo incus exec $CONTAINER_NAME --  bash -c "echo 'SUBSYSTEMS==\"usb\", ATTRS{idVendor}==\"0bd7\", ATTRS{idProduct}==\"a012\" GROUP=\"uucp\", MODE=\"0666\"' >> /etc/udev/rules.d/50-spectro.rules"

#sudo udevadm control --reload-rules && sudo udevadm trigger

# NKT Laser:
# ID 10c4:ea60 Silicon Labs CP210x UART Bridge
sudo incus config device add $CONTAINER_NAME nkt_laser usb vendorid=10c4 productid=ea60

# Arduino
# ID 1a86:7523 QinHeng Electronics CH340 serial converter
sudo incus config device add $CONTAINER_NAME arduino usb vendorid=1a86 productid=7523
# allow access to the Arduino-tty-USB device for regular users
sudo incus exec $CONTAINER_NAME -- sudo -u archlinux bash -c 'sudo usermod -aG uucp $(whoami)'
#sudo incus exec $CONTAINER_NAME -- newgrp uucp

: "
# if there is not enough storage:
sudo incus config device override $CONTAINER_NAME root size=60GB
sudo incus config device set $CONTAINER_NAME root size 60GB
# inside the container:
# fdisk /dev/sda
# d,n,w : delete the partition, create a new one (with the full size) and write the changes to the partition-table 
"
# setup Python 3.10 (required by the Stellarnet-Lib, since there is no .so library for Python 3.11 availible yet)
sudo incus exec $CONTAINER_NAME -- bash /home/slay/make_python3_10_9.sh

# start the VM, unset the DISPLAY variable (force the use of Wayland instead of Xorg, for security)
sudo -EH env DISPLAY= incus restart $CONTAINER_NAME --console=vga

#/usr/local/bin/python3 /home/slay/laser_messungen.py
sudo incus exec $CONTAINER_NAME -- /usr/local/bin/python3 /home/slay/laser_messungen.py
