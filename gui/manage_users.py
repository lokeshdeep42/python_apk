# gui/manage_users.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QComboBox, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from database.queries import fetch_all_users, create_user, toggle_user_status, delete_user

class ManageUsers(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Management")
        self.resize(900, 500)  # Increased width to accommodate delete button

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Header
        header = QLabel("👥 Manage Users")
        header.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 12px;")
        self.layout.addWidget(header, alignment=Qt.AlignLeft)

        # Input Form Layout
        form_layout = QHBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedWidth(150)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedWidth(150)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["employee", "admin"])
        self.role_combo.setFixedWidth(120)

        self.add_user_btn = QPushButton("➕ Create User")
        self.add_user_btn.clicked.connect(self.create_user)
        self.add_user_btn.setStyleSheet(self.button_style("#0078D7"))

        form_layout.addWidget(self.username_input)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.role_combo)
        form_layout.addWidget(self.add_user_btn)
        form_layout.setSpacing(15)

        self.layout.addLayout(form_layout)

        # Table Setup
        self.table = QTableWidget()
        self.table.setColumnCount(6)  # Increased columns for delete button
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Role", "Status", "Toggle", "Delete"])
        
        # Set specific column widths to ensure buttons fit properly
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # ID column
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Username column
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Role column
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Status column
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # Toggle column
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Delete column
        
        self.table.setColumnWidth(0, 60)   # ID
        self.table.setColumnWidth(2, 100)  # Role
        self.table.setColumnWidth(3, 100)  # Status
        self.table.setColumnWidth(4, 110)  # Toggle (wider for button)
        self.table.setColumnWidth(5, 110)  # Delete (wider for button)
        
        self.table.setStyleSheet("""
            QTableWidget { 
                font-size: 14px; 
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.layout.addWidget(self.table)

        self.load_users()

    def button_style(self, color="#0078D7"):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 11px;
                min-width: 60px;
                max-width: 100px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
            QPushButton:pressed {{
                background-color: {color};
                opacity: 0.6;
            }}
        """

    def load_users(self):
        users = fetch_all_users()
        self.table.setRowCount(len(users))

        for row, (user_id, username, role, status) in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(str(user_id)))
            self.table.setItem(row, 1, QTableWidgetItem(username))
            self.table.setItem(row, 2, QTableWidgetItem(role))

            status_item = QTableWidgetItem(status)
            status_color = QColor("green") if status == "Active" else QColor("red")
            status_item.setForeground(status_color)
            self.table.setItem(row, 3, status_item)

            # Toggle button - properly sized to fit in cell
            toggle_btn = QPushButton("Disable" if status == "Active" else "Enable")
            toggle_btn.setStyleSheet(self.button_style("#F7630C" if status == "Active" else "#107C10"))
            toggle_btn.setMaximumSize(100, 26)  # Constrain button size
            toggle_btn.clicked.connect(
                lambda checked, uid=user_id, stat=status: self.toggle_user(uid, stat)
            )
            
            # Create a container widget to center the button
            toggle_container = QWidget()
            toggle_layout = QHBoxLayout(toggle_container)
            toggle_layout.addWidget(toggle_btn)
            toggle_layout.setContentsMargins(5, 2, 5, 2)
            toggle_layout.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 4, toggle_container)

            # Delete button - properly sized to fit in cell
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet(self.button_style("#D13438"))  # Red color for delete
            delete_btn.setMaximumSize(100, 26)  # Constrain button size
            delete_btn.clicked.connect(
                lambda checked, uid=user_id, uname=username: self.delete_user(uid, uname)
            )
            
            # Create a container widget to center the button
            delete_container = QWidget()
            delete_layout = QHBoxLayout(delete_container)
            delete_layout.addWidget(delete_btn)
            delete_layout.setContentsMargins(5, 2, 5, 2)
            delete_layout.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 5, delete_container)

            self.table.setRowHeight(row, 40)  # Slightly taller rows for better button fit

    def create_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_combo.currentText()

        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Username and password are required.")
            return

        try:
            create_user(username, password, role)
            QMessageBox.information(self, "Success", "User created successfully.")
            self.username_input.clear()
            self.password_input.clear()
            self.load_users()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create user: {e}")

    def toggle_user(self, user_id, current_status):
        new_status = "Disabled" if current_status == "Active" else "Active"
        try:
            toggle_user_status(user_id, 'inactive' if new_status == "Disabled" else 'active')
            self.load_users()
            QMessageBox.information(self, "Success", f"User status updated to {new_status}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update user status: {e}")

    def delete_user(self, user_id, username):
        # Confirmation dialog
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Are you sure you want to delete user '{username}'?\n\n"
            "⚠️ This action cannot be undone and will remove:\n"
            "• The user account\n"
            "• All associated sessions\n"
            "• All related data\n\n"
            "Continue with deletion?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                delete_user(user_id)
                QMessageBox.information(self, "Success", f"User '{username}' deleted successfully.")
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete user: {e}")