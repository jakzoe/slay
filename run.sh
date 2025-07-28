#!/bin/bash

get_tty_path() {
  local VENDOR_ID="$1"
  local PRODUCT_ID="$2"
  local SERIAL_ID="$3"

  DEVICE_PATH=$(for device in /dev/ttyUSB*; do
    if udevadm info -a -n "$device" | grep -q "ATTRS{idVendor}==\"$VENDOR_ID\"" &&
       udevadm info -a -n "$device" | grep -q "ATTRS{idProduct}==\"$PRODUCT_ID\""; then

      if [ -n "$SERIAL_ID" ]; then
        if udevadm info -a -n "$device" | grep -q "ATTRS{serial}==\"$SERIAL_ID\""; then
          echo "$device"
        fi
      else
        echo "$device"
      fi
    fi
  done)

  if [ -n "$DEVICE_PATH" ]; then
    echo "$DEVICE_PATH"
  else
    echo ""
  fi
}

get_usb_spec_path_by_ids() {
  local input="$1"
  local bus=$(echo "$input" | awk '{print $2}' | sed 's/://')
  local device=$(echo "$input" | awk '{print $4}' | sed 's/://')
  echo "/dev/bus/usb/$bus/$device"
}

get_usb_path_by_serial() {
  local serial_id="$1"
  for dev in /sys/bus/usb/devices/*; do
    if [ -f "$dev/serial" ]; then
      local current_serial
      current_serial=$(cat "$dev/serial")
      if [ "$current_serial" == "$serial_id" ]; then
        local busnum=$(cat "$dev/busnum")
        local devnum=$(cat "$dev/devnum")
        printf "%03d/%03d\n" "$busnum" "$devnum"
        return 0
      fi
    fi
  done
  return 1
}

usb_to_video() {
    local vendor="$1"
    local product="$2"
    for dev in /dev/video*; do
        if udevadm info --query=property --name="$dev" |
           grep -q "ID_VENDOR_ID=${vendor}" &&
           udevadm info --query=property --name="$dev" |
           grep -q "ID_MODEL_ID=${product}"; then
            echo "$dev"
            return 0
        fi
    done
    echo "No video device found for $vendor:$product" >&2
    return 1
}

run_docker_with_device() {
  local spec_path=$(get_usb_spec_path_by_ids "$1")
  # serial_path=$(get_tty_path "1a86" "7523") # Arduino (not used anymore)
  serial_path=$(get_tty_path "0403" "6001" "A5069RR4") # FT232 Serial
  serial_path_usb=$(get_usb_path_by_serial "A5069RR4") # FT232 Serial USB path
  cam_path=$(usb_to_video 0c45 62c0)

  nkt_path=$(get_tty_path "10c4" "ea60")
  # the LTB uses an FT232 too, it seems, thus having the same IDs, Thus checking for iSerial too
  # (lsusb -v -d 0403:6001 | grep iSerial)
  ltb_path=$(get_tty_path "0403" "6001" "FTDD2M08")
  ltb_path_usb=$(get_usb_path_by_serial "FTDD2M08")

   local devices=""

  if [ -n "$spec_path" ]; then
    devices+="--device=$spec_path "
  else
    spec_path="none"
  fi

  if [ -n "$serial_path" ]; then
    devices+="--device=$serial_path "
  else
    serial_path="none"
  fi

  if [ -n "$nkt_path" ]; then
    devices+="--device=$nkt_path "
  else
    nkt_path="none"
  fi

  if [ -n "$ltb_path" ]; then
    devices+="--device=$ltb_path "
  else
    ltb_path="none"
  fi

  if [ -n "$cam_path" ]; then
    devices+="--device=$cam_path "
  else
    cam_path="none"
  fi

  if [[ ! -c "$spec_path" ]]; then
    echo "Could not find the spectrometer. Exiiting."
    return 1
  fi

  echo "Using serial: $serial_path, also at $serial_path_usb"
  echo "Using NKT: $nkt_path"
  echo "Using LTB: $ltb_path"
  echo "Using spectrometer: $spec_path"
  echo "Using camera: $cam_path"
  echo

  usbreset $serial_path_usb

  dev_name=$(basename "$serial_path")

  echo 1 | sudo tee /sys/bus/usb-serial/devices/"$dev_name"/latency_timer
  sleep 0.5

  # ESP32
  usbreset "303a:1001"
  usbreset $ltb_path_usb

  # the port is used to attach the debugger
  # --rm is used as the container is unusable as soon as it stops, as the devices have to be added again.
  # Simply restarting would not work therefore.
  docker run -v /home/user/slay/myproject/slay:/root/slay \
    -e "DISPLAY=$DISPLAY" \
    --mount type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix \
    --device=/dev/dri:/dev/dri \
    --rm \
    -p 5678:5678 \
    $devices \
    "laserdocker:$DOCKER_MODE" "$serial_path" "$nkt_path" "$ltb_path" "$cam_path"
    
  return $?
}

shutdown_docker_containers() {
  echo "Shutting down any running Docker containers..."

  docker ps -q --filter ancestor=laserdocker:release | xargs -r docker stop
  docker ps -q --filter ancestor=laserdocker:debug | xargs -r docker stop
}

cleanup() {
  echo
  echo "Keyboard interrupt detected."
  shutdown_docker_containers
  exit 1
}

trap cleanup INT


DOCKER_MODE="$1"
if [ "$DOCKER_MODE" != "release" ] && [ "$DOCKER_MODE" != "debug" ]; then
  echo "Usage: $0 [release|debug]"
  exit 1
fi


lsmod | grep -q uvcvideo || sudo modprobe uvcvideo

# in my case, to prevent the PC from shutting down after a certain period of inactivity
pkill hypridle
# should there be any other instances that did not terminate properly
shutdown_docker_containers
# IDs of the spectrometer and the IDs of the device that is created after init of the spectrometer
run_docker_with_device "$(lsusb  -d 04b4:8613)"
run_docker_with_device "$(lsusb  -d 0bd7:a012)"

# Arduino. Try this, and when it fails, do it without adding it (so that I can select whether the Arduino should stil be availible to the Arduino IDE or not)
# probably need some udev hooks in Dockerfile as well then.
# As long as I am root in the Dockerfile/the devices are 666 anyway (nouser/nogroup problem), this does not matter anyway though, does not make a difference.
# run_docker_with_device "$(lsusb  -d 1a86:7523)"
