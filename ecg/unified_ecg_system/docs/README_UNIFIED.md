# ECG/PPG Signal Processing System

A unified signal processing system with support for both stream mode (HealthyPi 5) and file mode, with real-time PyQt viewer and backend integration.

## Features

- **Dual Mode Operation**:
  - **Stream Mode**: Real-time ECG/PPG from HealthyPi 5 via serial
  - **File Mode**: Load pre-recorded ECG/PPG data from files

- **Signal Processing**:
  - Automatic normalization to [-1, 1] range
  - FFT, MFCC, and Spectrogram computation
  - AI-based classification (optional, requires model)

- **Real-time Visualization**:
  - PyQt5-based viewer with live updates
  - Signal smoothing with NeuroKit2
  - Smart y-axis auto-scaling
  - Statistics display

- **Backend Integration**:
  - Automatic chunking (5-second windows)
  - HTTP upload to backend API
  - Result tracking and export

## Module Structure

### Core Libraries

#### `healthypi_lib.py`
Refactored HealthyPi serial communication library:
- `HealthyPiStream`: Low-level stream decoder
- `HealthyPiStreamWithQueue`: Stream with built-in buffering
- State machine for protocol parsing
- Callback-based event system

```python
from healthypi_lib import HealthyPiStreamWithQueue

stream = HealthyPiStreamWithQueue(port='COM5')
stream.start()
ecg = stream.get_ecg()  # Get single value
ppg = stream.get_ppg()  # Get single value
all_ecg = stream.get_all_ecg()  # Get all buffered values
stream.stop()
```

#### `signal_loader.py`
Signal loading abstraction:
- `SignalLoader`: Base loader class
- `FileSignalLoader`: Load from .ecg/.ppg files
- `StreamSignalLoader`: Load from HealthyPi stream
- `SignalFactory`: Factory pattern for creating loaders

```python
from signal_loader import SignalFactory

# File mode
loader = SignalFactory.create('file', base_path='mydata')
ecg, ppg = loader.load()

# Stream mode
loader = SignalFactory.create('stream', port='COM5', duration=10)
ecg, ppg = loader.load()
```

#### `signal_sender.py`
Signal processing and transmission:
- `SignalNormalizer`: Normalize signals to [-1, 1]
- `SignalProcessor`: Process signals in chunks, compute FFT/MFCC/Spectrogram
- AI model integration
- Backend API communication

```python
from signal_sender import SignalProcessor

processor = SignalProcessor(sampling_rate=500, 
                           model_dir='./model')
results = processor.process_signals(
    signals={'I': ecg, 'II': ppg},
    description='Test',
    send_to_backend=True
)
```

#### `signal_viewer_pyqt.py`
Real-time visualization:
- `SignalViewer`: PyQt5 main window
- Live plotting with pyqtgraph
- Data smoothing with NeuroKit2
- Export functionality

## Installation

### Requirements

```bash
pip install PyQt5 pyqtgraph numpy scipy librosa
pip install neurokit2  # Optional, for ECG smoothing
```

### Optional Dependencies

For full functionality:
- AI Model support: `AICode`, `api` modules from your backend
- Signal smoothing: `neurokit2`

## Usage

### Command Line

#### File Mode
```bash
# Basic usage - load and display
python main_unified.py --file path/to/data

# Process with backend
python main_unified.py --file data/patient_001 --sampling-rate 500

# With AI model
python main_unified.py --file data/ecg \
  --model ./demo_rf_model/2026-01-29_10-06-37/models/fold_2

# Don't send to backend, just show viewer
python main_unified.py --file data/ecg --no-backend --no-viewer
```

#### Stream Mode
```bash
# Basic streaming for 30 seconds
python main_unified.py --stream --duration 30

# Custom port
python main_unified.py --stream --port /dev/ttyUSB0 --duration 60

# Without backend
python main_unified.py --stream --no-backend --duration 20

# With AI processing
python main_unified.py --stream \
  --port COM5 \
  --duration 10 \
  --model ./demo_rf_model/model_path
```

#### Options

```
--file PATH              Load from files (PATH.ecg, PATH.ppg)
--stream                 Load from HealthyPi stream
--sampling-rate RATE     Sampling rate in Hz (default: 500)
--no-backend             Skip backend transmission
--model PATH             Path to AI model directory
--no-viewer              Skip PyQt viewer
--port PORT              Serial port (default: COM5)
--duration SECONDS       Stream duration (default: continuous)
```

### Python API

#### Load from File
```python
from signal_loader import SignalFactory

loader = SignalFactory.create('file', base_path='ecg_data')
ecg, ppg = loader.load()

stats = loader.get_stats()
print(f"ECG samples: {stats['ecg']['count']}")
print(f"ECG range: [{stats['ecg']['min']}, {stats['ecg']['max']}]")
```

