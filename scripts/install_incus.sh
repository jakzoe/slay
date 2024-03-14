USER_NAME=$(whoami)

# setting up Incus (Arch Linux)
sudo pacman -S incus
sudo systemctl enable incus.socket
# start all containers unprivileged by default
sudo usermod -v 1000000-1000999999 -w 1000000-1000999999 $USER_NAME
sudo incus admin init
# allow $USER_NAME to access incus when utilizing e.g. sudo/doas
sudo usermod -aG incus $USER_NAME

# grant all containers full network access
sudo ufw allow in on incusbr0
sudo ufw route allow in on incusbr0
sudo ufw route allow out on incusbr0

# download an image of a container (Ubuntu) from incus image list images: is from https://images.linuxcontainers.org/
incus launch images:ubuntu/23.10/cloud ubuntu
incus exec ubuntu -- apt-get update
incus exec ubuntu -- apt-get upgrade
incus snapshot create ubuntu clean

# add project-dir as bind-mount
incus config device add ubuntu slaydir disk source=/myproject path=/home/ubuntu/slay
#source has to be 
sudo chmod -R 777 /myproject
#see https://linuxcontainers.org/incus/docs/main/faq/ to see methods that do grad the permission so that pemrissions of 777 are not needed.

# add the spectrometer
incus config device add ubuntu spectro usb vendorid=04b4 productid=8613

# setup python 3.10 (required by the Stellarnet-Libs)
cd /usr/src
sudo apt install libssl-dev openssl wget build-essential zlib1g-dev -y
sudo apt-get install libffi-dev
sudo wget https://www.python.org/ftp/python/3.10.9/Python-3.10.9.tgz
sudo tar zxvf Python-3.10.9.tgz
cd Python-3.10.9
sudo ./configure --enable-optimizations
#make -j2
sudo make install -j4\
#cd /usr/local/bin/
sudo apt install libusb-1.0-0-dev
/usr/local/bin/pip3 install pyusb pyserial numpy matplotlib
/usr/local/bin/python3 /home/ubuntu/slay/stellarnet/stellarnet_demo.py
sudo apt-get install usbutils


# more fine grained: see wiki
':
# allow the guest to get an IP from the Incus host
sudo ufw allow in on incusbr0 to any port 67 proto udp
sudo ufw allow in on incusbr0 to any port 547 proto udp

# allow the guest to resolve host names from the Incus host
sudo ufw allow in on incusbr0 to any port 53

# allow the guest to have access to outbound connections
CIDR4="$(incus network get incusbr0 ipv4.address | sed 's|\.[0-9]\+/|.0/|')"
CIDR6="$(incus network get incusbr0 ipv6.address | sed 's|:[0-9]\+/|:/|')"
sudo ufw route allow in on incusbr0 from "${CIDR4}"
sudo ufw route allow in on incusbr0 from "${CIDR6}"
'

exit

# bind-mount
# the path is required for file systems, but not for block devices.
incus config device add <instance_name> <device_name> disk source=<path_on_host> [path=<path_in_instance>]


# devices are mainly identified using a pair of hexadecimal numbers, like 04b3:3108.
#- The 4 first hexadecimal digits are the Vendor ID (04b3 = IBM).
#- The 4 last hexadecimal digits are the Device ID (3108 = ThinkPad 800dpi Optical Travel Mouse).
# more information: 
lsusb
usb-devices


sudo pacman -S virt-viewer
incus launch images:ubuntu/22.04/desktop vmubuntu --vm -c security.secureboot=false -c limits.cpu=4 -c limits.memory=8GiB --console=vga
incus launch images:archlinux/desktop-gnome archlinux --vm -c security.secureboot=false -c limits.cpu=4 -c limits.memory=8GiB --console=vga

