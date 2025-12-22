# settings_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox, QPushButton, QColorDialog, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QSettings

class SettingsDialog(QDialog):
    """Dialog to pick theme colors and store them in QSettings.

    The dialog exposes simple color buttons for the application and
    editor foreground/background. Selections are saved immediately so
    the rest of the app can read them on next run or when the dialog
    is accepted.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Settings")
        self.resize(400, 200)
        self.s = QSettings("MyJourney", "App")

        layout = QVBoxLayout(self)

        # App background/foreground
        app_row = QHBoxLayout()
        app_row.addWidget(QLabel("App background:"))
        self.app_bg_btn = QPushButton()
        self.app_bg_btn.clicked.connect(lambda: self.choose_color("app_bg"))
        app_row.addWidget(self.app_bg_btn)
        app_row.addWidget(QLabel("App foreground:"))
        self.app_fg_btn = QPushButton()
        self.app_fg_btn.clicked.connect(lambda: self.choose_color("app_fg"))
        app_row.addWidget(self.app_fg_btn)
        layout.addLayout(app_row)

        # Editor colors
        ed_row = QHBoxLayout()
        ed_row.addWidget(QLabel("Editor background:"))
        self.ed_bg_btn = QPushButton()
        self.ed_bg_btn.clicked.connect(lambda: self.choose_color("editor_bg"))
        ed_row.addWidget(self.ed_bg_btn)
        ed_row.addWidget(QLabel("Editor foreground:"))
        self.ed_fg_btn = QPushButton()
        self.ed_fg_btn.clicked.connect(lambda: self.choose_color("editor_fg"))
        ed_row.addWidget(self.ed_fg_btn)
        layout.addLayout(ed_row)

        # Load current
        self._refresh_buttons()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_buttons(self):
        app_bg = self.s.value("app_bg", "#2b2b2b")
        app_fg = self.s.value("app_fg", "#ffffff")
        ed_bg = self.s.value("editor_bg", "#1e1e1e")
        ed_fg = self.s.value("editor_fg", "#ffffff")
        self.app_bg_btn.setStyleSheet(f"background-color: {app_bg}")
        self.app_fg_btn.setStyleSheet(f"background-color: {app_fg}")
        self.ed_bg_btn.setStyleSheet(f"background-color: {ed_bg}")
        self.ed_fg_btn.setStyleSheet(f"background-color: {ed_fg}")

    def choose_color(self, key: str):
        current = self.s.value(key, "#000000")
        # Use QColorDialog to pick a color
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(parent=self)
        if c.isValid():
            hexc = c.name()
            self.s.setValue(key, hexc)
            self._refresh_buttons()