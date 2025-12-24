# main_window.py
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QCalendarWidget, QListWidget, QListWidgetItem, QTextEdit,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QMessageBox, QMenu, QToolBar, QFontComboBox, QSpinBox, QToolButton, QInputDialog
)
from PySide6.QtCore import Qt, QDate, QSettings, QUrl, QTimer, QEvent, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import (
    QTextCharFormat, QDesktopServices, QAction, QTextDocument, QColor, QFont,
    QKeySequence, QTextListFormat, QTextCursor, QTextImageFormat, QTextTableFormat,
    QTextBlockFormat, QTextFrameFormat, QShortcut, QPixmap, QPainter, QIcon, QImage,
    QPalette
)
from entry import Entry
from settings_dialog import SettingsDialog
import base64
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from PySide6.QtCore import QPoint


class ResizableTextEdit(QTextEdit):
    """QTextEdit subclass that supports drag-to-resize for images while preserving aspect ratio.

    Click on an image then drag horizontally to change width; height is adjusted to keep aspect ratio.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._resizing = False
        self._resize_cursor = None
        self._start_pos = QPoint()
        self._orig_w = 0
        self._orig_h = 0

    def mousePressEvent(self, event):
        try:
            cursor = self.cursorForPosition(event.pos())
            cf = cursor.charFormat()
            if cf.isImageFormat():
                self._resizing = True
                self._resize_cursor = cursor
                self._start_pos = event.pos()
                imgfmt = cf.toImageFormat()
                self._orig_w = int(imgfmt.width()) if imgfmt.width() else 0
                self._orig_h = int(imgfmt.height()) if imgfmt.height() else 0
                # if sizes not set, try to read actual image resource
                if self._orig_w == 0 or self._orig_h == 0:
                    name = imgfmt.name()
                    try:
                        res = self.document().resource(QTextDocument.ResourceType.ImageResource, QUrl(name))
                        if isinstance(res, QImage):
                            self._orig_w = res.width()
                            self._orig_h = res.height()
                        else:
                            try:
                                pm = QPixmap.fromImage(res)
                                self._orig_w = pm.width()
                                self._orig_h = pm.height()
                            except Exception:
                                pass
                    except Exception:
                        pass
                # accept the event and do not propagate further
                return
        except Exception:
            pass
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_resizing', False) and self._resize_cursor:
            try:
                dx = event.pos().x() - self._start_pos.x()
                new_w = max(1, int(self._orig_w + dx))
                if self._orig_w > 0 and self._orig_h > 0:
                    ratio = self._orig_h / float(self._orig_w)
                    new_h = int(round(new_w * ratio))
                else:
                    new_h = int(self._orig_h or new_w)
                # apply format
                cur = self._resize_cursor
                imgfmt = cur.charFormat().toImageFormat()
                newfmt = QTextImageFormat(imgfmt)
                newfmt.setWidth(new_w)
                newfmt.setHeight(new_h)
                try:
                    cur.beginEditBlock()
                    cur.select(QTextCursor.SelectionType.WordUnderCursor)
                    cur.setCharFormat(newfmt)
                finally:
                    try:
                        cur.endEditBlock()
                    except Exception:
                        pass
                # also inject width/height attributes into the HTML so they persist
                try:
                    src = newfmt.name()
                    html = self.toHtml()
                    import re
                    pattern = re.compile(r"(<img[^>]*src=[\'\"]%s[\'\"][^>]*)(>)" % re.escape(src))
                    repl = r"\1 width=\"%d\" height=\"%d\"\2" % (new_w, new_h)
                    new_html = pattern.sub(repl, html, count=1)
                    if new_html != html:
                        self.blockSignals(True)
                        try:
                            self.setHtml(new_html)
                        finally:
                            self.blockSignals(False)
                except Exception:
                    pass
                # mark dirty on owning window
                try:
                    w = self.window()
                    if hasattr(w, '_dirty'):
                        setattr(w, '_dirty', True)
                except Exception:
                    pass
                return
            except Exception:
                pass
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_resizing', False):
            self._resizing = False
            self._resize_cursor = None
            return
        super().mouseReleaseEvent(event)

    def insertFromMimeData(self, source):
        """Override to handle pasting into code blocks better."""
        if source.hasText():
            # Check if we are in a code block (heuristic: monospace font)
            font = self.currentFont()
            mono_fonts = ['Consolas', 'Courier New', 'Courier', 'Monospace', 'Lucida Console', 'Menlo', 'Monaco']
            if any(mf.lower() in font.family().lower() for mf in mono_fonts):
                self.insertPlainText(source.text())
                return
        super().insertFromMimeData(source)


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
        # ensure entries without font metadata reflect app default in UI
        self._apply_defaults_to_entries()
        self.current_entry = None
        self.setWindowTitle("MyJourney")
        self.resize(1200, 800)
        self._build_ui()
        self._apply_theme()
        self._load_calendar_dates()
        self._load_entry_list()
        # Setup inactivity timer for auto-logout
        s = QSettings("MyJourney", "App")
        timeout_minutes = int(s.value("inactivity_timeout", 30))  # type: ignore
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setInterval(timeout_minutes * 60 * 1000)  # minutes to milliseconds
        self.inactivity_timer.timeout.connect(self._logout_due_to_inactivity)
        self.inactivity_timer.start()

    def _build_ui(self):
        """Initialize and arrange all UI components."""
        # prevent signal handlers from reacting during initialization
        self._initializing = True
        
        self._setup_menus()
        self._setup_toolbar()
        self._setup_main_layout()
        self._setup_shortcuts()
        self._setup_timers_and_settings()
        
        # initialization complete
        self._initializing = False

    def _setup_menus(self):
        """Create the menu bar and its actions."""
        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        file_menu.addAction("New Entry", self.new_entry, "Ctrl+N")
        file_menu.addAction("Delete Entry", self.delete_entry)
        file_menu.addSeparator()
        file_menu.addAction("Backup Database", self.backup_db)
        
        edit_menu = menu.addMenu("Edit")
        edit_menu.addAction("Save Entry", lambda: self.save_current_entry(show_message=True), "Ctrl+S")
        edit_menu.addAction("Find", lambda: self.search.setFocus(), "Ctrl+F")

        view_menu = menu.addMenu("View")
        view_menu.addAction("Toggle Theme", self._toggle_theme)
        view_menu.addAction("Journal Statistics", self.show_statistics)
        
        export_menu = menu.addMenu("Export")
        export_menu.addAction("Export All", self.export_all_entries)
        export_menu.addAction("Export Current", self.export_current_entry)

        menu.addAction("Settings", self.open_settings)
        menu.addAction("About", self.show_about)

    def _setup_toolbar(self):
        """Create the main toolbar with font and formatting controls."""
        toolbar = QToolBar()
        toolbar.addAction("New", self.new_entry)
        
        # Font selector
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(lambda f: self._set_font_family(f.family()))
        self.font_combo.currentFontChanged.connect(self._toolbar_font_changed)
        toolbar.addWidget(self.font_combo)
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(6, 72)
        self.font_size.setValue(12)
        self.font_size.valueChanged.connect(self._set_font_size)
        self.font_size.valueChanged.connect(self._toolbar_font_size_changed)
        toolbar.addWidget(self.font_size)
        
        # Font size adjustments
        inc_btn = QToolButton()
        inc_btn.setToolTip("Increase font size")
        inc_btn.setIcon(self._make_icon("+"))
        inc_btn.clicked.connect(lambda: self._change_selection_font_size(1))
        toolbar.addWidget(inc_btn)
        
        dec_btn = QToolButton()
        dec_btn.setToolTip("Decrease font size")
        dec_btn.setIcon(self._make_icon("-"))
        dec_btn.clicked.connect(lambda: self._change_selection_font_size(-1))
        toolbar.addWidget(dec_btn)
        
        # Theme toggle
        theme_toggle = QToolButton()
        theme_toggle.setToolTip("Toggle Light/Dark Theme")
        theme_toggle.setIcon(self._make_icon("T"))
        theme_toggle.clicked.connect(self._toggle_theme)
        toolbar.addWidget(theme_toggle)
        
        # List formatting
        bullet_btn = QToolButton()
        bullet_btn.setToolTip("Bulleted list")
        bullet_btn.setIcon(self._make_icon("•"))
        bullet_btn.clicked.connect(self._insert_bullet_list)
        toolbar.addWidget(bullet_btn)
        
        number_btn = QToolButton()
        number_btn.setToolTip("Numbered list")
        number_btn.setIcon(self._make_icon("1."))
        number_btn.clicked.connect(self._insert_numbered_list)
        toolbar.addWidget(number_btn)

        # Table, Code, Link
        table_btn = QToolButton()
        table_btn.setToolTip("Insert Table")
        table_btn.setIcon(self._make_icon("田"))
        table_btn.clicked.connect(self._insert_table)
        toolbar.addWidget(table_btn)

        code_btn = QToolButton()
        code_btn.setToolTip("Insert Code Block")
        code_btn.setIcon(self._make_icon("{}"))
        code_btn.clicked.connect(self._insert_code_block)
        toolbar.addWidget(code_btn)

        link_btn = QToolButton()
        link_btn.setToolTip("Insert Link")
        link_btn.setIcon(self._make_icon("🔗"))
        link_btn.clicked.connect(self._insert_link)
        toolbar.addWidget(link_btn)

        def _get_icon(name: str, letter: str):
            base = os.path.join(os.path.dirname(__file__), "assets")
            path_svg = os.path.join(base, f"{name}.svg")
            if os.path.exists(path_svg):
                return QIcon(path_svg)
            return self._make_icon(letter)

        # Style buttons
        self.bold_btn = QToolButton()
        self.bold_btn.setIcon(_get_icon("bold", "B"))
        self.bold_btn.setCheckable(True)
        self.bold_btn.clicked.connect(self._toggle_bold)
        toolbar.addWidget(self.bold_btn)
        
        self.italic_btn = QToolButton()
        self.italic_btn.setIcon(_get_icon("italic", "I"))
        self.italic_btn.setCheckable(True)
        self.italic_btn.clicked.connect(self._toggle_italic)
        toolbar.addWidget(self.italic_btn)
        
        self.underline_btn = QToolButton()
        self.underline_btn.setIcon(_get_icon("underline", "U"))
        self.underline_btn.setCheckable(True)
        self.underline_btn.clicked.connect(self._toggle_underline)
        toolbar.addWidget(self.underline_btn)
        
        self.strike_btn = QToolButton()
        self.strike_btn.setIcon(_get_icon("strike", "S"))
        self.strike_btn.setCheckable(True)
        self.strike_btn.clicked.connect(self._toggle_strike)
        toolbar.addWidget(self.strike_btn)
        
        color_btn = QToolButton()
        color_btn.setIcon(_get_icon("color", "C"))
        color_btn.clicked.connect(self._choose_color)
        toolbar.addWidget(color_btn)
        
        apply_btn = QToolButton()
        apply_btn.setToolTip("Apply font to entire entry")
        apply_btn.setIcon(_get_icon("apply", "A"))
        apply_btn.clicked.connect(self._apply_font_to_entry)
        toolbar.addWidget(apply_btn)
        
        undo_btn = QToolButton()
        undo_btn.setToolTip("Undo last apply")
        undo_btn.setIcon(_get_icon("undo", "<"))
        undo_btn.clicked.connect(self._undo_apply)
        undo_btn.setEnabled(False)
        self._undo_btn = undo_btn
        toolbar.addWidget(undo_btn)
        
        self.addToolBar(toolbar)

    def _setup_main_layout(self):
        """Create the main splitter layout with left and right panels."""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        # Create fresh calendar widget with default settings
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.ISOWeekNumbers)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.calendar.clicked.connect(self.filter_by_date)
        left_layout.addWidget(self.calendar)
        
        self.entry_list = QListWidget()
        self.entry_list.itemClicked.connect(self.load_entry)
        self.entry_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entry_list.customContextMenuRequested.connect(self._entry_list_context_menu)
        left_layout.addWidget(self.entry_list)
        
        self.search = QLineEdit(placeholderText="Search titles, content, tags...")
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)  # 300ms debounce
        self._search_timer.timeout.connect(self.filter_by_search)
        self.search.textChanged.connect(lambda: self._search_timer.start())
        left_layout.addWidget(self.search)
        splitter.addWidget(left)
        
        # Right panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        
        title_l = QHBoxLayout()
        title_l.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter entry title...")
        self.title_edit.textEdited.connect(self._on_title_edited)
        title_l.addWidget(self.title_edit)
        right_layout.addLayout(title_l)
        
        self.editor = ResizableTextEdit()
        self.editor.setPlaceholderText("Write your journal entry here...")
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self._editor_context_menu)
        self.editor.textChanged.connect(self._on_editor_text_changed)
        self.editor.cursorPositionChanged.connect(self._update_toolbar_from_cursor)
        right_layout.addWidget(self.editor, stretch=3)
        
        btn_l = QHBoxLayout()
        self.insert_img_btn = QPushButton("Insert Image Inline")
        self.insert_img_btn.clicked.connect(self.insert_image)
        btn_l.addWidget(self.insert_img_btn)
        
        self.attach_btn = QPushButton("Attach File")
        self.attach_btn.clicked.connect(self.attach_file)
        btn_l.addWidget(self.attach_btn)
        right_layout.addLayout(btn_l)
        
        self.attach_list = QListWidget()
        self.attach_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.attach_list.customContextMenuRequested.connect(self._attachment_context_menu)
        self.attach_list.itemDoubleClicked.connect(self.save_attachment_as)
        right_layout.addWidget(QLabel("Attachments (double-click to save/insert):"))
        right_layout.addWidget(self.attach_list, stretch=1)
        
        tag_l = QHBoxLayout()
        tag_l.addWidget(QLabel("Tags:"))
        self.tags_edit = QLineEdit(placeholderText="comma separated")
        tag_l.addWidget(self.tags_edit)
        right_layout.addLayout(tag_l)

        # Per-entry font controls
        entry_font_row = QHBoxLayout()
        entry_font_row.addWidget(QLabel("Entry font:"))
        self.entry_font_combo = QFontComboBox()
        entry_font_row.addWidget(self.entry_font_combo)
        self.entry_font_size = QSpinBox()
        self.entry_font_size.setRange(6, 72)
        entry_font_row.addWidget(self.entry_font_size)
        apply_entry_font_btn = QPushButton("Set for Entry")
        apply_entry_font_btn.clicked.connect(self._apply_entry_font_from_ui)
        entry_font_row.addWidget(apply_entry_font_btn)
        right_layout.addLayout(entry_font_row)
        
        # Save / Discard buttons
        btn_l = QHBoxLayout()
        save_btn = QPushButton("Save Entry")
        save_btn.clicked.connect(lambda: self.save_current_entry(show_message=True))
        btn_l.addWidget(save_btn)
        discard_btn = QPushButton("Discard Entry")
        discard_btn.clicked.connect(self.discard_current_entry)
        btn_l.addWidget(discard_btn)
        right_layout.addLayout(btn_l)
        
        splitter.addWidget(right)
        splitter.setSizes([350, 850])
        self.setCentralWidget(splitter)

    def _setup_shortcuts(self):
        """Initialize keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(self._toggle_bold)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(self._toggle_italic)
        QShortcut(QKeySequence("Ctrl+U"), self).activated.connect(self._toggle_underline)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self._toggle_strike)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._undo_apply)
        QShortcut(QKeySequence("Ctrl+]"), self).activated.connect(lambda: self._change_selection_font_size(1))
        QShortcut(QKeySequence("Ctrl+["), self).activated.connect(lambda: self._change_selection_font_size(-1))
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(lambda: self.save_current_entry(show_message=True))
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(lambda: self.search.setFocus())

    def _setup_timers_and_settings(self):
        """Initialize settings, timers, and dirty tracking."""
        s = QSettings("MyJourney", "App")
        df = s.value("default_font", "")
        df_size = int(s.value("default_font_size", 12))  # type: ignore
        
        try:
            self.font_combo.blockSignals(True)
            if df:
                try:
                    self.font_combo.setCurrentFont(QFont(str(df)))
                except Exception:
                    pass
        finally:
            self.font_combo.blockSignals(False)
            
        try:
            self.font_size.blockSignals(True)
            self.font_size.setValue(df_size)
        finally:
            self.font_size.blockSignals(False)
            
        self._apply_app_default_font()
        
        self._dirty = False
        self._suppress_dirty = False
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30 * 1000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

    def _apply_theme(self):
        """Apply the current theme colors to the application widgets."""
        s = QSettings("MyJourney", "App")
        app_bg = str(s.value("app_bg", "#2b2b2b"))
        app_fg = str(s.value("app_fg", "#ffffff"))
        ed_bg = str(s.value("editor_bg", "#1e1e1e"))
        ed_fg = str(s.value("editor_fg", "#ffffff"))
        
        # Header color is always red (#8b0000) for calendar highlights
        cal_header_bg = "#8b0000"
        cal_header_fg = "#ffffff"
        self.cal_header_bg = cal_header_bg
        self.cal_header_fg = cal_header_fg
        
        # Set the main stylesheet for the window
        stylesheet = f"""
            QWidget {{ background-color: {app_bg}; color: {app_fg}; }}
            QTextEdit {{ background-color: {ed_bg}; color: {ed_fg}; }}
            QLineEdit, QListWidget {{ background-color: {ed_bg}; color: {ed_fg}; }}
            
            /* Calendar - Complete styling from scratch */
            QCalendarWidget {{
                background-color: {app_bg};
            }}
            
            /* Navigation bar at top */
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {cal_header_bg};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar QToolButton {{
                background-color: {cal_header_bg};
                color: {cal_header_fg};
                border: none;
                min-width: 30px;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar QToolButton:hover {{
                background-color: #a00000;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar QSpinBox {{
                background-color: {cal_header_bg};
                color: {cal_header_fg};
                border: none;
            }}
            
            /* Day grid */
            QCalendarWidget QAbstractItemView {{
                background-color: {app_bg};
                color: {app_fg};
                selection-background-color: {cal_header_bg};
                selection-color: {cal_header_fg};
                gridline-color: {app_bg};
                border: none;
            }}
            
            /* Headers (weekday names and week numbers) */
            QCalendarWidget QHeaderView::section {{
                background-color: {cal_header_bg};
                color: {cal_header_fg};
                font-weight: bold;
                border: none;
                padding: 4px;
            }}
            
            /* Corner button between headers */
            QCalendarWidget QTableCornerButton::section {{
                background-color: {cal_header_bg};
                border: none;
            }}
        """
        self.setStyleSheet(stylesheet)
        
        # Apply calendar-specific formatting with format objects
        self._setup_calendar_formats(cal_header_bg, cal_header_fg, app_bg, app_fg)
        
        # Fix link colors in editor using direct HTML/CSS injection
        self._fix_editor_link_colors(cal_header_bg)

    def _setup_calendar_formats(self, header_bg: str, header_fg: str, day_bg: str, day_fg: str):
        """Apply text character formats for calendar dates with red header highlight."""
        # Set format for header (weekends can use header color)
        header_fmt = QTextCharFormat()
        header_fmt.setBackground(QColor(header_bg))
        header_fmt.setForeground(QColor(header_fg))
        
        # Weekend format (Saturdays and Sundays) - use header colors
        weekend_fmt = QTextCharFormat()
        weekend_fmt.setForeground(QColor(header_fg))
        weekend_fmt.setBackground(QColor(day_bg))
        
        # Apply to calendar
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, weekend_fmt)
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, weekend_fmt)
        
    def _fix_editor_link_colors(self, color: str):
        """Force all links in the editor to use the specified color."""
        palette = self.editor.palette()
        palette.setColor(QPalette.ColorRole.Link, QColor(color))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(color))
        self.editor.setPalette(palette)

        css = f"""
        a, a:link, a:visited, a:hover, a:active {{
            color: {color} !important;
            text-decoration: underline !important;
        }}
        """
        self.editor.document().setDefaultStyleSheet(css)
        QTimer.singleShot(0, self._recolor_all_links)

    def _recolor_all_links(self):
        """Iterate through the document and force all links to use the theme color."""
        if not hasattr(self, 'cal_header_bg'):
            return
        color = self.cal_header_bg
        doc = self.editor.document()
        target = QColor(color)
        self.editor.blockSignals(True)
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        try:
            block = doc.begin()
            while block.isValid():
                it = block.begin()
                while not it.atEnd():
                    fragment = it.fragment()
                    if fragment.isValid():
                        fmt = fragment.charFormat()
                        if fmt.isAnchor() and fmt.foreground().color() != target:
                            new_fmt = QTextCharFormat(fmt)
                            new_fmt.setForeground(target)
                            # Create a cursor and select the fragment to apply the format
                            frag_cursor = QTextCursor(doc)
                            frag_cursor.setPosition(fragment.position())
                            frag_cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, fragment.length())
                            frag_cursor.setCharFormat(new_fmt)
                    it += 1
                block = block.next()
        finally:
            cursor.endEditBlock()
            self.editor.blockSignals(False)

    def _autosave(self):
        """Automatically save the current entry if it has been modified."""
        if getattr(self, '_saving', False):
            return
        if not getattr(self, '_dirty', False):
            return
        if not self.current_entry:
            return
        # don't autosave entries without a title
        try:
            title = self.title_edit.text().strip() if hasattr(self, 'title_edit') else ''
            if not title:
                return
        except Exception:
            # on any unexpected error reading the title, skip autosave to avoid data loss
            return
        # perform silent save
        self._saving = True
        try:
            self.save_current_entry(show_message=False)
            # show a brief status indicator
            try:
                self.statusBar().showMessage("Autosaved", 2000)
            except Exception:
                pass
        except Exception:
            # autosave failed; ignore to avoid interrupting the user
            pass
        finally:
            self._saving = False

    def _apply_app_default_font(self):
        """Apply the application-wide default font to the editor."""
        s = QSettings("MyJourney", "App")
        df = s.value("default_font", "")
        df_size = int(s.value("default_font_size", 12))  # type: ignore
        if df:
            try:
                qf = QFont(str(df), int(df_size))
                # apply to editor/default-entry area only (do not change control/widget fonts)
                try:
                    self.editor.setFont(qf)
                except Exception:
                    pass
                # apply as default in entry font controls if not set
                if hasattr(self, 'entry_font_combo'):
                    try:
                        self.entry_font_combo.setCurrentFont(QFont(str(df)))
                    except Exception:
                        pass
                if hasattr(self, 'entry_font_size'):
                    self.entry_font_size.setValue(df_size)
            except Exception:
                pass

    def _toolbar_font_changed(self, qfont: QFont):
        """Handle font family changes from the main toolbar."""
        # don't persist while initializing UI
        if getattr(self, '_initializing', False):
            return
        try:
            fam = qfont.family()
            
            # Apply to selection if it exists
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                fmt = QTextCharFormat()
                fmt.setFontFamily(fam)
                self._merge_format_on_selection(fmt)
                return

            # If no selection, set the current char format so typing from here uses the new font
            fmt = self.editor.currentCharFormat()
            fmt.setFontFamily(fam)
            self.editor.setCurrentCharFormat(fmt)
            # Also set the editor's default font so the cursor reflects the change immediately
            editor_font = self.editor.font()
            editor_font.setFamily(fam)
            self.editor.setFont(editor_font)

            # Also update app default
            s = QSettings("MyJourney", "App")
            s.setValue("default_font", fam)
            s.setValue("default_font_size", int(self.font_size.value()))
            # apply immediately
            self._apply_app_default_font()
        except Exception:
            pass

    def _toolbar_font_size_changed(self, value: int):
        """Handle font size changes from the main toolbar."""
        # don't persist while initializing UI
        if getattr(self, '_initializing', False):
            return
        try:
            # Apply to selection if it exists
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                fmt = QTextCharFormat()
                fmt.setFontPointSize(float(value))
                self._merge_format_on_selection(fmt)
                return

            # If no selection, set the current char format so typing from here uses the new size
            fmt = self.editor.currentCharFormat()
            fmt.setFontPointSize(float(value))
            self.editor.setCurrentCharFormat(fmt)
            # Also set the editor's default font so the cursor reflects the change immediately
            editor_font = self.editor.font()
            editor_font.setPointSize(int(value))
            self.editor.setFont(editor_font)

            # Also update app default
            s = QSettings("MyJourney", "App")
            s.setValue("default_font_size", int(value))
            # apply immediately
            self._apply_app_default_font()
        except Exception:
            pass

    def _update_toolbar_from_cursor(self):
        """Update the toolbar font/size controls based on the current selection or cursor position."""
        if getattr(self, '_initializing', False):
            return
            
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        
        self.font_combo.blockSignals(True)
        self.font_size.blockSignals(True)
        
        try:
            # Use the font object from the format to get resolved values
            f = fmt.font()
            family = f.family()
            size = f.pointSize()
            
            if family:
                self.font_combo.setCurrentFont(QFont(family))
            else:
                # Fallback to app default if not explicitly set
                s = QSettings("MyJourney", "App")
                df = s.value("default_font", "")
                if df:
                    self.font_combo.setCurrentFont(QFont(str(df)))

            if size > 0:
                self.font_size.setValue(int(size))
            else:
                # Fallback to app default size
                s = QSettings("MyJourney", "App")
                df_size = int(s.value("default_font_size", 12)) # type: ignore
                self.font_size.setValue(df_size)
                
            # Also update style buttons (Bold, Italic, etc.)
            if hasattr(self, 'bold_btn'):
                self.bold_btn.blockSignals(True)
                self.bold_btn.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
                self.bold_btn.blockSignals(False)
            if hasattr(self, 'italic_btn'):
                self.italic_btn.blockSignals(True)
                self.italic_btn.setChecked(fmt.fontItalic())
                self.italic_btn.blockSignals(False)
            if hasattr(self, 'underline_btn'):
                self.underline_btn.blockSignals(True)
                self.underline_btn.setChecked(fmt.fontUnderline())
                self.underline_btn.blockSignals(False)
            if hasattr(self, 'strike_btn'):
                self.strike_btn.blockSignals(True)
                self.strike_btn.setChecked(fmt.fontStrikeOut())
                self.strike_btn.blockSignals(False)
        finally:
            self.font_combo.blockSignals(False)
            self.font_size.blockSignals(False)

    def _apply_defaults_to_entries(self):
        """Ensure entries without explicit font metadata will appear using app defaults."""
        try:
            s = QSettings("MyJourney", "App")
            df = s.value("default_font", "")
            df_size = int(s.value("default_font_size", 12))  # type: ignore
            for e in self.entries:
                if not getattr(e, 'font_family', None):
                    e.font_family = df if df else None
                if not getattr(e, 'font_size', None):
                    e.font_size = int(df_size)
        except Exception:
            pass

    def _apply_entry_font_from_ui(self):
        """Apply the font settings from the entry-specific controls to the current entry."""
        # apply the font from the entry font controls to the editor and current_entry
        fam = self.entry_font_combo.currentFont().family()
        size = int(self.entry_font_size.value())
        if self.current_entry:
            self.current_entry.font_family = fam
            self.current_entry.font_size = size
        # push current html to undo stack
        if self.current_entry is not None:
            if not hasattr(self.current_entry, '_undo_stack'):
                self.current_entry._undo_stack = []
            try:
                self.current_entry._undo_stack.append(self.editor.toHtml())
            except Exception:
                pass
            self._undo_btn.setEnabled(True)
        new_html = self.format_whole_entry_html(self.editor.toHtml(), fam, size)
        self._suppress_dirty = True
        try:
            self.editor.setHtml(new_html)
        finally:
            self._suppress_dirty = False
        # mark dirty
        self._dirty = True

    def _make_icon(self, text: str, size: int = 16) -> QIcon:
        """Create a simple text-based icon."""
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        try:
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            p.setFont(font)
            p.setPen(Qt.GlobalColor.white)
            p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, text)
        finally:
            p.end()
        return QIcon(pix)

    # --- Editor formatting helpers ---
    def _set_font_family(self, family: str):
        """Set the font family for the current selection."""
        fmt = QTextCharFormat()
        fmt.setFontFamily(family)
        self._merge_format_on_selection(fmt)

    def _set_font_size(self, size: int):
        """Set the font size for the current selection."""
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        self._merge_format_on_selection(fmt)

    def _change_selection_font_size(self, delta: int):
        """Increase/decrease the font size for the current selection or word under cursor."""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.WordUnderCursor)
        current_fmt = cursor.charFormat()
        # try to read current point size, fallback to editor/default spinbox
        try:
            cur_size = current_fmt.fontPointSize()
        except Exception:
            cur_size = 0
        if not cur_size or cur_size <= 0:
            try:
                cur_size = float(self.font_size.value())
            except Exception:
                cur_size = float(self.editor.font().pointSize())
        new_size = int(max(6, min(72, round(cur_size + delta))))
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(new_size))
        self._merge_format_on_selection(fmt)
        # reflect in toolbar spinbox if selection covers whole doc
        try:
            self.font_size.setValue(new_size)
        except Exception:
            pass

    def _toggle_bold(self):
        """Toggle bold formatting for the current selection."""
        is_bold = self.editor.fontWeight() == QFont.Weight.Bold
        new_state = not is_bold
        if hasattr(self, 'bold_btn'):
            self.bold_btn.blockSignals(True)
            self.bold_btn.setChecked(new_state)
            self.bold_btn.blockSignals(False)
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if new_state else QFont.Weight.Normal)
        self._merge_format_on_selection(fmt)

    def _toggle_italic(self):
        """Toggle italic formatting for the current selection."""
        is_italic = self.editor.fontItalic()
        new_state = not is_italic
        if hasattr(self, 'italic_btn'):
            self.italic_btn.blockSignals(True)
            self.italic_btn.setChecked(new_state)
            self.italic_btn.blockSignals(False)
        fmt = QTextCharFormat()
        fmt.setFontItalic(new_state)
        self._merge_format_on_selection(fmt)

    def _toggle_underline(self):
        """Toggle underline formatting for the current selection."""
        is_under = self.editor.fontUnderline()
        new_state = not is_under
        if hasattr(self, 'underline_btn'):
            self.underline_btn.blockSignals(True)
            self.underline_btn.setChecked(new_state)
            self.underline_btn.blockSignals(False)
        fmt = QTextCharFormat()
        fmt.setFontUnderline(new_state)
        self._merge_format_on_selection(fmt)

    def _toggle_strike(self):
        """Toggle strikethrough formatting for the current selection."""
        cursor = self.editor.textCursor()
        is_strike = cursor.charFormat().fontStrikeOut()
        new_state = not is_strike
        if hasattr(self, 'strike_btn'):
            self.strike_btn.blockSignals(True)
            self.strike_btn.setChecked(new_state)
            self.strike_btn.blockSignals(False)
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(new_state)
        self._merge_format_on_selection(fmt)

    def _choose_color(self):
        """Open a color dialog and apply the selected color to the current selection."""
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(parent=self)
        if c.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(c)
            self._merge_format_on_selection(fmt)

    def _apply_font_to_entry(self):
        """Apply the selected font family and size to the entire entry."""
        # Wrap the entire document HTML in a div with font-family and size
        family = self.font_combo.currentFont().family()
        size = self.font_size.value()
        html = self.editor.toHtml()
        # push to undo stack
        if self.current_entry is not None:
            if not hasattr(self.current_entry, '_undo_stack'):
                self.current_entry._undo_stack = []
            try:
                self.current_entry._undo_stack.append(html)
            except Exception:
                pass
            self._undo_btn.setEnabled(True)
        new_html = self.format_whole_entry_html(html, family, size)
        self._suppress_dirty = True
        try:
            self.editor.setHtml(new_html)
        finally:
            self._suppress_dirty = False
        self._dirty = True

    @staticmethod
    def format_whole_entry_html(html: str, family: str, size: int) -> str:
        # Ensure we wrap the body content while preserving full HTML if present
        # If html already contains a body tag, inject style into the topmost wrapper.
        wrapper = f'<div style="font-family:{family}; font-size:{size}px;">{html}</div>'
        return wrapper

    def _merge_format_on_selection(self, format: QTextCharFormat):
        """Apply a QTextCharFormat to the current selection or word under cursor."""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(format)
        self.editor.mergeCurrentCharFormat(format)
        # mark dirty when user changes formatting
        if not getattr(self, '_suppress_dirty', False):
            self._dirty = True

    def _editor_context_menu(self, pos: QPoint):
        """Create and show a context menu for the editor."""
        menu = self.editor.createStandardContextMenu()
        # detect image under cursor (for resize)
        try:
            cursor_at_pos = self.editor.cursorForPosition(pos)
            cf = cursor_at_pos.charFormat()
            is_image = False
            try:
                is_image = cf.isImageFormat()
            except Exception:
                is_image = False
            if is_image:
                menu.addSeparator()
                menu.addAction("Resize Image...", lambda: self._resize_image_at_cursor(cursor_at_pos))
        except Exception:
            pass
        menu.addSeparator()
        menu.addAction("Bold", self._toggle_bold)
        menu.addAction("Italic", self._toggle_italic)
        menu.addAction("Underline", self._toggle_underline)
        menu.addAction("Strikethrough", self._toggle_strike)
        menu.addSeparator()
        menu.addAction("Bulleted List", self._insert_bullet_list)
        menu.addAction("Numbered List", self._insert_numbered_list)
        menu.addSeparator()
        menu.addAction("Insert Table...", self._insert_table)
        menu.addAction("Insert Code Block", self._insert_code_block)
        menu.addAction("Insert Link...", self._insert_link)
        # font sizes submenu
        size_menu = menu.addMenu("Font size")
        for sz in (8, 10, 12, 14, 18, 24, 36):
            size_menu.addAction(str(sz), lambda s=sz: self._set_font_size(s))
        menu.exec(self.editor.mapToGlobal(pos))

    def _insert_bullet_list(self):
        """Insert a bulleted list at the current cursor position."""
        try:
            cursor = self.editor.textCursor()
            fmt = QTextListFormat()
            fmt.setStyle(QTextListFormat.Style.ListDisc)
            cursor.beginEditBlock()
            try:
                cursor.createList(fmt)
            finally:
                cursor.endEditBlock()
            self._dirty = True
        except Exception:
            pass

    def _insert_numbered_list(self):
        """Insert a numbered list at the current cursor position."""
        try:
            cursor = self.editor.textCursor()
            fmt = QTextListFormat()
            fmt.setStyle(QTextListFormat.Style.ListDecimal)
            cursor.beginEditBlock()
            try:
                cursor.createList(fmt)
            finally:
                cursor.endEditBlock()
            self._dirty = True
        except Exception:
            pass

    def _insert_table(self):
        """Prompt for rows/columns and insert a table at the current cursor position."""
        from PySide6.QtWidgets import QInputDialog
        rows, ok = QInputDialog.getInt(self, "Insert Table", "Rows:", 2, 1, 50)
        if not ok:
            return
        cols, ok = QInputDialog.getInt(self, "Insert Table", "Columns:", 2, 1, 50)
        if not ok:
            return
        
        cursor = self.editor.textCursor()
        fmt = QTextTableFormat()
        fmt.setCellPadding(4)
        fmt.setCellSpacing(0)
        fmt.setBorder(1)
        fmt.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
        cursor.insertTable(rows, cols, fmt)
        self._dirty = True

    def _insert_code_block(self):
        """Insert a formatted code block at the current cursor position."""
        cursor = self.editor.textCursor()
        
        # Create a block format for the code block
        block_fmt = QTextBlockFormat()
        block_fmt.setBackground(QColor("#f0f0f0") if self.editor.palette().base().color().lightness() > 128 else QColor("#333333"))
        block_fmt.setLeftMargin(10)
        block_fmt.setRightMargin(10)
        block_fmt.setTopMargin(5)
        block_fmt.setBottomMargin(5)
        
        # Create a char format for the code text
        char_fmt = QTextCharFormat()
        char_fmt.setFontFamilies(["Courier New", "Monospace"])
        char_fmt.setFontFixedPitch(True)
        
        cursor.beginEditBlock()
        try:
            # If there's a selection, wrap it. Otherwise insert a placeholder.
            if cursor.hasSelection():
                text = cursor.selectedText()
                cursor.removeSelectedText()
            else:
                text = "code here"
            
            cursor.insertBlock(block_fmt, char_fmt)
            cursor.insertText(text)
            # Insert a normal block after to "exit" the code block
            cursor.insertBlock(QTextBlockFormat(), QTextCharFormat())
        finally:
            cursor.endEditBlock()
        self._dirty = True

    def _insert_link(self):
        """Prompt for a URL and insert a link at the current cursor position."""
        from PySide6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(self, "Insert Link", "URL (e.g. https://google.com):")
        if not ok or not url:
            return
        
        cursor = self.editor.textCursor()
        text = cursor.selectedText() or url
        
        fmt = QTextCharFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(url)
        # Use the theme's highlight color for links
        link_color = getattr(self, 'cal_header_bg', "#8b0000")
        fmt.setForeground(QColor(link_color))
        fmt.setFontUnderline(True)
        
        cursor.insertText(text, fmt)
        # Reset format for subsequent typing
        cursor.insertText(" ", QTextCharFormat())
        self._dirty = True

    def _resize_image_at_cursor(self, cursor: QTextCursor):
        """Prompt for new width/height and apply to the image at `cursor`."""
        try:
            cf = cursor.charFormat()
            if not cf.isImageFormat():
                return
            img_fmt = QTextImageFormat(cf.toImageFormat())
            # current sizes (may be 0 if not set)
            cur_w = int(img_fmt.width()) if img_fmt.width() else 0
            cur_h = int(img_fmt.height()) if img_fmt.height() else 0
            from PySide6.QtWidgets import QInputDialog
            w, ok = QInputDialog.getInt(self, "Resize Image", "Width (px, 0 = original):", cur_w, 0, 5000)
            if not ok:
                return
            h, ok = QInputDialog.getInt(self, "Resize Image", "Height (px, 0 = original):", cur_h, 0, 5000)
            if not ok:
                return
            # apply sizes (0 means don't set or reset)
            new_fmt = QTextImageFormat(img_fmt)
            if w > 0:
                new_fmt.setWidth(w)
            else:
                new_fmt.setWidth(0)
            if h > 0:
                new_fmt.setHeight(h)
            else:
                new_fmt.setHeight(0)
            # set format at cursor (select the image then set)
            try:
                cursor.beginEditBlock()
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)
                cursor.setCharFormat(new_fmt)
            finally:
                try:
                    cursor.endEditBlock()
                except Exception:
                    pass
            # inject width/height into HTML so it persists in saved content
            try:
                src = new_fmt.name()
                html = self.editor.toHtml()
                import re
                pattern = re.compile(r"(<img[^>]*src=[\'\"]%s[\'\"][^>]*)(>)" % re.escape(src))
                repl = r"\1 width=\"%d\" height=\"%d\"\2" % (w, h)
                new_html = pattern.sub(repl, html, count=1)
                if new_html != html:
                    self.editor.blockSignals(True)
                    try:
                        self.editor.setHtml(new_html)
                    finally:
                        self.editor.blockSignals(False)
            except Exception:
                pass
            # reflect change in editor and mark dirty
            self._dirty = True
        except Exception:
            pass

    # --- Auto-create entry when user types ---
    def _on_title_edited(self, text: str):
        if self.current_entry is None:
            # preserve typed text: create new entry and reapply text
            self.new_entry()
            self.title_edit.blockSignals(True)
            try:
                self.title_edit.setText(text)
            finally:
                self.title_edit.blockSignals(False)
            # set current entry title
            if self.current_entry:
                self.current_entry.title = text
            # select the new entry in the list
            for i in range(self.entry_list.count()):
                item = self.entry_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) is self.current_entry:
                    self.entry_list.setCurrentItem(item)
                    break
        # mark dirty
        if not getattr(self, '_suppress_dirty', False):
            self._dirty = True

    def _undo_apply(self):
        """Apply the last state from the undo stack."""
        if not self.current_entry:
            return
        stack = getattr(self.current_entry, '_undo_stack', None)
        if not stack:
            return
        try:
            prev = stack.pop()
            self._suppress_dirty = True
            try:
                self.editor.setHtml(prev)
            finally:
                self._suppress_dirty = False
            # update entry content and mark dirty
            try:
                self.current_entry.content = prev
            except Exception:
                pass
            self._dirty = True
        finally:
            if not getattr(self.current_entry, '_undo_stack', None):
                self._undo_btn.setEnabled(False)

    def _on_editor_text_changed(self):
        """Handle editor content changes, creating a new entry if none exists."""
        if getattr(self, '_initializing', False):
            return
            
        # only create a new entry if there's non-empty content and no current entry
        try:
            plain = self.editor.toPlainText().strip()
        except Exception:
            plain = ''
        if plain and self.current_entry is None:
            # capture current HTML and create new entry
            html = self.editor.toHtml()
            self.new_entry()
            self.editor.blockSignals(True)
            try:
                self.editor.setHtml(html)
                QTimer.singleShot(0, self._recolor_all_links)
            finally:
                self.editor.blockSignals(False)
            # set current entry content
            if self.current_entry:
                self.current_entry.content = html
            # select the new entry in the list
            for i in range(self.entry_list.count()):
                item = self.entry_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) is self.current_entry:
                    self.entry_list.setCurrentItem(item)
                    break
        # mark dirty
        if not getattr(self, '_suppress_dirty', False):
            self._dirty = True
        
        # Clean up link colors in HTML if present
        QTimer.singleShot(50, self._recolor_all_links)

    def discard_current_entry(self):
        """Discard the current entry after confirmation."""
        if not self.current_entry:
            return
        reply = QMessageBox.question(self, "Discard", "Discard current entry? This will remove it permanently.")
        if reply != QMessageBox.StandardButton.Yes:
            return
        # remove from DB if persisted
        try:
            if getattr(self.current_entry, 'id', None):
                self.db.delete_entry(self.current_entry.id)
        except Exception as e:
            QMessageBox.critical(self, "Discard failed", f"Could not discard entry: {e}")
            return
        # remove from in-memory list if present
        try:
            self.entries.remove(self.current_entry)
        except Exception:
            pass
        self.current_entry = None
        # reset editor to a new blank entry
        self.new_entry()

    def open_settings(self):
        """Open the settings dialog and apply changes."""
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._apply_theme()
            # apply default font settings immediately
            self._apply_app_default_font()
            # apply autosave interval if changed
            try:
                s = QSettings("MyJourney", "App")
                interval = int(s.value("autosave_interval", 30))  # type: ignore
                self._autosave_timer.setInterval(max(5, interval) * 1000)
            except Exception:
                pass
    
    def show_about(self):
        """Show an About dialog for the application."""
        QMessageBox.about(
            self,
            "About MyJourney",
            "MyJourney - A Personal Journal Application\n\n"
            "Version 1.1\n"
            "Built with Python 3.6+, PySide6 and SQLite.\n\n"
            "Features include encrypted entries, TOTP authentication, "
            "rich text editing, attachments, inline images, and more.\n\n"
            "GitHub: https://github.com/quantumpixelator/myjourney\n\n"
            "MIT License\n\n"
            "© 2025 Quantum Pixelator"
        )

    def show_statistics(self):
        """Show the journal statistics dialog."""
        from stats_dialog import StatsDialog
        dlg = StatsDialog(self.entries, self)
        dlg.exec()

    def _load_calendar_dates(self):
        """Highlight dates in the calendar that have journal entries."""
        dates = self.db.get_dates_with_entries()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.cal_header_fg))
        fmt.setBackground(QColor(self.cal_header_bg))
        fmt.setFontWeight(QFont.Weight.Bold)
        
        # Highlight today
        today = QDate.currentDate()
        self.calendar.setDateTextFormat(today, fmt)
        
        for i, d_str in enumerate(dates):
            if i % 100 == 0:
                QApplication.processEvents()
            qd = QDate.fromString(d_str, "yyyy-MM-dd")
            self.calendar.setDateTextFormat(qd, fmt)

    def _entry_list_context_menu(self, pos: QPoint):
        """Show a context menu for items in the entry list."""
        item = self.entry_list.itemAt(pos)
        if item is None:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        del_act = menu.addAction("Delete Entry")
        act = menu.exec(self.entry_list.mapToGlobal(pos))
        if act == del_act:
            # confirm and delete this entry
            reply = QMessageBox.question(self, "Delete", f"Permanently delete '{entry.title or 'Untitled'}'?")
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    if getattr(entry, 'id', None):
                        self.db.delete_entry(entry.id)
                except Exception as e:
                    QMessageBox.critical(self, "Delete failed", f"Could not delete entry: {e}")
                    return
                try:
                    self.entries.remove(entry)
                except Exception:
                    pass
                # if this was the currently selected entry, clear editor
                if self.current_entry is entry:
                    self.current_entry = None
                    self.title_edit.clear()
                    self.editor.clear()
                    self.tags_edit.clear()
                    self.attach_list.clear()
                self._load_entry_list()
                self._load_calendar_dates()

    def _load_entry_list(self, entries: Optional[List] = None):
        """Populate the entry list widget with entries."""
        self.entry_list.clear()
        to_show = entries or self.entries
        to_show = sorted(to_show, key=lambda e: e.date, reverse=True)
        
        s = QSettings("MyJourney", "App")
        df = s.value("default_font", "")
        df_size = int(s.value("default_font_size", 12))  # type: ignore
        base = os.path.join(os.path.dirname(__file__), "assets")
        font_icon_path = os.path.join(base, "font.svg")
        has_font_icon = os.path.exists(font_icon_path)
        
        for i, entry in enumerate(to_show):
            # Keep UI responsive during large list loads
            if i % 100 == 0:
                QApplication.processEvents()
                
            text = f"{entry.date} — {entry.title or 'Untitled'}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            # show badge icon if entry uses custom font
            fam = getattr(entry, 'font_family', None)
            fsize = getattr(entry, 'font_size', None)
            if fam and (fam != df or (fsize and int(fsize) != int(df_size))):
                if has_font_icon:
                    item.setIcon(QIcon(font_icon_path))
            # store last_saved in item tooltip for quick view
            try:
                if getattr(entry, 'last_saved', None):
                    item.setToolTip(f"Last saved: {entry.last_saved}")
            except Exception:
                pass
            self.entry_list.addItem(item)

    def filter_by_date(self, qdate: QDate):
        """Filter the entry list to show only entries from a specific date."""
        dstr = qdate.toString("yyyy-MM-dd")
        filtered = [e for e in self.entries if e.date == dstr]
        self._load_entry_list(filtered)

    def filter_by_search(self):
        """Filter the entry list based on the search query with optimized HTML stripping."""
        query = self.search.text().strip().lower()
        if not query:
            self._load_entry_list()
            return
            
        import re
        tag_re = re.compile(r'<[^>]+>')
        filtered = []
        
        for i, e in enumerate(self.entries):
            # Keep UI responsive during large searches
            if i % 50 == 0:
                QApplication.processEvents()
                
            # Strip HTML tags for searching content
            plain_content = tag_re.sub('', e.content).lower()
            
            if (query in e.title.lower() or
                query in plain_content or
                any(query in t.lower() for t in e.tags)):
                filtered.append(e)
        self._load_entry_list(filtered)

    def load_entry(self, item: QListWidgetItem):
        """Load the selected entry into the editor."""
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        self._initializing = True
        self.title_edit.blockSignals(True)
        self.editor.blockSignals(True)
        self.tags_edit.blockSignals(True)
        
        try:
            self.current_entry = entry
            self.title_edit.setText(self.current_entry.title)
            self.editor.setHtml(self.current_entry.content)
            self.tags_edit.setText(", ".join(self.current_entry.tags))
            self._refresh_attachment_list()
            # Force link recoloring after loading HTML
            QTimer.singleShot(0, self._recolor_all_links)
            # load per-entry font settings into UI and apply to editor
            s = QSettings("MyJourney", "App")
            df = s.value("default_font", "")
            df_size = int(s.value("default_font_size", 12))  # type: ignore
            if getattr(self.current_entry, 'font_family', None):
                try:
                    fam = self.current_entry.font_family
                    self.entry_font_combo.setCurrentFont(QFont(fam))
                except Exception:
                    pass
            else:
                if df:
                    try:
                        self.entry_font_combo.setCurrentFont(QFont(str(df)))
                    except Exception:
                        pass
            if getattr(self.current_entry, 'font_size', None):
                self.entry_font_size.setValue(self.current_entry.font_size)
                try:
                    self.editor.setFont(QFont(self.entry_font_combo.currentFont().family(), self.entry_font_size.value()))
                except Exception:
                    pass
            else:
                self.entry_font_size.setValue(df_size)
                # apply app default font to editor
                if df:
                    try:
                        self.editor.setFont(QFont(str(df), int(df_size)))
                    except Exception:
                        pass
            # ensure title required note (no change) and keep UI consistent
            # apply tooltip from last_saved if present
            try:
                if getattr(self.current_entry, 'last_saved', None):
                    self.statusBar().showMessage(f"Last saved: {self.current_entry.last_saved}", 5000)
            except Exception:
                pass
        finally:
            self.title_edit.blockSignals(False)
            self.editor.blockSignals(False)
            self.tags_edit.blockSignals(False)
            self._initializing = False

    def new_entry(self):
        """Create a new blank entry and load it into the editor."""
        self._initializing = True
        self.title_edit.blockSignals(True)
        self.editor.blockSignals(True)
        self.tags_edit.blockSignals(True)
        
        try:
            today = str(datetime.today().date())
            new_e = Entry(entry_date=today)
            self.entries.append(new_e)
            self.current_entry = new_e
            self.title_edit.clear()
            self.editor.clear()
            # apply app default font to the new/blank entry editor
            s = QSettings("MyJourney", "App")
            df = s.value("default_font", "")
            df_size = int(s.value("default_font_size", 12))  # type: ignore
            if df:
                try:
                    self.editor.setFont(QFont(str(df), int(df_size)))
                except Exception:
                    pass
            self.tags_edit.clear()
            self.attach_list.clear()
            # set per-entry font controls to defaults
            if df:
                try:
                    self.entry_font_combo.setCurrentFont(QFont(str(df)))
                except Exception:
                    pass
            self.entry_font_size.setValue(int(s.value("default_font_size", 12)))  # type: ignore
            self._load_entry_list()
            self._load_calendar_dates()
        finally:
            self.title_edit.blockSignals(False)
            self.editor.blockSignals(False)
            self.tags_edit.blockSignals(False)
            self._initializing = False

    def insert_image(self):
        """Open a file dialog to select an image, resize if large, and insert it into the editor."""
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp)")
        if not path:
            return
            
        pix = QPixmap(path)
        if pix.isNull():
            return
            
        # Memory management: Resize if image is very large (e.g., > 1200px width)
        if pix.width() > 1200:
            pix = pix.scaledToWidth(1200, Qt.TransformationMode.SmoothTransformation)
            
        # Convert to base64
        from PySide6.QtCore import QBuffer, QIODevice
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        
        ext = os.path.splitext(path)[1].lower().replace(".", "")
        if ext not in ("png", "jpg", "jpeg", "gif", "bmp"):
            ext = "png"
        
        pix.save(buffer, ext.upper())
        b64 = base64.b64encode(ba.data()).decode()
        
        html = f'<img src="data:image/{ext};base64,{b64}" />'
        self.editor.textCursor().insertHtml(html)
        self._dirty = True

    def attach_file(self):
        """Open a file dialog to select a file and attach it to the current entry."""
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
        self._refresh_attachment_list()
        self._dirty = True

    def save_attachment_as(self, item: QListWidgetItem):
        """Save the selected attachment to a file or insert it inline if it's an image."""
        idx = item.data(Qt.ItemDataRole.UserRole)
        assert self.current_entry is not None
        att = self.current_entry.attachments[idx]
        filename = att["filename"]
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            # Insert image inline into editor
            pix = QPixmap()
            pix.loadFromData(att["data"])
            self.editor.document().addResource(QTextDocument.ResourceType.ImageResource, QUrl(filename), pix)
            cursor = self.editor.textCursor()
            imgfmt = QTextImageFormat()
            imgfmt.setName(filename)
            imgfmt.setWidth(min(pix.width(), 400))  # Limit width
            imgfmt.setHeight(int(pix.height() * (imgfmt.width() / pix.width())))
            cursor.insertImage(imgfmt)
        else:
            # Save as file
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Attachment", filename)
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(att["data"])

    def _attachment_context_menu(self, pos):
        """Show a context menu for the attachment list."""
        item = self.attach_list.itemAt(pos)
        if not item:
            return
        
        menu = QMenu()
        save_action = menu.addAction("Save/Insert")
        delete_action = menu.addAction("Delete Attachment")
        
        action = menu.exec(self.attach_list.mapToGlobal(pos))
        if action == save_action:
            self.save_attachment_as(item)
        elif action == delete_action:
            self._delete_attachment(item)

    def _delete_attachment(self, item: QListWidgetItem):
        """Remove the selected attachment from the current entry."""
        if not self.current_entry:
            return
            
        idx = item.data(Qt.ItemDataRole.UserRole)
        filename = item.text()
        
        reply = QMessageBox.question(
            self, "Delete Attachment",
            f"Are you sure you want to delete '{filename}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from entry list
            self.current_entry.attachments.pop(idx)
            self._dirty = True
            # Refresh the list UI
            self._refresh_attachment_list()

    def _refresh_attachment_list(self):
        """Refresh the attachment list widget from the current entry."""
        self.attach_list.clear()
        if not self.current_entry:
            return
        for i, att in enumerate(self.current_entry.attachments):
            filename = att["filename"]
            item = QListWidgetItem(filename)
            item.setData(Qt.ItemDataRole.UserRole, i)
            
            # Set icon based on file type
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                try:
                    pix = QPixmap()
                    pix.loadFromData(att["data"])
                    if not pix.isNull():
                        icon = QIcon(pix.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                        item.setIcon(icon)
                    else:
                        item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                except Exception:
                    item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
            else:
                # Generic file icon
                item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                
            self.attach_list.addItem(item)

    def save_current_entry(self, show_message: bool = True):
        """Save the current entry to the database."""
        if not self.current_entry:
            QMessageBox.warning(self, "No entry", "Create or select an entry first.")
            return
        # require a title
        title_text = self.title_edit.text().strip()
        if not title_text:
            QMessageBox.warning(self, "Missing title", "Entries must have a title to save.")
            return
        self.current_entry.title = title_text
        self.current_entry.content = self.editor.toHtml()
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        self.current_entry.tags = tags
        # save per-entry font metadata from UI
        try:
            self.current_entry.font_family = self.entry_font_combo.currentFont().family()
            self.current_entry.font_size = int(self.entry_font_size.value())
        except Exception:
            self.current_entry.font_family = None
            self.current_entry.font_size = None
        # update last_saved timestamp
        try:
            self.current_entry.last_saved = datetime.utcnow().isoformat()
        except Exception:
            self.current_entry.last_saved = None
            
        if show_message:
            self.statusBar().showMessage("Saving entry...", 0)
            QApplication.processEvents()
            
        try:
            self.db.save_entry(self.current_entry)
        except Exception as e:
            if show_message:
                QMessageBox.critical(self, "Save failed", f"Could not save entry: {e}")
            return
            
        # Only reload UI lists if this is a manual save or if we need to update the calendar
        if show_message:
            self._load_entry_list()
        else:
            # Update the list item text for autosave
            for i in range(self.entry_list.count()):
                item = self.entry_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self.current_entry:
                    item.setText(f"{self.current_entry.date} - {self.current_entry.title or 'Untitled'}")
                    break
            self._load_calendar_dates()
            
        # clear dirty flag
        self._dirty = False
        if not show_message:
            return
        QMessageBox.information(self, "Saved", "Entry saved successfully.")
        # also show last-saved in the status bar briefly
        try:
            if getattr(self.current_entry, 'last_saved', None):
                self.statusBar().showMessage(f"Saved at {self.current_entry.last_saved}", 4000)
        except Exception:
            pass

    def delete_entry(self):
        """Delete the current entry after confirmation."""
        if not self.current_entry or self.current_entry.id is None:
            return
        reply = QMessageBox.question(self, "Delete", "Permanently delete this entry?")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_entry(self.current_entry.id)
            except Exception as e:
                QMessageBox.critical(self, "Delete failed", f"Could not delete entry: {e}")
                return
            try:
                self.entries.remove(self.current_entry)
            except ValueError:
                pass
            self.current_entry = None
            self.title_edit.clear()
            self.editor.clear()
            self.tags_edit.clear()
            self.attach_list.clear()
            self._load_entry_list()
            self._load_calendar_dates()

    def _prompt_export_format(self):
        """Prompt user to select export format."""
        from PySide6.QtWidgets import QInputDialog
        formats = ["PDF", "HTML", "RTF", "Markdown"]
        format_choice, ok = QInputDialog.getItem(
            self, "Export Format", "Select export format:", formats, 0, False
        )
        if ok and format_choice:
            return format_choice
        return None

    def export_current_entry(self):
        """Export the current entry to the selected format."""
        if not self.current_entry:
            QMessageBox.warning(self, "No Entry", "Please select an entry to export.")
            return
        
        format_choice = self._prompt_export_format()
        if not format_choice:
            return
        
        self._export_entries_to_format([self.current_entry], format_choice)
    
    def export_all_entries(self):
        """Export all entries to the selected format."""
        if not self.entries:
            QMessageBox.warning(self, "No Entries", "There are no entries to export.")
            return
        
        format_choice = self._prompt_export_format()
        if not format_choice:
            return
        
        self._export_entries_to_format(self.entries, format_choice)
    
    def _export_entries_to_format(self, entries, format_choice: str):
        """Export given entries to the specified format."""
        if format_choice == "PDF":
            self._export_to_pdf(entries)
        elif format_choice == "HTML":
            self._export_to_html(entries)
        elif format_choice == "RTF":
            self._export_to_rtf(entries)
        elif format_choice == "Markdown":
            self._export_to_markdown(entries)
    
    def _export_to_pdf(self, entries):
        """Export entries to PDF format."""
        from PySide6.QtGui import QPdfWriter, QPageSize
        from PySide6.QtCore import QMarginsF
        
        filename = "all_entries.pdf" if len(entries) > 1 else f"{entries[0].title or 'entry'}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Export to PDF", filename, "PDF (*.pdf)")
        
        if not path:
            return
        
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        
        writer = QPdfWriter(path)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageMargins(QMarginsF(15, 15, 15, 15))
        
        # Combine all entries into one document
        combined_html = ""
        for i, entry in enumerate(entries):
            if i > 0:
                combined_html += "<div style='page-break-before: always;'></div>"
            combined_html += f"<h1>{entry.title}</h1>"
            combined_html += f"<p><i>{entry.date}</i></p>"
            combined_html += entry.content
            combined_html += "<hr/>"
        
        doc = QTextDocument()
        doc.setHtml(combined_html)
        doc.print_(writer)
        
        QMessageBox.information(self, "Export", f"{len(entries)} entry(ies) exported to {path}")
    
    def _export_to_html(self, entries):
        """Export entries to HTML format."""
        filename = "all_entries.html" if len(entries) > 1 else f"{entries[0].title or 'entry'}.html"
        path, _ = QFileDialog.getSaveFileName(self, "Export to HTML", filename, "HTML (*.html)")
        
        if not path:
            return
        
        if not path.lower().endswith(".html"):
            path += ".html"
        
        html = "<html><head><meta charset='utf-8'><title>Journal Export</title></head><body>"
        for i, entry in enumerate(entries):
            if i > 0:
                html += "<div style='page-break-before: always;'></div>"
            html += f"<h1>{entry.title}</h1>"
            html += f"<p><i>{entry.date}</i></p>"
            html += entry.content
            html += "<hr/>"
        html += "</body></html>"
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        
        QMessageBox.information(self, "Export", f"{len(entries)} entry(ies) exported to {path}")
    
    def _export_to_rtf(self, entries):
        """Export entries to RTF format."""
        filename = "all_entries.rtf" if len(entries) > 1 else f"{entries[0].title or 'entry'}.rtf"
        path, _ = QFileDialog.getSaveFileName(self, "Export to RTF", filename, "RTF (*.rtf)")
        
        if not path:
            return
        
        if not path.lower().endswith(".rtf"):
            path += ".rtf"
        
        # Create a QTextDocument and set the combined content
        combined_html = ""
        for i, entry in enumerate(entries):
            if i > 0:
                combined_html += "<div style='page-break-before: always;'></div>"
            combined_html += f"<h1>{entry.title}</h1>"
            combined_html += f"<p><i>{entry.date}</i></p>"
            combined_html += entry.content
            combined_html += "<hr/>"
        
        doc = QTextDocument()
        doc.setHtml(combined_html)
        
        # Write to RTF using QTextDocumentWriter
        from PySide6.QtGui import QTextDocumentWriter
        writer = QTextDocumentWriter(path, b"rtf")
        writer.write(doc)
        
        QMessageBox.information(self, "Export", f"{len(entries)} entry(ies) exported to {path}")
    
    def _export_to_markdown(self, entries):
        """Export entries to Markdown format."""
        filename = "all_entries.md" if len(entries) > 1 else f"{entries[0].title or 'entry'}.md"
        path, _ = QFileDialog.getSaveFileName(self, "Export to Markdown", filename, "Markdown (*.md)")
        
        if not path:
            return
        
        if not path.lower().endswith(".md"):
            path += ".md"
        
        md_content = ""
        for entry in entries:
            md_content += f"# {entry.title}\n\n"
            md_content += f"*{entry.date}*\n\n"
            
            # Convert HTML to Markdown
            doc = QTextDocument()
            doc.setHtml(entry.content)
            md_content += doc.toMarkdown()
            md_content += "\n\n---\n\n"
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        QMessageBox.information(self, "Export", f"{len(entries)} entry(ies) exported to {path}")

    def backup_db(self):
        """Create an encrypted backup of the database."""
        from PySide6.QtWidgets import QInputDialog
        password, ok = QInputDialog.getText(self, "Backup Password", "Enter a password to encrypt the backup:", QLineEdit.EchoMode.Password)
        if not ok or not password:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Backup Database", "myjourney_backup.enc")
        if path:
            from encryption import EncryptionManager
            salt = EncryptionManager.generate_salt()
            enc = EncryptionManager(password, salt)
            with open("myjourney.db", "rb") as f:
                data = f.read()
            encrypted_data = enc.encrypt_data(data)
            with open(path, "wb") as f:
                f.write(salt + encrypted_data)  # Prepend salt
            QMessageBox.information(self, "Backup", "Encrypted database backed up. Store the password securely!")

    def _logout_due_to_inactivity(self):
        """Logout due to inactivity by closing the window."""
        QMessageBox.information(self, "Session Expired", "You have been logged out due to inactivity.")
        self.close()
        # Since the main loop is in main.py, this will exit the app

    def _toggle_theme(self):
        """Toggle between light and dark themes."""
        s = QSettings("MyJourney", "App")
        current_bg = s.value("app_bg", "#2b2b2b")
        if current_bg == "#2b2b2b":  # Dark, switch to light
            s.setValue("app_bg", "#ffffff")
            s.setValue("app_fg", "#000000")
            s.setValue("editor_bg", "#f0f0f0")
            s.setValue("editor_fg", "#000000")
        else:  # Light, switch to dark
            s.setValue("app_bg", "#2b2b2b")
            s.setValue("app_fg", "#ffffff")
            s.setValue("editor_bg", "#1e1e1e")
            s.setValue("editor_fg", "#ffffff")
        self._apply_theme()
        self._load_calendar_dates()

    def event(self, event: QEvent) -> bool:
        """Override to reset inactivity timer on user activity."""
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress):
            self.inactivity_timer.start()  # Reset the timer
        return super().event(event)