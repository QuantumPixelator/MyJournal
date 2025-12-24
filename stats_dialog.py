from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QGridLayout, QFrame, QCheckBox, QWidget
from PySide6.QtGui import QTextDocument
from collections import Counter
import datetime

class StatsDialog(QDialog):
    """A dialog showing journal statistics."""
    
    def __init__(self, entries, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Journal Statistics")
        self.setMinimumWidth(400)
        self.entries = entries
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Calculate stats
        total_entries = len(self.entries)
        total_words = 0
        all_tags = []
        entries_by_month = Counter()
        
        for entry in self.entries:
            # Word count
            doc = QTextDocument()
            doc.setHtml(entry.content)
            text = doc.toPlainText()
            total_words += len(text.split())
            
            # Tags
            all_tags.extend(entry.tags)
            
            # Month
            try:
                dt = datetime.datetime.strptime(entry.date, "%Y-%m-%d")
                entries_by_month[dt.strftime("%Y-%m")] += 1
            except Exception:
                pass
                
        avg_words = total_words / total_entries if total_entries > 0 else 0
        most_common_tags = Counter(all_tags).most_common(5)
        
        # UI Elements
        grid = QGridLayout()
        
        def add_stat(row, label, value):
            lbl = QLabel(f"<b>{label}</b>")
            val = QLabel(str(value))
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            
        add_stat(0, "Total Entries:", total_entries)
        add_stat(1, "Total Words:", total_words)
        add_stat(2, "Average Words/Entry:", f"{avg_words:.1f}")
        
        layout.addLayout(grid)
        
        # Tags section
        if most_common_tags:
            layout.addWidget(self._create_separator())
            
            self.tags_check = QCheckBox("Show Most Used Tags")
            self.tags_check.setChecked(False)
            layout.addWidget(self.tags_check)
            
            self.tags_widget = QWidget()
            tags_layout = QVBoxLayout(self.tags_widget)
            tags_layout.setContentsMargins(0, 0, 0, 0)
            tags_layout.addWidget(QLabel("<b>Most Used Tags:</b>"))
            for tag, count in most_common_tags:
                tags_layout.addWidget(QLabel(f"  • {tag} ({count})"))
            
            layout.addWidget(self.tags_widget)
            self.tags_widget.setVisible(False)
            self.tags_check.toggled.connect(self.tags_widget.setVisible)
                
        # Recent activity
        layout.addWidget(self._create_separator())
        layout.addWidget(QLabel("<b>Recent Activity (Last 6 Months):</b>"))
        
        # Sort months
        sorted_months = sorted(entries_by_month.keys(), reverse=True)[:6]
        for month in sorted_months:
            count = entries_by_month[month]
            layout.addWidget(QLabel(f"  • {month}: {count} entries"))
            
        if not sorted_months:
            layout.addWidget(QLabel("  No activity recorded."))

    def _create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line
