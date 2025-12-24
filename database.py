# database.py
import sqlite3
import os
import json
from typing import Optional
from encryption import EncryptionManager
from entry import Entry
from datetime import date

DB_FILE = "myjourney.db"


"""Database access layer for MyJournal.

This module exposes a small `DatabaseManager` that wraps sqlite3 and
handles storing encrypted entries, attachments, and the per-install
configuration (salt and TOTP secret). The manager expects to be
connected with an `EncryptionManager` before use.
"""

class DatabaseManager:
    def __init__(self):
        """Create a manager instance; call `connect()` before use."""
        self.conn: Optional[sqlite3.Connection] = None
        self.cur: Optional[sqlite3.Cursor] = None
        self.enc: Optional[EncryptionManager] = None

    def connect(self, enc_manager: EncryptionManager):
        """Open (or create) the database file and set the encoder.

        ``enc_manager`` is used to encrypt/decrypt fields stored in the
        database. The method opens `DB_FILE` in the current working
        directory.
        """
        self.conn = sqlite3.connect(DB_FILE)
        self.cur = self.conn.cursor()
        self.enc = enc_manager

    def _ensure_connected(self):
        # Narrow types for static analysis using assertions
        assert self.conn is not None and self.cur is not None and self.enc is not None, (
            "DatabaseManager is not connected. Call connect() first.")
    def close(self):
        if self.conn:
            self.conn.close()
        self.conn = None
        self.cur = None
        self.enc = None

    def init_db(self):
        """Initialize the database schema if it doesn't exist."""
        self._ensure_connected()
        assert self.conn is not None and self.cur is not None and self.enc is not None
        self.cur.execute("""CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            salt BLOB,
            totp_secret BLOB
        )""")
        self.cur.execute("""CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            encrypted_title BLOB,
            encrypted_content BLOB,
            encrypted_tags BLOB,
            encrypted_font_family BLOB,
            encrypted_font_size BLOB,
            encrypted_last_saved BLOB
        )""")
        self.cur.execute("""CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER,
            filename TEXT NOT NULL,
            encrypted_data BLOB NOT NULL,
            FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
        )""")
        self.conn.commit()

    def is_new(self) -> bool:
        """Check if the database is new (no config or entries)."""
        if not os.path.exists(DB_FILE):
            return True
        if self.conn is None or self.cur is None:
            # Not connected, open a temp connection just to check
            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='config'")
                if cur.fetchone() is None:
                    return True
                cur.execute("SELECT 1 FROM config LIMIT 1")
                return cur.fetchone() is None
        self.cur.execute("SELECT 1 FROM config LIMIT 1")
        return self.cur.fetchone() is None

    def save_config(self, salt: bytes, totp_secret: str):
        """Save the salt and TOTP secret to the config table."""
        self._ensure_connected()
        assert self.conn is not None and self.cur is not None and self.enc is not None
        enc_secret = self.enc.encrypt_text(totp_secret)
        self.cur.execute("INSERT OR REPLACE INTO config (id, salt, totp_secret) VALUES (1, ?, ?)",
                         (salt, enc_secret))
        self.conn.commit()

    def load_salt(self) -> bytes | None:
        """Load the salt from the config table."""
        self._ensure_connected()
        assert self.conn is not None and self.cur is not None and self.enc is not None
        self.cur.execute("SELECT salt FROM config WHERE id = 1")
        row = self.cur.fetchone()
        return row[0] if row else None

    def load_totp_secret(self) -> str | None:
        """Load and decrypt the TOTP secret from the config table."""
        self._ensure_connected()
        assert self.conn is not None and self.cur is not None and self.enc is not None
        self.cur.execute("SELECT totp_secret FROM config WHERE id = 1")
        row = self.cur.fetchone()
        if row:
            return self.enc.decrypt_text(row[0])
        return None

    def get_all_entries(self) -> list[Entry]:
        """Retrieve and decrypt all journal entries from the database."""
        self._ensure_connected()
        assert self.conn is not None and self.cur is not None and self.enc is not None
        # ensure new columns exist (safe migration)
        self.cur.execute("PRAGMA table_info(entries)")
        cols = [r[1] for r in self.cur.fetchall()]
        if 'encrypted_font_family' not in cols:
            try:
                self.cur.execute("ALTER TABLE entries ADD COLUMN encrypted_font_family BLOB")
            except Exception:
                pass
        if 'encrypted_font_size' not in cols:
            try:
                self.cur.execute("ALTER TABLE entries ADD COLUMN encrypted_font_size BLOB")
            except Exception:
                pass
        if 'encrypted_last_saved' not in cols:
            try:
                self.cur.execute("ALTER TABLE entries ADD COLUMN encrypted_last_saved BLOB")
            except Exception:
                pass
        self.conn.commit()
        self.cur.execute("SELECT id, date, encrypted_title, encrypted_content, encrypted_tags, encrypted_font_family, encrypted_font_size, encrypted_last_saved FROM entries ORDER BY date DESC")
        entries = []
        for row in self.cur.fetchall():
            eid, edate, etitle, econtent, etags, efontfam, efontsize, elast = row
            title = self.enc.decrypt_text(etitle) if etitle else ""
            content = self.enc.decrypt_text(econtent) if econtent else ""
            tags_json = self.enc.decrypt_text(etags) if etags else "[]"
            tags = json.loads(tags_json)
            entry = Entry(eid, edate, title, content, tags)
            # per-entry font metadata
            try:
                entry.font_family = self.enc.decrypt_text(efontfam) if efontfam else None
            except Exception:
                entry.font_family = None
            try:
                fs = self.enc.decrypt_text(efontsize) if efontsize else None
                entry.font_size = int(fs) if fs else None
            except Exception:
                entry.font_size = None
            # last saved
            try:
                entry.last_saved = self.enc.decrypt_text(elast) if elast else None
            except Exception:
                entry.last_saved = None
            # load attachments
            self.cur.execute("SELECT filename, encrypted_data FROM attachments WHERE entry_id = ?", (eid,))
            for fname, edata in self.cur.fetchall():
                data = self.enc.decrypt_data(edata)
                entry.attachments.append({"filename": fname, "data": data})
            entries.append(entry)
        return entries

    def get_dates_with_entries(self) -> list[str]:
        """Get a list of all dates that have journal entries."""
        self._ensure_connected()
        assert self.conn is not None and self.cur is not None and self.enc is not None
        self.cur.execute("SELECT DISTINCT date FROM entries ORDER BY date")
        return [row[0] for row in self.cur.fetchall()]

    def save_entry(self, entry: Entry):
        """Save or update a journal entry and its attachments."""
        self._ensure_connected()
        assert self.conn is not None and self.cur is not None and self.enc is not None
        enc_title = self.enc.encrypt_text(entry.title) if entry.title else None
        enc_content = self.enc.encrypt_text(entry.content) if entry.content else None
        enc_tags = self.enc.encrypt_text(json.dumps(entry.tags))
        enc_font_family = self.enc.encrypt_text(entry.font_family) if getattr(entry, 'font_family', None) else None
        enc_font_size = self.enc.encrypt_text(str(entry.font_size)) if getattr(entry, 'font_size', None) else None
        enc_last_saved = self.enc.encrypt_text(entry.last_saved) if getattr(entry, 'last_saved', None) else None
        if entry.id is None:
            self.cur.execute("""INSERT INTO entries (date, encrypted_title, encrypted_content, encrypted_tags, encrypted_font_family, encrypted_font_size, encrypted_last_saved)
                                VALUES (?, ?, ?, ?, ?, ?, ?)""", (entry.date, enc_title, enc_content, enc_tags, enc_font_family, enc_font_size, enc_last_saved))
            entry.id = self.cur.lastrowid
        else:
            self.cur.execute("""UPDATE entries SET date = ?, encrypted_title = ?, encrypted_content = ?, encrypted_tags = ?, encrypted_font_family = ?, encrypted_font_size = ?, encrypted_last_saved = ?
                                WHERE id = ?""", (entry.date, enc_title, enc_content, enc_tags, enc_font_family, enc_font_size, enc_last_saved, entry.id))
            self.cur.execute("DELETE FROM attachments WHERE entry_id = ?", (entry.id,))
        for att in entry.attachments:
            enc_data = self.enc.encrypt_data(att["data"])
            self.cur.execute("INSERT INTO attachments (entry_id, filename, encrypted_data) VALUES (?, ?, ?)",
                             (entry.id, att["filename"], enc_data))
        self.conn.commit()

    def delete_entry(self, entry_id: int):
        """Delete a journal entry and its attachments by ID."""
        self._ensure_connected()
        assert self.conn is not None and self.cur is not None and self.enc is not None
        self.cur.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self.conn.commit()