#### Stream from HealthyPi
```python
from signal_loader import SignalFactory

loader = SignalFactory.create('stream', port='COM5', duration=10)
ecg, ppg = loader.load()

print(f"Collected {len(ecg)} ECG samples")
```

#### Process Signals
```python
from signal_sender import SignalProcessor, SignalNormalizer

# Normalize
normalized, scale, stats = SignalNormalizer.normalize_signals({
    'I': ecg,
    'II': ppg,
})

# Process
processor = SignalProcessor(sampling_rate=500)
results = processor.process_signals(
    {'I': ecg, 'II': ppg},
    description="Patient test",
    send_to_backend=False
)
```

#### Real-time Viewer
```python
from signal_viewer_pyqt import SignalViewer
from PyQt5.QtWidgets import QApplication

app = QApplication([])
viewer = SignalViewer(ecg_data=ecg, ppg_data=ppg, sampling_rate=500)
viewer.show()
app.exec_()
```

## File Formats

### Input Files (File Mode)

**`<name>.ecg`** - ECG data
```
-105
-98
-102
...
```

**`<name>.ppg`** - PPG data
```
8420
8425
8418
...
```

Both files should have one value per line, matching sample count.

### Output Files

**`ai_results.json`** - AI processing results
```json
[
  {
    "part": 1,
    "description": "Part 1",
    "ai_prediction": 2,
    "ai_probabilities": [0.01, 0.02, 0.95, 0.02, 0.0, 0.0]
  },
  ...
]
```

**`exported_ecg.txt`**, **`exported_ppg.txt`** - Exported signal data

## Configuration

### Sampling Rate
Default: 500 Hz (HealthyPi native rate)
Change with `--sampling-rate` flag

### Chunk Size
Default: 5 seconds = 2500 samples
Modify in `SignalProcessor.__init__`

### Serial Port
Default: COM5
Change with `--port` flag or in code

## Architecture

```
┌─────────────────────────────────────────────┐
│         Command Line Interface              │
│         (main_unified.py)                   │
└────────────┬────────────────────────────────┘
             │
     ┌───────┴────────┐
     │                │
┌────▼────────┐  ┌───▼──────────┐
│ File Mode   │  │ Stream Mode  │
│ (CSV/TXT)   │  │ (HealthyPi)  │
└────┬────────┘  └───┬──────────┘
     │                │
     └───────┬────────┘
             │
     ┌───────▼─────────────┐
     │  Signal Loader      │
     │ (signal_loader.py)  │
     └───────┬─────────────┘
             │
     ┌───────▼──────────────┐
     │ Signal Processing    │
     │(signal_sender.py)    │
     │- Normalize           │
     │- FFT/MFCC/Spec       │
     │- AI Model            │
     └───────┬──────────────┘
             │
    ┌────────┴──────────┐
    │                   │
┌───▼─────────┐  ┌─────▼────────┐
│ PyQt Viewer │  │ Backend API  │
│ (display)   │  │ (HTTP POST)  │
└─────────────┘  └──────────────┘
```

## Error Handling

### File Not Found
```
✗ Files not found: ecg_data.ecg or ecg_data.ppg
```
Solution: Ensure files exist and use correct base path

### Serial Connection Failed
```
✗ Failed to connect to COM5
```
Solution: Check device is connected, use correct port

### AI Model Not Available
```
⚠ Failed to load AI model: ...
```
Solution: Model is optional, processing will continue without it

### Backend Connection Failed
```
⚠ Backend authorization failed: ...
```
Solution: Use `--no-backend` flag to skip transmission

## Performance

- **File Loading**: ~100K samples/sec
- **Streaming**: 500 Hz native (HealthyPi rate)
- **Viewer Update**: 500ms interval
- **Backend Upload**: ~1s per 5-second chunk

## Troubleshooting

### Viewer Doesn't Show
```bash
# Check dependencies
pip install PyQt5 pyqtgraph

# Run with no-viewer to test processing
python main_unified.py --file data --no-viewer
```

### Stream Data Empty
```bash
# Check serial connection
# Try longer duration
python main_unified.py --stream --duration 30

# Monitor raw data
# Check COM port number
```

### Backend Upload Fails
```bash
# Try without backend
python main_unified.py --file data --no-backend

# Check API availability
# Verify token authentication
```

## Examples

### Complete Workflow: File Processing with Viewer
```bash
python main_unified.py --file data/patient_001 --sampling-rate 500
```

### Stream Recording with AI Classification
```bash
python main_unified.py --stream \
  --duration 60 \
  --model ./rf_model/fold_2 \
  --sampling-rate 500
```

### Batch Processing (No Display)
```bash
python main_unified.py --file data/batch_001 --no-viewer --no-backend
python main_unified.py --file data/batch_002 --no-viewer --no-backend
```

### Debug Mode (File, No Backend, With Viewer)
```bash
python main_unified.py --file test_data --no-backend
```

## License

Proprietary - MSAI Lab

## Support

For issues or questions, contact the development team.
