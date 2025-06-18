# gui/admin_dashboard.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QHBoxLayout, QMessageBox,
    QGroupBox, QDateEdit, QLineEdit, QComboBox, QDialog,
    QTextEdit, QDialogButtonBox, QAbstractItemView
)
from PyQt5.QtCore import QTimer, QDate, Qt
from datetime import datetime, date, timedelta
from gui.manage_users import ManageUsers
from database.queries import (
    fetch_all_sessions, fetch_sessions_by_date_range, fetch_filtered_feedback, 
    insert_feedback, fetch_all_users
)
import threading
from utils.activity_monitor import start_activity_monitor
from utils.session_timeout import start_timeout_monitor

class CommentViewDialog(QDialog):
    """Dialog to view full comment text"""
    def __init__(self, comment, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Full Comment")
        self.setModal(True)
        self.resize(500, 300)
        
        layout = QVBoxLayout()
        
        # Add label
        label = QLabel("Full Comment:")
        label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)
        
        # Add text edit for comment
        text_edit = QTextEdit()
        text_edit.setPlainText(comment or "No comment provided")
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        
        # Add close button
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

class AdminDashboard(QWidget):
    def __init__(self, account_id):
        super().__init__()
        self.account_id = account_id
        self.current_session_id = None
        self.clock_in_time = None
        self.manage_window = None

        self.setWindowTitle("Admin Dashboard")
        self.resize(1100, 900)
        self.setStyleSheet("""
            QWidget { background-color: #f0f4f8; font-family: Arial; font-size: 14px; }
            QLabel { font-size: 18px; font-weight: bold; color: #2c3e50; }
            QPushButton {
                background-color: #007bff; color: white; padding: 6px 12px; border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #0056b3; }
            QPushButton:disabled { background-color: #cccccc; color: #555555; }
            QTableWidget { background-color: #ffffff; font-size: 13px; }
            QGroupBox { 
                background-color: #e9eff5; 
                border-radius: 6px; 
                padding: 8px; 
                font-size: 14px;
                font-weight: bold;
            }
            QComboBox, QLineEdit, QDateEdit {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #ffffff;
            }
        """)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

        self.header = QLabel("📊 Admin - Employee Sessions")
        self.status_label = QLabel("Status: Not Clocked In")
        self.timer_label = QLabel("")

        self.clock_in_button = QPushButton("🟢 Clock In")
        self.clock_out_button = QPushButton("🔴 Clock Out")
        self.clock_out_button.setEnabled(False)
        self.refresh_button = QPushButton("🔄 Refresh All")
        self.manage_users_button = QPushButton("👥 Manage Users")
        self.logout_button = QPushButton("🚪 Logout")

        self.clock_in_button.clicked.connect(self.handle_clock_in)
        self.clock_out_button.clicked.connect(self.handle_clock_out)
        self.refresh_button.clicked.connect(self.refresh_all)
        self.manage_users_button.clicked.connect(self.open_manage_users)
        self.logout_button.clicked.connect(self.handle_logout)

        session_filter_box = QGroupBox("🗓️ Filter Sessions")
        session_filter_layout = QHBoxLayout()

        session_filter_layout.addWidget(QLabel("Employee:"))
        self.employee_search = QLineEdit()
        self.employee_search.setPlaceholderText("Search employee name...")
        session_filter_layout.addWidget(self.employee_search)

        self.day_combo = QComboBox()
        self.day_combo.addItem("Day")
        for day in range(1, 32):
            self.day_combo.addItem(str(day))

        self.month_combo = QComboBox()
        months = ["Month", "January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        self.month_combo.addItems(months)

        self.year_combo = QComboBox()
        current_year = datetime.now().year
        self.year_combo.addItem("Year")
        for year in range(current_year - 5, current_year + 2):
            self.year_combo.addItem(str(year))

        self.apply_session_filter_btn = QPushButton("Apply Filter")
        self.apply_session_filter_btn.clicked.connect(self.filter_sessions_by_dropdowns)

        self.clear_session_filter_btn = QPushButton("Clear Filter")
        self.clear_session_filter_btn.clicked.connect(self.clear_session_filters)

        session_filter_layout.addWidget(QLabel("Day:"))
        session_filter_layout.addWidget(self.day_combo)
        session_filter_layout.addWidget(QLabel("Month:"))
        session_filter_layout.addWidget(self.month_combo)
        session_filter_layout.addWidget(QLabel("Year:"))
        session_filter_layout.addWidget(self.year_combo)
        session_filter_layout.addWidget(self.apply_session_filter_btn)
        session_filter_layout.addWidget(self.clear_session_filter_btn)
        session_filter_layout.addStretch()

        session_filter_box.setLayout(session_filter_layout)
        session_filter_box.setMaximumHeight(70)

        feedback_filter_box = QGroupBox("🗣️ Filter Feedback")
        feedback_filter_layout = QHBoxLayout()

        feedback_filter_layout.addWidget(QLabel("From:"))
        self.feedback_from_date = QDateEdit(calendarPopup=True)
        self.feedback_from_date.setDate(QDate.currentDate().addMonths(-1))
        feedback_filter_layout.addWidget(self.feedback_from_date)

        feedback_filter_layout.addWidget(QLabel("To:"))
        self.feedback_to_date = QDateEdit(calendarPopup=True)
        self.feedback_to_date.setDate(QDate.currentDate())
        feedback_filter_layout.addWidget(self.feedback_to_date)

        feedback_filter_layout.addWidget(QLabel("Mood:"))
        self.mood_filter = QComboBox()
        self.mood_filter.addItems(["All", "Terrible", "Poor", "Good", "Great", "Excellent"])
        feedback_filter_layout.addWidget(self.mood_filter)

        feedback_filter_layout.addWidget(QLabel("Keyword:"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("Search...")
        feedback_filter_layout.addWidget(self.keyword_input)

        self.filter_feedback_button = QPushButton("Apply Filter")
        self.filter_feedback_button.clicked.connect(self.load_feedback_filtered)
        feedback_filter_layout.addWidget(self.filter_feedback_button)

        self.clear_feedback_filter_btn = QPushButton("Clear Filter")
        self.clear_feedback_filter_btn.clicked.connect(self.clear_feedback_filters)
        feedback_filter_layout.addWidget(self.clear_feedback_filter_btn)

        feedback_filter_box.setLayout(feedback_filter_layout)
        feedback_filter_box.setMaximumHeight(70)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Employee Name", "Clock In", "Clock Out", "Date",
            "Work Time (min)", "Sleep Time (min)", "Session ID"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.feedback_table = QTableWidget()
        self.feedback_table.setColumnCount(5)
        self.feedback_table.setHorizontalHeaderLabels([
            "Employee Name", "Mood", "Comment", "Anonymous", "Submitted At"
        ])
        self.feedback_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.feedback_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.feedback_table.cellDoubleClicked.connect(self.show_full_comment)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.clock_in_button)
        top_layout.addWidget(self.clock_out_button)
        top_layout.addWidget(self.refresh_button)
        top_layout.addWidget(self.manage_users_button)
        top_layout.addWidget(self.logout_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(self.header)
        layout.addWidget(self.status_label)
        layout.addWidget(self.timer_label)
        layout.addLayout(top_layout)

        layout.addWidget(session_filter_box)
        layout.addWidget(QLabel("📅 Sessions:"))
        layout.addWidget(self.table)

        layout.addWidget(feedback_filter_box)
        layout.addWidget(QLabel("🗣️ User Feedback: (Double-click row to view full comment)"))
        layout.addWidget(self.feedback_table)

        self.feedback_given = False
        self.feedback_shown = False
        
        self.setLayout(layout)
        self.load_sessions()
        self.load_feedback()

    def clear_session_filters(self):
        self.employee_search.clear()
        self.day_combo.setCurrentIndex(0)
        self.month_combo.setCurrentIndex(0)
        self.year_combo.setCurrentIndex(0)
        self.load_sessions()

    def filter_sessions_by_dropdowns(self):
        day = self.day_combo.currentText()
        month = self.month_combo.currentText()
        year = self.year_combo.currentText()
        employee_search = self.employee_search.text().strip().lower()
        
        start_date = None
        end_date = None

        try:
            if year != "Year":
                year_int = int(year)
                
                if month != "Month":
                    month_int = self.month_combo.currentIndex()
                    
                    if day != "Day":
                        day_int = int(day)
                        start_date = date(year_int, month_int, day_int)
                        end_date = start_date
                    else:
                        start_date = date(year_int, month_int, 1)
                        
                        if month_int == 12:
                            end_date = date(year_int + 1, 1, 1) - timedelta(days=1)
                        else:
                            end_date = date(year_int, month_int + 1, 1) - timedelta(days=1)
                else:
                    start_date = date(year_int, 1, 1)
                    end_date = date(year_int, 12, 31)

            if start_date and end_date:
                sessions = fetch_sessions_by_date_range(start_date, end_date)
            else:
                sessions = fetch_all_sessions()
            
            if employee_search:
                sessions = [session for session in sessions 
                        if employee_search in session[0].lower()]
                
            self.populate_sessions_table(sessions)
        
        except (ValueError, TypeError) as e:
            QMessageBox.warning(self, "Invalid Date", "Please select a valid date combination.")
            self.load_sessions()

    def show_full_comment(self, row, column):
        if column == 2:
            comment_item = self.feedback_table.item(row, 2)
            if comment_item:
                comment = comment_item.text()
                dialog = CommentViewDialog(comment, self)
                dialog.exec_()

    def clear_feedback_filters(self):
        self.feedback_from_date.setDate(QDate.currentDate().addMonths(-1))
        self.feedback_to_date.setDate(QDate.currentDate())
        self.mood_filter.setCurrentIndex(0)
        self.keyword_input.clear()
        self.load_feedback()

    def handle_clock_in(self):
        from database.queries import start_session
        if self.current_session_id:
            QMessageBox.warning(self, "Already Clocked In", "You are already clocked in.")
            return

        self.clock_in_time = datetime.now()
        self.current_session_id = start_session(self.account_id, self.clock_in_time)

        if self.current_session_id:
            self.status_label.setText(f"Clocked in at {self.clock_in_time.strftime('%H:%M:%S')}")
            self.clock_in_button.setEnabled(False)
            self.clock_out_button.setEnabled(True)
            self.timer.start(1000)
            start_timeout_monitor(self.account_id, self.current_session_id, self.clock_in_time)
            threading.Thread(
                target=start_activity_monitor,
                args=(self.account_id, self.current_session_id),
                daemon=True
            ).start()
            self.load_sessions()
        else:
            QMessageBox.critical(self, "Error", "Failed to clock in.")

    def handle_clock_out(self):
        from database.queries import end_session
        if not self.current_session_id:
            return
        clock_out_time = datetime.now()
        total_minutes = end_session(self.current_session_id, clock_out_time)
        self.status_label.setText(f"Clocked out at {clock_out_time.strftime('%H:%M:%S')} | Total: {total_minutes} min")
        self.timer.stop()
        self.timer_label.setText("")
        self.clock_in_button.setEnabled(True)
        self.clock_out_button.setEnabled(False)
        self.current_session_id = None
        self.load_sessions()

    def update_timer(self):
        if self.clock_in_time:
            elapsed = datetime.now() - self.clock_in_time
            minutes, seconds = divmod(elapsed.seconds, 60)
            hours, minutes = divmod(minutes, 60)
            self.timer_label.setText(f"⏱ Elapsed Time: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def load_sessions(self):
        sessions = fetch_all_sessions()
        self.populate_sessions_table(sessions)

    def populate_sessions_table(self, sessions):
        self.table.setRowCount(len(sessions))
        for row_idx, session in enumerate(sessions):
            username, clock_in, clock_out, session_date, work_minutes, sleep_minutes, session_id = session
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(username)))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(clock_in)))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(clock_out)))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(session_date)))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(work_minutes)))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(sleep_minutes or 0)))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(session_id)))

    def load_feedback(self):
        feedbacks = fetch_filtered_feedback()
        self.populate_feedback_table(feedbacks)

    def load_feedback_filtered(self):
        start_date = self.feedback_from_date.date().toPyDate()
        end_date = self.feedback_to_date.date().toPyDate()
        mood = self.mood_filter.currentText()
        keyword = self.keyword_input.text()
        
        feedbacks = fetch_filtered_feedback(start_date, end_date, mood, keyword)
        self.populate_feedback_table(feedbacks)

    def populate_feedback_table(self, feedbacks):
        self.feedback_table.setRowCount(len(feedbacks))
        for row_idx, feedback in enumerate(feedbacks):
            feedback_id, username, mood, comment, anonymous, submitted_at = feedback
            display_name = username if username else "Anonymous"
            self.feedback_table.setItem(row_idx, 0, QTableWidgetItem(display_name))
            self.feedback_table.setItem(row_idx, 1, QTableWidgetItem(mood))
            
            truncated_comment = ""
            if comment:
                truncated_comment = comment[:50] + "..." if len(comment) > 50 else comment
            
            self.feedback_table.setItem(row_idx, 2, QTableWidgetItem(truncated_comment))
            self.feedback_table.setItem(row_idx, 3, QTableWidgetItem(anonymous))
            self.feedback_table.setItem(row_idx, 4, QTableWidgetItem(submitted_at.strftime("%Y-%m-%d %H:%M:%S")))

    def refresh_all(self):
        self.load_sessions()
        self.load_feedback()

    def open_manage_users(self):
        if self.manage_window is None or not self.manage_window.isVisible():
            self.manage_window = ManageUsers()
            self.manage_window.show()
        else:
            self.manage_window.raise_()
            self.manage_window.activateWindow()

    def handle_logout(self):
        self.show_feedback_dialog()
        
        if self.current_session_id and self.clock_out_button.isEnabled():
            self.handle_clock_out()
            
        from gui.login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        
        self.hide()
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.close)

    def closeEvent(self, event):
        self.show_feedback_dialog()
        
        if self.manage_window and self.manage_window.isVisible():
            self.manage_window.close()

        if self.current_session_id:
            self.handle_clock_out()

        event.accept()
    
    def show_feedback_dialog(self):
        if not self.feedback_shown:
            self.feedback_shown = True
            from gui.feedback_dialog import FeedbackDialog
            
            def submit_callback(account_id, mood, comment, anonymous):
                insert_feedback(account_id, mood, comment, anonymous)
                self.feedback_given = True
            
            feedback_dialog = FeedbackDialog(self.account_id, submit_callback)
            feedback_dialog.exec_()