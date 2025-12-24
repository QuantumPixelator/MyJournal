MyJournal
MyJournal
=========

A small, encrypted personal journaling app with a rich-text editor.

![App screenshot](screenshot.png)

Run
---
- Windows (PowerShell):

```powershell
& .\\.venv\\Scripts\\Activate.ps1
.venv\\Scripts\\python.exe main.py
```

- Linux / macOS (bash):

```bash
python3 -m venv .venv
source .venv/bin/activate
python main.py
```

Features
--------
- Encrypted SQLite storage (per-field encryption)
- Rich-text editor (bold, italic, underline, strike, color, inline images)
- Per-entry or app-default font and size (persisted via settings)
- Autosave, Save / Discard flows, and right-click delete with confirmation
- List formatting (bulleted / numbered) and selection font-size increase/decrease

Notes
-----
- The database is encrypted; losing the master password or authenticator makes data unrecoverable.
