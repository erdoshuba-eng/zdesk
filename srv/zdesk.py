#!/usr/bin/env python3
"""
Simple screen capture test - displays your screen in a PyQt window
Uses PyQt6's built-in screen capture (works on Wayland)
"""

import sys
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap, QScreen
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
        
        # Label to display the captured screen
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)
        layout.addWidget(self.image_label)
        
        # Status label for FPS
        self.status_label = QLabel("Starting...")
        layout.addWidget(self.status_label)
        
        # Get primary screen
        self.screen = QApplication.primaryScreen()
        
        # FPS tracking
        self.frame_count = 0
        self.last_time = time.time()
        self.fps = 0
        
        # Timer for periodic capture
        self.timer = QTimer()
        self.timer.timeout.connect(self.capture_and_display)
        self.timer.start(33)  # ~30 FPS (33ms interval)
        
    def capture_and_display(self):
        """Capture screen and display it"""
        # Capture screenshot using Qt
        pixmap = self.screen.grabWindow(0)
        
        if pixmap.isNull():
            self.status_label.setText("Failed to capture screen - check Wayland permissions")
            return
        
        # Display in label
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        
        # Update FPS
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.status_label.setText(
                f"FPS: {self.fps:.1f} | Resolution: {pixmap.width()}x{pixmap.height()}"
            )
            self.frame_count = 0
            self.last_time = current_time
    
    def closeEvent(self, event):
        """Clean up when closing"""
        self.timer.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Check if we can access the screen
    screen = app.primaryScreen()
    if not screen:
        print("ERROR: Cannot access primary screen")
        return 1
    
    window = ScreenCaptureWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()