"""Pythonic wrapper around a connected ICompactSpectrographDriver instance."""
import logging
from dataclasses import dataclass
from datetime import datetime
from time import sleep
from typing import Dict, List, Optional

from . import _runtime
from .exceptions import SpectrometerError

logger = logging.getLogger(__name__)

# Mechanical shutter travel time, per the vendor SDK documentation/examples.
_SHUTTER_SETTLE_S = 0.04

# Poll interval for acquire()'s wait loop; see the comment there for why we
# poll instead of blocking on Task.Result directly.
_ACQUIRE_POLL_S = 0.01


@dataclass(frozen=True)
class Spectrum:
    """A single spectrum snapshot (measurement, dark, background, or reference)."""

    wavelength_nm: List[float]
    intensity: List[float]
    exposure_ms: float
    hardware_average: int
    acquired: datetime
    amplitude_corrected: bool
    input_hw_triggered: bool
    tick: int


def _to_spectrum(raw) -> Spectrum:
    acquired = raw.Acquired
    return Spectrum(
        wavelength_nm=list(raw.Wavelength),
        intensity=list(raw.Intensity),
        exposure_ms=round(raw.SensorExposureMs, 2),
        hardware_average=int(raw.HardwareAverage),
        acquired=datetime(
            acquired.Year, acquired.Month, acquired.Day,
            acquired.Hour, acquired.Minute, acquired.Second,
            acquired.Millisecond * 1000,
        ),
        amplitude_corrected=bool(raw.AmplitudeCorrected),
        input_hw_triggered=bool(raw.InputHardwareTrigger),
        tick=int(raw.Tick),
    )


