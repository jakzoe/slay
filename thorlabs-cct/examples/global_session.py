"""
Example: thorlabs_cct keeps one connected Spectrometer per process. Any
function that imports the module can reach it via cct.current() - no global
variable or connection bookkeeping needed in calling code.

Interactive use:
    .venv/bin/python -i examples/global_session.py
    >>> cct.current().set_exposure_ms(10)
    >>> spectrum = measure()
    >>> cct.disconnect()
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import thorlabs_cct as cct


def measure_dark() -> None:
    spec = cct.current()
    spec.set_shutter(False)
    spec.update_dark_spectrum()
    spec.set_shutter(True)


def measure() -> cct.Spectrum:
    return cct.current().acquire()


if __name__ == "__main__":
    cct.connect(use_virtual=False)
    try:
        cct.current().set_exposure_ms(8.3)
        cct.current().set_hardware_average(5)
        measure_dark()
        spectrum = measure()
        print(
            f"Acquired {len(spectrum.wavelength_nm)} points, exposure {spectrum.exposure_ms} ms"
        )
    finally:
        cct.disconnect()
