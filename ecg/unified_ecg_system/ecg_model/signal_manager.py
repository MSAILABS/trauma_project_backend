import pandas as pd
import numpy as np
from collections import defaultdict
from scipy import stats
from pyentrp import entropy as ent 
import neurokit2 as nk

from .preprocess import compute_stage1_feature_list, compute_stage2_features
from .template_builder import build_template,noise_classify




class SignalManager:

    def __init__(self, sampling_rate: int = 500):
        self.sampling_rate = sampling_rate
        self.ecg_signal = []
        self.ppg_signal = []
        self.processed_features=defaultdict(list)
        self.last_processed_ecg_index = 0  # Track how much of the signal has been processed
        self.last_processed_ppg_index = 0
    
    def load_signals(self, ecg_data: list, ppg_data: list):
        """reset and Load ECG and PPG signals"""
        self.ecg_signal = ecg_data
        self.ppg_signal = ppg_data

        self.last_processed_ecg_index = 0  # Track how much of the signal has been processed
        self.last_processed_ppg_index = 0

    def append_signals(self, ecg_data: list, ppg_data: list):
        """Append new ECG and PPG data to existing signals"""
        self.ecg_signal.extend(ecg_data)
        self.ppg_signal.extend(ppg_data)

        print(f"Appended {len(ecg_data)} ECG samples and {len(ppg_data)} PPG samples. Total ECG: {len(self.ecg_signal)}, Total PPG: {len(self.ppg_signal)}")

    def process_signals(self):
        """Process the loaded signals and extract features"""
        if not self.ecg_signal:
            return {}
        
        
        unprocessed_ecg = self.ecg_signal[self.last_processed_ecg_index:]
        #unprocessed_ppg = self.ppg_signal[self.last_processed_ppg_index:]  
        print(f"Processing new ECG data from index {self.last_processed_ecg_index} to {len(self.ecg_signal)} ({len(unprocessed_ecg)} samples)")
        feature_collections,last_right = compute_stage1_feature_list(unprocessed_ecg, misc_dict={'hosp':"UMB"}, channel_name='pre_hospital/signal/ECG_dummy', clean_threshold=0.85, debug=False,sampling_rate=self.sampling_rate)
        self.last_processed_ecg_index += last_right
        noisy_key = 'rri_noisy'
        clean_key = 'rri_clean'
        print(feature_collections[clean_key])
        print('Total unprocessed noisy heartbeats: ', len(feature_collections.get(noisy_key, [])))
        print('Total unprocessed clean heartbeats: ', len(feature_collections.get(clean_key, [])))

        for feature_name, feature_values in feature_collections.items():
            if 'noisy' in feature_name:
                continue
            self.processed_features[feature_name].extend(feature_values)


        
        if noisy_key in self.processed_features:
            print(f"Total processed noisy heartbeats in key {noisy_key}: {len(self.processed_features[noisy_key])}")
        else:
            print(f"No noisy heartbeats processed in key {noisy_key}")

        if clean_key in self.processed_features:
            print(f"Total processed clean heartbeats in key {clean_key}: {len(self.processed_features[clean_key])}")
        else:
            print(f"No clean heartbeats processed in key {clean_key}")
           

    def get_stage2_features(self) -> dict: 
        """Get the final processed features after stage 2 computation"""
        if not self.processed_features:
            return {}
        first_key = next(iter(self.processed_features))
        
        print(f"Computing stage 2 features from {len(self.processed_features[first_key])} heartbeats...")
        return compute_stage2_features(self.processed_features)
    
    def get_ecg(self) -> list:
        """Get ECG signal"""
        return self.ecg_signal
    
    def get_ppg(self) -> list:
        """Get PPG signal"""
        return self.ppg_signal
    
    def get_stats(self) -> dict:
        """Get signal statistics"""
        if not self.ecg_signal or not self.ppg_signal:
            return {}
        
        ecg_all = self.ecg_signal
        ppg_all = self.ppg_signal
        
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