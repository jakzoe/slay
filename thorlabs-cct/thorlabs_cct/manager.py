"""Discovery and connection management for Thorlabs CCT spectrometers."""
import logging
from pathlib import Path
from typing import List, Optional, Union

from . import _runtime
from .exceptions import SpectrometerError
from .spectrometer import Spectrometer

logger = logging.getLogger(__name__)


class SpectrometerManager:
    """
    Wraps `StartupHelperCompactSpectrometer`: discovers spectrometers (USB,
    Ethernet, and/or a virtual device) and hands out connected
    `Spectrometer` instances.

    Create one per process/session and close it (or use it as a context
    manager) when done - it owns the underlying USB/Ethernet/virtual
    connection managers and their background workflows.
    """

    def __init__(self, *, use_virtual: bool = False, ethernet_ips: Optional[List[str]] = None,
                 log_name: str = "ThorlabsCCT", log_level: Optional[int] = None,
                 log_to_file: bool = False, sdk_root: Optional[Union[str, Path]] = None):
        _runtime.load(sdk_root)
        level = log_level if log_level is not None else _runtime.LogLevel.Information
        self._logger = _runtime.ExampleLogger(log_name, level, log_to_file, "Python")
        self._helper = _runtime.StartupHelperCompactSpectrometer(self._logger)
        self._helper.WithVirtual = use_virtual
        for ip in ethernet_ips or []:
            self.register_ethernet_ip(ip)

    def __enter__(self) -> "SpectrometerManager":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def use_virtual(self) -> bool:
        return bool(self._helper.WithVirtual)

    @use_virtual.setter
    def use_virtual(self, value: bool) -> None:
        self._helper.WithVirtual = bool(value)

    def register_ethernet_ip(self, ip_address: str) -> bool:
        """Add an IP address to scan during Ethernet discovery. Returns whether it was newly added."""
        try:
            return bool(self._helper.RegisterEthernetIpAddress(ip_address))
        except Exception as exc:
            raise SpectrometerError(f"Failed to register Ethernet IP '{ip_address}': {exc}") from exc

    def discover(self, cancellation_token=None) -> List[str]:
        """Run device discovery across USB, registered Ethernet addresses, and the virtual device (if enabled)."""
        token = cancellation_token if cancellation_token is not None else _runtime.CancellationTokenSource().Token
        try:
            devices = list(self._helper.GetKnownDevicesAsync(token).Result)
        except Exception as exc:
            raise SpectrometerError(f"Device discovery failed: {exc}") from exc
        logger.info("Discovered %d spectrometer(s): %s", len(devices), devices)
        return devices

    def connect(self, device_id: str) -> Spectrometer:
        """Connect to a previously discovered device by its id (see discover())."""
        driver = self._helper.GetCompactSpectrographById(device_id)
        if driver is None:
            raise SpectrometerError(f"No known spectrometer with id '{device_id}'")
        return Spectrometer(driver)

    def set_disconnected(self, device_id: str, connect_back: bool = False) -> bool:
        """
        Force a known device Offline, or (connect_back=True) clear that flag so it
        is reconnected on the next discover() call.
        """
        try:
            return bool(self._helper.SetSpectrometerDisconnectedByIdAsync(device_id, connect_back).Result)
        except Exception as exc:
            raise SpectrometerError(f"Failed to change connection state for '{device_id}': {exc}") from exc

    def close(self) -> None:
        """Disposes all connection managers and connected devices."""
        self._helper.Dispose()
