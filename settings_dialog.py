# settings_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox, QPushButton,
    QColorDialog, QWidget, QHBoxLayout, QFontComboBox, QSpinBox, QMessageBox
)
from PySide6.QtGui import QFont
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
        self.setWindowTitle("Settings")
        self.resize(400, 200)
        self.s = QSettings("MyJourney", "App")

        # helpers to safely coerce settings values
        def _as_int(key: str, default: int) -> int:
            try:
                val = self.s.value(key, default)
                # QSettings may return QVariant, str, or numeric; normalize safely
                if val is None:
                    return default
                if isinstance(val, int):
                    return val
                if isinstance(val, str):
                    try:
                        return int(val.strip())
                    except Exception:
                        return default
                try:
                    return int(val)  # fallback for other numeric types
                except Exception:
                    return default
            except Exception:
                return default

        def _as_str(key: str, default: str = "") -> str:
            try:
                val = self.s.value(key, default)
                return str(val) if val is not None else default
            except Exception:
                return default

        self._as_int = _as_int  # store for reuse
        self._as_str = _as_str

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

        # Default font for the app/editor
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Default font:"))
        self.font_combo = QFontComboBox()
        font_row.addWidget(self.font_combo)
        self.font_size = QSpinBox()
        self.font_size.setRange(6, 72)
        self.font_size.setValue(self._as_int("default_font_size", 12))
        font_row.addWidget(self.font_size)
        layout.addLayout(font_row)

        # Autosave options
        autosave_row = QHBoxLayout()
        autosave_row.addWidget(QLabel("Autosave message:"))
        self.autosave_msg = QLineEdit()
        autosave_row.addWidget(self.autosave_msg)
        autosave_row.addWidget(QLabel("Interval (s):"))
        self.autosave_interval = QSpinBox()
        self.autosave_interval.setRange(5, 3600)
        autosave_row.addWidget(self.autosave_interval)
        layout.addLayout(autosave_row)

        # Inactivity timeout
        inactivity_row = QHBoxLayout()
        inactivity_row.addWidget(QLabel("Inactivity timeout (min):"))
        self.inactivity_timeout = QSpinBox()
        self.inactivity_timeout.setRange(5, 120)
        inactivity_row.addWidget(self.inactivity_timeout)
        layout.addLayout(inactivity_row)

        # Theme save/load
        theme_row = QHBoxLayout()
        self.save_theme_btn = QPushButton("Save Theme")
        self.save_theme_btn.clicked.connect(self._save_theme)
        theme_row.addWidget(self.save_theme_btn)
        self.load_theme_btn = QPushButton("Load Theme")
        self.load_theme_btn.clicked.connect(self._load_theme)
        theme_row.addWidget(self.load_theme_btn)
        layout.addLayout(theme_row)

        # Load current
        self._refresh_buttons()
        self._refresh_autosave()
        self._refresh_inactivity()

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
        # load font settings
        df_family = self.s.value("default_font", "")
        if df_family:
            try:
                self.font_combo.setCurrentFont(QFont(str(df_family)))
            except Exception:
                pass
        self.font_size.setValue(self._as_int("default_font_size", 12))

    def _refresh_autosave(self):
        self.autosave_msg.setText(self._as_str("autosave_message", "Autosaved"))
        self.autosave_interval.setValue(self._as_int("autosave_interval", 30))

    def _refresh_inactivity(self):
        self.inactivity_timeout.setValue(self._as_int("inactivity_timeout", 30))

    def choose_color(self, key: str):
        current = self.s.value(key, "#000000")
        # Use QColorDialog to pick a color
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(parent=self)
        if c.isValid():
            hexc = c.name()
            self.s.setValue(key, hexc)
            self._refresh_buttons()

    def _save_theme(self):
        # Save current colors as custom theme
        self.s.setValue("custom_app_bg", self.s.value("app_bg", "#2b2b2b"))
        self.s.setValue("custom_app_fg", self.s.value("app_fg", "#ffffff"))
        self.s.setValue("custom_editor_bg", self.s.value("editor_bg", "#1e1e1e"))
        self.s.setValue("custom_editor_fg", self.s.value("editor_fg", "#ffffff"))
        QMessageBox.information(self, "Theme Saved", "Custom theme saved.")

    def _load_theme(self):
        # Load custom theme if exists
        custom_bg = self.s.value("custom_app_bg")
        if custom_bg:
            self.s.setValue("app_bg", custom_bg)
            self.s.setValue("app_fg", self.s.value("custom_app_fg", "#ffffff"))
            self.s.setValue("editor_bg", self.s.value("custom_editor_bg", "#1e1e1e"))
            self.s.setValue("editor_fg", self.s.value("custom_editor_fg", "#ffffff"))
            self._refresh_buttons()
            QMessageBox.information(self, "Theme Loaded", "Custom theme loaded.")
        else:
            QMessageBox.warning(self, "No Custom Theme", "No custom theme saved yet.")

    def accept(self) -> None:
        # save font selections
        f = self.font_combo.currentFont()
        self.s.setValue("default_font", f.family())
        self.s.setValue("default_font_size", self.font_size.value())
        # save autosave settings
        self.s.setValue("autosave_message", self.autosave_msg.text())
        self.s.setValue("autosave_interval", self.autosave_interval.value())
        # save inactivity timeout
        self.s.setValue("inactivity_timeout", self.inactivity_timeout.value())
        super().accept()