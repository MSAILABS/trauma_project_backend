from scipy.signal import spectrogram, get_window
import librosa.display
import librosa
import matplotlib.pyplot as plt
import os
import numpy as np
import matplotlib
# Use the 'Agg' backend to avoid Tkinter thread issues
matplotlib.use('Agg')


def save_fft_mfcc_spectrogram(
    signal_time_axis,          # time axis for ECG
    signal_values,             # raw ECG signal
    fft_freqs, fft_magnitude,  # FFT results
    mfccs,                     # MFCC matrix
    spec_t, spec_f, spec_power,  # Spectrogram results (already in dB)
    prefix="chunk",
    out_dir="images",
    sampling_rate=500
):
    os.makedirs(out_dir, exist_ok=True)

    # --- ECG + FFT ---
    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    axs[0].plot(signal_time_axis, signal_values)
    axs[0].set_title("Raw ECG Signal")
    axs[0].set_xlabel("Time (s)")
    axs[0].set_ylabel("Amplitude")

    axs[1].plot(fft_freqs, fft_magnitude)
    axs[1].set_title("FFT Spectrum (one-sided)")
    axs[1].set_xlabel("Frequency (Hz)")
    axs[1].set_ylabel("Magnitude")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{prefix}_fft_pair.png"))
    plt.close()

    # --- MFCC ---
    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    axs[0].plot(signal_time_axis, signal_values)
    axs[0].set_title("Raw ECG Signal")
    axs[0].set_xlabel("Time (s)")
    axs[0].set_ylabel("Amplitude")

    mfccs = np.array(mfccs, dtype=np.float32)

    img1 = librosa.display.specshow(
        mfccs, x_axis='time', sr=sampling_rate, ax=axs[1])
    axs[1].set_title("MFCC")
    fig.colorbar(img1, ax=axs[1])
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{prefix}_mfcc_pair.png"))
    plt.close()

    # --- Spectrogram ---
    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    axs[0].plot(signal_time_axis, signal_values)
    axs[0].set_title("Raw ECG Signal")
    axs[0].set_xlabel("Time (s)")
    axs[0].set_ylabel("Amplitude")

    img2 = axs[1].pcolormesh(spec_t, spec_f, spec_power, shading='gouraud')
    axs[1].set_title("Spectrogram")
    axs[1].set_ylabel("Frequency [Hz]")
    axs[1].set_xlabel("Time [sec]")
    axs[1].set_yscale('log')
    axs[1].set_ylim(1, max(spec_f))
    fig.colorbar(img2, ax=axs[1], label="Power (dB)")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{prefix}_spectrogram_pair.png"))
    plt.close()
