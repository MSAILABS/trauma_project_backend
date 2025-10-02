from scipy.signal import butter, filtfilt
import numpy as np

class PPGGenerator:
    def __init__(self, fs, heart_rate=75):
        self.fs = fs
        self.phase = 0
        self.hr_hz = heart_rate / 60

    def next(self, length):
        t = np.arange(length) / self.fs
        ppg = np.sin(2 * np.pi * self.hr_hz * t + self.phase)
        # advance phase so next call starts where this one left off
        self.phase += 2 * np.pi * self.hr_hz * (length / self.fs)
        return ppg

def simulate_ppg(length, fs, heart_rate=75):
    hr_hz = heart_rate / 60  # beats per second

    # IMPORTANT: Make time continuous without rounding issues
    t = np.arange(length) / fs

    # Pure sine wave between -1 and 1
    ppg = np.sin(2 * np.pi * hr_hz * t)

    return ppg


def butter_bandpass(lowcut, highcut, fs, order=4):
    nyquist = 0.5 * fs  # Nyquist frequency = half sampling rate
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

def butter_bandpass_filter(data, lowcut, highcut, fs, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = filtfilt(b, a, data)  # Apply forward-backward filter
    return y

def normalize_to_minus1_1(values):
    min_val = min(values)
    max_val = max(values)

    if max_val == min_val:  # avoid division by zero
        return [0.0 for _ in values]

    return [2 * ((x - min_val) / (max_val - min_val)) - 1 for x in values]