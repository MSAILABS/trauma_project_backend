"""
Signal Sender - Send ECG/PPG signals to backend (similar to ecg_decompress_v3)
"""
import os
import numpy as np
import librosa
from scipy.signal import spectrogram
from typing import Dict, List, Optional
import time
import json
from pathlib import Path
import sys
import random

import matplotlib.pyplot as plt

# Import from parent directory
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from unified_ecg_system.ecg_model.signal_manager import SignalManager
from unified_ecg_system.ecg_model.poting_model import PotingModel

try:
    from AICode import AIModelProcessor
    from api import ArrayData, getTokenForRequest, resetOldVisualization, sendData
    AI_ENABLED = True
    BACKEND_ENABLED = True
except ImportError as e:
    AI_ENABLED = False
    BACKEND_ENABLED = False
    print(f"⚠ Backend/AI modules not available: {e}")


class SignalNormalizer:
    """Normalize raw ECG/PPG signals"""
    
    @staticmethod
    def normalize(signal_slice: List[float], scale: float) -> List[float]:
        """
        Normalize signal slice to [-1, 1] range (matching ecg_decompress_v3.py)
        
        Args:
            signal_slice: Raw signal values for this chunk
            scale: Scale factor (typically max absolute value)
        
        Returns:
            Normalized signal clamped to [-1, 1]
        """
        return [v / scale for v in signal_slice]
    
    @staticmethod
    def scale_to_16bit(signal_slice: List[float], scale: float) -> List[float]:
        """
        Scale raw signal to 16-bit signed range [-32767, 32767]
        by rescaling (not clipping)
        
        Args:
            signal_slice: Raw signal values
            scale: Max absolute value from all signals
        
        Returns:
            Signal rescaled to 16-bit range
        """
        bit16_max = 32767
        scale_factor = scale or 1
        # Normalize to [-1, 1] then scale to 16-bit range
        return [int((v / scale_factor) * bit16_max) for v in signal_slice]
    
    @staticmethod
    def normalize_signals(signals: Dict[str, List[float]]) -> tuple:
        """
        Normalize multiple signals
        
        Returns:
            (normalized_signals, scale_factor, stats)
        """
        if not signals:
            return {}, 1, {}
        
        # Calculate global scale factor
        all_values = []
        for samples in signals.values():
            all_values.extend(samples)
        
        min_val = min(all_values) if all_values else 0
        max_abs_val = max(abs(v) for v in all_values) if all_values else 1
        scale_factor = max_abs_val or 1
        
        # Normalize each channel
        normalized = {}
        for name, samples in signals.items():
            normalized[name] = SignalNormalizer.normalize(samples, scale_factor)
        
        stats = {
            'min_value': min_val,
            'max_absolute_value': max_abs_val,
            'scale_factor': scale_factor,
        }
        
        return normalized, scale_factor, stats


