"""
PyQt5 Signal Viewer - Display ECG and PPG data in real-time
Refactored from ecg_ppg_viewer_pyqt.py with support for pre-loaded data
"""
import sys
import os
from typing import List, Optional
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QSpinBox, QPushButton, QCheckBox, QComboBox
)
from PyQt5.QtCore import QTimer, Qt
import pyqtgraph as pg

try:
    import neurokit2 as nk
    HAS_NEUROKIT = True
except ImportError:
    HAS_NEUROKIT = False


class SignalViewer(QMainWindow):
    """Real-time signal viewer with pre-loaded or streaming data"""
    
    def __init__(self, ecg_data: Optional[List[float]] = None,
                 ppg_data: Optional[List[float]] = None,
                 sampling_rate: int = 500, parent=None):
        """
        Initialize viewer
        
        Args:
            ecg_data: Pre-loaded ECG data
            ppg_data: Pre-loaded PPG data
            sampling_rate: Sampling rate (Hz)
        """
        super().__init__(parent)
        self.sampling_rate = sampling_rate
        self.ecg_data = ecg_data or []
        self.ppg_data = ppg_data or []
        
        # UI Setup
        self.setup_ui()
        
        # Data tracking
        self.last_ecg_count = 0
        self.last_ppg_count = 0
        self.last_ecg_y_span = None
        self.last_ppg_y_span = None
        
        # Timer for updating plot
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(500)  # Update every 500ms
    
    def setup_ui(self):
        """Set up UI components"""
        self.setWindowTitle('Signal Viewer - ECG & PPG Data')
        self.setGeometry(50, 50, 1600, 1000)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        
        # Control panel
        control_layout = QHBoxLayout()
        
        # Time window control
        control_label = QLabel('Show last:')
        self.time_spinbox = QSpinBox()
        self.time_spinbox.setMinimum(1)
        self.time_spinbox.setMaximum(300)
        self.time_spinbox.setValue(10)
        self.time_spinbox.setSuffix(' seconds')
        self.time_spinbox.setStyleSheet("padding: 5px; font-weight: bold;")
        self.time_spinbox.valueChanged.connect(self.on_time_changed)
        
        # Smooth checkbox
        self.smooth_checkbox = QCheckBox('Smooth Signal (ECG Clean)')
        self.smooth_checkbox.setStyleSheet("padding: 5px; font-weight: bold;")
        self.smooth_checkbox.stateChanged.connect(self.update_plot)
        self.smooth_checkbox.setEnabled(HAS_NEUROKIT)
        
        if not HAS_NEUROKIT:
            self.smooth_checkbox.setToolTip("neurokit2 not installed")
        
        # Sample rate label
        self.srate_label = QLabel(f'Sample Rate: {self.sampling_rate} Hz')
        self.srate_label.setStyleSheet("padding: 5px; font-weight: bold;")
        
        # Reset button
        self.reset_button = QPushButton('Reset Display')
        self.reset_button.clicked.connect(self.reset_display)
        self.reset_button.setStyleSheet("padding: 5px;")
        
        # Export button
        self.export_button = QPushButton('Export Data')
        self.export_button.clicked.connect(self.export_data)
        self.export_button.setStyleSheet("padding: 5px;")
        
        control_layout.addWidget(control_label)
        control_layout.addWidget(self.time_spinbox)
        control_layout.addWidget(self.smooth_checkbox)
        control_layout.addWidget(self.srate_label)
        control_layout.addStretch()
        control_layout.addWidget(self.reset_button)
        control_layout.addWidget(self.export_button)
        
        # Plot area
        plot_area_layout = QVBoxLayout()
        
        # ECG plot
        self.ecg_plot_widget = pg.PlotWidget()
        self.ecg_plot_widget.setLabel('bottom', 'Time (samples)', **{'font-size': '14pt'})
        self.ecg_plot_widget.setLabel('left', 'ECG Value', **{'font-size': '14pt'})
        self.ecg_plot_widget.setTitle('ECG Data - Real-time Monitoring', size='16pt')
        self.ecg_plot_widget.setBackground('white')
        self.ecg_plot_widget.showGrid(True, True, alpha=0.5)
        self.ecg_plot_widget.plotItem.setClipToView(True)
        
        self.ecg_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='black', width=2))
        self.ecg_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='black', width=2))
        self.ecg_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='red', width=1))
        self.ecg_plot_widget.getAxis('left').setPen(pg.mkPen(color='red', width=1))
        
        self.ecg_curve = self.ecg_plot_widget.plot(pen=pg.mkPen(color='#0052CC', width=2, cosmetic=False))
        
        # PPG plot
        self.ppg_plot_widget = pg.PlotWidget()
        self.ppg_plot_widget.setLabel('bottom', 'Time (samples)', **{'font-size': '14pt'})
        self.ppg_plot_widget.setLabel('left', 'PPG Value', **{'font-size': '14pt'})
        self.ppg_plot_widget.setTitle('PPG Data - Real-time Monitoring', size='16pt')
        self.ppg_plot_widget.setBackground('white')
        self.ppg_plot_widget.showGrid(True, True, alpha=0.5)
        self.ppg_plot_widget.plotItem.setClipToView(True)
        
        self.ppg_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='black', width=2))
        self.ppg_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='black', width=2))
        self.ppg_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='red', width=1))
        self.ppg_plot_widget.getAxis('left').setPen(pg.mkPen(color='red', width=1))
        
        self.ppg_curve = self.ppg_plot_widget.plot(pen=pg.mkPen(color='#00AA00', width=2, cosmetic=False))
        
        plot_area_layout.addWidget(self.ecg_plot_widget, 1)
        plot_area_layout.addWidget(self.ppg_plot_widget, 1)
        
        # Status label
        self.status_label = QLabel('Ready')
        self.status_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; font-weight: bold;")
        
        main_layout.addLayout(control_layout)
        main_layout.addLayout(plot_area_layout, 1)
        main_layout.addWidget(self.status_label)
        central_widget.setLayout(main_layout)
    
    def on_time_changed(self):
        """Handle time window change"""
        self.update_plot()
    
    def update_data(self, ecg_chunk: List[float], ppg_chunk: List[float]):
        """Append new data chunk and update plot"""
        self.ecg_data.extend(ecg_chunk)
        self.ppg_data.extend(ppg_chunk)
        # Trigger update via timer or immediately if desired
        # self.update_plot() is called by timer every 500ms
    
    def reset_display(self):
        """Reset display ranges"""
        self.ecg_plot_widget.enableAutoRange('xy', True)
        self.ppg_plot_widget.enableAutoRange('xy', True)
        self.last_ecg_y_span = None
        self.last_ppg_y_span = None
        self.update_plot()
    
    def export_data(self):
        """Export data to files"""
        try:
            if self.ecg_data:
                with open('exported_ecg.txt', 'w') as f:
                    for val in self.ecg_data:
                        f.write(f"{val}\n")
                print(f"✓ Exported {len(self.ecg_data)} ECG samples")
            
            if self.ppg_data:
                with open('exported_ppg.txt', 'w') as f:
                    for val in self.ppg_data:
                        f.write(f"{val}\n")
                print(f"✓ Exported {len(self.ppg_data)} PPG samples")
            
            self.status_label.setText("✓ Data exported to exported_ecg.txt and exported_ppg.txt")
        except Exception as e:
            self.status_label.setText(f"✗ Export failed: {e}")
    
    def apply_smoothing(self, display_data: List[float], 
                       display_start_idx: int,
                       total_data: List[float],
                       display_end_idx: int) -> tuple:
        """Apply ECG smoothing with padding"""
        if not HAS_NEUROKIT:
            return display_data, False
        
        try:
            # Calculate padding
            padding_samples = 4 * self.sampling_rate
            
            # Get padded data
            padded_start = max(0, display_start_idx - padding_samples)
            padded_end = len(total_data)
            padded_data = total_data[padded_start:padded_end]
            
            # Apply smoothing
            smoothed_padded = nk.ecg_clean(padded_data, sampling_rate=self.sampling_rate,
                                           method="neurokit")
            
            # Extract display portion
            offset = display_start_idx - padded_start
            display_data = list(smoothed_padded[offset:offset + len(display_data)])
            return display_data, True
        except Exception as e:
            print(f"Smoothing error: {e}")
            return display_data, False
    
    def update_plot(self):
        """Update plots"""
        time_window = self.time_spinbox.value()
        samples_to_show = time_window * self.sampling_rate
        padding_samples = 4 * self.sampling_rate
        
        if not self.ecg_data or not self.ppg_data:
            self.status_label.setText('Waiting for data...')
            return
        
        # ECG processing
        ecg_display_start = max(0, len(self.ecg_data) - samples_to_show - padding_samples)
        ecg_display_end = max(samples_to_show, len(self.ecg_data) - padding_samples)
        ecg_display = self.ecg_data[ecg_display_start:ecg_display_end]
        
        ecg_smooth_applied = False
        if self.smooth_checkbox.isChecked():
            ecg_display, ecg_smooth_applied = self.apply_smoothing(
                ecg_display, ecg_display_start, self.ecg_data, ecg_display_end
            )
        
        # PPG processing
        ppg_display_start = max(0, len(self.ppg_data) - samples_to_show - padding_samples)
        ppg_display_end = max(samples_to_show, len(self.ppg_data) - padding_samples)
        ppg_display = self.ppg_data[ppg_display_start:ppg_display_end]
        
        # Update curves
        self.ecg_curve.setData(ecg_display)
        self.ppg_curve.setData(ppg_display)
        
        # Set x-axis range
        self.ecg_plot_widget.enableAutoRange('x', False)
        self.ecg_plot_widget.setXRange(0, len(ecg_display), padding=0)
        
        self.ppg_plot_widget.enableAutoRange('x', False)
        self.ppg_plot_widget.setXRange(0, len(ppg_display), padding=0)
        
        # Smart y-axis scaling for ECG
        if len(ecg_display) > 0:
            ecg_min = min(ecg_display)
            ecg_max = max(ecg_display)
            ecg_span = ecg_max - ecg_min
            
            if ecg_span == 0:
                ecg_span = 1
            
            ecg_padding = ecg_span * 0.1 if ecg_span > 0 else 5
            ecg_y_range = (ecg_min - ecg_padding, ecg_max + ecg_padding)
            ecg_y_span = ecg_span + 2 * ecg_padding
            
            should_rescale = False
            if self.last_ecg_y_span is None:
                should_rescale = True
            else:
                ratio = ecg_y_span / self.last_ecg_y_span
                should_rescale = ratio >= 2.0 or ratio <= 0.5
            
            if should_rescale:
                self.ecg_plot_widget.setYRange(ecg_y_range[0], ecg_y_range[1])
                self.last_ecg_y_span = ecg_y_span
            else:
                self.ecg_plot_widget.enableAutoRange('y', False)
        
        # Smart y-axis scaling for PPG
        if len(ppg_display) > 0:
            ppg_min = min(ppg_display)
            ppg_max = max(ppg_display)
            ppg_span = ppg_max - ppg_min
            
            if ppg_span == 0:
                ppg_span = 1
            
            ppg_padding = ppg_span * 0.1 if ppg_span > 0 else 5
            ppg_y_range = (ppg_min - ppg_padding, ppg_max + ppg_padding)
            ppg_y_span = ppg_span + 2 * ppg_padding
            
            should_rescale = False
            if self.last_ppg_y_span is None:
                should_rescale = True
            else:
                ratio = ppg_y_span / self.last_ppg_y_span
                should_rescale = ratio >= 2.0 or ratio <= 0.5
            
            # Always auto-scale PPG for now to debug range issues
            self.ppg_plot_widget.enableAutoRange('y', True)
            # if should_rescale:
            #     self.ppg_plot_widget.setYRange(ppg_y_range[0], ppg_y_range[1])
            #     self.last_ppg_y_span = ppg_y_span
            # else:
            #     self.ppg_plot_widget.enableAutoRange('y', False)
        
        # Update statistics
        ecg_stats = self._calc_stats(ecg_display)
        ppg_stats = self._calc_stats(ppg_display)
        
        ecg_smooth_str = "Smoothed (4s pad)" if ecg_smooth_applied else "Raw"
        ppg_smooth_str = "Raw"
        
        ecg_new = len(self.ecg_data) - self.last_ecg_count
        ppg_new = len(self.ppg_data) - self.last_ppg_count
        
        status = (
            f"ECG [{ecg_smooth_str}] - Total: {len(self.ecg_data)} | "
            f"Current: {ecg_stats['curr']:.0f} | Min: {ecg_stats['min']:.0f} | "
            f"Max: {ecg_stats['max']:.0f} | Mean: {ecg_stats['mean']:.1f} | New: {ecg_new}  |  "
            f"PPG [{ppg_smooth_str}] - Total: {len(self.ppg_data)} | "
            f"Current: {ppg_stats['curr']:.0f} | Min: {ppg_stats['min']:.0f} | "
            f"Max: {ppg_stats['max']:.0f} | Mean: {ppg_stats['mean']:.1f} | New: {ppg_new}"
        )
        self.status_label.setText(status)
        
        self.last_ecg_count = len(self.ecg_data)
        self.last_ppg_count = len(self.ppg_data)
    
    def _calc_stats(self, data: List[float]) -> dict:
        """Calculate statistics for a signal"""
        if not data:
            return {'curr': 0, 'min': 0, 'max': 0, 'mean': 0}
        
        return {
            'curr': data[-1],
            'min': min(data),
            'max': max(data),
            'mean': np.mean(data),
        }


def main():
    app = QApplication(sys.argv)
    viewer = SignalViewer()
    viewer.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
