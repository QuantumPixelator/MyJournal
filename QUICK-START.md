# Quick Start Guide - MyJournal WPF

## Installation & First Run

### System Requirements
- Windows 10 or 11 (64-bit)
- .NET 8 Runtime or newer
- 50 MB free disk space
- Authenticator app on your phone

### First Launch

1. **Run the application**
   ```
   Double-click MyJournalWPF.exe
   ```

2. **Initial Setup** (First time only)
   - Create a strong master password
   - Confirm your password
   - Open your authenticator app (Google Authenticator, Microsoft Authenticator, etc.)
   - Scan the QR code displayed
   - Click "Complete Setup"

3. **Login**
   - Enter your master password
   - Enter the 6-digit code from your authenticator app
   - Click "Login"

## Common Tasks

### Creating a New Entry

**Method 1: Using Menu**
```
File → New Entry
```

**Method 2: Using Toolbar**
```
Click "New Entry" button
```

**Method 3: Using Keyboard**
```
Press Ctrl+N
```

### Writing an Entry

1. **Add a Title** (Required)
   - Click in the "Entry Title..." field
   - Type your title

2. **Write Content**
   - Click in the editor area
   - Start typing
   - Use formatting toolbar for rich text

3. **Add Tags** (Optional)
   - Enter comma-separated tags
   - Example: `personal, journal, ideas`

4. **Save**
   - Click "Save Entry"
   - Or press `Ctrl+S`

### Formatting Text

| Action | Toolbar Button | Keyboard Shortcut |
|--------|---------------|-------------------|
| **Bold** | **B** button | `Ctrl+B` |
| **Italic** | *I* button | `Ctrl+I` |
| **Underline** | <u>U</u> button | `Ctrl+U` |
| **Font** | Font dropdown | N/A |
| **Size** | Size dropdown | N/A |
| **Color** | Color button | N/A |

### Adding Images

1. Click "Insert Image" in toolbar
2. Browse to your image file
3. Select image (JPG, PNG, GIF, BMP)
4. Click "Open"
5. Image appears inline in your text

### Attaching Files

1. Click "Attach File" button
2. Browse to any file
3. Click "Open"
4. File appears in Attachments list
5. Double-click attachment to save it later

### Finding Entries

**By Date:**
1. Click a date on the calendar
2. Entries for that date appear in the list

**By Search:**
1. Type in the search box
2. Entries matching your search appear
3. Searches titles, content, and tags

**Clear Filters:**
1. Clear the search box
2. Click any calendar date to reset

### Viewing an Entry

1. Click any entry in the list
2. Entry loads in the editor
3. Edit as needed
4. Click "Save Entry" to save changes

### Deleting an Entry

**Method 1: Using Menu**
```
File → Delete Entry
Confirm deletion
```

**Method 2: While Viewing Entry**
```
Click "Discard Changes"
Confirm deletion (if entry is saved)
```

### Exporting an Entry

1. Open the entry you want to export
2. Go to `File → Export to HTML`
3. Choose save location
4. Click "Save"
5. HTML file contains your entry

### Backing Up Your Data

1. Go to `File → Backup Database`
2. Choose save location
3. Save as: `myjournal_backup_YYYYMMDD.db`
4. Click "Save"

**Important:** Store backups securely! They contain encrypted data.

## Settings

### Changing Theme

1. Click `Settings` in menu bar
2. Select theme:
   - Light Theme
   - Dark Theme
   - Auto (follows system)
3. Click "Save"

### Default Font

1. Click `Settings`
2. Choose font family
3. Choose font size
4. Click "Save"
5. New entries use this font

### Auto-Save Settings

1. Click `Settings`
2. Check/uncheck "Enable auto-save"
3. Select interval (15s, 30s, 1min, etc.)
4. Click "Save"

## Security Best Practices

### Password Management
✅ **DO:**
- Use a unique, strong password
- Write it down and store securely
- Never share your password

❌ **DON'T:**
- Reuse passwords from other services
- Use simple or common passwords
- Store password in plain text files

### Authenticator App
✅ **DO:**
- Keep your phone secure
- Enable backup for authenticator app
- Test TOTP codes during setup

❌ **DON'T:**
- Uninstall authenticator without backup
- Share TOTP secret
- Screenshot QR code and leave it on device

### Data Backup
✅ **DO:**
- Backup regularly (weekly recommended)
- Store backups in multiple locations
- Test restoring from backup

❌ **DON'T:**
- Rely on a single backup
- Store backups in same location as PC
- Forget your master password

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New Entry | `Ctrl+N` |
| Save Entry | `Ctrl+S` |
| Bold Text | `Ctrl+B` |
| Italic Text | `Ctrl+I` |
| Underline Text | `Ctrl+U` |
| Exit App | `Alt+F4` |

## Troubleshooting

### Can't Login

**Symptom:** "Invalid password" error

**Solutions:**
1. Make sure Caps Lock is OFF
2. Check password is correct
3. Verify TOTP code is current (refreshes every 30s)
4. Check time on computer is correct

### Lost Authenticator

**Symptom:** Don't have access to TOTP codes

**Solutions:**
1. If you have backup codes from authenticator, use those
2. If you have database backup, you can recover
3. If neither: **Data is permanently lost** (by design)

### Entry Won't Save

**Symptom:** Can't save entry

**Solutions:**
1. Ensure entry has a title
2. Check disk space
3. Verify database isn't read-only
4. Try restarting application

### Application Won't Start

**Symptom:** Double-click does nothing

**Solutions:**
1. Install .NET 8 Runtime
2. Check Windows version (10/11 required)
3. Run as Administrator
4. Check antivirus isn't blocking

### Database Corrupted

**Symptom:** Error loading entries

**Solutions:**
1. Restore from latest backup
2. Check if database file exists
3. Verify file isn't corrupted
4. Last resort: Delete and start fresh

## Tips & Tricks

### Productivity
- Use `Ctrl+N` to quickly create entries
- Use tags to categorize entries
- Search is your friend - tag entries consistently
- Export important entries as HTML backup

### Organization
- Develop a tagging system (work, personal, ideas, etc.)
- Review old entries periodically
- Use calendar to find entries by date
- Keep titles descriptive

### Security
- Change master password annually
- Backup before major system updates
- Test restore process occasionally
- Keep authenticator app updated

### Writing
- Use formatting to highlight important parts
- Add images to make entries memorable
- Attach related files to keep everything together
- Write regularly - even short entries

## Getting Help

### Error Messages
Most error messages are self-explanatory. Common ones:

- **"Missing Title"** - Add a title before saving
- **"Invalid Code"** - Check TOTP is current
- **"Too Many Attempts"** - Wait and restart app
- **"Database Error"** - Restore from backup

### Additional Resources
- Check README-WPF.md for technical details
- See WPF-COMPARISON.md for feature comparison
- Review WPF-VISUAL-GUIDE.md for UI walkthrough

### Support
For bugs or questions, open an issue on GitHub.

---

**Enjoy journaling with MyJournal WPF!** 📝✨
