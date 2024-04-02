#!/bin/bash

#sudo apt install libssl-dev openssl wget build-essential zlib1g-dev libffi-dev libusb-1.0-0-dev usbutils -y
sudo pacman -S --needed --noconfirm base-devel git wget libusb usbutils

cd /usr/src
sudo wget https://www.python.org/ftp/python/3.10.9/Python-3.10.9.tgz
sudo tar zxvf Python-3.10.9.tgz
cd Python-3.10.9
sudo ./configure --enable-optimizations
#make -j2
sudo make install -j4

# PyGObject as an alternative to the larger matplotlib backend tkinter:
# sudo pacman -S --needed --noconfirm tk
sudo -u archlinux /usr/local/bin/pip3 install pyusb pyserial numpy matplotlib PyGObject