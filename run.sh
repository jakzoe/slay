#!/bin/bash

run_docker_with_device() {
  local input="$1"
  local bus=$(echo "$input" | awk '{print $2}' | sed 's/://')
  local device=$(echo "$input" | awk '{print $4}' | sed 's/://')
  local spec_path="/dev/bus/usb/$bus/$device"

  if [[ ! -c "$spec_path" ]]; then
    # echo "character device file does not exist"
    return 1
  fi

  docker run -v /home/user/slay/myproject:/root/slay \
    -e "DISPLAY=$DISPLAY" \
    --mount type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix \
    --device=/dev/dri:/dev/dri \
    --device="$spec_path" \
    laserdocker

 #--device="/dev/ttyUSB0" \
  return $?
}

# to figure out USB0 vs USB1: udevadm info -n /dev/ttyUSB0 or udevadm info -q property --property=ID_VENDOR_ID --value -n /dev/ttyUSB0 , productid is ID_MODEL_ID


# IDs of the spectrometer and the IDs of the device that is created after init of the spectrometer
run_docker_with_device "$(lsusb  -d 04b4:8613)"
run_docker_with_device "$(lsusb  -d 0bd7:a012)"

# Arduino. Try this, and when it fails, do it without adding it (so that I can select whether the Arduino should stil be availible to the Arduino IDE or not)
# probably need some udev hooks in Dockerfile as well then.
# As long as I am root in the Dockerfile/the devices are 666 anyway (nouser/nogroup problem), this does not matter anyway though, does not make a difference.
# run_docker_with_device "$(lsusb  -d 1a86:7523)"