class SignalProcessor:
    """Process and send signals"""
    
    def __init__(self, sampling_rate: int = 500, chunk_seconds: int = 5,
                 model_dir: Optional[str] = None):
        """
        Initialize signal processor
        
        Args:
            sampling_rate: Sampling rate (Hz)
            chunk_seconds: Chunk duration (seconds)
            model_dir: Path to AI model directory (optional)
        """
        self.sampling_rate = sampling_rate
        self.chunk_seconds = chunk_seconds
        self.chunk_size = sampling_rate * chunk_seconds
        
        self.ai_processor = None
        self.poting_model = None
        if AI_ENABLED and model_dir:
            try:
                
                self.ai_processor = AIModelProcessor(
                    model_dir=model_dir,
                    sampling_rate=sampling_rate
                )
                print("✓ AI model loaded")
                self.poting_model = PotingModel(device="cpu")
                print("✓ PoTing model loaded")
            except Exception as e:
                print("[WARNING] Failed to load AI model: " + str(e))
        
        self.results_file = "ai_results.json"

        self.signal_manager = SignalManager(sampling_rate=sampling_rate)
    
    def process_signals(self, signals: Dict[str, List[float]], 
                       description: str = "",
                       send_to_backend: bool = True,
                       on_data_chunk=None) -> List[Dict]:
        """
        Process and send signals in chunks
        
        Args:
            signals: Dict of channel_name -> signal_values
            description: Description of the data
            send_to_backend: Whether to send to backend
        
        Returns:
            List of results
        """
        # Prepare signals
        # Use all provided channels (no filtering)
        
        if not signals:
            raise ValueError("No signals to process")
        
        # Normalize
        normalized, scale_factor, stats = SignalNormalizer.normalize_signals(signals)
        
        print("[STATS] Signal statistics:")
        print("   Min value: " + str(stats['min_value']))
        print("   Max absolute value: " + str(stats['max_absolute_value']))
        
        # Get authorization token
        token = None
        if send_to_backend and BACKEND_ENABLED:
            try:
                token = getTokenForRequest()
                print("[OK] Got auth token for backend")
                
                # Reset visualization
                resetOldVisualization(token=token)
                print("[OK] Reset backend visualization")
            except Exception as e:
                print("[WARNING] Backend unavailable: " + str(e))
                token = None
        elif send_to_backend and not BACKEND_ENABLED:
            print("[WARNING] Backend disabled (api.py not available)")
            try:
                token = getTokenForRequest()
                resetOldVisualization(token=token)
            except Exception as e:
                print("[WARNING] Backend authorization failed: " + str(e))
        
        # Process chunks
        results = []
        total_samples = len(next(iter(signals.values())))
        part_number = 9
        print('TOTAL SAMPLE',total_samples)
        print('CHUNK SIZE',self.chunk_size)
        for start in range(0, total_samples, self.chunk_size):
            end = min(start + self.chunk_size, total_samples)
            chunk_length = end - start
            
            # Raw signals (non-normalized)
            raw_signals_chunk = {
                name: samples[start:end]
                for name, samples in signals.items()
            }
            
            scale_factor= max(abs(v) for samples in raw_signals_chunk.values() for v in samples) or 1
            # Scale raw signals to 16-bit range for display
            '''raw_signals_16bit = {
                name: SignalNormalizer.normalize(samples, scale_factor/600)
                for name, samples in raw_signals_chunk.items()
            }


            raw_signals_16bit_int = {
                name: np.array(samples, dtype=np.int32).tolist()
                for name, samples in raw_signals_16bit.items()
            }'''
            
            # Normalize this chunk using global scale factor
            chunk_signals = {
                name: SignalNormalizer.normalize(samples, scale_factor*100)
                for name, samples in raw_signals_chunk.items()
            }

            

            os.makedirs('chunks', exist_ok=True)
            plt.plot(raw_signals_chunk['I'])
            plt.title(f'Raw ECG Signal (Part {part_number})')
            plt.savefig(f'chunks/raw_ecg_part_{part_number}.png')
            plt.clf()
            plt.plot(chunk_signals['I'])
            plt.title(f'Normalized ECG Signal (Part {part_number})')
            plt.savefig(f'chunks/normalized_ecg_part_{part_number}.png')
            plt.clf()

            print(f'max value in chunk: {max(abs(v) for samples in raw_signals_chunk.values() for v in samples)}')
            print(f'chunk_signals max value: {max(abs(v) for samples in chunk_signals.values() for v in samples)}')
            print(f'first 10 raw values: {list(raw_signals_chunk.values())[0][:10]}')
            print(f'first 10 normalized values: {list(chunk_signals.values())[0][:10]}')
            self.signal_manager.append_signals(raw_signals_chunk['I'],[])
            self.signal_manager.process_signals()
            featureset=self.signal_manager.get_stage2_features()
            os.makedirs('featureset_250',exist_ok=True)
            with open(f'featureset_250/{start}.json', 'w') as f:
                json.dump(featureset, f, indent=4)

            # AI processing
            ai_result = None
            print('self.ai_processor',self.ai_processor)
            if self.ai_processor:
                try:
                    ai_result = self.ai_processor.process_new_chunk(raw_signals_chunk)
                    print(len(featureset))
                    poting_result = self.poting_model.predict(featureset)
                    threshold=0.5
                    poting_result_binary = np.where(np.array(poting_result) >= threshold, 1, 0)
                    processed_results= (np.array(poting_result_binary),np.array(poting_result))
                    print(f"✓ AI prediction: {ai_result}, PoTing prediction: {poting_result}")
                    
                    
                except Exception as e:
                    print("[WARNING] AI processing error: " + str(e))
            
            # Prepare metadata
            chunk_desc = f"{description} (Part {part_number})" if description else f"Part {part_number}"
            lsi_meta = {
                'lsi_description': chunk_desc,
                'lsi_sampling_rate': self.sampling_rate,
            }
            
            # Add AI results to metadata
            if processed_results:
                preds, probas = processed_results

                # Map probabilities if CLASS_NAMES available
                print('processed_results',processed_results)
                try:
                    from demo_rf_model.demo_rf_model.rf_predict import CLASS_NAMES
                    for i, class_name in CLASS_NAMES.items():
                        #print(probas[i])
                        lsi_meta[f'lsi_{class_name}'] = float(probas[0][i]) 
                    print('lsi_meta',lsi_meta)
                except Exception as e:
                    print(f"[WARNING] Error processing AI results: {e}")
                    pass
                
                results.append({
                    'part': part_number,
                    'description': chunk_desc,
                    'ai_prediction': preds,
                    'ai_probabilities': probas.tolist() if hasattr(probas, 'tolist') else probas,
                })
            else:
                # If buffer isn't 60s yet, use random or default values
                try:
                    from demo_rf_model.demo_rf_model.rf_predict import CLASS_NAMES
                    for i, class_name in CLASS_NAMES.items():
                        lsi_meta[f'lsi_{class_name}'] = 0.0
                except:
                    pass
            
            # Extract first channel for FFT/MFCC/Spectrogram
            first_channel_name = list(raw_signals_chunk.keys())[0]
            first_channel_signal = np.array(raw_signals_chunk[first_channel_name], dtype=np.float32)
            
            # Compute FFT
            fft_vals = np.fft.rfft(first_channel_signal)
            fft_freqs = np.fft.rfftfreq(len(first_channel_signal), d=1/self.sampling_rate)
            fft_magnitude = np.abs(fft_vals).tolist()
            
            # Compute MFCC
            mfccs = librosa.feature.mfcc(y=first_channel_signal,
                                        sr=self.sampling_rate, n_mfcc=13).tolist()
            
            # Compute Spectrogram
            nperseg = int(self.sampling_rate * 0.5)
            noverlap = nperseg // 2
            f, t, Sxx = spectrogram(
                first_channel_signal,
                fs=self.sampling_rate,
                nperseg=nperseg,
                noverlap=noverlap,
                nfft=nperseg
            )
            Sxx_db = 10 * np.log10(Sxx + 1e-12)
            
            # Debug: Log signal values for first part only           
               
            # Send to backend
            
            for name, samples in chunk_signals.items():
                print('shape of chunk_signals',name,len(samples))

            if send_to_backend and token:
                try:
                    payload = ArrayData(
                        data={
                        "meta": lsi_meta,
                        "signals": chunk_signals,  # Send normalized signals [-1, 1] like ecg_decompress_v3
                        "raw_signals": raw_signals_chunk,  # Send 16-bit rescaled raw signals
                        "fft_frequencies": fft_freqs.tolist(),
                        "fft_magnitude": fft_magnitude,
                        "mfcc": mfccs,
                        "spectrogram_time_bins": t.tolist(),
                        "spectrogram_freq_bins": f.tolist(),
                        "spectrogram_power": Sxx_db.tolist(),
                        "chunk_seconds": self.chunk_seconds,
                        "chunk_length": chunk_length,
                        },
                        file_name="ecg_ppg_signal"
                    )
                    
                    sendData(payload_data=payload, token=token,
                            chunk_seconds=self.chunk_seconds, part_number=part_number)
                    
                    print("[OK] Sent part " + str(part_number) + " to backend")
                except Exception as e:
                    print("[WARNING] Failed to send part " + str(part_number) + ": " + str(e))
            else:
                # No backend connection: just show what would be sent
                if not token:
                    print("[OK] [Simulated] Would send part " + str(part_number) + " to backend (no token)")
            
            # Wait 1 second between chunks (matching ecg_decompress_v3 behavior)
            if end < total_samples:
                print("[WAIT] Waiting 1 second before next chunk...")
                time.sleep(1)
            
            if on_data_chunk:
                try:
                    # Extract ECG (I) and PPG (II) for visualization
                    # Use raw_signals_16bit_int for better visualization scaling for ECG
                    ecg_chunk = raw_signals_16bit_int.get('I', [])
                    # Use raw unscaled data for PPG as requested by user ("ppg doesn't need normalization")
                    ppg_chunk = raw_signals_chunk.get('II', []) if 'II' in raw_signals_chunk else []
                    
                    on_data_chunk(ecg_chunk, ppg_chunk)
                except Exception as e:
                    print(f"[WARNING] Visualization update failed: {e}")

            part_number += 1
        
        # Save results
        self._save_results(results)
        
        print(f"✓ Processing complete ({part_number - 1} parts)")
        return results
    
    def _save_results(self, results: List[Dict]):
        """Save AI results to JSON file"""
        if not results:
            return
        
        try:
            # Load existing results
            if Path(self.results_file).exists():
                with open(self.results_file, 'r') as f:
                    all_results = json.load(f)
            else:
                all_results = []
            
            # Append new results
            all_results.extend(results)
            
            # Save
            with open(self.results_file, 'w') as f:
                json.dump(all_results, f, indent=4)
            
            print("[OK] Saved " + str(len(results)) + " results to " + str(self.results_file))
        except Exception as e:
            print("[WARNING] Failed to save results: " + str(e))


if __name__ == '__main__':
    # Example usage
    # Create sample signals
    fs = 500
    duration = 5
    t = np.arange(0, duration, 1/fs)
    
    # Simulate ECG (mix of frequencies)
    ecg = (100 * np.sin(2 * np.pi * 1 * t) + 
           50 * np.sin(2 * np.pi * 5 * t)).tolist()
    
    # Simulate PPG
    ppg = (80 * np.sin(2 * np.pi * 1.2 * t)).tolist()
    
    signals = {'I': ecg, 'II': ecg, 'III': ecg}
    
    processor = SignalProcessor(sampling_rate=fs, chunk_seconds=5)
    results = processor.process_signals(signals, description="Test", send_to_backend=False)
    
    print(f"Processed {len(results)} parts")
