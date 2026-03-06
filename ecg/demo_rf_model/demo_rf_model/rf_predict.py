
import argparse
import numpy as np
import pandas as pd
import joblib
import os
import sys
from io import StringIO
from datetime import datetime

# ============================================================
# Logging - capture all output to summary.txt
# ============================================================
output_log = []

_original_print = print

def log_print(*args, **kwargs):
    """Print to both stdout and capture for summary file."""
    output = StringIO()
    _original_print(*args, file=output, **kwargs)
    message = output.getvalue()
    output_log.append(message)
    sys.stdout.write(message)
    sys.stdout.flush()

# Override built-in print
print = log_print

# ============================================================
# ALL FEATURES - Used for ALL classes
# ============================================================
ALL_FEATURES =  [
 'ECG_HRV_CVNN',
 'ECG_HRV_CVSD',
 'ECG_HRV_HF',
 'ECG_HRV_HFn',
 'ECG_HRV_HTI',
 'ECG_HRV_IQRNN',
 'ECG_HRV_LF',
 'ECG_HRV_LFHF',
 'ECG_HRV_LFn',
 'ECG_HRV_LnHF',
 'ECG_HRV_MCVNN',
 'ECG_HRV_MadNN',
 'ECG_HRV_MaxNN',
 'ECG_HRV_MeanNN',
 'ECG_HRV_MedianNN',
 'ECG_HRV_MinNN',
 'ECG_HRV_Prc20NN',
 'ECG_HRV_Prc80NN',
 'ECG_HRV_RMSSD',
 'ECG_HRV_SDANN1',
 'ECG_HRV_SDANN2',
 'ECG_HRV_SDANN5',
 'ECG_HRV_SDNN',
 'ECG_HRV_SDNNI1',
 'ECG_HRV_SDNNI2',
 'ECG_HRV_SDNNI5',
 'ECG_HRV_SDRMSSD',
 'ECG_HRV_SDSD',
 'ECG_HRV_TINN',
 'ECG_HRV_TP',
 'ECG_HRV_ULF',
 'ECG_HRV_VHF',
 'ECG_HRV_VLF',
 'ECG_HRV_pNN20',
 'ECG_HRV_pNN50',

'PPG_HRV_AI',
 'PPG_HRV_ApEn',
 'PPG_HRV_C1a',
 'PPG_HRV_C1d',
 'PPG_HRV_C2a',
 'PPG_HRV_C2d',
 'PPG_HRV_CD',
 'PPG_HRV_CMSEn',
 'PPG_HRV_CSI',
 'PPG_HRV_CSI_Modified',
 'PPG_HRV_CVI',
 'PPG_HRV_CVNN',
 'PPG_HRV_CVSD',
 'PPG_HRV_Ca',
 'PPG_HRV_Cd',
 'PPG_HRV_DFA_alpha1',
 'PPG_HRV_DFA_alpha2',
 'PPG_HRV_FuzzyEn',
 'PPG_HRV_GI',
 'PPG_HRV_HF',
 'PPG_HRV_HFD',
 'PPG_HRV_HFn',
 'PPG_HRV_HTI',
 'PPG_HRV_IALS',
 'PPG_HRV_IQRNN',
 'PPG_HRV_KFD',
 'PPG_HRV_LF',
 'PPG_HRV_LFHF',
 'PPG_HRV_LFn',
 'PPG_HRV_LZC',
 'PPG_HRV_LnHF',
 'PPG_HRV_MCVNN',
 'PPG_HRV_MFDFA_alpha1_Asymmetry',
 'PPG_HRV_MFDFA_alpha1_Delta',
 'PPG_HRV_MFDFA_alpha1_Fluctuation',
 'PPG_HRV_MFDFA_alpha1_Increment',
 'PPG_HRV_MFDFA_alpha1_Max',
 'PPG_HRV_MFDFA_alpha1_Mean',
 'PPG_HRV_MFDFA_alpha1_Peak',
 'PPG_HRV_MFDFA_alpha1_Width',
 'PPG_HRV_MFDFA_alpha2_Asymmetry',
 'PPG_HRV_MFDFA_alpha2_Delta',
 'PPG_HRV_MFDFA_alpha2_Fluctuation',
 'PPG_HRV_MFDFA_alpha2_Increment',
 'PPG_HRV_MFDFA_alpha2_Max',
 'PPG_HRV_MFDFA_alpha2_Mean',
 'PPG_HRV_MFDFA_alpha2_Peak',
 'PPG_HRV_MFDFA_alpha2_Width',
 'PPG_HRV_MSEn',
 'PPG_HRV_MadNN',
 'PPG_HRV_MaxNN',
 'PPG_HRV_MeanNN',
 'PPG_HRV_MedianNN',
 'PPG_HRV_MinNN',
 'PPG_HRV_PAS',
 'PPG_HRV_PI',
 'PPG_HRV_PIP',
 'PPG_HRV_PSS',
 'PPG_HRV_Prc20NN',
 'PPG_HRV_Prc80NN',
 'PPG_HRV_RCMSEn',
 'PPG_HRV_RMSSD',
 'PPG_HRV_S',
 'PPG_HRV_SD1',
 'PPG_HRV_SD1SD2',
 'PPG_HRV_SD1a',
 'PPG_HRV_SD1d',
 'PPG_HRV_SD2',
 'PPG_HRV_SD2a',
 'PPG_HRV_SD2d',
 'PPG_HRV_SDANN1',
 'PPG_HRV_SDANN2',
 'PPG_HRV_SDANN5',
 'PPG_HRV_SDNN',
 'PPG_HRV_SDNNI1',
 'PPG_HRV_SDNNI2',
 'PPG_HRV_SDNNI5',
 'PPG_HRV_SDNNa',
 'PPG_HRV_SDNNd',
 'PPG_HRV_SDRMSSD',
 'PPG_HRV_SDSD',
 'PPG_HRV_SI',
 'PPG_HRV_SampEn',
 'PPG_HRV_ShanEn',
 'PPG_HRV_TINN',
 'PPG_HRV_TP',
 'PPG_HRV_ULF',
 'PPG_HRV_VHF',
 'PPG_HRV_VLF',
 'PPG_HRV_pNN20',
 'PPG_HRV_pNN50',
 
]

