#!/usr/bin/env python3
"""
Test script for ECG/PPG signal processing system
Validates all components without requiring actual hardware
"""
import sys
import os
import json
import tempfile
from pathlib import Path
import numpy as np

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))


def test_imports():
    """Test all imports"""
    print("Testing imports...")
    try:
        import healthypi_lib
        import signal_loader
        import signal_sender
        import signal_viewer_pyqt
        print("✓ All imports successful\n")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}\n")
        return False


def test_signal_normalizer():
    """Test signal normalization"""
    print("Testing SignalNormalizer...")
    try:
        from signal_sender import SignalNormalizer
        
        # Create test signals
        test_signal = [0, 50, -50, 100, -100]
        normalized = SignalNormalizer.normalize_channel(test_signal)
        
        # Check range
        assert all(-1 <= v <= 1 for v in normalized), "Values outside [-1, 1]"
        assert abs(normalized[3] - 1.0) < 0.01, "Max should be ~1.0"
        
        print(f"  Original: {test_signal}")
        print(f"  Normalized: {[f'{v:.3f}' for v in normalized]}")
        print("✓ SignalNormalizer works\n")
        return True
    except Exception as e:
        print(f"✗ SignalNormalizer test failed: {e}\n")
        return False


def test_file_signal_loader():
    """Test file-based signal loading"""
    print("Testing FileSignalLoader...")
    try:
        from signal_loader import FileSignalLoader
        
        # Create temporary test files
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = os.path.join(tmpdir, 'test_data')
            
            # Create test ECG file
            ecg_data = [100 * np.sin(2 * np.pi * i / 50) for i in range(500)]
            with open(f'{base_path}.ecg', 'w') as f:
                for val in ecg_data:
                    f.write(f"{val:.1f}\n")
            
            # Create test PPG file
            ppg_data = [80 * np.sin(2 * np.pi * i / 80) for i in range(500)]
            with open(f'{base_path}.ppg', 'w') as f:
                for val in ppg_data:
                    f.write(f"{val:.1f}\n")
            
            # Load
            loader = FileSignalLoader(base_path, sampling_rate=500)
            ecg, ppg = loader.load()
            
            assert len(ecg) == 500, f"Expected 500 ECG samples, got {len(ecg)}"
            assert len(ppg) == 500, f"Expected 500 PPG samples, got {len(ppg)}"
            
            stats = loader.get_stats()
            print(f"  Loaded {len(ecg)} ECG samples, range: [{stats['ecg']['min']:.1f}, {stats['ecg']['max']:.1f}]")
            print(f"  Loaded {len(ppg)} PPG samples, range: [{stats['ppg']['min']:.1f}, {stats['ppg']['max']:.1f}]")
            print("✓ FileSignalLoader works\n")
            return True
    except Exception as e:
        print(f"✗ FileSignalLoader test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_signal_factory():
    """Test SignalFactory pattern"""
    print("Testing SignalFactory...")
    try:
        from signal_loader import SignalFactory
        
        # Create temporary test files
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = os.path.join(tmpdir, 'factory_test')
            
            # Create test files
            with open(f'{base_path}.ecg', 'w') as f:
                for i in range(100):
                    f.write(f"{i}\n")
            
            with open(f'{base_path}.ppg', 'w') as f:
                for i in range(100):
                    f.write(f"{i*2}\n")
            
            # Test factory
            loader = SignalFactory.create('file', base_path=base_path)
            ecg, ppg = loader.load()
            
            assert len(ecg) == 100, "ECG length mismatch"
            assert len(ppg) == 100, "PPG length mismatch"
            
            print(f"  Created FileSignalLoader via factory")
            print(f"  Loaded {len(ecg)} ECG and {len(ppg)} PPG samples")
            print("✓ SignalFactory works\n")
            return True
    except Exception as e:
        print(f"✗ SignalFactory test failed: {e}\n")
        return False


def test_signal_processor():
    """Test signal processor"""
    print("Testing SignalProcessor...")
    try:
        from signal_sender import SignalProcessor
        
        # Create test signals
        fs = 500
        duration = 5
        t = np.arange(0, duration, 1/fs)
        ecg = (100 * np.sin(2 * np.pi * 1 * t)).tolist()
        ppg = (80 * np.sin(2 * np.pi * 1.2 * t)).tolist()
        
        signals = {'I': ecg, 'II': ppg, 'III': ecg}
        
        # Process
        processor = SignalProcessor(sampling_rate=fs, chunk_seconds=5)
        results = processor.process_signals(
            signals,
            description="Test",
            send_to_backend=False
        )
        
        print(f"  Processed {len(results)} result(s)")
        print("✓ SignalProcessor works\n")
        return True
    except Exception as e:
        print(f"✗ SignalProcessor test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_healthypi_lib():
    """Test HealthyPi library (without serial connection)"""
    print("Testing HealthyPi library...")
    try:
        from healthypi_lib import HealthyPiStream, HealthyPiStreamWithQueue
        
        # Just test instantiation
        stream1 = HealthyPiStream()
        stream2 = HealthyPiStreamWithQueue()
        
        print("  Created HealthyPiStream instance")
        print("  Created HealthyPiStreamWithQueue instance")
        print("✓ HealthyPi library works\n")
        return True
    except Exception as e:
        print(f"✗ HealthyPi library test failed: {e}\n")
        return False


def test_command_line_interface():
    """Test CLI argument parsing"""
    print("Testing Command Line Interface...")
    try:
        import argparse
        import main_unified
        
        # Just verify the module loads
        print("  Imported main_unified module")
        print("✓ CLI interface loads\n")
        return True
    except Exception as e:
        print(f"✗ CLI interface test failed: {e}\n")
        return False


def test_end_to_end():
    """Test complete workflow"""
    print("Testing End-to-End Workflow...")
    try:
        from signal_loader import FileSignalLoader
        from signal_sender import SignalProcessor, SignalNormalizer
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test data
            base_path = os.path.join(tmpdir, 'e2e_test')
            fs = 500
            
            ecg_sig = [50 * np.sin(2 * np.pi * i / fs) for i in range(fs * 5)]  # 5 seconds
            ppg_sig = [40 * np.sin(2 * np.pi * i / (fs*1.2)) for i in range(fs * 5)]
            
            with open(f'{base_path}.ecg', 'w') as f:
                for val in ecg_sig:
                    f.write(f"{val:.1f}\n")
            
            with open(f'{base_path}.ppg', 'w') as f:
                for val in ppg_sig:
                    f.write(f"{val:.1f}\n")
            
            # Load
            print("  Loading signals...")
            loader = FileSignalLoader(base_path, sampling_rate=fs)
            ecg, ppg = loader.load()
            
            # Normalize
            print("  Normalizing...")
            signals = {'I': ecg, 'II': ppg, 'III': ecg}
            normalized, scale, stats = SignalNormalizer.normalize_signals(signals)
            
            # Process
            print("  Processing...")
            processor = SignalProcessor(sampling_rate=fs, chunk_seconds=5)
            results = processor.process_signals(
                signals,
                description="E2E Test",
                send_to_backend=False
            )
            
            print(f"  Scale factor: {scale:.2f}")
            print(f"  Generated {len(results)} results")
            print("✓ End-to-end workflow succeeds\n")
            return True
    except Exception as e:
        print(f"✗ End-to-end test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("ECG/PPG Signal Processing System - Test Suite")
    print("="*60 + "\n")
    
    tests = [
        ("Imports", test_imports),
        ("SignalNormalizer", test_signal_normalizer),
        ("FileSignalLoader", test_file_signal_loader),
        ("SignalFactory", test_signal_factory),
        ("SignalProcessor", test_signal_processor),
        ("HealthyPi Library", test_healthypi_lib),
        ("CLI Interface", test_command_line_interface),
        ("End-to-End", test_end_to_end),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"✗ {name} crashed: {e}\n")
            results.append((name, False))
    
    # Summary
    print("="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, passed_test in results:
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"{status:8} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. See QUICKSTART.md for usage examples")
        print("  2. Run: python main_unified.py --help")
        print("  3. Test with your data: python main_unified.py --file <data_path>")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please check the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
