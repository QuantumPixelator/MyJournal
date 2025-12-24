"""Application entry point.

This script initializes the Qt application, runs the setup flow on
first run, and then prompts the user to log in. After successful
authentication the main window is shown.
"""

import sys
import os
import sqlite3
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon
import pyotp
from encryption import EncryptionManager
from database import DatabaseManager, DB_FILE
from auth import SetupDialog, LoginDialog
from main_window import MainWindow
from datetime import datetime, timezone


app = QApplication(sys.argv)
app.setStyle("Fusion")
icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
if os.path.exists(icon_path):
    app.setWindowIcon(QIcon(icon_path))

db = DatabaseManager()

if db.is_new():
    # First-run setup: pick a password and register a TOTP secret
    setup = SetupDialog()
    if not setup.exec():
        sys.exit(0)
    password = setup.password
    salt = EncryptionManager.generate_salt()
    enc = EncryptionManager(password, salt)
    db.connect(enc)
    db.init_db()
    db.save_config(salt, setup.secret)
    QMessageBox.information(None, "Setup complete", "Account created. Log in with your password and authenticator.")

# Login loop: allow a few attempts before exiting
attempts = 0
while attempts < 5:
    login = LoginDialog()
    if not login.exec():
        sys.exit(0)
    password = login.pw.text()
    code = login.totp.text()
    # Load salt and encrypted totp secret from DB (use a temp connection)
    temp_conn = sqlite3.connect(DB_FILE)
    temp_cur = temp_conn.cursor()
    temp_cur.execute("SELECT salt, totp_secret FROM config")
    row = temp_cur.fetchone()
    temp_conn.close()
    if not row:
        QMessageBox.critical(None, "Error", "Database corrupted.")
        sys.exit(1)
    salt, enc_secret = row
    try:
        enc = EncryptionManager(password, bytes(salt))
        try:
            totp_secret = enc.decrypt_text(enc_secret)
        except Exception:
            raise ValueError("Invalid password")
        
        totp = pyotp.TOTP(totp_secret)
        if not totp.verify(code):
            raise ValueError("Invalid authenticator code")
            
        # Successful login: connect DB and show main window
        db.connect(enc)
        db.init_db()  # ensure tables exist
        win = MainWindow(db)
        win.show()
        # Apply saved theme
        s = QSettings("MyJourney", "App")
        app_bg = s.value("app_bg", "#2b2b2b")
        app_fg = s.value("app_fg", "#ffffff")
        ed_bg = s.value("editor_bg", "#1e1e1e")
        ed_fg = s.value("editor_fg", "#ffffff")
        app.setStyleSheet(f"""
            QWidget {{ background-color: {app_bg}; color: {app_fg}; }}
            QTextEdit, QLineEdit, QListWidget {{ background-color: {ed_bg}; color: {ed_fg}; }}
        """)
        sys.exit(app.exec())
    except Exception as e:
        attempts += 1
        error_msg = str(e) if str(e) else "Unknown error"
        QMessageBox.warning(None, "Login failed", f"Error: {error_msg}\n\nAttempts remaining: {5-attempts}\n\nIf you've forgotten your password, you may need to restore from a backup or reset the database (data will be lost).")

QMessageBox.critical(None, "Too many attempts", "Application locked.")
sys.exit(1)