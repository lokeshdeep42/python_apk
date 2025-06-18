# gui/employee_dashboard.py
import sys
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QMessageBox
)
from PyQt5.QtCore import QTimer
from datetime import datetime
from database.queries import start_session, end_session, insert_feedback
from utils.activity_monitor import start_activity_monitor
from utils.session_timeout import start_timeout_monitor
import threading

class EmployeeDashboard(QWidget):
    def __init__(self, account_id):
        super().__init__()
        self.setWindowTitle("Employee Dashboard")
        self.setFixedSize(400, 300)
        self.account_id = account_id
        self.session_id = None
        self.clock_in_time = None
        self.feedback_given = False

        self.setStyleSheet("""
            QWidget {
                background-color: #f0f4f8;
                font-family: Arial;
                font-size: 14px;
            }
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                height: 40px;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 15px;
                letter-spacing: 0.5px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #555555;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

        self.header = QLabel("👷 Employee Session Tracker")
        self.status_label = QLabel("Status: Not Clocked In")
        self.timer_label = QLabel("")

        self.clock_in_button = QPushButton("Clock In")
        self.clock_out_button = QPushButton("Clock Out")
        self.clock_out_button.setEnabled(False)

        self.clock_in_button.clicked.connect(self.handle_clock_in)
        self.clock_out_button.clicked.connect(self.handle_clock_out)

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)
        layout.addWidget(self.header)
        layout.addWidget(self.status_label)
        layout.addWidget(self.timer_label)
        layout.addWidget(self.clock_in_button)
        layout.addWidget(self.clock_out_button)

        self.logout_button = QPushButton("🚪 Logout")
        self.logout_button.clicked.connect(self.handle_logout)
        layout.addWidget(self.logout_button)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

    def handle_clock_in(self):
        self.clock_in_time = datetime.now()
        self.session_id = start_session(self.account_id, self.clock_in_time)

        if self.session_id:
            self.status_label.setText(f"Clocked in at {self.clock_in_time.strftime('%H:%M:%S')}")
            self.clock_in_button.setEnabled(False)
            self.clock_out_button.setEnabled(True)
            self.timer.start(1000)
            start_timeout_monitor(self.account_id, self.session_id, self.clock_in_time)
            threading.Thread(
                target=start_activity_monitor,
                args=(self.account_id, self.session_id),
                daemon=True
            ).start()
        else:
            QMessageBox.critical(self, "Error", "Failed to clock in.")

    def handle_clock_out(self):
        clock_out_time = datetime.now()
        total_minutes = end_session(self.session_id, clock_out_time)
        self.status_label.setText(f"Clocked out at {clock_out_time.strftime('%H:%M:%S')}\nTotal: {total_minutes} min")
        self.timer.stop()
        self.timer_label.setText("")
        self.clock_in_button.setEnabled(True)
        self.clock_out_button.setEnabled(False)

    def update_timer(self):
        if self.clock_in_time:
            elapsed = datetime.now() - self.clock_in_time
            minutes, seconds = divmod(elapsed.seconds, 60)
            hours, minutes = divmod(minutes, 60)
            self.timer_label.setText(f"⏱ Elapsed Time: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def show_feedback_dialog(self):
        if not self.feedback_given:
            from gui.feedback_dialog import FeedbackDialog
            def submit_callback(account_id, mood, comment, anonymous):
                insert_feedback(account_id, mood, comment, anonymous)
            feedback_dialog = FeedbackDialog(self.account_id, submit_callback)
            feedback_dialog.exec_()
            self.feedback_given = True

    def closeEvent(self, event):
        self.show_feedback_dialog()

        if self.session_id and self.clock_out_button.isEnabled():
            self.handle_clock_out()

        event.accept()

    def handle_logout(self):
        self.show_feedback_dialog()

        if self.session_id and self.clock_out_button.isEnabled():
            self.handle_clock_out()

        from gui.login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()
