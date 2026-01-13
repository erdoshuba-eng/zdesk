#!/usr/bin/env python3
"""
ZDesk Client - Connects to server and displays remote screen
"""

import sys
import socket
import struct
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QSpinBox, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QCloseEvent
from PIL import Image
import io


class ReceiveThread(QThread):
    """Thread for receiving frames from server"""
    frame_received = pyqtSignal(QImage)
    status_update = pyqtSignal(str)
    
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.running = False
        self.client_socket = None
        
    def run(self):
        """Connect to server and receive frames"""
        self.running = True
        
        try:
            # Connect to server
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)
            self.client_socket.connect((self.host, self.port))
            self.status_update.emit(f"Connected to {self.host}:{self.port}")
            
            # Receive frames
            while self.running:
                try:
                    # Receive frame size (4 bytes)
                    size_data = self.recv_exact(4)
                    if not size_data:
                        break
                        
                    frame_size = struct.unpack('!I', size_data)[0]
                    
                    # Receive frame data
                    frame_data = self.recv_exact(frame_size)
                    if not frame_data:
                        break
                        
                    # Decompress and convert to QImage
                    qimage = self.decompress_frame(frame_data)
                    if qimage:
                        self.frame_received.emit(qimage)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.status_update.emit(f"Error: {str(e)}")
                    break
                    
        except Exception as e:
            self.status_update.emit(f"Connection error: {str(e)}")
        finally:
            if self.client_socket:
                self.client_socket.close()
            self.status_update.emit("Disconnected")
            
    def recv_exact(self, size):
        """Receive exactly size bytes"""
        data = b''
        while len(data) < size and self.running:
            try:
                if not self.client_socket:
                    return None
                chunk = self.client_socket.recv(size - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.timeout:
                continue
        return data if len(data) == size else None
        
    def decompress_frame(self, data):
        """Decompress JPEG data to QImage"""
        try:
            # Load JPEG with PIL
            pil_image = Image.open(io.BytesIO(data))
            
            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
                
            # Convert to QImage
            width, height = pil_image.size
            rgb_data = pil_image.tobytes()
            
            qimage = QImage(rgb_data, width, height, width * 3, QImage.Format.Format_RGB888)
            return qimage.copy()  # Make a copy since the data will be freed
            
        except Exception as e:
            self.status_update.emit(f"Decompression error: {str(e)}")
            return None
            
    def stop(self):
        """Stop receiving"""
        self.running = False
        if self.client_socket:
            self.client_socket.close()


class ClientWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZDesk Client - Remote Screen Viewer")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Connection settings
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("Host:"))
        self.host_edit = QLineEdit()
        self.host_edit.setText("localhost")
        conn_layout.addWidget(self.host_edit)
        
        conn_layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(5555)
        conn_layout.addWidget(self.port_spin)
        
        layout.addLayout(conn_layout)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_button)
        
        # Display label for remote screen
        self.display_label = QLabel()
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setScaledContents(False)
        self.display_label.setMinimumSize(640, 480)
        self.display_label.setStyleSheet("QLabel { background-color: black; }")
        layout.addWidget(self.display_label, stretch=1)
        
        # Status label
        self.status_label = QLabel("Not connected")
        layout.addWidget(self.status_label)
        
        # FPS tracking
        self.frame_count = 0
        self.last_time = time.time()
        self.fps = 0
        
        # Receive thread
        self.receive_thread = None
        
    def toggle_connection(self):
        """Connect/disconnect from server"""
        if self.receive_thread and self.receive_thread.isRunning():
            # Disconnect
            self.receive_thread.stop()
            self.receive_thread.wait()
            self.receive_thread = None
            
            self.connect_button.setText("Connect")
            self.host_edit.setEnabled(True)
            self.port_spin.setEnabled(True)
            self.status_label.setText("Disconnected")
        else:
            # Connect
            host = self.host_edit.text()
            port = self.port_spin.value()
            
            self.receive_thread = ReceiveThread(host, port)
            self.receive_thread.frame_received.connect(self.display_frame)
            self.receive_thread.status_update.connect(self.update_status)
            self.receive_thread.start()
            
            self.connect_button.setText("Disconnect")
            self.host_edit.setEnabled(False)
            self.port_spin.setEnabled(False)
            self.status_label.setText("Connecting...")
            
            # Reset FPS counter
            self.frame_count = 0
            self.last_time = time.time()
            
    def display_frame(self, qimage):
        """Display received frame"""
        # Convert to pixmap and scale
        pixmap = QPixmap.fromImage(qimage)
        
        label_size = self.display_label.size()
        if label_size.width() > 0 and label_size.height() > 0:
            scaled_pixmap = pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.display_label.setPixmap(scaled_pixmap)
        else:
            self.display_label.setPixmap(pixmap)
            
        # Update FPS
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.status_label.setText(
                f"Connected | FPS: {self.fps:.1f} | Resolution: {qimage.width()}x{qimage.height()}"
            )
            self.frame_count = 0
            self.last_time = current_time
            
    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)
        
    def closeEvent(self, a0: QCloseEvent | None):
        """Clean up on close"""
        if self.receive_thread:
            self.receive_thread.stop()
            self.receive_thread.wait()
        if a0:
            a0.accept()


def main():
    app = QApplication(sys.argv)
    window = ClientWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()