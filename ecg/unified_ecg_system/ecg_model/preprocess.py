import pandas as pd
import numpy as np
from collections import defaultdict
from scipy import stats
from pyentrp import entropy as ent 
import neurokit2 as nk

from .template_builder import build_template,noise_classify

def safe_calc(func, *args, **kwargs):
    """Helper to run a function and return np.nan if it fails."""
    try:
        result = func(*args, **kwargs)
        # Check for cases where result is empty or invalid
        return result if np.isscalar(result) or len(result) > 0 else np.nan
    except Exception:
        return np.nan



def compute_stage2_features(feature_collections):
    '''this function compute stage 2 features from the stage 1 feature lists, and return the dict of final features'''
    summary_features = {}
    

    # A. Global Quality Ratios (Length-Independent)
    clean_counts = sum(len(v) for k, v in feature_collections.items() if k.endswith('_clean'))
    noisy_counts = sum(len(v) for k, v in feature_collections.items() if k.endswith('_noisy'))
    total = clean_counts + noisy_counts
    summary_features['ratio_clean'] = clean_counts / total if total > 0 else np.nan

    # B. Statistical & Trend Analysis for every feature list
    for key, values in feature_collections.items():
        # 1. Convert to numpy and create a mask of valid indices
        data_raw = np.array(values, dtype=float)
        valid_mask = np.isfinite(data_raw)
        data = data_raw[valid_mask]  # This is your "ignored" list for distribution stats

        # CHANGE: If no valid data exists, we must handle the empty case
        if len(data) < 2:
            metrics = {k: 0.0 for k in ['mean', 'std', 'median', 'min', 'max', 
                                       'skew', 'kurt', 'iqr', 'cv', 
                                       'slope', 'trend_tau', 'net_change']}
        else:
            # 2. Distribution Stats (Now guaranteed to have no NaNs)
            m, s = np.mean(data), np.std(data)
            metrics = {
                'mean': m,
                'std': s,
                'median': np.median(data),
                'min': np.min(data),
                'max': np.max(data),
                'skew': stats.skew(data) if len(data) > 2 else 0.0,
                'kurt': stats.kurtosis(data) if len(data) > 2 else 0.0,
                'iqr': stats.iqr(data),
                'cv': s / (m + 1e-6)
            }

            # 3. Trend Stats (Paired filtering)
            # We filter BOTH the x-axis and y-axis using the same mask 
            # so the slope is calculated only on existing data points.
            full_x_axis = np.arange(len(data_raw))
            x_filtered = full_x_axis[valid_mask]
            
            # Linear Slope on existing points only
            slope, _ = np.polyfit(x_filtered, data, 1)
            metrics['slope'] = slope

            # Kendall Tau on existing points only
            tau, _ = stats.kendalltau(x_filtered, data)
            metrics['trend_tau'] = np.nan_to_num(tau, nan=0.0)

            # Net Change (Using the original list logic but ignoring internal NaNs)
            win = max(1, len(data) // 10)
            metrics['net_change'] = np.mean(data[-win:]) - np.mean(data[:win])

        # Flatten into the final dict
        for stat_name, stat_value in metrics.items():
            summary_features[f"{key}_{stat_name}"] = stat_value

    return summary_features


#current design is also similar to phase2, as I only use the first channel in vt dict
def compute_channel(raw_ecg_signal,misc_dict={'hosp':"UMB"},channel_name='in_hospital/signal/ECG_dummy',clean_threshold=0.85,debug=False):
    '''
    args: raw_ecg_signal: list of raw ECG signal values
    misc_dict: dict of miscellaneous info, currently only contains 'hosp' key for hospital-specific processing
    channel_name: name of the signal channel, used for hospital-specific processing and feature naming
    clean_threshold: threshold for classifying heartbeats as clean or noisy based on noise score  
    returns: dict of computed features for this channel, with keys like 'sig_std_clean_mean', 'd1_skew_noisy_median', etc.
    '''
    feature_collections = compute_stage1_feature_list(raw_ecg_signal,misc_dict,channel_name,clean_threshold,debug)

    ret=compute_stage2_features(feature_collections)

    return ret

def compute_stage1_feature_list(raw_ecg_signal,misc_dict={'hosp':"UMB"},channel_name='in_hospital/signal/ECG_dummy',clean_threshold=0.85,debug=False,sampling_rate=250):
    '''this function compute stage 1 feature lists from the raw signal, and return the dict of feature lists. The stage 2 feature will be computed from these lists'''
    raw_ecg_signal=np.array(raw_ecg_signal).flatten()
    length=raw_ecg_signal.shape[0]
    hosp=misc_dict['hosp']
    frequency=sampling_rate
    #unlike the noise evaluation, we always use full signal, since we can't append the
    #signal if the signal is shorter than min_len
    #ranges = get_sub_ranges(predict_range, min_len)
    #frequency=250
    if 'in_hospital' in channel_name and hosp=='UMB':
        #only UMB in_hospital need convert uV to mV
        #and it has different frequency
        frequency=240
        #raw_ecg_signal=raw_ecg_signal*2.44e-3


    ecg_clean=nk.ecg_clean(raw_ecg_signal, sampling_rate=frequency, method="neurokit")

    intervals,scores,template=noise_classify(ecg_clean,frequency)
    #print(intervals,scores)

    feature_collections = defaultdict(list)
    last_right=0
    for (left, right), score in zip(intervals, scores):
        #print
        heartbeats_signal = ecg_clean[left:right]
        last_right=right
        #print(heartbeats_signal)
        # Pre-check: Need enough points for 2nd derivative (n-2) and entropy
        if len(heartbeats_signal) < 6: continue

        # 1. Device Invariance: Normalize base signal
        mean_val, std_val = np.mean(heartbeats_signal), np.std(heartbeats_signal)
        norm_signal = (heartbeats_signal - mean_val) / (std_val + 1e-6)

        # 2. Define the three "views" of the heartbeat
        views = {
            'sig': norm_signal,           # Position (Normalized)
            'd1': np.diff(norm_signal),   # Velocity
            'd2': np.diff(norm_signal, n=2) # Acceleration
        }

        # 3. Comprehensive Feature Map
        # We apply the same statistical suite to all three views
        stats_map = {
            'rri': safe_calc(lambda: abs(right - left) / frequency)
        }

        for prefix, data in views.items():
            stats_map.update({
                f'{prefix}_std':       safe_calc(np.std, data),
                f'{prefix}_max':       safe_calc(np.max, data),
                f'{prefix}_min':       safe_calc(np.min, data),
                f'{prefix}_median':    safe_calc(np.median, data),
                f'{prefix}_skew':      safe_calc(stats.skew, data),
                f'{prefix}_kurt':      safe_calc(stats.kurtosis, data),
                f'{prefix}_rms':       safe_calc(lambda x: np.sqrt(np.mean(x**2)), data),
                f'{prefix}_zcr':       safe_calc(lambda x: ((x[:-1] * x[1:]) < 0).sum
                () / len(x), data),
                f'{prefix}_perm_ent': safe_calc(ent.permutation_entropy, data, order=3, delay=1)
            })
        #print('stats_map',stats_map)
        # 4. Dynamic Suffix Logic
        suffix = 'clean' if score > clean_threshold else 'noisy'
        for key, value in stats_map.items():
            feature_collections[f'{key}_{suffix}'].append(value)
        #now, the dict should be
        #print('features',feature_collections)
    return feature_collections,last_right