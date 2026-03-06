"""
HealthyPi 5 LSL Stream Library
Refactored from healthypi_lsi_stream.py as a reusable library
"""
import serial
import time
from queue import Queue
from threading import Thread
from typing import Optional, Callable


# System Settings
SERIAL_PORT_NAME = 'COM5'
SERIAL_BAUD = 115200

# CES State Machine
CESState_Init = 0
CESState_SOF1_Found = 1
CESState_SOF2_Found = 2
CESState_PktLen_Found = 3

# CES CMD IF Packet Format
CES_CMDIF_PKT_START_1 = '0a'
CES_CMDIF_PKT_START_2 = 'fa'
CES_CMDIF_PKT_STOP = '0b'

# CES CMD IF Packet Indices
CES_CMDIF_IND_LEN = 2
CES_CMDIF_IND_LEN_MSB = 3
CES_CMDIF_IND_PKTTYPE = 4
CES_CMDIF_PKT_OVERHEAD = 5


class HealthyPiStream:
    """HealthyPi 5 serial stream decoder"""
    
    def __init__(self, port: str = SERIAL_PORT_NAME, baudrate: int = SERIAL_BAUD,
                 ecg_callback: Optional[Callable] = None,
                 ppg_callback: Optional[Callable] = None,
                 sampling_rate: int = 500):
        """
        Initialize HealthyPi stream reader
        
        Args:
            port: Serial port name (e.g., 'COM5', '/dev/ttyUSB0')
            baudrate: Baud rate (typically 115200)
            ecg_callback: Callback function(ecg_value) when ECG sample received
            ppg_callback: Callback function(ppg_value) when PPG sample received
            sampling_rate: Expected sampling rate (default 500 Hz)
        """
        self.port = port
        self.baudrate = baudrate
        self.ecg_callback = ecg_callback
        self.ppg_callback = ppg_callback
        self.sampling_rate = sampling_rate
        
        # State machine
        self.ecs_rx_state = CESState_Init
        self.CES_Pkt_Data_Counter = [''] * 50
        self.CES_Data_Counter = 0
        self.CES_Pkt_ECG = bytearray()
        self.CES_Pkt_PPG_IR = bytearray()
        self.CES_Pkt_Len = 0
        self.CES_Pkt_Pos_Counter = 0
        self.CES_Pkt_PktType = 0
        
        # Serial connection
        self.ser: Optional[serial.Serial] = None
        self.is_running = False
        self.reader_thread: Optional[Thread] = None
        
    def connect(self) -> bool:
        """Connect to HealthyPi device"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate)
            print(f"✓ Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"✗ Failed to connect to {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from HealthyPi device"""
        if self.ser:
            self.is_running = False
            if self.reader_thread:
                self.reader_thread.join(timeout=2)
            self.ser.close()
            print("✓ Disconnected from device")
    
    def start(self):
        """Start reading from stream in background thread"""
        if not self.ser or not self.ser.is_open:
            if not self.connect():
                return False
        
        self.is_running = True
        self.reader_thread = Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()
        print("✓ Stream reader started")
        return True
    
    def stop(self):
        """Stop reading from stream"""
        self.is_running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=2)
        print("✓ Stream reader stopped")
    
    def _read_loop(self):
        """Main read loop (runs in background thread)"""
        while self.is_running:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    ser_bytes = self.ser.read()
                    rxch = bytes.hex(ser_bytes)
                    self._process_byte(rxch)
                else:
                    time.sleep(0.001)  # Prevent busy waiting
            except Exception as e:
                print(f"Error in read loop: {e}")
                time.sleep(0.1)
    
    def _process_byte(self, rxch: str):
        """Process a single byte from serial stream"""
        if self.ecs_rx_state == CESState_Init:
            if rxch == CES_CMDIF_PKT_START_1:
                self.ecs_rx_state = CESState_SOF1_Found
        
        elif self.ecs_rx_state == CESState_SOF1_Found:
            if rxch == CES_CMDIF_PKT_START_2:
                self.ecs_rx_state = CESState_SOF2_Found
            else:
                self.ecs_rx_state = CESState_Init
        
        elif self.ecs_rx_state == CESState_SOF2_Found:
            self.ecs_rx_state = CESState_PktLen_Found
            self.CES_Pkt_Len = int(rxch, 16)
            self.CES_Pkt_Pos_Counter = CES_CMDIF_IND_LEN
            self.CES_Data_Counter = 0
        
        elif self.ecs_rx_state == CESState_PktLen_Found:
            self.CES_Pkt_Pos_Counter += 1
            
            if self.CES_Pkt_Pos_Counter < CES_CMDIF_PKT_OVERHEAD:
                if self.CES_Pkt_Pos_Counter == CES_CMDIF_IND_LEN_MSB:
                    self.CES_Pkt_Len = self.CES_Pkt_Len
                elif self.CES_Pkt_Pos_Counter == CES_CMDIF_IND_PKTTYPE:
                    self.CES_Pkt_PktType = int(rxch, 16)
            
            elif (self.CES_Pkt_Pos_Counter >= CES_CMDIF_PKT_OVERHEAD and 
                  self.CES_Pkt_Pos_Counter < CES_CMDIF_PKT_OVERHEAD + self.CES_Pkt_Len + 1):
                if self.CES_Pkt_PktType == 2:
                    self.CES_Pkt_Data_Counter[self.CES_Data_Counter] = rxch
                    self.CES_Data_Counter += 1
            
            else:
                # All data received
                if rxch == CES_CMDIF_PKT_STOP:
                    self._extract_and_send_data()
                    self.ecs_rx_state = CESState_Init
                else:
                    self.ecs_rx_state = CESState_Init
    
    def _extract_and_send_data(self):
        """Extract ECG and PPG data and call callbacks"""
        # Extract ECG (bytes 0-3)
        self.CES_Pkt_ECG.clear()
        for i in range(4):
            self.CES_Pkt_ECG.append(int(self.CES_Pkt_Data_Counter[i], 16))
        
        ecg_int_val = int.from_bytes(self.CES_Pkt_ECG, 'little', signed=True)
        
        if self.ecg_callback:
            self.ecg_callback(ecg_int_val)
        
        # Extract PPG IR (bytes 9-12)
        self.CES_Pkt_PPG_IR.clear()
        for i in range(9, 13):
            self.CES_Pkt_PPG_IR.append(int(self.CES_Pkt_Data_Counter[i], 16))
        
        ppg_int_val = int.from_bytes(self.CES_Pkt_PPG_IR, 'little', signed=True)
        
        if self.ppg_callback:
            self.ppg_callback(ppg_int_val)


