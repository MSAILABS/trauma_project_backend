"""
Signal Loader - Load ECG/PPG from stream or files
"""
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from healthypi_lib import HealthyPiStreamWithQueue
import time
import numpy as np

class SignalLoader:
    """Base class for signal loading"""
    
    def __init__(self, sampling_rate: int = 500):
        self.sampling_rate = sampling_rate
        self.ecg_data: List[float] = []
        self.ppg_data: List[float] = []
        self.is_running = False
    
    def load(self) -> Tuple[List[float], List[float]]:
        """Load ECG and PPG data. Returns (ecg, ppg) tuples"""
        raise NotImplementedError
    
    def is_loaded(self) -> bool:
        """Check if data is loaded"""
        return len(self.ecg_data) > 0 and len(self.ppg_data) > 0
    
    def get_ecg(self) -> List[float]:
        """Get ECG data"""
        return self.ecg_data
    
    def get_ppg(self) -> List[float]:
        """Get PPG data"""
        return self.ppg_data
    
    def get_stats(self) -> Dict:
        """Get signal statistics"""
        if not self.ecg_data or not self.ppg_data:
            return {}
        
        ecg_all = self.ecg_data
        ppg_all = self.ppg_data
        
        return {
            'ecg': {
                'count': len(ecg_all),
                'min': min(ecg_all),
                'max': max(ecg_all),
                'mean': sum(ecg_all) / len(ecg_all),
            },
            'ppg': {
                'count': len(ppg_all),
                'min': min(ppg_all),
                'max': max(ppg_all),
                'mean': sum(ppg_all) / len(ppg_all),
            }
        }


class FileSignalLoader(SignalLoader):
    """Load signals from .ecg and .ppg files"""
    
    def __init__(self, base_path: str, sampling_rate: int = 500):
        """
        Initialize file loader
        
        Args:
            base_path: Base path (files will be base_path.ecg and base_path.ppg)
            sampling_rate: Sampling rate (default 500 Hz)
        """
        super().__init__(sampling_rate)
        self.base_path = base_path
        if base_path.endswith('.hdf5'):
            self.ecg_file = base_path
            self.ppg_file = base_path
        else:
            self.ecg_file = f"{base_path}.ecg"
            self.ppg_file = f"{base_path}.ppg"
    
    def load(self) -> Tuple[List[float], List[float]]:
        """Load ECG and PPG data from files"""
        
        if self.ecg_file.endswith('.hdf5'):
            ecg = self._load_hdf5(self.ecg_file)
        else:
            ecg = self._load_file(self.ecg_file)
        
        if self.ppg_file.endswith('.hdf5'):
            ppg = self._load_hdf5(self.ppg_file)
        else:
            ppg = self._load_file(self.ppg_file)
        
        self.ecg_data = np.array(ecg).flatten().tolist()
        print(f"Loaded {len(self.ecg_data)} ECG samples from {self.ecg_file}")
        self.ppg_data = []
                    
        print("[OK] Loaded " + str(len(self.ecg_data)) + " ECG samples from " + str(self.ecg_file))
        print("[OK] Loaded " + str(len(self.ppg_data)) + " PPG samples from " + str(self.ppg_file))
        
        return self.ecg_data, self.ppg_data
    
    def _load_hdf5(self, filepath: str) -> List[float]:
        from junkcode.peek_hdf5 import load_hdf5
        data_dict = load_hdf5(filepath)
        for key, value in data_dict.items():
            if ('ecg' in key.lower() or 'lead' in key.lower()) and 'time' not in key.lower():
                return value.tolist()
    
    def _load_file(self, filepath: str) -> List[float]:
        """Load data from a single file"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        data = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            value = float(line)
                            data.append(value)
                        except ValueError:
                            pass  # Skip non-numeric lines
        except Exception as e:
            raise IOError(f"Error reading file {filepath}: {e}")
        
        return data


class StreamSignalLoader(SignalLoader):
    """Load signals from HealthyPi stream"""
    
    def __init__(self, port: str = 'COM5', sampling_rate: int = 500,
                 duration: Optional[float] = None):
        """
        Initialize stream loader
        
        Args:
            port: Serial port (e.g., 'COM5', '/dev/ttyUSB0')
            sampling_rate: Expected sampling rate
            duration: Duration to record (None = continuous)
        """
        super().__init__(sampling_rate)
        self.port = port
        self.duration = duration
        self.stream = HealthyPiStreamWithQueue(
            port=port,
            sampling_rate=sampling_rate
        )
    
    def load(self) -> Tuple[List[float], List[float]]:
        """Start loading from stream"""
        if not self.stream.connect():
            raise RuntimeError(f"Failed to connect to {self.port}")
        
        if not self.stream.start():
            raise RuntimeError("Failed to start stream")
        
        self.is_running = True
        print(f"✓ Connected to stream on {self.port}")
        print(f"✓ Recording ECG/PPG data (duration: {'∞' if not self.duration else f'{self.duration}s'})")
        
        if self.duration:
            time.sleep(self.duration)
            self.stop()
        
        # Get data from queues
        self.ecg_data = self.stream.get_all_ecg()
        self.ppg_data = self.stream.get_all_ppg()
        
        return self.ecg_data, self.ppg_data
    
    def get_latest(self) -> Tuple[Optional[float], Optional[float]]:
        """Get latest ECG and PPG values (non-blocking)"""
        ecg = self.stream.get_ecg(timeout=0.01)
        ppg = self.stream.get_ppg(timeout=0.01)
        return ecg, ppg
    
    def collect_for_duration(self, duration: float):
        """Collect data for specified duration"""
        start_time = time.time()
        while time.time() - start_time < duration:
            ecg, ppg = self.get_latest()
            if ecg is not None:
                self.ecg_data.append(ecg)
            if ppg is not None:
                self.ppg_data.append(ppg)
            time.sleep(0.001)
    
    def stop(self):
        """Stop streaming"""
        self.is_running = False
        self.stream.stop()
        self.stream.disconnect()
        print(f"✓ Stream stopped. Collected {len(self.ecg_data)} ECG and {len(self.ppg_data)} PPG samples")


class SignalFactory:
    """Factory to create appropriate signal loader"""
    
    @staticmethod
    def create(mode: str, **kwargs) -> SignalLoader:
        """
        Create signal loader
        
        Args:
            mode: 'file' or 'stream'
            **kwargs: Arguments for the loader
        
        Returns:
            SignalLoader instance
        """
        if mode == 'file':
            if 'base_path' not in kwargs:
                raise ValueError("base_path required for file mode")
            return FileSignalLoader(kwargs['base_path'], 
                                   kwargs.get('sampling_rate', 500))
        
        elif mode == 'stream':
            return StreamSignalLoader(
                port=kwargs.get('port', 'COM5'),
                sampling_rate=kwargs.get('sampling_rate', 500),
                duration=kwargs.get('duration', None)
            )
        
        else:
            raise ValueError(f"Unknown mode: {mode}")


if __name__ == '__main__':
    # Example usage
    
    # File mode
    print("Testing File Mode:")
    loader = SignalFactory.create('file', base_path='ecg_data')
    try:
        ecg, ppg = loader.load()
        stats = loader.get_stats()
        print(f"Stats: {stats}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Stream mode (commented out to avoid blocking)
    # print("\nTesting Stream Mode:")
    # loader = SignalFactory.create('stream', port='COM5', duration=5)
    # try:
    #     loader.load()
    #     stats = loader.get_stats()
    #     print(f"Stats: {stats}")
    # except Exception as e:
    #     print(f"Error: {e}")