class Spectrometer:
    """
    Wraps a connected `ICompactSpectrographDriver` with Pythonic properties
    and methods instead of the raw *Async(...).Result .NET calling
    convention.

    Created via `SpectrometerManager.connect()` - not meant to be
    instantiated directly.
    """

    def __init__(self, driver):
        # Escape hatch: the raw .NET driver, for anything not wrapped below.
        self.raw = driver

    def __enter__(self) -> "Spectrometer":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        pass

    def _token(self, cancellation_token):
        return cancellation_token if cancellation_token is not None else _runtime.CancellationTokenSource().Token

    def _run(self, description: str, async_fn, *args):
        try:
            result = async_fn(*args).Result
        except Exception as exc:
            raise SpectrometerError(f"{description} failed: {exc}") from exc
        if not result:
            errors = "; ".join(self.latest_errors)
            raise SpectrometerError(f"{description} failed" + (f": {errors}" if errors else ""))
        return result

    # --- identity / state ---------------------------------------------------

    # device_id/is_open/is_offline are inherited from IManagedDevice rather
    # than declared on ICompactSpectrographDriver itself; pythonnet cannot
    # bind them on the real (non-virtual) driver class (see close() below).
    # They work against the SDK's virtual device but will raise
    # "'MethodObject' object is not callable" against real hardware.

    @property
    def device_id(self) -> str:
        return self.raw.DeviceId

    @property
    def electronics_id(self) -> str:
        return self.raw.ElectronicsId

    @property
    def firmware_version(self) -> str:
        return self.raw.FirmwareVersion

    @property
    def is_open(self) -> bool:
        return bool(self.raw.IsOpen)

    @property
    def is_offline(self) -> bool:
        return bool(self.raw.IsOffline)

    @property
    def ethernet_connected(self) -> bool:
        return bool(self.raw.EthernetConnected)

    @property
    def is_saturated(self) -> bool:
        return bool(self.raw.IsSaturated)

    @property
    def latest_errors(self) -> List[str]:
        return list(self.raw.LatestError)

    @property
    def resolution_adc_bits(self) -> int:
        return int(self.raw.ResolutionAdc)

    # --- acquisition settings ------------------------------------------------

    @property
    def exposure_ms(self) -> float:
        return round(self.raw.ManualExposure, 2)

    def set_exposure_ms(self, value: float, cancellation_token=None) -> None:
        self._run("Set exposure", self.raw.SetManualExposureAsync, value, self._token(cancellation_token))

    @property
    def gain_db(self) -> float:
        return round(self.raw.ManualGain, 2)

    def set_gain_db(self, value: float, cancellation_token=None) -> None:
        self._run("Set gain", self.raw.SetManualGainAsync, value, self._token(cancellation_token))

    @property
    def offset_counts(self) -> float:
        return round(self.raw.ManualOffset, 2)

    def set_offset_counts(self, value: float, cancellation_token=None) -> None:
        self._run("Set offset", self.raw.SetManualOffsetAsync, value, self._token(cancellation_token))

    @property
    def hardware_average(self) -> int:
        return int(self.raw.HwAverage)

    def set_hardware_average(self, frames: int, cancellation_token=None) -> None:
        self._run("Set hardware averaging", self.raw.SetHwAverageAsync, frames, self._token(cancellation_token))

    @property
    def client_limit_exposure_ms(self) -> float:
        return round(self.raw.ClientLimitExposure, 2)

    def set_client_limit_exposure_ms(self, value: float, cancellation_token=None) -> None:
        self._run("Set client exposure limit", self.raw.SetClientLimitExposureAsync, value, self._token(cancellation_token))

    @property
    def use_amplitude_correction(self) -> bool:
        return bool(self.raw.UseAmplitudeCorrection)

    @use_amplitude_correction.setter
    def use_amplitude_correction(self, value: bool) -> None:
        self.raw.UseAmplitudeCorrection = bool(value)

    # --- shutter / triggers ---------------------------------------------------

    @property
    def shutter_open(self) -> bool:
        return bool(self.raw.ShutterOpen)

    def set_shutter(self, open_position: bool, cancellation_token=None) -> None:
        self._run("Set shutter", self.raw.SetShutterAsync, open_position, self._token(cancellation_token))
        sleep(_SHUTTER_SETTLE_S)

    def set_input_hw_trigger(self, enabled: bool, ave_no_wait: bool = False,
                              slope_falling_edge: bool = False, cancellation_token=None) -> None:
        self._run(
            "Set input hardware trigger",
            self.raw.SetInputHwTriggerAsync,
            enabled, ave_no_wait, slope_falling_edge, self._token(cancellation_token),
        )

    @property
    def hw_trigger_in(self) -> bool:
        return bool(self.raw.HwTriggerIn)

    @property
    def hw_trigger_in_ave_no_wait(self) -> bool:
        return bool(self.raw.HwTriggerInAveNoWait)

    @property
    def hw_trigger_in_slope_falling(self) -> bool:
        return bool(self.raw.HwTriggerInSlope)

    def set_output_hw_trigger_delay_ms(self, delay_ms: float, cancellation_token=None) -> None:
        self._run(
            "Set output hardware trigger delay",
            self.raw.SetOutputHwTriggerDelayAsync,
            delay_ms, self._token(cancellation_token),
        )

    @property
    def hw_trigger_out_delay_ms(self) -> float:
        return round(self.raw.HwTriggerOutDelayMs, 2)

    # --- LED / temperature ------------------------------------------------------

    @property
    def led_on(self) -> bool:
        return bool(self.raw.LedIndicatorOn)

    def set_led(self, on: bool, cancellation_token=None) -> None:
        self._run("Set LED indicator", self.raw.SetLedIndicatorAsync, on, self._token(cancellation_token))

    @property
    def temperature_electronics_c(self) -> float:
        """Last-measured electronics temperature; call fetch_temperature_electronics_c() to refresh it."""
        return round(self.raw.TemperatureElectronics, 2)

    def fetch_temperature_electronics_c(self, cancellation_token=None) -> float:
        token = self._token(cancellation_token)
        try:
            return round(self.raw.FetchTemperatureElectronicsAsync(token).Result, 2)
        except Exception as exc:
            raise SpectrometerError(f"Fetch temperature failed: {exc}") from exc

    # --- spectra ------------------------------------------------------------------

    def acquire(self, cancellation_token=None) -> Spectrum:
        token = self._token(cancellation_token)
        try:
            task = self.raw.AcquireSingleSpectrumAsync(token)
            # pythonnet keeps holding the Python GIL for the whole duration of a
            # blocking .NET call (Task.Result included), since the wait happens
            # inside a native call the GIL-releasing device driver code never
            # runs. AcquireSingleSpectrumAsync blocks for ~exposure_ms doing
            # hardware I/O, so polling instead lets sleep() release the GIL
            # between checks - letting other Python threads (e.g. a second
            # spectrometer's measurement loop) run concurrently instead of being
            # starved for the entire exposure.
            while not task.IsCompleted:
                sleep(_ACQUIRE_POLL_S)
            raw = task.Result
        except Exception as exc:
            raise SpectrometerError(f"Spectrum acquisition failed: {exc}") from exc
        return _to_spectrum(raw)

    def update_dark_spectrum(self, drop: bool = False, cancellation_token=None) -> None:
        self._run("Update dark spectrum", self.raw.UpdateDarkSpectrumAsync, drop, self._token(cancellation_token))

    def update_background_spectrum(self, drop: bool = False, cancellation_token=None) -> None:
        self._run("Update background spectrum", self.raw.UpdateBackgroundSpectrumAsync, drop, self._token(cancellation_token))

    def get_dark_spectrum(self) -> Optional[Spectrum]:
        raw = self.raw.GetDarkSpectrum()
        return _to_spectrum(raw) if raw else None

    def get_background_spectrum(self) -> Optional[Spectrum]:
        raw = self.raw.GetBackgroundSpectrum()
        return _to_spectrum(raw) if raw else None

    def get_latest_spectrum(self) -> Optional[Spectrum]:
        raw = self.raw.GetLatestSpectrum()
        return _to_spectrum(raw) if raw else None

    def get_active_dispersion_and_amplitude_correction(self) -> Spectrum:
        """Wavelength holds dispersion correction data; intensity holds amplitude correction data."""
        return _to_spectrum(self.raw.GetActiveDispersionAndAmplitudeCorrection())

    def get_hot_pixels_wavelengths(self) -> Dict[int, float]:
        return {int(kv.Key): float(kv.Value) for kv in self.raw.GetHotPixelsWavelengths()}

    # --- maintenance ------------------------------------------------------------------

    def soft_reset(self, only_usb: bool = True, cancellation_token=None) -> None:
        """Leaves the device Offline afterwards - rediscover it via SpectrometerManager.discover()."""
        self._run("Soft reset", self.raw.SoftResetAsync, only_usb, self._token(cancellation_token))

    def restore_factory_settings(self, cancellation_token=None) -> None:
        """Leaves the device Offline afterwards - rediscover it via SpectrometerManager.discover()."""
        self._run("Restore factory settings", self.raw.RestoreFactorySettingsAsync, self._token(cancellation_token))

    def close(self) -> None:
        """
        No-op: per-device Close()/CloseAsync() are inherited from
        IManagedDevice rather than declared on ICompactSpectrographDriver
        itself, and pythonnet cannot bind them on the real (non-virtual)
        driver class - even Object.GetType() fails the same way there, so
        this isn't fixable via casting or reflection from here. The vendor's
        own examples never call them either: use SpectrometerManager.close()
        (StartupHelperCompactSpectrometer.Dispose()), which releases all
        connected devices and is the documented cleanup path.
        """
