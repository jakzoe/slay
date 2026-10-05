![License](https://img.shields.io/badge/license-GPLv3-blue)
![Language](https://img.shields.io/badge/language-Python-blue)

## Overview

slay (Spectrometer + Laser = Amazing Yield) controls the hardware for a laser-induced fluorescence setup and plots the resulting data. It does two things: run a measurement first and turn the saved measurements into plots thereafter.

A measurement is described by a config (`MeasurementSettings`): this includes e.g. laser intensities, timings, spectrometer settings and how many repetitions the measurement should do. slay sends this to an ESP32-C3 SuperMini that triggers the diode lasers, talks to the NKT SuperK and LTB nitrogen laser directly over serial and reads the spectrometer(s) and camera during the run. The measurement data is saved as a zip-compressed NumPy array, while the corresponding measurement settings are saved as `.json`. `SpectrumPlot` then turns these into various plots such as heatmaps, gradients, time series, etc.

The ESP32 firmware lives in [`laser-control-firmware`](laser-control-firmware).

Right now, this only works for a combination of an NKT SuperK supercontinuum laser, two UV diode lasers, an LTB nitrogen laser, StellarNet/Thorlabs spectrometers and a USB camera, with the triggering being done by an ESP32. To use different hardware, it is necessary to swap out the device drivers (`slay/lasers.py`, `slay/stellarnet.py`, `slay/thorlabs.py`, `slay/camera.py`) and adapt the firmware. The settings/measurement/plotting code on top work regardless of the underling hardware though.

## Requirements

The project was developed and therefore tested on Linux, but should mostly work elsewhere using Docker. The only component that won't work without using Linux is [`run.sh`](run.sh), which automatically resolves the lab devices to their `/dev/...` paths by vendor/product ID so they can be directly passed to Docker. On another platform you'd have to write your own version of that or just hand in the paths yourself.

## Installation

Use it without Docker:

Clone it and add it to `PYTHONPATH`:

```shell
export PYTHONPATH="$PYTHONPATH:/path/to/slay"
```
Then, check `Dockerfile` for which dependencies need to be present.

Use it with Docker:
```shell
# without debugging
docker build -t laserdocker:release .
# with debugging
docker build -t laserdocker:debug --target debug .
```

and start it with [`run.sh`](run.sh) (or your own device-mapping command).

## Examples

See the [examples](examples) dir for a full measurement + plotting run.
