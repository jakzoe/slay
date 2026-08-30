"""
Process-wide spectrometer session.

Connect once with connect(); any other function in the process - a REPL
call, a notebook cell, a GUI callback - can then reach the same connected
Spectrometer via current(), without the spectrometer being passed around or
a global variable being managed by calling code.
"""
import logging
from typing import Optional

from .exceptions import SpectrometerError
from .manager import SpectrometerManager
from .spectrometer import Spectrometer

logger = logging.getLogger(__name__)

_manager: Optional[SpectrometerManager] = None
_spectrometer: Optional[Spectrometer] = None


def connect(use_virtual: bool = True, device_id: Optional[str] = None, **manager_kwargs) -> Spectrometer:
    """
    Discover and connect to a spectrometer, keeping it as the current()
    session for the rest of the process. A no-op returning the existing
    session if already connected.

    Parameters:
    use_virtual: Include the SDK's virtual device in discovery.
    device_id: Connect to this specific device id instead of the first one discovered.
    manager_kwargs: Forwarded to SpectrometerManager (e.g. ethernet_ips=[...]).
    """
    global _manager, _spectrometer

    if _spectrometer is not None:
        return _spectrometer

    manager = SpectrometerManager(use_virtual=use_virtual, **manager_kwargs)
    try:
        if device_id is None:
            device_ids = manager.discover()
            if not device_ids:
                raise SpectrometerError("No spectrometers found.")
            device_id = device_ids[0]
        _spectrometer = manager.connect(device_id)
    except Exception:
        manager.close()
        raise
    _manager = manager

    logger.info("Connected to %s", _spectrometer.device_id)
    return _spectrometer


def disconnect() -> None:
    """Release the current() session, if any. Safe to call when not connected."""
    global _manager, _spectrometer
    if _manager is not None:
        _manager.close()
    _manager = None
    _spectrometer = None


def is_connected() -> bool:
    return _spectrometer is not None


def current() -> Spectrometer:
    """The spectrometer connected by connect(), for use by any other function."""
    if _spectrometer is None:
        raise SpectrometerError("Not connected - call thorlabs_cct.connect() first.")
    return _spectrometer