CLASS_NAMES = {
    0: 'Airway & Respiration',
    1: 'Bleeding Control',
    2: 'Blood Products',
    3: 'Chest Decompression',
    4: 'Neurologic Products & Procedures',
    5: 'Damage Control Procedures'
}

NUM_SEGMENTS_AFTER = 4


# ============================================================
# Data loading
# ============================================================
def _parse_scalar_value(val):
    """Parse a single value to float, handling '<', '>' prefixes and arrays."""
    if val is None:
        return np.nan
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val)
    if isinstance(val, str):
        if val.startswith('<'):
            try:
                return float(val[1:]) - 0.0001
            except ValueError:
                return np.nan
        elif val.startswith('>'):
            try:
                return float(val[1:]) + 0.0001
            except ValueError:
                return np.nan
        else:
            try:
                return float(val)
            except ValueError:
                return np.nan
    if isinstance(val, (list, np.ndarray)):
        if len(val) > 0:
            try:
                arr = np.array(val, dtype=float)
                non_nan_indices = np.where(~np.isnan(arr))[0]
                if len(non_nan_indices) > 0:
                    return float(arr[non_nan_indices[-1]])
            except (ValueError, TypeError):
                pass
        return np.nan
    return np.nan


def compute_valid_indices(df, num_segments_after=4):
    """Filter to segments up to num_segments_after past the last LSI event."""
    valid_indices = []
    for studyid, group in df.groupby('studyid'):
        group = group.sort_values('segmentid')
        label_list = group['label'].tolist()

        processed_labels = []
        for lbl in label_list:
            if lbl is None:
                processed_labels.append([0, 0, 0, 0, 0, 0, 1])
            elif isinstance(lbl, (list, np.ndarray)):
                processed_labels.append(lbl)
            else:
                processed_labels.append([0, 0, 0, 0, 0, 0, 1])

        labels = np.array(processed_labels)
        if labels.ndim == 1:
            labels = labels.reshape(1, -1)

        segments = group['segmentid'].values
        original_indices = group.index.values
        any_lsi = labels[:, :6].sum(axis=1) > 0

        if any_lsi.any():
            last_lsi_idx = np.where(any_lsi)[0][-1]
            last_lsi_segment = segments[last_lsi_idx]
            keep_mask = segments <= (last_lsi_segment + num_segments_after)
            valid_indices.extend(original_indices[keep_mask])
        else:
            valid_indices.extend(original_indices)

    return valid_indices


