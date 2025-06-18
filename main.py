import sys
from PyQt5.QtWidgets import QApplication
from gui.login_window import LoginWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec_())