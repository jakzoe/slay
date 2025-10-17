#!/bin/bash

get_tty_path() {

  local VENDOR_ID="$1"
  local PRODUCT_ID="$2"

  DEVICE_PATH=$(for device in /dev/ttyUSB*; do
    if udevadm info -a -n "$device" | grep -q "ATTRS{idVendor}==\"$VENDOR_ID\"" && udevadm info -a -n "$device" | grep -q "ATTRS{idProduct}==\"$PRODUCT_ID\""; then
      echo "$device"
    fi
  done)

  if [ -n "$DEVICE_PATH" ]; then
    echo "$DEVICE_PATH"
  else
    echo ""
  fi

}

run_docker_with_device() {
  local input="$1"
  local bus=$(echo "$input" | awk '{print $2}' | sed 's/://')
  local device=$(echo "$input" | awk '{print $4}' | sed 's/://')
  local spec_path="/dev/bus/usb/$bus/$device"
  arduino_path=$(get_tty_path "1a86" "7523")
  laser_path=$(get_tty_path "10c4" "ea60")

  if [ -n "$spec_path" ]; then
    spec_device="--device=$spec_path"
  else
    spec_device=""
  fi

  if [ -n "$arduino_path" ]; then
    arduino_device="--device=$arduino_path"
  else
    arduino_device=""
  fi

  if [ -n "$laser_path" ]; then
    laser_device="--device=$laser_path"
  else
    laser_device=""
  fi

  if [[ ! -c "$spec_path" ]]; then
    # echo "character device file does not exist"
    return 1
  fi

  docker run -v /home/user/slay/myproject/slay:/root/slay \
    -e "DISPLAY=$DISPLAY" \
    --mount type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix \
    --device=/dev/dri:/dev/dri \
    "$spec_device" "$arduino_device" "$laser_device" \
    laserdocker "$arduino_path" "$laser_path"

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
