"""
Bootstraps pythonnet/clr and loads the Thorlabs CCT SDK .NET assemblies.

The vendor documentation (Thorlabs_Compact-Spectrometer_CCT-SDK.pdf) and the
example script CctGetSpectrum.py describe this platform-detection dance for
Windows (.NET Framework, net48) vs. Linux/macOS (.NET Core, net8.0). This
module performs it once, at first use, so the rest of `thorlabs_cct` can be
plain Python.

The pythonnet runtime must be selected *before* `clr` is imported, which is
why this module does that work at call time inside `load()` rather than
leaving it to import side effects scattered across the package.
"""

import os
import platform
import sys
from pathlib import Path
from typing import Optional, Union

_PACKAGE_ROOT = Path(__file__).resolve().parent
_DEFAULT_SDK_ROOT = _PACKAGE_ROOT.parent / "pyCCT"

_loaded = False

# Populated by load(); typed as object so this module has no hard dependency
# on pythonnet at import time.
StartupHelperCompactSpectrometer = None
ICompactSpectrographDriver = None
ExampleLogger = None
LogLevel = None
CancellationTokenSource = None


def _dll_dir(sdk_root: Path) -> Path:
    return sdk_root / ("net48" if os.name == "nt" else "net8.0")


def _native_dir(dll_dir: Path) -> Path:
    """Resolve the runtimes/<rid>/native folder pythonnet needs for non-Windows OSes."""
    system = platform.system().lower()
    if system == "darwin":
        system = "osx"
    elif system != "linux":
        raise RuntimeError(f"Unsupported platform for the Thorlabs CCT SDK: '{system}'")

    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    elif "arm" in machine:
        arch = "arm"
    else:
        raise RuntimeError(
            f"Unsupported machine architecture for the Thorlabs CCT SDK: '{machine}'"
        )

    return dll_dir / "runtimes" / f"{system}-{arch}" / "native"


def load(sdk_root: Optional[Union[str, Path]] = None) -> None:
    """
    Load the .NET runtime and the CCT SDK assemblies.

    Idempotent - later calls (including with a different `sdk_root`) are a
    no-op once the CLR is loaded, since pythonnet cannot switch runtimes
    within a process.

    Parameters:
    sdk_root: Path to the "pyCCT" folder shipped with the CCT SDK
        distribution (contains net8.0/net48 subfolders with the driver
        DLLs). Defaults to the "pyCCT" folder next to this package, or the
        THORLABS_CCT_SDK_DIR environment variable if set.
    """
    global _loaded
    global StartupHelperCompactSpectrometer, ICompactSpectrographDriver
    global ExampleLogger, LogLevel, CancellationTokenSource

    if _loaded:
        return

    root = (
        Path(sdk_root)
        if sdk_root is not None
        else Path(os.environ.get("THORLABS_CCT_SDK_DIR", _DEFAULT_SDK_ROOT))
    )
    dll_dir = _dll_dir(root)
    if not dll_dir.is_dir():
        raise FileNotFoundError(
            f"Thorlabs CCT SDK assemblies not found at '{dll_dir}'. "
            "Pass sdk_root=... or set THORLABS_CCT_SDK_DIR to the 'pyCCT' "
            "folder shipped with the CCT SDK distribution."
        )

    import pythonnet

    pythonnet.load("netfx" if os.name == "nt" else "coreclr")

    # clr must only be imported after the runtime above has been selected.
    import clr  # noqa: F401

    if str(dll_dir) not in sys.path:
        sys.path.append(str(dll_dir))

    if os.name != "nt":
        native_dir = _native_dir(dll_dir)
        if str(native_dir) not in sys.path:
            sys.path.append(str(native_dir))

    clr.AddReference("System.IO.Ports")
    clr.AddReference("Thorlabs.ManagedDevice.CompactSpectrographDriver")
    clr.AddReference("Microsoft.Extensions.Logging.Abstractions")

    from Microsoft.Extensions.Logging import LogLevel as _LogLevel
    from System.Threading import CancellationTokenSource as _CancellationTokenSource
    from Thorlabs.ManagedDevice.CompactSpectrographDriver import (
        ICompactSpectrographDriver as _ICompactSpectrographDriver,
    )
    from Thorlabs.ManagedDevice.CompactSpectrographDriver.Workflow import (
        StartupHelperCompactSpectrometer as _StartupHelperCompactSpectrometer,
    )
    from Thorlabs.ManagedDevice.Trace import ExampleLogger as _ExampleLogger

    StartupHelperCompactSpectrometer = _StartupHelperCompactSpectrometer
    ICompactSpectrographDriver = _ICompactSpectrographDriver
    ExampleLogger = _ExampleLogger
    LogLevel = _LogLevel
    CancellationTokenSource = _CancellationTokenSource

    _loaded = True
