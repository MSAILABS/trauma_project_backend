#!/usr/bin/env python3
"""
ECG Decompressor for Lepu ER3 format.
Reverse-engineered from com.lepu.blepro.utils.DecompressUtil (doah.doag)
"""

from scipy.signal import spectrogram
import numpy as np
import librosa
from pathlib import Path
import requests
import argparse
import matplotlib.pyplot as plt
import time
import random

from AICode import AIModelProcessor
import demo_rf_model.demo_rf_model.rf_predict as rf_predict
from api import ArrayData, getTokenForRequest, resetOldVisualization, sendData
from map import save_fft_mfcc_spectrogram
# url  =https://trauma-back.msailab.com
import json
import os


def append_result_to_json(new_result, filename="ai_results.json"):
    """
    Saves results into a JSON array. If the file doesn't exist, it creates one.
    Otherwise, it appends the new result to the existing array.
    """
    # 1. Load existing data or initialize an empty list
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                data_list = json.load(f)
                # Ensure the loaded data is actually a list
                if not isinstance(data_list, list):
                    data_list = []
        except (json.JSONDecodeError, IOError):
            # If file is corrupted or empty, start fresh
            data_list = []
    else:
        data_list = []

    # 2. Append the new inference dictionary
    data_list.append(new_result)

    # 3. Write the updated array back to the file
    with open(filename, 'w') as f:
        json.dump(data_list, f, indent=4)

    print(f"✅ Result appended to {filename}")


class ER3Decompressor:
    """
    State machine decompressor matching doah.doag from the Java library.
    """

    def __init__(self, num_channels):
        self.doai = num_channels  # Number of channels
        self.doaj = 0             # Current state
        self.doam = 0             # Current channel index
        self.doak = [0] * num_channels  # Accumulators
        self.doal = [0] * num_channels  # Previous values (output buffer)
        self.doan = 0             # Byte flag/bitmask

    def process_byte(self, byte_val):
        """
        Process a single byte and return output array if complete, else None.
        byte_val should be 0-255 (unsigned byte).
        """
        # Convert to signed byte for comparison
        sb = byte_val if byte_val < 128 else byte_val - 256

        result = None

        if self.doaj == 0:
            # State 0: Normal delta mode or escape detection
            if sb == -128:  # 0x80 - escape byte
                self.doaj = 17
                self.doan = 0
                self.doam = 0
            else:
                # Add delta to current channel
                self.doak[self.doam] += sb
                self.doal[self.doam] = self.doak[self.doam]
                self.doam += 1
                if self.doam >= self.doai:
                    result = list(self.doal)
                    self.doam = 0

        elif self.doaj == 17:
            # State 17: Read bitmask
            self.doan = byte_val
            # If bitmask is not -1 (0xFF) and not 0, reset doal[0]
            if sb != -1 and sb != 0:
                self.doal[0] = 0
            self.doaj = 18

        elif self.doaj == 18:
            # State 18: Process channel based on bitmask
            bit = (self.doan >> self.doam) & 1
            if bit:
                # Bit set: read low byte of absolute value
                self.doak[self.doam] = byte_val  # Store low byte
                self.doaj = 19
            else:
                # Bit clear: add delta
                self.doak[self.doam] += sb
                self.doal[self.doam] = self.doak[self.doam]
                self.doam += 1
                if self.doam >= self.doai:
                    result = list(self.doal)
                    self.doaj = 0
                    self.doam = 0

        elif self.doaj == 19:
            # State 19: Read high byte of absolute value
            val = self.doak[self.doam] | (byte_val << 8)
            if val >= 32768:
                val -= 65536  # Convert to signed
            self.doak[self.doam] = val
            self.doal[self.doam] = val
            self.doam += 1
            self.doaj = 18
            if self.doam >= self.doai:
                result = list(self.doal)
                self.doaj = 0
                self.doam = 0

        return result


