# Add these imports at the top of ecg_decompress_v3.py
from collections import deque
# Assuming rf_predict.py is in the same directory
import ecg.demo_rf_model.demo_rf_model.rf_predict as rf_predict
import numpy as np
import neurokit2 as nk
import pandas as pd


class AIModelProcessor:
    def __init__(self, model_dir, sampling_rate=500):
        self.sampling_rate = sampling_rate
        self.required_seconds = 60
        self.chunk_seconds = 5
        # We need 12 chunks of 5s to reach 60s
        self.max_chunks = self.required_seconds // self.chunk_seconds

        # Buffer to store raw signal chunks for each channel
        self.buffer = {
            'I': deque(maxlen=self.max_chunks),
            'II': deque(maxlen=self.max_chunks),
            'III': deque(maxlen=self.max_chunks)
        }

        # Load the models once during initialization
        print(f"--- Loading AI Models from {model_dir} ---")
        self.models, self.feature_info, self.thresholds, self.clip_bounds, self.col_means = \
            rf_predict.load_models(model_dir)

    def process_new_chunk(self, raw_signals_5s):
        """
        Takes a dictionary of 5s chunks, adds to buffer, 
        and returns predictions if buffer is full (60s).
        """
        # 1. Add new 5s chunks to the rolling buffer
        for name, signal in raw_signals_5s.items():
            if name in self.buffer:
                self.buffer[name].append(signal)

        # 2. Check if we have enough data (60 seconds / 12 chunks)
        # We check one channel (e.g., 'I') assuming all are synchronized
        if len(self.buffer['I']) < self.max_chunks:
            print(
                f"--- Buffer building: {len(self.buffer['I'])}/{self.max_chunks} chunks ---")
            return None

        # 3. Flatten the buffer into a single 60s array for each channel
        full_60s_signals = {
            name: np.concatenate(list(chunks))
            for name, chunks in self.buffer.items()
        }

        # 4. Feature Extraction (Crucial Step)
        # Note: rf_predict expects a 'data_dict' of HRV/ECG features.
        extracted_features = self.extract_features_from_60s(full_60s_signals)

        # 5. Preprocess and Predict using rf_predict logic
        X = rf_predict.extract_and_preprocess(
            extracted_features,
            self.feature_info['feature_names'],
            self.clip_bounds,
            self.col_means
        )

        preds, probas = rf_predict.predict(X, self.models, self.thresholds)
        return preds, probas

    def extract_features_from_60s(self, signals_60s):
        """
        Processes 60s of ECG data using NeuroKit2 to extract features.
        Returns a dict mapping ALL_FEATURES to values.
        """
        data_dict = {}

        # 1. Select the best lead for analysis
        # Lead II is generally preferred for HRV/Peak detection. Fallback to I.
        target_lead = 'I'

        # Ensure we have data
        if target_lead not in signals_60s:
            # Emergency fallback: use the first available key
            target_lead = list(signals_60s.keys())[0]

        ecg_signal = signals_60s[target_lead]

        try:
            # 2. Process the signal (Clean & Find Peaks)
            # nk.ecg_process returns a DataFrame (signals) and a dict (info/peaks)
            ecg_signals, info = nk.ecg_process(
                ecg_signal, sampling_rate=self.sampling_rate)

            # 3. Analyze features (HRV, Interval related)
            # method='interval' calculates HRV and other interval-based metrics
            # This returns a single-row DataFrame
            ecg_features = nk.ecg_analyze(
                ecg_signals, sampling_rate=self.sampling_rate, method='interval')

            # 4. Match against the RF model's expected features by stripping first 4 chars
            for original_feature in rf_predict.ALL_FEATURES:
                # Strip first 4 characters from the model's required feature name
                stripped_feature = original_feature[4:]

                if stripped_feature in ecg_features.columns:
                    val = ecg_features[stripped_feature].iloc[0]
                    # Handle NaNs or infinite values
                    if pd.isna(val) or np.isinf(val):
                        data_dict[original_feature] = [0.0]
                    else:
                        data_dict[original_feature] = [float(val)]
                else:
                    # If the stripped name doesn't exist in NeuroKit output, default to 0.0
                    data_dict[original_feature] = [0.0]

        except Exception as e:
            print(f"⚠️ Error during NeuroKit2 extraction: {e}")
            # If extraction fails (e.g., too much noise, no peaks found), fill with zeros
            for feature in rf_predict.ALL_FEATURES:
                data_dict[feature] = [0.0]

        return data_dict
