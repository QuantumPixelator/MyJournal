"""Authentication dialogs used at startup.

These dialogs are small UI helpers: one for initial setup (create a
master password and show a QR code for TOTP) and a login dialog that
asks for the master password and the one-time code.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox, QMessageBox
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import pyotp
import qrcode
from io import BytesIO


class SetupDialog(QDialog):
    """Initial setup dialog.

    The dialog collects a master password (with confirmation) and
    generates a TOTP secret shown as a QR code for the user's
    authenticator app.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyJourney - Initial Setup")
        layout = QVBoxLayout(self)
        self.pw1 = QLineEdit()
        self.pw1.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw2 = QLineEdit()
        self.pw2.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel("Create master password:"))
        layout.addWidget(self.pw1)
        layout.addWidget(QLabel("Confirm password:"))
        layout.addWidget(self.pw2)
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.qr_label)
        layout.addWidget(QLabel("Scan this QR code with an authenticator app (Google Authenticator, Authy, etc.)."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.secret = pyotp.random_base32()
        self._generate_qr()

    def _generate_qr(self):
        """Create and display the QR code for the TOTP secret."""
        totp = pyotp.TOTP(self.secret)
        uri = totp.provisioning_uri(name="MyJourney", issuer_name="Python")
        qr = qrcode.make(uri)
        bio = BytesIO()
        qr.save(bio, "PNG")
        pix = QPixmap()
        pix.loadFromData(bio.getvalue())
        self.qr_label.setPixmap(pix.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def validate(self):
        """Check that the two password fields match and are not empty."""
        if self.pw1.text() == self.pw2.text() and self.pw1.text():
            self.password: str = self.pw1.text()
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Passwords do not match or are empty.")


class LoginDialog(QDialog):
    """Simple login dialog asking for master password and TOTP code."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyJourney - Login")
        layout = QVBoxLayout(self)
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel("Master password:"))
        layout.addWidget(self.pw)
        self.totp = QLineEdit()
        self.totp.setPlaceholderText("6-digit code")
        layout.addWidget(QLabel("Authenticator code:"))
        layout.addWidget(self.totp)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)