def decompress_er3(data_bytes, lead_type):
    """
    Decompress ER3 ECG data.

    Args:
        data_bytes: Data section (after 5-byte file header)
        lead_type: 0 for 12-lead, 2 for 8-lead

    Returns:
        List of sample arrays, one per output channel
    """
    # Number of internal decompressor channels
    if lead_type == 0:
        num_channels = 8  # 12-lead uses 8 internal channels
    else:
        num_channels = 4  # 8-lead uses 4 internal channels

    decompressor = ER3Decompressor(num_channels)

    # Process all bytes
    sample_sets = []
    for byte_val in data_bytes:
        result = decompressor.process_byte(byte_val)
        if result is not None:
            # Apply 32767 -> 0 conversion (from doad.doe)
            processed = [0 if v == 32767 else v for v in result]
            sample_sets.append(processed)

    return sample_sets


def distribute_to_channels(sample_sets, lead_type):
    """
    Distribute decompressed samples to output channels.
    Based on doad.doe tableswitch logic.
    """
    if lead_type == 0:
        # 12-lead mode: return samples directly
        # The 8 decompressed channels map directly to output
        # Channels: I, II, III, aVR, aVL, aVF, V1, V2 (repeated for 12 channels)
        # Actually for leadType 0, doad.doe just returns the array as-is
        channel_names = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2']
        channels = {name: [] for name in channel_names}

        for sample_set in sample_sets:
            for i, val in enumerate(sample_set):
                channels[channel_names[i]].append(val)

        return channels

    elif lead_type == 2:
        # 8-lead mode (leadType 2): expand 4 channels to 8
        # Pattern from bytecode: [0, s[1], s[2], s[3], 0, 0, 0, s[0]]
        channel_names = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V5']
        channels = {name: [] for name in channel_names}

        for sample_set in sample_sets:
            channels['I'].append(0)
            channels['II'].append(sample_set[1] if len(sample_set) > 1 else 0)
            channels['III'].append(sample_set[2] if len(sample_set) > 2 else 0)
            channels['aVR'].append(sample_set[3] if len(sample_set) > 3 else 0)
            channels['aVL'].append(0)
            channels['aVF'].append(0)
            channels['V1'].append(0)
            channels['V5'].append(sample_set[0] if len(sample_set) > 0 else 0)

        return channels

    else:
        raise ValueError(f"Unsupported lead type: {lead_type}")


