# main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QCalendarWidget, QListWidget, QListWidgetItem, QTextEdit,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QMessageBox, QMenu, QToolBar
)
from PySide6.QtCore import Qt, QDate, QSettings, QUrl
from PySide6.QtGui import QTextCharFormat, QDesktopServices, QAction, QTextDocument  # for stripping HTML in search
from entry import Entry
from settings_dialog import SettingsDialog
import base64
import os
from datetime import datetime

class MainWindow(QMainWindow):
    """Main application window showing calendar and entries.

    The window loads entries from the provided `db` manager and offers
    basic editing, attachment handling, search and export.
    """

    def __init__(self, db):
        super().__init__()
        self.db = db
        # load current entries into memory
        self.entries = db.get_all_entries()
        self.current_entry = None
        self.setWindowTitle("MyJourney")
        self.resize(1200, 800)
        self._build_ui()
        self._load_calendar_dates()
        self._load_entry_list()
        self._apply_theme()

    def _build_ui(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        file_menu.addAction("New Entry", self.new_entry, "Ctrl+N")
        file_menu.addAction("Delete Entry", self.delete_entry)
        file_menu.addSeparator()
        file_menu.addAction("Export Entry to HTML", self.export_entry)
        file_menu.addAction("Backup Database", self.backup_db)
        menu.addAction("Theme Settings", self.open_settings)

        toolbar = QToolBar()
        toolbar.addAction("New", self.new_entry)
        self.addToolBar(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.filter_by_date)
        left_layout.addWidget(self.calendar)
        self.entry_list = QListWidget()
        self.entry_list.itemClicked.connect(self.load_entry)
        left_layout.addWidget(self.entry_list)
        self.search = QLineEdit(placeholderText="Search titles, content, tags...")
        self.search.textChanged.connect(self.filter_by_search)
        left_layout.addWidget(self.search)
        splitter.addWidget(left)
        # Right panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        title_l = QHBoxLayout()
        title_l.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        title_l.addWidget(self.title_edit)
        right_layout.addLayout(title_l)
        self.editor = QTextEdit()
        right_layout.addWidget(self.editor)
        btn_l = QHBoxLayout()
        self.insert_img_btn = QPushButton("Insert Image Inline")
        self.insert_img_btn.clicked.connect(self.insert_image)
        btn_l.addWidget(self.insert_img_btn)
        self.attach_btn = QPushButton("Attach File")
        self.attach_btn.clicked.connect(self.attach_file)
        btn_l.addWidget(self.attach_btn)
        right_layout.addLayout(btn_l)
        self.attach_list = QListWidget()
        self.attach_list.itemDoubleClicked.connect(self.save_attachment_as)
        right_layout.addWidget(QLabel("Attachments (double-click to save):"))
        right_layout.addWidget(self.attach_list)
        tag_l = QHBoxLayout()
        tag_l.addWidget(QLabel("Tags:"))
        self.tags_edit = QLineEdit(placeholderText="comma separated")
        tag_l.addWidget(self.tags_edit)
        right_layout.addLayout(tag_l)
        save_btn = QPushButton("Save Entry")
        save_btn.clicked.connect(self.save_current_entry)
        right_layout.addWidget(save_btn)
        splitter.addWidget(right)
        splitter.setSizes([350, 850])
        self.setCentralWidget(splitter)

    def _apply_theme(self):
        s = QSettings("MyJourney", "App")
        app_bg = s.value("app_bg", "#2b2b2b")
        app_fg = s.value("app_fg", "#ffffff")
        ed_bg = s.value("editor_bg", "#1e1e1e")
        ed_fg = s.value("editor_fg", "#ffffff")
        stylesheet = f"""
            QWidget {{ background-color: {app_bg}; color: {app_fg}; }}
            QTextEdit {{ background-color: {ed_bg}; color: {ed_fg}; }}
            QLineEdit, QListWidget {{ background-color: {ed_bg}; color: {ed_fg}; }}
        """
        self.setStyleSheet(stylesheet)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._apply_theme()

    def _load_calendar_dates(self):
        dates = self.db.get_dates_with_entries()
        fmt = QTextCharFormat()
        fmt.setForeground(Qt.GlobalColor.white)
        fmt.setBackground(Qt.GlobalColor.blue)
        fmt.setFontWeight(75)
        for d_str in dates:
            qd = QDate.fromString(d_str, "yyyy-MM-dd")
            self.calendar.setDateTextFormat(qd, fmt)

    def _load_entry_list(self, entries=None):
        self.entry_list.clear()
        to_show = entries or self.entries
        to_show = sorted(to_show, key=lambda e: e.date, reverse=True)
        for entry in to_show:
            text = f"{entry.date} — {entry.title or 'Untitled'}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.entry_list.addItem(item)

    def filter_by_date(self, qdate: QDate):
        dstr = qdate.toString("yyyy-MM-dd")
        filtered = [e for e in self.entries if e.date == dstr]
        self._load_entry_list(filtered)

    def filter_by_search(self):
        query = self.search.text().strip().lower()
        if not query:
            self._load_entry_list()
            return
        filtered = []
        for e in self.entries:
            plain = QTextDocument()
            plain.setHtml(e.content)
            if (query in e.title.lower() or
                query in plain.toPlainText().lower() or
                any(query in t.lower() for t in e.tags)):
                filtered.append(e)
        self._load_entry_list(filtered)

    def load_entry(self, item: QListWidgetItem):
        self.current_entry = item.data(Qt.ItemDataRole.UserRole)
        assert self.current_entry is not None
        self.title_edit.setText(self.current_entry.title)
        self.editor.setHtml(self.current_entry.content)
        self.tags_edit.setText(", ".join(self.current_entry.tags))
        self.attach_list.clear()
        for i, att in enumerate(self.current_entry.attachments):
            list_item = QListWidgetItem(att["filename"])
            list_item.setData(Qt.ItemDataRole.UserRole, i)
            self.attach_list.addItem(list_item)

    def new_entry(self):
        today = str(datetime.today().date())
        new_e = Entry(entry_date=today)
        self.entries.append(new_e)
        self.current_entry = new_e
        self.title_edit.clear()
        self.editor.clear()
        self.tags_edit.clear()
        self.attach_list.clear()
        self._load_entry_list()
        self._load_calendar_dates()

    def insert_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp)")
        if not path:
            return
        with open(path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        ext = os.path.splitext(path)[1].lower()
        mime = "png" if ext == ".png" else "jpeg"
        html = f'<img src="data:image/{mime};base64,{b64}" />'
        self.editor.textCursor().insertHtml(html)

    def attach_file(self):
        if not self.current_entry:
            self.new_entry()
        path, _ = QFileDialog.getOpenFileName(self, "Attach File")
        if not path:
            return
        filename = os.path.basename(path)
        with open(path, "rb") as f:
            data = f.read()
        assert self.current_entry is not None
        self.current_entry.attachments.append({"filename": filename, "data": data})
        i = len(self.current_entry.attachments) - 1
        item = QListWidgetItem(filename)
        item.setData(Qt.ItemDataRole.UserRole, i)
        self.attach_list.addItem(item)

    def save_attachment_as(self, item: QListWidgetItem):
        idx = item.data(Qt.ItemDataRole.UserRole)
        assert self.current_entry is not None
        att = self.current_entry.attachments[idx]
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Attachment", att["filename"])
        if save_path:
            with open(save_path, "wb") as f:
                f.write(att["data"])

    def save_current_entry(self):
        if not self.current_entry:
            QMessageBox.warning(self, "No entry", "Create or select an entry first.")
            return
        self.current_entry.title = self.title_edit.text()
        self.current_entry.content = self.editor.toHtml()
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        self.current_entry.tags = tags
        self.db.save_entry(self.current_entry)
        self._load_entry_list()
        self._load_calendar_dates()
        QMessageBox.information(self, "Saved", "Entry saved successfully.")

    def delete_entry(self):
        if not self.current_entry or self.current_entry.id is None:
            return
        reply = QMessageBox.question(self, "Delete", "Permanently delete this entry?")
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_entry(self.current_entry.id)
            self.entries.remove(self.current_entry)
            self.current_entry = None
            self.title_edit.clear()
            self.editor.clear()
            self.tags_edit.clear()
            self.attach_list.clear()
            self._load_entry_list()
            self._load_calendar_dates()

    def export_entry(self):
        if not self.current_entry:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export to HTML", f"{self.current_entry.title or 'entry'}.html", "HTML (*.html)")
        if path:
            full_html = f"<html><head><title>{self.current_entry.title}</title></head><body>{self.current_entry.content}</body></html>"
            with open(path, "w", encoding="utf-8") as f:
                f.write(full_html)

    def backup_db(self):
        path, _ = QFileDialog.getSaveFileName(self, "Backup Database", "myjourney_backup.db")
        if path:
            import shutil
            shutil.copy("myjourney.db", path)
            QMessageBox.information(self, "Backup", "Database backed up.")