class HealthyPiStreamWithQueue(HealthyPiStream):
    """HealthyPi stream with built-in queue for buffering"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecg_queue = Queue()
        self.ppg_queue = Queue()
        
        # Set callbacks to queue the data
        self.ecg_callback = self._queue_ecg
        self.ppg_callback = self._queue_ppg
    
    def _queue_ecg(self, value):
        """Queue ECG value"""
        self.ecg_queue.put(value)
    
    def _queue_ppg(self, value):
        """Queue PPG value"""
        self.ppg_queue.put(value)
    
    def get_ecg(self, timeout: Optional[float] = None) -> Optional[float]:
        """Get next ECG value from queue"""
        try:
            return self.ecg_queue.get(timeout=timeout)
        except:
            return None
    
    def get_ppg(self, timeout: Optional[float] = None) -> Optional[float]:
        """Get next PPG value from queue"""
        try:
            return self.ppg_queue.get(timeout=timeout)
        except:
            return None
    
    def get_all_ecg(self) -> list:
        """Get all available ECG values"""
        values = []
        while not self.ecg_queue.empty():
            try:
                values.append(self.ecg_queue.get_nowait())
            except:
                break
        return values
    
    def get_all_ppg(self) -> list:
        """Get all available PPG values"""
        values = []
        while not self.ppg_queue.empty():
            try:
                values.append(self.ppg_queue.get_nowait())
            except:
                break
        return values


if __name__ == '__main__':
    # Example usage
    import time
    
    def on_ecg(value):
        print(f"ECG: {value}")
    
    def on_ppg(value):
        print(f"PPG: {value}")
    
    stream = HealthyPiStream(ecg_callback=on_ecg, ppg_callback=on_ppg)
    stream.start()
    
    try:
        time.sleep(10)
    finally:
        stream.stop()
        stream.disconnect()
