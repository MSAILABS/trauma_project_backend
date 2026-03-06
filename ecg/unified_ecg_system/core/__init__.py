"""
Core modules for ECG/PPG signal processing

Modules:
    - healthypi_lib: Serial communication with HealthyPi 5
    - signal_loader: Unified interface for file and stream loading
    - signal_sender: Signal processing pipeline
    - signal_viewer_pyqt: Real-time PyQt5 visualization
    - main_unified: CLI entry point
"""

from . import healthypi_lib
from . import signal_loader
from . import signal_sender
from . import signal_viewer_pyqt
from .signal_loader import SignalFactory, SignalLoader
from .signal_sender import SignalProcessor, SignalNormalizer

__all__ = [
    "healthypi_lib",
    "signal_loader",
    "signal_sender",
    "signal_viewer_pyqt",
    "SignalFactory",
    "SignalLoader",
    "SignalProcessor",
    "SignalNormalizer",
]
