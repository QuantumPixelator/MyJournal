# main_window.py
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QCalendarWidget, QListWidget, QListWidgetItem, QTextEdit,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QMessageBox, QMenu, QToolBar, QFontComboBox, QSpinBox, QToolButton
)
from PySide6.QtCore import Qt, QDate, QSettings, QUrl, QTimer
from PySide6.QtGui import QTextCharFormat, QDesktopServices, QAction, QTextDocument, QColor, QFont, QKeySequence, QTextListFormat, QTextCursor, QTextImageFormat
from PySide6.QtGui import QShortcut
from PySide6.QtGui import QPixmap, QPainter, QIcon
from entry import Entry
from settings_dialog import SettingsDialog
import base64
import os
from datetime import datetime
from PySide6.QtCore import QUrl, QPoint
from PySide6.QtGui import QImage


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
                        res = self.document().resource(QTextDocument.ImageResource, QUrl(name))
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
                        w._dirty = True
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
        self._load_calendar_dates()
        self._load_entry_list()
        self._apply_theme()

    def _build_ui(self):
        # prevent signal handlers from reacting during initialization
        self._initializing = True
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
        # Font selector
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(lambda f: self._set_font_family(f.family()))
        # when toolbar default font changes, save it immediately for next startup
        self.font_combo.currentFontChanged.connect(self._toolbar_font_changed)
        toolbar.addWidget(self.font_combo)
        # font size
        self.font_size = QSpinBox()
        self.font_size.setRange(6, 72)
        self.font_size.setValue(12)
        self.font_size.valueChanged.connect(self._set_font_size)
        # persist default font size when changed from toolbar
        self.font_size.valueChanged.connect(self._toolbar_font_size_changed)
        toolbar.addWidget(self.font_size)
        # increase/decrease selection font size
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
        # list formatting buttons
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
        # style buttons (load SVG icons from assets when available)
        def _get_icon(name: str, letter: str):
            base = os.path.join(os.path.dirname(__file__), "assets")
            path_svg = os.path.join(base, f"{name}.svg")
            if os.path.exists(path_svg):
                return QIcon(path_svg)
            return self._make_icon(letter)

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
        # color
        color_btn = QToolButton()
        color_btn.setIcon(_get_icon("color", "C"))
        color_btn.clicked.connect(self._choose_color)
        toolbar.addWidget(color_btn)
        # apply current font/size to whole entry
        apply_btn = QToolButton()
        apply_btn.setToolTip("Apply font to entire entry")
        apply_btn.setIcon(_get_icon("apply", "A"))
        apply_btn.clicked.connect(self._apply_font_to_entry)
        toolbar.addWidget(apply_btn)
        # undo for whole-entry apply
        undo_btn = QToolButton()
        undo_btn.setToolTip("Undo last apply")
        undo_btn.setIcon(_get_icon("undo", "<"))
        undo_btn.clicked.connect(self._undo_apply)
        undo_btn.setEnabled(False)
        self._undo_btn = undo_btn
        toolbar.addWidget(undo_btn)
        self.addToolBar(toolbar)

        # Keyboard shortcuts for formatting
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self._toggle_bold)
        QShortcut(QKeySequence("Ctrl+I"), self, activated=self._toggle_italic)
        QShortcut(QKeySequence("Ctrl+U"), self, activated=self._toggle_underline)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self._toggle_strike)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self._undo_apply)
        QShortcut(QKeySequence("Ctrl+]"), self, activated=lambda: self._change_selection_font_size(1))
        QShortcut(QKeySequence("Ctrl+["), self, activated=lambda: self._change_selection_font_size(-1))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.filter_by_date)
        left_layout.addWidget(self.calendar)
        self.entry_list = QListWidget()
        self.entry_list.itemClicked.connect(self.load_entry)
        # right-click context menu for entries
        self.entry_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entry_list.customContextMenuRequested.connect(self._entry_list_context_menu)
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
        # create entry when user starts typing a title
        self.title_edit.textEdited.connect(self._on_title_edited)
        right_layout.addLayout(title_l)
        self.editor = ResizableTextEdit()
        # enable custom context menu for formatting
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self._editor_context_menu)
        # create entry when user starts typing in editor
        self.editor.textChanged.connect(self._on_editor_text_changed)
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
        # apply saved default font (block signals during initial set)
        s = QSettings("MyJourney", "App")
        df = s.value("default_font", "")
        df_size = int(s.value("default_font_size", 12))
        try:
            self.font_combo.blockSignals(True)
            if df:
                try:
                    self.font_combo.setCurrentFont(QFont(df))
                except Exception:
                    pass
        finally:
            self.font_combo.blockSignals(False)
        try:
            self.font_size.blockSignals(True)
            self.font_size.setValue(df_size)
        finally:
            self.font_size.blockSignals(False)
        # apply app default font to editor and entry controls
        self._apply_app_default_font()
        # initialization complete
        self._initializing = False
        # autosave timer and dirty tracking
        self._dirty = False
        self._suppress_dirty = False
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30 * 1000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

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

    def _autosave(self):
        if not getattr(self, '_dirty', False):
            return
        if not self.current_entry:
            return
        # perform silent save
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

    def _apply_app_default_font(self):
        s = QSettings("MyJourney", "App")
        df = s.value("default_font", "")
        df_size = int(s.value("default_font_size", 12))
        if df:
            try:
                qf = QFont(df, df_size)
                # apply to editor/default-entry area only (do not change control/widget fonts)
                try:
                    self.editor.setFont(qf)
                except Exception:
                    pass
                # apply as default in entry font controls if not set
                if hasattr(self, 'entry_font_combo'):
                    try:
                        self.entry_font_combo.setCurrentFont(QFont(df))
                    except Exception:
                        pass
                if hasattr(self, 'entry_font_size'):
                    self.entry_font_size.setValue(df_size)
            except Exception:
                pass

    def _toolbar_font_changed(self, qfont):
        # don't persist while initializing UI
        if getattr(self, '_initializing', False):
            return
        try:
            fam = qfont.family()
            s = QSettings("MyJourney", "App")
            s.setValue("default_font", fam)
            s.setValue("default_font_size", int(self.font_size.value()))
            # apply immediately
            self._apply_app_default_font()
        except Exception:
            pass

    def _toolbar_font_size_changed(self, value: int):
        # don't persist while initializing UI
        if getattr(self, '_initializing', False):
            return
        try:
            s = QSettings("MyJourney", "App")
            s.setValue("default_font_size", int(value))
            # apply immediately
            self._apply_app_default_font()
        except Exception:
            pass

    def _apply_defaults_to_entries(self):
        """Ensure entries without explicit font metadata will appear using app defaults."""
        try:
            s = QSettings("MyJourney", "App")
            df = s.value("default_font", "")
            df_size = int(s.value("default_font_size", 12))
            for e in self.entries:
                if not getattr(e, 'font_family', None):
                    e.font_family = df if df else None
                if not getattr(e, 'font_size', None):
                    e.font_size = int(df_size)
        except Exception:
            pass

    def _apply_entry_font_from_ui(self):
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
        fmt = QTextCharFormat()
        fmt.setFontFamily(family)
        self._merge_format_on_selection(fmt)

    def _set_font_size(self, size: int):
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
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.bold_btn.isChecked() else QFont.Weight.Normal)
        self._merge_format_on_selection(fmt)

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_btn.isChecked())
        self._merge_format_on_selection(fmt)

    def _toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.underline_btn.isChecked())
        self._merge_format_on_selection(fmt)

    def _toggle_strike(self):
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(self.strike_btn.isChecked())
        self._merge_format_on_selection(fmt)

    def _choose_color(self):
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(parent=self)
        if c.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(c)
            self._merge_format_on_selection(fmt)

    def _apply_font_to_entry(self):
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
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(format)
        self.editor.mergeCurrentCharFormat(format)
        # mark dirty when user changes formatting
        if not getattr(self, '_suppress_dirty', False):
            self._dirty = True

    def _editor_context_menu(self, pos):
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
        # font sizes submenu
        size_menu = menu.addMenu("Font size")
        for sz in (8, 10, 12, 14, 18, 24, 36):
            size_menu.addAction(str(sz), lambda s=sz: self._set_font_size(s))
        menu.exec(self.editor.mapToGlobal(pos))

    def _insert_bullet_list(self):
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
            try:
                self.current_entry.title = text
            except Exception:
                pass
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
            finally:
                self.editor.blockSignals(False)
            # set current entry content
            try:
                self.current_entry.content = html
            except Exception:
                pass
            # select the new entry in the list
            for i in range(self.entry_list.count()):
                item = self.entry_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) is self.current_entry:
                    self.entry_list.setCurrentItem(item)
                    break
        # mark dirty
        if not getattr(self, '_suppress_dirty', False):
            self._dirty = True

    def discard_current_entry(self):
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
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._apply_theme()
            # apply default font settings immediately
            self._apply_app_default_font()
            # apply autosave interval if changed
            try:
                s = QSettings("MyJourney", "App")
                interval = int(s.value("autosave_interval", 30))
                self._autosave_timer.setInterval(max(5, interval) * 1000)
            except Exception:
                pass

    def _load_calendar_dates(self):
        dates = self.db.get_dates_with_entries()
        fmt = QTextCharFormat()
        fmt.setForeground(Qt.GlobalColor.white)
        fmt.setBackground(Qt.GlobalColor.blue)
        fmt.setFontWeight(75)
        for d_str in dates:
            qd = QDate.fromString(d_str, "yyyy-MM-dd")
            self.calendar.setDateTextFormat(qd, fmt)

    def _entry_list_context_menu(self, pos):
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

    def _load_entry_list(self, entries=None):
        self.entry_list.clear()
        to_show = entries or self.entries
        to_show = sorted(to_show, key=lambda e: e.date, reverse=True)
        for entry in to_show:
            text = f"{entry.date} — {entry.title or 'Untitled'}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            # show badge icon if entry uses custom font
            s = QSettings("MyJourney", "App")
            df = s.value("default_font", "")
            df_size = int(s.value("default_font_size", 12))
            fam = getattr(entry, 'font_family', None)
            fsize = getattr(entry, 'font_size', None)
            if fam and (fam != df or (fsize and int(fsize) != int(df_size))):
                base = os.path.join(os.path.dirname(__file__), "assets")
                path = os.path.join(base, "font.svg")
                if os.path.exists(path):
                    item.setIcon(QIcon(path))
            # store last_saved in item tooltip for quick view
            try:
                if getattr(entry, 'last_saved', None):
                    item.setToolTip(f"Last saved: {entry.last_saved}")
            except Exception:
                pass
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
        # load per-entry font settings into UI and apply to editor
        s = QSettings("MyJourney", "App")
        df = s.value("default_font", "")
        df_size = int(s.value("default_font_size", 12))
        if getattr(self.current_entry, 'font_family', None):
            try:
                fam = self.current_entry.font_family
                self.entry_font_combo.setCurrentFont(QFont(fam))
            except Exception:
                pass
        else:
            if df:
                try:
                    self.entry_font_combo.setCurrentFont(QFont(df))
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
                    self.editor.setFont(QFont(df, df_size))
                except Exception:
                    pass
        # ensure title required note (no change) and keep UI consistent
        # apply tooltip from last_saved if present
        try:
            if getattr(self.current_entry, 'last_saved', None):
                self.statusBar().showMessage(f"Last saved: {self.current_entry.last_saved}", 5000)
        except Exception:
            pass
        # show last saved timestamp if available
        try:
            if getattr(self.current_entry, 'last_saved', None):
                self.statusBar().showMessage(f"Last saved: {self.current_entry.last_saved}", 5000)
        except Exception:
            pass

    def new_entry(self):
        today = str(datetime.today().date())
        new_e = Entry(entry_date=today)
        self.entries.append(new_e)
        self.current_entry = new_e
        self.title_edit.clear()
        self.editor.clear()
        # apply app default font to the new/blank entry editor
        s = QSettings("MyJourney", "App")
        df = s.value("default_font", "")
        df_size = int(s.value("default_font_size", 12))
        if df:
            try:
                self.editor.setFont(QFont(df, df_size))
            except Exception:
                pass
        self.tags_edit.clear()
        self.attach_list.clear()
        # set per-entry font controls to defaults
        s = QSettings("MyJourney", "App")
        df = s.value("default_font", "")
        if df:
            try:
                self.entry_font_combo.setCurrentFont(QFont(df))
            except Exception:
                pass
        self.entry_font_size.setValue(int(s.value("default_font_size", 12)))
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

    def save_current_entry(self, show_message: bool = True):
        if not self.current_entry:
            QMessageBox.warning(self, "No entry", "Create or select an entry first.")
            return
        # require a title
        title_text = self.title_edit.text().strip()
        if not title_text:
            QMessageBox.warning(self, "Missing title", "Entries must have a title to save.")
            return
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
        try:
            self.db.save_entry(self.current_entry)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"Could not save entry: {e}")
            return
        self._load_entry_list()
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