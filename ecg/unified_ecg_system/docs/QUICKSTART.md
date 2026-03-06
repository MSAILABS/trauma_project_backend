# Quick Start Guide

## Installation (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements_unified.txt
```

### 2. Verify Installation
```bash
python -c "import PyQt5, pyqtgraph, numpy, scipy, librosa; print('✓ All dependencies installed')"
```

## First Run

### Option A: Test with Sample File

If you have existing ECG/PPG files:

```bash
# Copy your data files
cp your_data.ecg data/test.ecg
cp your_data.ppg data/test.ppg

# Run viewer
python main_unified.py --file data/test --no-backend
```

### Option B: Stream from HealthyPi

1. Connect HealthyPi 5 device via USB
2. Check the COM port (Device Manager on Windows)
3. Run:

```bash
# Record for 30 seconds and display
python main_unified.py --stream --duration 30 --port COM5
```

## Common Tasks

### Display ECG/PPG Files Only (No Processing)
```bash
python main_unified.py --file path/to/data --no-backend --no-viewer
```

### Send Data to Backend
```bash
python main_unified.py --file path/to/data
```

### Use Custom Serial Port
```bash
python main_unified.py --stream --port COM3 --duration 30
```

### Process with AI Model
```bash
python main_unified.py --file path/to/data --model ./model_directory
```

### Export Displayed Data
In the viewer window, click "Export Data" button to save to:
- `exported_ecg.txt`
- `exported_ppg.txt`

## File Format

Create test files as simple text:

**test.ecg**
```
-100
-105
-102
-98
...
```

**test.ppg**
```
8400
8420
8410
8430
...
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'PyQt5'"
```bash
pip install PyQt5
```

### "Serial port not found"
- Check device is connected
- Get correct port: `python -m serial.tools.list_ports`
- Use `--port` flag

### "No data collected"
- Increase `--duration` (try 60 seconds)
- Check serial connection
- Verify baud rate matches device (usually 115200)

### Viewer window won't open
- Ensure you're not using `--no-viewer`
- Check PyQt5 installation
- Run on a machine with display (SSH without X11 won't work)

## Next Steps

1. **Understand the Architecture**
   - Read `README_UNIFIED.md` for full documentation
   - Review source code in modules

2. **Customize for Your Needs**
   - Modify `signal_sender.py` for different processing
   - Extend `SignalLoader` for other file formats
   - Customize viewer in `signal_viewer_pyqt.py`

3. **Integrate with Backend**
   - Update API endpoints in `api.py` if needed
   - Configure authentication tokens
   - Test with `--model` flag

4. **Production Deployment**
   - Use batch scripts for multiple files
   - Set up scheduled processing
   - Monitor `ai_results.json` output

## Example Workflows

### Batch Processing Multiple Files
```bash
for file in data/*.txt; do
    echo "Processing $file"
    python main_unified.py --file "$file" --no-viewer
done
```

### Real-time Monitoring (Continuous)
```bash
# Keep streaming and processing
python main_unified.py --stream --port COM5 --duration 3600
```

### Debug Mode (Minimal Processing)
```bash
# Load file, show viewer, don't process
python main_unified.py --file data/test --no-backend --sampling-rate 500
```

## Getting Help

1. Check log output for error messages
2. Review specific module documentation:
   - `healthypi_lib.py` - Serial communication
   - `signal_loader.py` - Data loading
   - `signal_sender.py` - Processing
   - `signal_viewer_pyqt.py` - Visualization

3. Test components individually:
   ```python
   # Test file loading
   from signal_loader import SignalFactory
   loader = SignalFactory.create('file', base_path='data/test')
   ecg, ppg = loader.load()
   ```

## Performance Tips

1. **Faster Processing**
   - Use `--no-backend` to skip HTTP upload
   - Reduce `--duration` for quick tests

2. **Better Visualization**
   - Increase time window in viewer (spinbox)
   - Use "Smooth Signal" checkbox (requires neurokit2)
   - Adjust plot scaling

3. **Stable Streaming**
   - Keep USB cable short and shielded
   - Close other serial applications
   - Use dedicated USB port (not hub)

## API Usage Examples

### Load and Process in Python
```python
from signal_loader import SignalFactory
from signal_sender import SignalProcessor

# Load file
loader = SignalFactory.create('file', base_path='mydata')
ecg, ppg = loader.load()

# Process
processor = SignalProcessor(sampling_rate=500)
results = processor.process_signals(
    {'I': ecg, 'II': ppg, 'III': ecg},
    send_to_backend=True
)
```

### Stream in Real-time
```python
from healthypi_lib import HealthyPiStreamWithQueue
import time

stream = HealthyPiStreamWithQueue(port='COM5')
stream.start()

# Collect for 10 seconds
time.sleep(10)

ecg_data = stream.get_all_ecg()
ppg_data = stream.get_all_ppg()

stream.stop()
stream.disconnect()
```

### Display Data
```python
from signal_viewer_pyqt import SignalViewer
from PyQt5.QtWidgets import QApplication

app = QApplication([])
viewer = SignalViewer(ecg_data=ecg, ppg_data=ppg)
viewer.show()
app.exec_()
```

---

**Last Updated**: 2026-02-14
**Version**: 1.0
