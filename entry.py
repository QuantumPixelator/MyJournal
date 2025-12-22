"""Small data container representing a journal entry.

Fields are plain Python types for easy serialization: ``date`` is a
string in YYYY-MM-DD format, ``content`` contains HTML, ``tags`` is a
list of short strings, and ``attachments`` holds dicts with filename
and raw bytes.
"""

from datetime import date


class Entry:
    """A journal entry.

    This class is used as an in-memory representation of an entry
    retrieved from or written to the database.
    """

    def __init__(self, id=None, entry_date=None, title="", content="", tags=None, attachments=None):
        self.id = id
        if entry_date is not None:
            self.date = entry_date
        else:
            from datetime import date as _date
            self.date = str(_date.today())
        self.title = title
        self.content = content  # HTML string
        self.tags = tags or []  # list of str
        self.attachments = attachments or []  # list of dict {'filename': str, 'data': bytes}
        # per-entry display metadata
        self.font_family: str | None = None
        self.font_size: int | None = None
        # last saved timestamp (ISO string)
        self.last_saved: str | None = None