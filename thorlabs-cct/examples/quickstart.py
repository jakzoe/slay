"""
Minimal usage example for the thorlabs_cct package.

Compare this to CctGetSpectrum.py (the vendor's raw pythonnet/clr example) -
same workflow, no manual .NET runtime setup or *Async(...).Result calls.

Run with the virtual device (no real hardware needed):
    .venv/bin/python examples/quickstart.py
"""
import sys
from csv import writer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from thorlabs_cct import SpectrometerManager, SpectrometerError


def main():
    with SpectrometerManager(use_virtual=True) as manager:
        device_ids = manager.discover()
        if not device_ids:
            print("No spectrometers found.")
            return
        print("Found spectrometers:", device_ids)

        with manager.connect(device_ids[0]) as spectrometer:
            print("Connected to:", spectrometer.device_id)

            spectrometer.set_exposure_ms(8.3)
            spectrometer.set_hardware_average(5)
            print(f"Exposure: {spectrometer.exposure_ms} ms, averaging: {spectrometer.hardware_average} frames")

            spectrometer.set_shutter(False)
            spectrometer.update_dark_spectrum()
            spectrometer.set_shutter(True)
            print("Acquired dark spectrum")

            spectrum = spectrometer.acquire()
            print(f"Acquired spectrum: {len(spectrum.wavelength_nm)} points, "
                  f"exposure {spectrum.exposure_ms} ms, averaged {spectrum.hardware_average} frames")

            filename = "spectrum_data.csv"
            with open(filename, mode="w", newline="") as csv_file:
                csv_writer = writer(csv_file)
                csv_writer.writerow(["Wavelength (nm)", "Intensity"])
                csv_writer.writerows(zip(spectrum.wavelength_nm, spectrum.intensity))
            print(f"Spectrum data saved into file '{filename}'")


if __name__ == "__main__":
    try:
        main()
    except SpectrometerError as e:
        print(f"An error occurred: {e}")
