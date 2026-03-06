import numpy as np
from scipy import signal
import neurokit2 as nk
import os,sys
import numpy as np
import matplotlib.pyplot as plt 
import math
from scipy import signal


def slice_ECG_v2(ecg_cleaned,frequency):

    # Detect R-peaks
    signals, info = nk.ecg_peaks(ecg_cleaned, sampling_rate=frequency)
    peaks = info["ECG_R_Peaks"]
    
    # Shift indices (subtracting 10 as in your original logic)
    # Using np.maximum ensures we don't get negative indices
    indices = np.maximum(0, peaks - 10)
    
    # Create a list of (left, right) tuples for consecutive intervals
    # This allows you to do: segment = signal[left:right] later
    intervals = [(indices[i], indices[i+1]) for i in range(len(indices) - 1)]
    
    return peaks,intervals

def build_template(ecg_cleaned, intervals, shift_window=2, correlation_threshold=0.85):
    """
    Builds a robust heartbeat template using absolute index intervals.
    """
    n_total = len(intervals)
    if n_total == 0:
        return None, 0

    # PHASE 1: Analyze Lengths
    # intervals are (left, right), so length is r - l
    lengths = np.array([r - l for l, r in intervals])
    q25, q75 = np.percentile(lengths, [25, 75])
    
    # Filter valid indices for template building
    template_valid_indices = [i for i, l in enumerate(lengths) if q25 <= l <= q75]

    if not template_valid_indices:
        template_valid_indices = [i for i in range(n_total) if lengths[i] > 0]
        if not template_valid_indices: return None, 0

    target_len = int(max([lengths[i] for i in template_valid_indices]))

    # PHASE 2: Build the Master Template
    stack_list = []
    for idx in template_valid_indices:
        l, r = intervals[idx]
        sig = np.array(ecg_cleaned[l:r]) # Extract data using indices

        if np.std(sig) < 1e-9: continue
        
        sig_range = np.ptp(sig)
        if sig_range == 0: continue
        
        roughness = (np.sum(np.abs(np.diff(sig))) / sig_range) / len(sig)
        if roughness > 2.5: continue

        pad_width = target_len - len(sig)
        padded = np.pad(sig, (0, pad_width), 'edge') if pad_width > 0 else sig[:target_len]

        # Note: Ensure 'signal' is imported (scipy.signal)
        detrended = signal.detrend(padded, type='linear')
        
        mu = np.mean(detrended)
        sigma = np.std(detrended)
        norm_sig = (detrended - mu) / (sigma + 1e-9)
        
        stack_list.append(norm_sig)

    if not stack_list:
        return np.zeros(target_len), target_len

    stack = np.vstack(stack_list)
    template = np.median(stack, axis=0)
    return template, target_len


def classify_intervals(ecg_cleaned, intervals, template, target_len, shift_window=2):
    """
    Returns a list of max correlation scores for each interval.
    Scores range from 0.0 (noisy/invalid) to 1.0 (perfect match).
    """
    scores = []
    n_total = len(intervals)
    
    if n_total == 0:
        return []

    for i in range(n_total):
        l, r = intervals[i]
        raw = np.array(ecg_cleaned[l:r])
        curr_len = len(raw)
        
        # --- 0. Pre-check: Reject invalid lengths ---
        if curr_len == 0 or curr_len > len(template) * 2:
            scores.append(0.0)
            continue

        # --- 1. Fit to Target Length ---
        if curr_len < target_len:
            padded = np.pad(raw, (0, target_len - curr_len), 'edge')
        elif curr_len > target_len:
            padded = raw[:target_len]
        else:
            padded = raw

        # --- 2. Preprocess ---
        detrended = signal.detrend(padded, type='linear')
        mu, sigma = np.mean(detrended), np.std(detrended)

        # Reject flat lines
        if sigma < 1e-9:
            scores.append(0.0)
            continue

        norm_sig = (detrended - mu) / sigma

        # --- 3. Sliding Window Correlation (The Score) ---
        max_corr = -1.0
        for s in range(-shift_window, shift_window + 1):
            if s == 0:
                shifted = norm_sig
            elif s > 0:
                shifted = np.pad(norm_sig, (s, 0), 'edge')[:target_len]
            else:
                shifted = np.pad(norm_sig, (0, abs(s)), 'edge')[abs(s):]
            
            # Compute Pearson Correlation
            c = np.corrcoef(template, shifted)[0, 1]
            if c > max_corr:
                max_corr = c
        
        # Ensure score is not negative (negative correlation is noise)
        scores.append(max(0.0, float(max_corr)))

    return scores


def noise_classify(actual_signal_clean, sampling_rate,signal_type='ECG'):
    """
    Returns:
        intervals_actual: List of (left_idx, right_idx)
        scores: List of correlation scores for each interval
        template: The median heartbeat template used
    """
    # 1. Process Chunked Signal (Template Building)
    #ecg_cleaned_chunked = nk.ecg_clean(chunked_signal, sampling_rate=sampling_rate, method="neurokit")
    if signal_type=='ECG':
        _,intervals = slice_ECG_v2(actual_signal_clean, sampling_rate)
    elif signal_type=='PPG':
        _,intervals=slice_PPG_v2(actual_signal_clean, sampling_rate)

    template, target_len = build_template(actual_signal_clean, intervals)
    
    if template is None:
        return [], [], None

    # Get the correlation scores for every heartbeat in the actual signal
    scores = classify_intervals(
        actual_signal_clean, 
        intervals, 
        template, 
        target_len
    )

    return intervals, scores, template