# ... existing imports ...
def process_and_send_er3_data(
    raw_data: bytes,
    sampling_rate: int = 250,
    description: str = ""
):
    """
    Decompresses ER3 data, splits it into 5-second chunks, 
    and sends each chunk 1 second apart.
    """
    # 1. Parse header and Decompress
    if len(raw_data) < 6:
        raise ValueError("Invalid ER3 file: too small")
    
    # Try reading bytes 3 and 4 as a Little-Endian or Big-Endian 16-bit integer:
    sr_little = int.from_bytes(raw_data[3:5], byteorder='little')
    sr_big = int.from_bytes(raw_data[3:5], byteorder='big')
    
    print(f"DEBUG: Header bytes: {list(raw_data[0:5])}")
    print(f"DEBUG: Potential Sampling Rates -> Little Endian: {sr_little} | Big Endian: {sr_big}")
    

    lead_type = raw_data[2]
    data_bytes = raw_data[5:]
    sample_sets = decompress_er3(data_bytes, lead_type)

    if not sample_sets:
        raise ValueError("No ECG samples decompressed")

    # 2. Distribute to channels
    channels = distribute_to_channels(sample_sets, lead_type)

    # Get only the first 3 key-value pairs
    channels = dict(list(channels.items())[:3])

    all_values = []
    for samples in channels.values():
        all_values.extend(samples)

    # Other stats
    # min_value = min(all_values)
    # max_abs_value = max(abs(v) for v in all_values)
    # Print results
    # print("📊 Global ECG stats:")
    # print(f"   Min value: {min_value}")
    # print(f"   Max absolute value: {max_abs_value}")

    # --- NEW: Robust Global Scaling ---
    all_values_np = np.array(all_values)
    
    # 1. Calculate the global baseline to ignore massive DC offsets (like in HealthPi)
    global_baseline = np.median(all_values_np)
    
    # 2. Center the data to find the true wave amplitude
    centered_values = all_values_np - global_baseline
    
    # 3. Use the 99th percentile to ignore extreme outlier spikes 
    robust_scale_factor = np.percentile(np.abs(centered_values), 99)
    if robust_scale_factor == 0:
        robust_scale_factor = 1.0

    # Print results
    print("📊 Global ECG stats (Robust):")
    print(f"   Raw Min: {np.min(all_values_np)}")
    print(f"   Raw Max: {np.max(all_values_np)}")
    print(f"   Global Baseline: {global_baseline}")
    print(f"   Robust Scale Factor: {robust_scale_factor}")


    # 3. Chunking Configuration
    chunk_seconds = 10
    chunk_size = sampling_rate * chunk_seconds  # 250 * 5 = 1250 samples
    total_samples = len(next(iter(channels.values())))

    # OLD Helper for normalization
    # def normalize(signal_slice, scale):
    #     return [max(-1.0, min(1.0, v / scale)) for v in signal_slice]
    
    # Helper for robust normalization
    def normalize(signal_slice, global_scale):
        slice_np = np.array(signal_slice)
        
        # Remove the DC offset locally for this chunk to prevent baseline drift
        chunk_baseline = np.median(slice_np)
        centered_slice = slice_np - chunk_baseline
        
        # Scale and safely clamp between -1.0 and 1.0
        return [float(max(-1.0, min(1.0, v / global_scale))) for v in centered_slice]

    # getting token for authorization
    token = getTokenForRequest()
    # removing old visualization data from backend to show latest visualization on frontend
    resetOldVisualization(token=token)

    # Initialize the AI Processor (specify your model path here)
    ai_processor = AIModelProcessor(
        model_dir="./demo_rf_model/demo_rf_model/2026-01-29_10-06-37/models/fold_2", sampling_rate=sampling_rate)

    # 4. Loop through the data in chunks
    # scale_factor = max_abs_value or 1  # avoid division by zero
    scale_factor = robust_scale_factor
    part_number = 1
    for start in range(0, total_samples, chunk_size):
        # --- 1. RECORD START TIME ---
        loop_start_time = time.time()

        end = start + chunk_size

        # Raw signals (non-normalized)
        raw_signals_chunk = {
            name: samples[start:end]
            for name, samples in channels.items()
        }

        # --- NEW: AI MODEL PROCESSING ---
        ai_results = ai_processor.process_new_chunk(raw_signals_chunk)

        lsi_meta = {
            'lsi_description': f"{description} (Part {part_number})",
            'lsi_sampling_rate': sampling_rate
        }

        if ai_results:
            preds, probas = ai_results

            # Map the AI probabilities to your metadata using CLASS_NAMES from rf_predict
            for i, class_name in rf_predict.CLASS_NAMES.items():
                lsi_meta[f'lsi_{class_name}'] = float(probas[0][i])

            print("--- AI Inference Complete ---")
            print(lsi_meta)

            # --- NEW: Save to JSON Array ---
            # We include the part_number and timestamp for better tracking
            result_to_save = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "part_number": part_number,
                "predictions": lsi_meta
            }
            append_result_to_json(result_to_save)
        else:
            # If buffer isn't 60s yet, use random or default values
            for class_name in rf_predict.CLASS_NAMES.values():
                lsi_meta[f'lsi_{class_name}'] = random.uniform(0.01, 0.05)

        # Slice and normalize each channel for this specific 5-second window
        signals_chunk = {
            name: normalize(samples[start:end], scale_factor)
            for name, samples in channels.items()
        }

        # Example: generate FFT & MFCC for the first channel
        first_channel_name = list(raw_signals_chunk.keys())[0]
        first_channel_signal = raw_signals_chunk[first_channel_name]

        # Build payload for this specific part
        chunk_description = f"{description} (Part {part_number})" if description else f"Part {part_number}"

        fft_vals = np.fft.rfft(first_channel_signal)
        fft_freqs = np.fft.rfftfreq(
            len(first_channel_signal), d=1/sampling_rate)

        mfccs = librosa.feature.mfcc(y=np.array(first_channel_signal, dtype=np.float32),
                                     sr=sampling_rate, n_mfcc=13).tolist()

        first_channel_signal = np.array(first_channel_signal, dtype=np.float32)

        nperseg = int(sampling_rate * 0.5)   # 0.5 seconds window
        noverlap = nperseg // 2        # 50% overlap
        nfft = nperseg                 # usually same as nperseg

        f, t, Sxx = spectrogram(
            first_channel_signal,
            fs=sampling_rate,
            nperseg=nperseg,
            noverlap=noverlap,
            nfft=nfft
        )

        f: np.ndarray
        t: np.ndarray
        Sxx: np.ndarray

        Sxx_db = 10 * np.log10(Sxx + 1e-12)

        fft_magnitude = np.abs(fft_vals).tolist()

        # time_axis = np.arange(len(first_channel_signal)) / sampling_rate

        # save_fft_mfcc_spectrogram(
        #     signal_time_axis=time_axis,
        #     signal_values=first_channel_signal,
        #     fft_freqs=fft_freqs,
        #     fft_magnitude=fft_magnitude,
        #     mfccs=mfccs,
        #     spec_t=t,
        #     spec_f=f,
        #     spec_power=Sxx_db,
        #     prefix=f"part_{part_number}",
        #     out_dir="images",
        #     sampling_rate=sampling_rate
        # )

        spectrogram_data = {
            "time_bins": t.tolist(),
            "freq_bins": f.tolist(),
            "power": Sxx_db.tolist()   # send dB values
        }

        lsi_meta["lsi_description"] = chunk_description

        # "meta": {
        #             'lsi_Damage Control Procedures': random.uniform(0.01, 0.05),
        #             'lsi_Neurologic Products & Procedures': random.uniform(0.01, 0.05),
        #             'lsi_Blood Products': random.uniform(0.01, 0.05),
        #             'lsi_Bleeding Control': 0.78 if part_number > 10 and part_number < 15 else random.uniform(0.01, 0.05),
        #             'lsi_Airway & Respiration': random.uniform(0.01, 0.05),
        #             'lsi_Chest Decompression': random.uniform(0.01, 0.05),
        #             "lsi_description": chunk_description,
        #             "lsi_sampling_rate": sampling_rate
        #         },
        payload_data = ArrayData(
            data={
                "meta": lsi_meta,
                "signals": signals_chunk,
                "raw_signals": raw_signals_chunk,
                "fft_frequencies": fft_freqs.tolist(),
                "fft_magnitude": fft_magnitude,
                "mfcc": mfccs,
                "spectrogram_time_bins": spectrogram_data["time_bins"],
                "spectrogram_freq_bins": spectrogram_data["freq_bins"],
                "spectrogram_power": spectrogram_data["power"],
                "chunk_seconds": chunk_seconds
            },
            file_name="none"
        )

        # if part_number > 8 and part_number < 11:
        # 5. Send to backend
        sendData(payload_data=payload_data, token=token,
                 chunk_seconds=chunk_seconds, part_number=part_number)
        

        # 6. Wait 1 second before next part
        if end < total_samples:  # Don't sleep after the very last chunk
            # --- 2. CALCULATE EXACT PROCESSING TIME ---
            processing_time = time.time() - loop_start_time
            
            # --- 3. CALCULATE WAIT TIME (Safeguard against negative sleep) ---
            wait_time = max(0.0, chunk_seconds - processing_time)
            print(f"⏳ Waiting {wait_time} second before sending next chunk...")
            time.sleep(wait_time)

        part_number += 1

    return {"status": "all_parts_processed"}


def main():
    parser = argparse.ArgumentParser(
        description='Decompress Lepu ER3 ECG files')
    parser.add_argument('input_file', help='Input ECG file')
    parser.add_argument(
        '-o', '--output', default='ECG_OUTPUT_V3', help='Output directory')
    parser.add_argument('-d', '--duration', type=int,
                        default=10, help='Plot duration in seconds')
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f'Processing: {input_path.name}')
    print('=' * 60)

    # Read file
    raw = input_path.read_bytes()

    process_and_send_er3_data(raw_data=raw)


if __name__ == '__main__':
    main()
