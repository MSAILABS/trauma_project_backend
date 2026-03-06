# System Architecture Diagrams

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INPUT (CLI)                             │
│  python main_unified.py --file data OR --stream --duration 30   │
└────────────────────────┬────────────────────────────────────────┘
                         │
           ┌─────────────┴──────────────┐
           │                            │
        FILE MODE                   STREAM MODE
           │                            │
    ┌──────▼─────────┐        ┌────────▼──────────┐
    │ FileSignalLoader│        │StreamSignalLoader │
    ├─ data.ecg      │        ├─ COM5/COM3        │
    ├─ data.ppg      │        ├─ HealthyPi device │
    └──────┬─────────┘        └────────┬──────────┘
           │                           │
           │  ecg_data, ppg_data       │
           │                           │
           └─────────────┬─────────────┘
                         │
           ┌─────────────▼──────────────┐
           │   Signal Normalization     │
           │  ([-1, 1] range)           │
           └─────────────┬──────────────┘
                         │
           ┌─────────────▼──────────────────┐
           │   Signal Processing (5s chunks)│
           ├─ FFT computation              │
           ├─ MFCC computation            │
           ├─ Spectrogram computation     │
           └─────────────┬──────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
   ┌────▼────────┐            ┌──────────▼───────┐
   │ AI Model    │            │ Backend API      │
   │ Processing  │            │ (HTTP POST)      │
   │ (optional)  │            │                  │
   └────┬────────┘            └──────────┬───────┘
        │                                │
        └────────────────┬───────────────┘
                         │
        ┌────────────────▼───────────────┐
        │    Results JSON File            │
        │  ai_results.json                │
        └─────────────────────────────────┘
        
        ┌────────────────────────────────┐
        │ PyQt5 Viewer (if not --no-viewer)
        │ - Display ECG/PPG              │
        │ - Real-time statistics         │
        │ - Signal smoothing             │
        │ - Data export                  │
        └────────────────────────────────┘
```

## Module Dependency Graph

```
main_unified.py (CLI Entry Point)
│
├─→ signal_loader.py
│   ├─→ healthypi_lib.py (for stream mode)
│   │   └─→ pyserial
│   └─→ os, pathlib
│
├─→ signal_sender.py
│   ├─→ signal_loader.py (for loaded signals)
│   ├─→ numpy, scipy, librosa
│   ├─→ AICode.py (optional, AI processing)
│   └─→ api.py (optional, backend)
│
├─→ signal_viewer_pyqt.py
│   ├─→ PyQt5
│   ├─→ pyqtgraph
│   ├─→ numpy
│   └─→ neurokit2 (optional, smoothing)
│
└─→ sys, os (standard library)


Individual Module Usage:

healthypi_lib.py (standalone)
├─→ serial
└─→ threading, queue

signal_loader.py (standalone)
├─→ os, pathlib
└─→ healthypi_lib.py (if stream mode)

signal_sender.py (standalone)
├─→ numpy, scipy, librosa
├─→ json, time
└─→ AICode.py, api.py (if AI/backend enabled)

signal_viewer_pyqt.py (standalone)
├─→ PyQt5, pyqtgraph
├─→ numpy
└─→ neurokit2 (optional)
```

## Class Hierarchy

```
SignalLoader (Abstract Base)
├── FileSignalLoader
│   └── load() → (ecg, ppg)
│   └── get_stats() → dict
│
└── StreamSignalLoader
    └── load() → (ecg, ppg)
    └── collect_for_duration(seconds)
    └── stop()

SignalFactory
└── create(mode: str, **kwargs) → SignalLoader

HealthyPiStream
└── State machine for serial parsing
└── Callbacks for events
└── connect(), disconnect()
└── start(), stop()

HealthyPiStreamWithQueue (extends HealthyPiStream)
└── Built-in queuing
└── get_ecg(), get_ppg()
└── get_all_ecg(), get_all_ppg()

SignalNormalizer
└── normalize_channel() → [float]
└── normalize_signals() → (dict, scale, stats)

SignalProcessor
├── process_signals(signals, description) → [results]
├── _save_results()
└── AI model integration

