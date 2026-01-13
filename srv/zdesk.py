#!/usr/bin/env python3
"""
Simple screen capture test - displays your screen in a PyQt window
Uses PyQt6's built-in screen capture (works on Wayland)
"""

import sys
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap, QScreen, QCloseEvent
from PyQt6.QtMultimedia import QScreenCapture, QVideoFrame, QMediaCaptureSession, QVideoSink
import time


class ScreenCaptureWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Capture Test (Wayland Compatible)")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Start button
        self.start_button = QPushButton("Start Capture")
        self.start_button.clicked.connect(self.start_capture)
        layout.addWidget(self.start_button)
        
        # Label to display the captured screen
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)  # Don't scale contents automatically
        self.image_label.setMinimumSize(640, 480)  # Set minimum size
        layout.addWidget(self.image_label, stretch=1)  # Give it stretch priority
        
        # Status label for FPS
        self.status_label = QLabel("Click 'Start Capture' to begin")
        layout.addWidget(self.status_label)
        
        # FPS tracking
        self.frame_count = 0
        self.last_time = time.time()
        self.fps = 0
        
        # Setup screen capture
        self.screen_capture = QScreenCapture(self)
        self.video_sink = QVideoSink(self)
        self.capture_session = QMediaCaptureSession(self)
        
        # Connect components
        self.capture_session.setScreenCapture(self.screen_capture)
        self.capture_session.setVideoSink(self.video_sink)
        
        # Connect signals
        self.video_sink.videoFrameChanged.connect(self.on_video_frame)
        self.screen_capture.errorOccurred.connect(self.on_error)
        
        # Timer for periodic capture
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.capture_and_display)
        # self.timer.start(33)  # ~30 FPS (33ms interval)
        
    def start_capture(self):
        """Start screen capture"""
        if self.screen_capture.isActive():
            self.screen_capture.stop()
            self.start_button.setText("Start Capture")
            self.status_label.setText("Capture stopped")
        else:
            # Get the primary screen
            screens = QApplication.screens()
            if screens:
                self.screen_capture.setScreen(screens[0])
            
            self.screen_capture.start()
            self.start_button.setText("Stop Capture")
            self.status_label.setText("Starting capture...")
            self.last_time = time.time()
            self.frame_count = 0
    
    def on_video_frame(self, frame: QVideoFrame):
        """Handle new video frame"""
        if not frame.isValid():
            return
        
        # Map the frame to access pixel data
        if not frame.map(QVideoFrame.MapMode.ReadOnly):
            return
        
        # Get frame info
        width = frame.width()
        height = frame.height()
        pixel_format = frame.pixelFormat()
        
        # Debug first frame
        # if self.frame_count == 0:
        #     print(f"Frame format: {pixel_format}, Size: {width}x{height}")
        
        # Convert to QImage
        image = frame.toImage()
        
        # Unmap the frame
        frame.unmap()
        
        if image.isNull():
            return
        
        # Convert to a standard format if needed
        if image.format() != QImage.Format.Format_RGB32:
            image = image.convertToFormat(QImage.Format.Format_RGB32)
        
        # Display in label
        pixmap = QPixmap.fromImage(image)
        # Scale to fit label while keeping aspect ratio
        label_size = self.image_label.size()
        if label_size.width() > 0 and label_size.height() > 0:
            scaled_pixmap = pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation  # Use Fast for better performance
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            # Initial size not set yet, use pixmap as-is
            self.image_label.setPixmap(pixmap)
        
        # Update FPS
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.status_label.setText(
                f"FPS: {self.fps:.1f} | Resolution: {image.width()}x{image.height()}"
            )
            self.frame_count = 0
            self.last_time = current_time
    
    def on_error(self, error, error_string):
        """Handle capture errors"""
        self.status_label.setText(f"Error: {error_string}")
        print(f"Screen capture error: {error} - {error_string}")
    
    def closeEvent(self, a0: QCloseEvent | None):
        """Clean up when closing"""
        # self.timer.stop()
        if self.screen_capture.isActive():
            self.screen_capture.stop()
        if a0:
            a0.accept()


def main():
    app = QApplication(sys.argv)
    
    # Check Qt version
    from PyQt6.QtCore import QT_VERSION_STR
    print(f"Qt version: {QT_VERSION_STR}")
    
    # Check if we can access the screen
    # screen = app.primaryScreen()
    # if not screen:
    #     print("ERROR: Cannot access primary screen")
    #     return 1
    
    window = ScreenCaptureWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()