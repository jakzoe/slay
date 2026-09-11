import os
import sys

import numpy as np

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_CURRENT_DIR)

_DEFAULT_DIR = os.path.join(_PARENT_DIR, "thorlabs-cct")
_THORLABS_CCT_DIR = os.environ.get("THORLABS_CCT_DIR", _DEFAULT_DIR)


if _THORLABS_CCT_DIR not in sys.path:
    sys.path.insert(0, _THORLABS_CCT_DIR)

from thorlabs_cct import SpectrometerError, SpectrometerManager  # type: ignore


class ThorlabsSpectrometer:

    def __init__(self, index, USE_VIRTUAL=False):
        self._manager = SpectrometerManager(use_virtual=USE_VIRTUAL)
        try:
            device_ids = self._manager.discover()
            if not device_ids:
                raise SpectrometerError("No thorlabs spectrometer found.")
            self._spectrometer = self._manager.connect(device_ids[index])
        except Exception:
            self._manager.close()
            raise

        self._last_spectrum = None
        self._closed = False

    def configure(self, specto_settings):
        self._spectrometer.set_exposure_ms(specto_settings.INTTIME)
        self._check_applied_exposure(specto_settings.INTTIME)
        self._spectrometer.set_hardware_average(specto_settings.SCAN_AVG)
        self._spectrometer.set_gain_db(specto_settings.GAIN)
        self._spectrometer.use_amplitude_correction = (
            specto_settings.AMPLITUDE_CORRECTION
        )
        if specto_settings.DARK_SPECTRUM_CALIBRATION:
            self._update_dark_spectrum()

    def _check_applied_exposure(self, requested_ms):
        # die SDK-Doku empfiehlt, nach dem Setzen zu prüfen, ob die Exposure tatsächlich
        # übernommen wurde (SetManualExposureAsync kann True zurückgeben, obwohl die
        # Hardware den Wert intern geklemmt/gerundet hat)
        applied_ms = self._spectrometer.exposure_ms
        if abs(applied_ms - requested_ms) > 0.01:
            print(
                f"Thorlabs: angeforderte Exposure {requested_ms} ms wurde nicht genau übernommen, "
                f"tatsächlich gesetzt: {applied_ms} ms.",
                flush=True,
            )

    def _update_dark_spectrum(self):
        try:
            self._spectrometer.set_shutter(False)
            self._spectrometer.update_dark_spectrum()
            self._spectrometer.set_shutter(True)
        except SpectrometerError as e:
            print(
                f"Thorlabs: Dunkelspektrum konnte nicht aufgenommen werden: {e}",
                flush=True,
            )

    def _acquire(self):
        self._last_spectrum = self._spectrometer.acquire()
        if self._spectrometer.is_saturated:
            print(
                "Thorlabs: Sensor ist gesättigt (IsSaturated=True). Belichtungszeit oder Lichtmenge reduzieren.",
                flush=True,
            )
        return self._last_spectrum

    def get_wavelengths(self):
        # die Wellenlängenkalibrierung ändert sich nicht zwischen Messungen,
        # daher reicht die erste (ohnehin nötige) Messung dafür aus
        spectrum = self._last_spectrum or self._acquire()
        return np.array(spectrum.wavelength_nm)

    def measure(self):
        return np.array(self._acquire().intensity)

    def close(self):
        if self._closed:
            return
        self._spectrometer.close()
        self._manager.close()
        self._closed = True