SignalViewer (QMainWindow)
├── UI components
├── Plotting (pyqtgraph)
├── Data processing
└── Export functionality
```

## State Machine: Serial Protocol

```
┌─────────────────────────────────────────────────────────────┐
│  HealthyPi Serial State Machine (ER3 Protocol)              │
└─────────────────────────────────────────────────────────────┘

State 0: INIT
  ├─ Receive byte 0x0A → State 1
  └─ Other → State 0

State 1: SOF1_FOUND
  ├─ Receive byte 0xFA → State 2
  └─ Other → State 0

State 2: SOF2_FOUND
  ├─ Receive length → State 3
  └─ Initialize counters

State 3: PktLen_FOUND (reading packet data)
  ├─ Count < OVERHEAD → Read header
  ├─ OVERHEAD <= Count < END → Read data
  │  └─ Extract ECG, PPG values
  └─ Count >= END
     ├─ Receive 0x0B → Extract & emit
     └─ Other → State 0 (error)

Processing ECG:
  Bytes[0-3] → ECG value (little-endian signed int)

Processing PPG:
  Bytes[9-12] → PPG IR value (little-endian signed int)
```

## Signal Processing Pipeline

```
Raw Signal (2500 samples, 5 seconds @ 500Hz)
│
├─→ Normalize [-1, 1]
│
├─→ FFT Analysis
│   ├─ rfft() → frequency spectrum
│   └─ rfftfreq() → frequency bins
│
├─→ MFCC (13 coefficients)
│   └─ librosa.feature.mfcc()
│
├─→ Spectrogram
│   ├─ scipy.signal.spectrogram()
│   ├─ Window: 0.5s (250 samples)
│   ├─ Overlap: 50% (125 samples)
│   └─ Convert to dB scale
│
└─→ AI Model (if available)
    ├─ Input: Raw signal
    └─ Output: Classification + Probabilities
```

## Timing Diagram

```
Time (seconds):
0          1          2          3          4          5
│──────────│──────────│──────────│──────────│──────────│
 ▁▁▁▁▁▁▁▁▁▁ ▁▁▁▁▁▁▁▁▁▁ ▁▁▁▁▁▁▁▁▁▁ ▁▁▁▁▁▁▁▁▁▁ ▁▁▁▁▁▁▁▁▁▁
 Serial streaming (500 Hz = 500 samples/sec)

Chunk 1: samples [0-2499]      (5 seconds)
│
├─→ Process (FFT/MFCC) 100ms
│
├─→ AI inference 50ms
│
├─→ Send to backend 1000ms
│
├─→ Wait 1 second (before next chunk)

Chunk 2: samples [2500-4999]   (5 seconds)
│
└─→ ...repeat...

Viewer updates every 500ms regardless of chunking
```

## Configuration Hierarchy

```
Defaults (in code)
    ↓
Command Line Args (--sampling-rate, --duration, etc.)
    ↓
Environment Variables (optional, future)
    ↓
Config File (optional, future)
    ↓
Runtime Parameters

Example:
python main_unified.py --file data --sampling-rate 500
                              │         │
                        Override    Override
                        default      default
```

## Error Handling Flow

```
User Input
    │
    ├─→ Validate arguments
    │
    ├─→ Check file existence
    │   └─ File not found → Print error, exit(1)
    │
    ├─→ Initialize loader
    │   └─ Connection error → Print error, exit(1)
    │
    ├─→ Load signals
    │   └─ Read error → Print error, exit(1)
    │
    ├─→ Process signals
    │   ├─ AI error → Print warning, continue
    │   └─ Backend error → Print warning, continue
    │
    └─→ Display viewer
        └─ PyQt error → Print warning, exit(0)

Success: exit(0)
Failure: exit(1)
```

## Storage Format

### Input Files
```
data/patient_001.ecg:
-105
-98
-102
...

data/patient_001.ppg:
8420
8425
8418
...
```

### Output: ai_results.json
```json
[
  {
    "part": 1,
    "description": "File: patient_001 (Part 1)",
    "ai_prediction": 2,
    "ai_probabilities": [0.01, 0.02, 0.95, 0.02, 0.0, 0.0]
  },
  ...
]
```

### Exported Data
```
exported_ecg.txt:
-0.534
-0.498
-0.512
...

exported_ppg.txt:
0.420
0.425
0.418
...
```

---

See README_UNIFIED.md for detailed documentation.
