MyJournal
=========

A small, encrypted personal journaling app with a rich-text editor.

Run
---
- Activate the project's venv and run the app (Windows):

```powershell
& .\.venv\Scripts\Activate.ps1
.venv\Scripts\python.exe main.py
```

Features
--------
- Encrypted SQLite storage (per-field encryption)
- Rich-text editor (bold, italic, underline, strike, color, inline images)
- Per-entry or app-default font and size (persisted via settings)
- Autosave, Save / Discard flows, and right-click delete with confirmation
- List formatting (bulleted / numbered) and selection font-size increase/decrease

Quick tests performed
---------------------
- DB round-trip: save and reload entries including font metadata and last-saved timestamp
- Settings: `QSettings` persistence for default font and size

Notes
-----
- The database is encrypted; losing the master password or authenticator makes data unrecoverable.
- If you need automated GUI tests, we can add a small headless test harness.

If everything looks good I can keep polishing or add automated tests and a small diagnostics command.
