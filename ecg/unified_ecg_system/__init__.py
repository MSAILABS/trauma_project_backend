"""
Unified ECG/PPG Signal Processing System

A modular, production-ready system for processing ECG and PPG signals
in both real-time stream and file-based modes.

Components:
    - core: Implementation modules (healthypi_lib, signal_loader, signal_sender, etc.)
    - tests: Test suite
    - docs: Complete documentation

Usage:
    CLI mode:
        python -m unified_ecg_system.core.main_unified --file <path>
        python -m unified_ecg_system.core.main_unified --stream

    Python API:
        from unified_ecg_system.core import SignalFactory, SignalProcessor
        loader = SignalFactory.create('file', base_path='data')
        ecg, ppg = loader.load()
"""

__version__ = "1.0"
__author__ = "Signal Processing Team"
__all__ = ["core", "tests", "docs"]