def load_parquet_data(parquet_path, filter_by_lsi=True):
    """
    Load data from parquet file.

    Returns:
        data_dict: dict of feature_name -> np.array
        labels: np.array (n_samples, 7) or None if 'label' column missing
        patient_ids: np.array of study IDs, or None if 'studyid' column missing
    """
    df = pd.read_parquet(parquet_path)
    print(f"  Loaded {len(df)} samples from {parquet_path}")

    if filter_by_lsi and 'label' in df.columns and 'studyid' in df.columns:
        valid_indices = compute_valid_indices(df, NUM_SEGMENTS_AFTER)
        df = df.loc[valid_indices].reset_index(drop=True)
        print(f"  After LSI filtering: {len(df)} samples")

    # Extract features
    data_dict = {}
    for c in ALL_FEATURES:
        if c in df.columns:
            col = df[c]
            if col.dtype == object or col.dtype == 'O':
                data_dict[c] = np.array([_parse_scalar_value(v) for v in col.values], dtype=np.float64)
            else:
                data_dict[c] = col.to_numpy(dtype=np.float64, na_value=np.nan)
        else:
            data_dict[c] = np.full(len(df), np.nan, dtype=np.float64)

    # Extract labels if available
    labels = None
    if 'label' in df.columns:
        labels = np.stack(df['label'].apply(
            lambda x: np.array(x, dtype=np.float64) if x is not None else np.zeros(7, dtype=np.float64)
        ).values)

    # Extract patient IDs if available
    patient_ids = df['studyid'].values if 'studyid' in df.columns else None

    return data_dict, labels, patient_ids


# ============================================================
# Model loading
# ============================================================
def load_models(model_dir):
    """
    Load all saved artifacts from a fold directory.

    Returns:
        models: dict of class_idx -> RF model
        feature_info: dict with 'feature_names' and 'col_means'
        thresholds: np.array of shape (6,)
        clip_bounds: list of (lower, upper) or None
    """
    # Load 6 class models
    models = {}
    for class_idx in range(6):
        path = os.path.join(model_dir, f'rf_class_{class_idx}.joblib')
        if os.path.exists(path):
            models[class_idx] = joblib.load(path)
            print(f"  Loaded model for class {class_idx} ({CLASS_NAMES[class_idx]})")
        else:
            print(f"  WARNING: Model not found for class {class_idx}: {path}")

    # Load feature info
    feature_info = np.load(
        os.path.join(model_dir, 'feature_info.npy'), allow_pickle=True
    ).item()
    print(f"  Feature count: {len(feature_info['feature_names'])}")

    # Load thresholds
    thresholds = np.load(os.path.join(model_dir, 'thresholds.npy'))
    print(f"  Thresholds: {[f'{t:.2f}' for t in thresholds]}")

    # Load clip_bounds if available
    clip_path = os.path.join(model_dir, 'clip_bounds.npy')
    if os.path.exists(clip_path):
        saved = np.load(clip_path, allow_pickle=True).item()
        clip_bounds = saved['clip_bounds']
        col_means = saved['col_means']
        print(f"  Loaded clip_bounds ({len(clip_bounds)} features)")
    else:
        clip_bounds = None
        col_means = feature_info['col_means']
        print("  WARNING: clip_bounds.npy not found. Using col_means from feature_info only.")
        print("           Run inference_fold2.py first to generate clip_bounds.npy,")
        print("           or predictions may differ slightly from training-time evaluation.")

    return models, feature_info, thresholds, clip_bounds, col_means


# ============================================================
# Feature extraction & preprocessing
# ============================================================
def extract_and_preprocess(data_dict, feature_names, clip_bounds, col_means):
    """
    Extract features, apply augmentation, clip, and impute.

    Args:
        data_dict: dict of feature_name -> np.array (raw values)
        feature_names: list of feature names from feature_info (includes _sq, _sqrt)
        clip_bounds: list of (lower, upper) tuples, or None
        col_means: np.array for imputation

    Returns:
        X: np.array (n_samples, n_features) preprocessed feature matrix
    """
    # Get base feature names (exclude augmented)
    base_features = [f for f in feature_names if not f.endswith(('_sq', '_sqrt'))]

    # Build base matrix
    X_base = np.column_stack([data_dict.get(f, np.full(len(list(data_dict.values())[0]), np.nan)) for f in base_features])

    # Augment: square + sqrt
    has_augmentation = any(f.endswith('_sq') for f in feature_names)
    if has_augmentation:
        X_sq = np.square(X_base)
        X_sqrt = np.sqrt(np.abs(X_base))
        X = np.concatenate([X_base, X_sq, X_sqrt], axis=1)
    else:
        X = X_base

    # Preprocess
    X = np.where(np.isinf(X), np.nan, X)

    if clip_bounds is not None:
        for col_idx, (lower, upper) in enumerate(clip_bounds):
            X[:, col_idx] = np.clip(X[:, col_idx], lower, upper)

    X = np.where(np.isnan(X), col_means, X)
    X = np.where(np.isinf(X), 0.0, X)

    return X


