# Usage Examples

## Installation

```bash
# Navigate to project directory
cd c:\msai\ecg

# Install dependencies
pip install -r requirements_unified.txt

# Verify installation
python test_system.py
```

## Example 1: View Existing ECG/PPG Files

**Scenario**: You have ECG and PPG data saved in files

```bash
# Basic usage
python main_unified.py --file mydata

# Where:
# - mydata.ecg contains raw ECG values
# - mydata.ppg contains raw PPG values
```

**Expected Output**:
```
============================================================
File Mode: mydata
============================================================

✓ Loaded 2500 ECG samples from mydata.ecg
✓ Loaded 2500 PPG samples from mydata.ppg

📊 Signal statistics:
   Min value: -2150
   Max absolute value: 3200

✓ Processing complete (1 parts)

[PyQt Viewer opens with plots]
```

## Example 2: Stream from HealthyPi Device

**Scenario**: You want to collect real-time data from HealthyPi 5

```bash
# Simple streaming (30 seconds)
python main_unified.py --stream --duration 30

# Custom serial port
python main_unified.py --stream --port COM3 --duration 60

# Different sampling rate
python main_unified.py --stream --duration 10 --sampling-rate 500
```

**Expected Output**:
```
============================================================
Stream Mode: COM5
============================================================

✓ Connected to COM5 at 115200 baud
✓ Stream reader started
✓ Connected to stream on COM5
✓ Recording ECG/PPG data (duration: 30s)

✓ Stream stopped. Collected 15000 ECG and 15000 PPG samples

📊 Signal statistics:
   Min value: -2100
   Max absolute value: 3150

✓ Processing complete (6 parts)

[PyQt Viewer opens]
```

## Example 3: Process with AI Model

**Scenario**: You want AI-based classification of your ECG/PPG

```bash
# File mode with AI
python main_unified.py --file mydata \
  --model ./demo_rf_model/demo_rf_model/2026-01-29_10-06-37/models/fold_2

# Stream mode with AI
python main_unified.py --stream \
  --duration 30 \
  --model ./rf_model/fold_2 \
  --port COM5
```

**Expected Output**:
```
✓ AI model loaded
✓ Sent part 1 to backend
--- AI Inference Complete ---
{
    'lsi_description': 'File: mydata (Part 1)',
    'lsi_sampling_rate': 500,
    'lsi_Damage Control Procedures': 0.02,
    'lsi_Bleeding Control': 0.95,
    ...
}
✓ Saved 1 results to ai_results.json
```

## Example 4: Process Without Backend

**Scenario**: Analyze data locally without sending to server

```bash
# Don't send to backend
python main_unified.py --file mydata --no-backend

# Stream without backend
python main_unified.py --stream --duration 20 --no-backend
```

**Result**: Processes normally but skips HTTP transmission to backend

## Example 5: View Data Only (No Processing)

**Scenario**: Just want to visualize the signals

```bash
# File visualization only
python main_unified.py --file mydata --no-backend

# View with smoothing
# In viewer window: check "Smooth Signal (ECG Clean)"
```

## Example 6: Batch Processing Multiple Files

**Scenario**: Process multiple patient files

### Windows Batch Script:
```batch
@echo off
for %%f in (data\*.txt) do (
    echo Processing %%f
    python main_unified.py --file data\%%~nf --no-viewer
    timeout /t 5 > nul
)
```

### Linux/Mac Bash Script:
```bash
#!/bin/bash
for file in data/*.txt; do
    echo "Processing $file"
    python main_unified.py --file "${file%.txt}" --no-viewer
    sleep 5
done
```

## Example 7: Export Processed Data

**Scenario**: Save the processed signals for external analysis

```bash
# Process and display
python main_unified.py --file mydata

# In the PyQt window:
# Click "Export Data" button
# Files created:
#   - exported_ecg.txt
#   - exported_ppg.txt
```

## Example 8: Debug Mode

**Scenario**: Test without viewer for headless operation

```bash
# File mode, no viewer, no backend
python main_unified.py --file mydata --no-viewer --no-backend

# Just show what would be processed
python main_unified.py --file mydata --no-viewer
```

## Example 9: Python Script Usage

**Scenario**: Integrate into your own Python application

```python
from signal_loader import SignalFactory
from signal_sender import SignalProcessor
from signal_viewer_pyqt import SignalViewer
from PyQt5.QtWidgets import QApplication
import sys

# Load data
loader = SignalFactory.create('file', base_path='mydata')
ecg, ppg = loader.load()

# Process
processor = SignalProcessor(sampling_rate=500)
results = processor.process_signals(
    {'I': ecg, 'II': ppg, 'III': ecg},
    description="Custom App",
    send_to_backend=False
)

# Display
app = QApplication(sys.argv)
viewer = SignalViewer(ecg_data=ecg, ppg_data=ppg, sampling_rate=500)
viewer.show()
sys.exit(app.exec_())
```

## Example 10: Stream and Save to File

**Scenario**: Collect stream data and save for later analysis

