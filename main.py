"""Application entry point.

This script initializes the Qt application, runs the setup flow on
first run, and then prompts the user to log in. After successful
authentication the main window is shown.
"""

import sys
import sqlite3
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon
import pyotp
from encryption import EncryptionManager
from database import DatabaseManager, DB_FILE
from auth import SetupDialog, LoginDialog
from main_window import MainWindow
import logging
from datetime import datetime, timezone


app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setWindowIcon(QIcon("icon.ico"))

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
    QMessageBox.information(None, "Setup complete", "Account created. Now log in with your password and authenticator.")

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
    # setup simple logging for login attempts to help diagnose failures
    try:
        logging.basicConfig(filename='login_debug.log', level=logging.INFO)
        logging.info(f"{datetime.now(timezone.utc).isoformat()} - Login attempt")
    except Exception:
        pass
    try:
        enc = EncryptionManager(password, salt)
        try:
            totp_secret = enc.decrypt_text(enc_secret)
            logging.info("Decryption: OK")
        except Exception as de:
            logging.exception("Decryption failed")
            raise
        totp = pyotp.TOTP(totp_secret)
        valid = totp.verify(code)
        logging.info(f"TOTP verify: {valid}")
        if not valid:
            raise ValueError("Invalid TOTP")
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
    except Exception:
        attempts += 1
        try:
            logging.exception("Login exception")
        except Exception:
            pass
        QMessageBox.warning(None, "Login failed", f"Wrong password or code. Attempts left: {5-attempts}")

QMessageBox.critical(None, "Too many attempts", "Application locked.")
sys.exit(1)