# ============================================================
# Prediction
# ============================================================
def predict(X, models, thresholds):
    """
    Run 6 binary classifiers on preprocessed features.

    Returns:
        predictions: np.array (n_samples, 6) binary
        probabilities: np.array (n_samples, 6) float
    """
    n_samples = X.shape[0]
    all_preds = np.zeros((n_samples, 6))
    all_proba = np.zeros((n_samples, 6))

    for class_idx in range(6):
        if class_idx not in models:
            print(f"  WARNING: No model for class {class_idx}, skipping")
            continue

        proba = models[class_idx].predict_proba(X)[:, 1]
        all_proba[:, class_idx] = proba
        all_preds[:, class_idx] = (proba >= thresholds[class_idx]).astype(int)

    return all_preds, all_proba


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='RF inference using saved fold models')
    parser.add_argument('--model_dir', type=str, required=True,
                        help='Path to fold directory (e.g. checkpoints_rf_all_features/<ts>/models/fold_2)')
    parser.add_argument('--data_path', type=str, required=True,
                        help='Path to parquet file for inference')
    parser.add_argument('--output_path', type=str, default=None,
                        help='Path to save predictions CSV (optional)')
    parser.add_argument('--no_filter', action='store_true',
                        help='Skip LSI-based segment filtering')
    parser.add_argument('--eval', action='store_true',
                        help='Evaluate against labels if available in the data')
    args = parser.parse_args()

    print("=" * 60)
    print("RF Inference (all_features_mp)")
    print("=" * 60)

    # --- Load models ---
    print(f"\n[1] Loading models from {args.model_dir}...")
    models, feature_info, thresholds, clip_bounds, col_means = load_models(args.model_dir)

    # --- Load data ---
    print(f"\n[2] Loading data from {args.data_path}...")
    data_dict, labels, patient_ids = load_parquet_data(
        args.data_path, filter_by_lsi=(not args.no_filter)
    )

    # --- Extract & preprocess ---
    print("\n[3] Extracting and preprocessing features...")
    X = extract_and_preprocess(data_dict, feature_info['feature_names'], clip_bounds, col_means)
    print(f"  Feature matrix shape: {X.shape}")

    # --- Predict ---
    print("\n[4] Predicting...")
    predictions, probabilities = predict(X, models, thresholds)

    # --- Results ---
    print("\n" + "=" * 60)
    print("Predictions Summary")
    print("=" * 60)
    for class_idx in range(6):
        n_pos = int(predictions[:, class_idx].sum())
        n_total = len(predictions)
        print(f"  Class {class_idx} ({CLASS_NAMES[class_idx]}): {n_pos}/{n_total} predicted positive")

    # --- Evaluate (optional) ---
    if args.eval and labels is not None:
        from sklearn.metrics import balanced_accuracy_score, recall_score, precision_score, f1_score
        y_true = labels[:, :6]

        print("\n" + "=" * 60)
        print("Evaluation")
        print("=" * 60)
        for class_idx in range(6):
            ba = balanced_accuracy_score(y_true[:, class_idx], predictions[:, class_idx])
            rec = recall_score(y_true[:, class_idx], predictions[:, class_idx], zero_division=0)
            prec = precision_score(y_true[:, class_idx], predictions[:, class_idx], zero_division=0)
            f1 = f1_score(y_true[:, class_idx], predictions[:, class_idx], zero_division=0)
            print(f"  Class {class_idx} ({CLASS_NAMES[class_idx]}): "
                  f"BA={ba:.4f}  Recall={rec:.4f}  Precision={prec:.4f}  F1={f1:.4f}")

    # --- Save (optional) ---
    if args.output_path:
        out_df = pd.DataFrame()
        if patient_ids is not None:
            out_df['studyid'] = patient_ids
        for class_idx in range(6):
            out_df[f'pred_{class_idx}'] = predictions[:, class_idx].astype(int)
            out_df[f'proba_{class_idx}'] = probabilities[:, class_idx]
        out_df.to_csv(args.output_path, index=False)
        print(f"\nPredictions saved to {args.output_path}")

    # --- Save summary ---
    summary_path = os.path.join(os.path.dirname(args.output_path) or '.', 'summary.txt')
    with open(summary_path, 'w') as f:
        f.write(f"Inference run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model dir: {args.model_dir}\n")
        f.write(f"Data path: {args.data_path}\n")
        f.write(f"Output path: {args.output_path}\n")
        f.write(f"LSI filter: {not args.no_filter}\n")
        f.write(f"Eval: {args.eval}\n")
        f.write("=" * 60 + "\n\n")
        f.write(''.join(output_log))
    print(f"\nSummary saved to {summary_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()