```python
from signal_loader import SignalFactory

# Record from stream
loader = SignalFactory.create('stream', port='COM5', duration=30)
ecg, ppg = loader.load()

# Save to files
with open('collected_data.ecg', 'w') as f:
    for val in ecg:
        f.write(f"{val}\n")

with open('collected_data.ppg', 'w') as f:
    for val in ppg:
        f.write(f"{val}\n")

print("✓ Saved to collected_data.ecg and collected_data.ppg")

# Later: process the saved data
# python main_unified.py --file collected_data
```

## Example 11: Custom Signal Processing

**Scenario**: Add your own processing step

```python
from signal_loader import SignalFactory
from signal_sender import SignalProcessor, SignalNormalizer
import numpy as np

# Load
loader = SignalFactory.create('file', base_path='mydata')
ecg, ppg = loader.load()

# Normalize
signals = {'I': ecg, 'II': ppg, 'III': ecg}
normalized, scale, stats = SignalNormalizer.normalize_signals(signals)

# Custom processing
for channel_name, signal in normalized.items():
    # Your custom algorithm here
    mean_val = np.mean(signal)
    std_val = np.std(signal)
    print(f"{channel_name}: mean={mean_val:.3f}, std={std_val:.3f}")

# Process normally
processor = SignalProcessor(sampling_rate=500)
results = processor.process_signals(signals, send_to_backend=False)
```

## Example 12: Continuous Streaming Loop

**Scenario**: Monitor device continuously

```python
from signal_loader import StreamSignalLoader
import time

loader = StreamSignalLoader(port='COM5')
loader.stream.start()

try:
    # Collect for 1 minute
    loader.collect_for_duration(60)
    
    print(f"Collected {len(loader.ecg_data)} ECG samples")
    print(f"Collected {len(loader.ppg_data)} PPG samples")
    
finally:
    loader.stop()
```

## Example 13: Real-time Viewer with File Data

**Scenario**: View file data with real-time update simulation

```python
from signal_loader import FileSignalLoader
from signal_viewer_pyqt import SignalViewer
from PyQt5.QtWidgets import QApplication
import sys

# Load once
loader = FileSignalLoader('mydata')
ecg, ppg = loader.load()

# Display with viewer
app = QApplication(sys.argv)
viewer = SignalViewer(
    ecg_data=ecg,
    ppg_data=ppg,
    sampling_rate=500
)
viewer.show()

# Try controls:
# - Change "Show last: X seconds"
# - Check "Smooth Signal"
# - Click "Reset Display"
# - Click "Export Data"

sys.exit(app.exec_())
```

## Example 14: Compare Normalization Factors

**Scenario**: Check how signals are normalized

```python
from signal_loader import FileSignalLoader
from signal_sender import SignalNormalizer

# Load
loader = FileSignalLoader('mydata')
ecg, ppg = loader.load()

# Create signals dict
signals = {'ECG': ecg, 'PPG': ppg}

# Get normalization info
normalized, scale, stats = SignalNormalizer.normalize_signals(signals)

print(f"Original ECG range: {stats['min_value']} to {stats['max_absolute_value']}")
print(f"Scale factor: {scale}")
print(f"Normalized ECG range: {min(normalized['ECG'])} to {max(normalized['ECG'])}")
```

## Example 15: Error Handling

**Scenario**: Robust error handling in scripts

```python
import sys
from signal_loader import SignalFactory

try:
    # Try to load file
    loader = SignalFactory.create('file', base_path='mydata')
    ecg, ppg = loader.load()
    
except FileNotFoundError as e:
    print(f"✗ File not found: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

else:
    print("✓ Data loaded successfully")
    # Process...
```

## Performance Tips

### Fast Processing (Skip Visualization)
```bash
python main_unified.py --file mydata --no-viewer --no-backend
```

### High-Quality Streaming
```bash
# Record longer and process without interruption
python main_unified.py --stream --duration 600 --port COM5
```

### Parallel Batch Processing
```bash
# Process multiple files in parallel (PowerShell)
1..10 | ForEach-Object {
    Start-Job -ScriptBlock {
        python main_unified.py --file "data\patient_$_" --no-viewer
    }
}
```

## Troubleshooting Examples

### Issue: "File not found"
```bash
# Check files exist
dir *.ecg
dir *.ppg

# Use correct path
python main_unified.py --file c:\data\mydata

# Verify file content
type mydata.ecg | head -10
```

### Issue: "Serial port not found"
```bash
# List available ports
python -m serial.tools.list_ports

# Use correct port
python main_unified.py --stream --port COM3

# Check baud rate (usually 115200)
```

### Issue: "Viewer won't open"
```bash
# Test PyQt5
python -c "from PyQt5.QtWidgets import QApplication; print('✓ PyQt5 works')"

# Run without viewer
python main_unified.py --file mydata --no-viewer

# Check display available (SSH without X11 won't work)
```

---

For more information, see:
- `README_UNIFIED.md` - Complete documentation
- `QUICKSTART.md` - Quick reference
- `ARCHITECTURE.md` - System design
- Source code docstrings - Detailed API docs
