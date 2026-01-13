#!/usr/bin/env python3
"""
ZDesk Server - Captures and streams screen to connected clients
"""

import sys
import socket
import struct
import io
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QSpinBox, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtMultimedia import QScreenCapture, QVideoFrame, QMediaCaptureSession, QVideoSink
from PyQt6.QtGui import QImage, QCloseEvent
from PIL import Image


class StreamThread(QThread):
    """Thread for handling client connections and streaming"""
    status_update = pyqtSignal(str)
    
    def __init__(self, port, quality):
        super().__init__()
        self.port = port
        self.quality = quality  # JPEG quality 1-100
        self.running = False
        self.server_socket = None
        self.client_socket = None
        self.current_frame = None
        
    def run(self):
        """Start server and accept connections"""
        self.running = True
        
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1.0)  # Timeout to check self.running
            
            self.status_update.emit(f"Server listening on port {self.port}")
            
            while self.running:
                try:
                    # Accept client connection
                    self.client_socket, addr = self.server_socket.accept()
                    self.status_update.emit(f"Client connected: {addr[0]}:{addr[1]}")
                    
                    # Stream to client
                    self.stream_to_client()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.status_update.emit(f"Error: {str(e)}")
                finally:
                    if self.client_socket:
                        self.client_socket.close()
                        self.client_socket = None
                        self.status_update.emit("Client disconnected")
                        
        except Exception as e:
            self.status_update.emit(f"Server error: {str(e)}")
        finally:
            if self.server_socket:
                self.server_socket.close()
                
    def stream_to_client(self):
        """Stream frames to connected client"""
        while self.running and self.client_socket:
            if self.current_frame is None:
                continue
                
            try:
                # Get frame and compress to JPEG
                frame_data = self.compress_frame(self.current_frame)
                
                if frame_data:
                    # Send frame size first (4 bytes)
                    size = len(frame_data)
                    self.client_socket.sendall(struct.pack('!I', size))
                    
                    # Send frame data
                    self.client_socket.sendall(frame_data)
                    
            except (BrokenPipeError, ConnectionResetError):
                break
            except Exception as e:
                self.status_update.emit(f"Streaming error: {str(e)}")
                break
                
    def compress_frame(self, qimage):
        """Compress QImage to JPEG bytes"""
        # Convert QImage to PIL Image
        width = qimage.width()
        height = qimage.height()
        
        # Convert to RGB format
        qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        
        # Get bytes and create PIL image
        ptr = qimage.bits()
        ptr.setsize(qimage.sizeInBytes())
        pil_image = Image.frombytes('RGB', (width, height), bytes(ptr), 'raw', 'RGB')
        
        # Compress to JPEG
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=self.quality, optimize=True)
        return buffer.getvalue()
        
    def set_frame(self, qimage):
        """Update current frame to be streamed"""
        self.current_frame = qimage
        
    def stop(self):
        """Stop the streaming thread"""
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()


class ServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZDesk Server - Screen Sharing Host")
        self.setGeometry(100, 100, 600, 400)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(5555)
        port_layout.addWidget(self.port_spin)
        port_layout.addStretch()
        layout.addLayout(port_layout)
        
        # Quality selection
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("JPEG Quality:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(10, 100)
        self.quality_spin.setValue(60)
        quality_layout.addWidget(self.quality_spin)
        quality_layout.addStretch()
        layout.addLayout(quality_layout)
        
        # Control buttons
        self.start_button = QPushButton("Start Server")
        self.start_button.clicked.connect(self.toggle_server)
        layout.addWidget(self.start_button)
        
        self.capture_button = QPushButton("Start Screen Capture")
        self.capture_button.clicked.connect(self.toggle_capture)
        self.capture_button.setEnabled(False)
        layout.addWidget(self.capture_button)
        
        # Status label
        self.status_label = QLabel("Server stopped")
        layout.addWidget(self.status_label)
        
        # Screen capture setup
        self.screen_capture = QScreenCapture(self)
        self.video_sink = QVideoSink(self)
        self.capture_session = QMediaCaptureSession(self)
        
        self.capture_session.setScreenCapture(self.screen_capture)
        self.capture_session.setVideoSink(self.video_sink)
        
        self.video_sink.videoFrameChanged.connect(self.on_video_frame)
        self.screen_capture.errorOccurred.connect(self.on_capture_error)
        
        # Stream thread
        self.stream_thread = None
        
    def toggle_server(self):
        """Start/stop server"""
        if self.stream_thread and self.stream_thread.isRunning():
            # Stop server
            self.stream_thread.stop()
            self.stream_thread.wait()
            self.stream_thread = None
            
            self.start_button.setText("Start Server")
            self.capture_button.setEnabled(False)
            self.port_spin.setEnabled(True)
            self.quality_spin.setEnabled(True)
            self.status_label.setText("Server stopped")
        else:
            # Start server
            port = self.port_spin.value()
            quality = self.quality_spin.value()
            
            self.stream_thread = StreamThread(port, quality)
            self.stream_thread.status_update.connect(self.update_status)
            self.stream_thread.start()
            
            self.start_button.setText("Stop Server")
            self.capture_button.setEnabled(True)
            self.port_spin.setEnabled(False)
            self.quality_spin.setEnabled(False)
            
    def toggle_capture(self):
        """Start/stop screen capture"""
        if self.screen_capture.isActive():
            self.screen_capture.stop()
            self.capture_button.setText("Start Screen Capture")
        else:
            screens = QApplication.screens()
            if screens:
                self.screen_capture.setScreen(screens[0])
            self.screen_capture.start()
            self.capture_button.setText("Stop Screen Capture")
            
    def on_video_frame(self, frame: QVideoFrame):
        """Handle captured frame"""
        if not frame.isValid() or not self.stream_thread:
            return
            
        if not frame.map(QVideoFrame.MapMode.ReadOnly):
            return
            
        image = frame.toImage()
        frame.unmap()
        
        if not image.isNull() and self.stream_thread:
            # Send frame to streaming thread
            self.stream_thread.set_frame(image)
            
    def on_capture_error(self, error, error_string):
        """Handle capture errors"""
        self.status_label.setText(f"Capture error: {error_string}")
        
    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)
        
    def closeEvent(self, a0: QCloseEvent | None):
        """Clean up on close"""
        if self.screen_capture.isActive():
            self.screen_capture.stop()
        if self.stream_thread:
            self.stream_thread.stop()
            self.stream_thread.wait()
        if a0:
            a0.accept()


def main():
    app = QApplication(sys.argv)
    window = ServerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()