# MyJournal - Modern WPF Edition

A beautiful, modern, and elegant personal journaling application built with **Windows Presentation Foundation (WPF)** and **.NET 8**.

![WPF Application](screenshot-wpf.png)

## Features

### 🎨 Modern & Elegant UI
- Clean, contemporary design with smooth animations
- Intuitive layout with calendar, entry list, and rich text editor
- Professional color scheme and typography
- Responsive controls with visual feedback

### 🔐 Security First
- AES-256 encryption for all journal entries and attachments
- PBKDF2 key derivation with 200,000 iterations
- Two-factor authentication using TOTP (Time-based One-Time Password)
- Master password protection
- Encrypted SQLite database

### ✨ Rich Text Editing
- Full formatting support (bold, italic, underline)
- Font family and size customization
- Text color selection
- Inline image insertion
- Per-entry font preferences

### 📅 Organization & Search
- Interactive calendar view with entry indicators
- List view of all entries sorted by date
- Real-time search across titles, content, and tags
- Tag-based categorization
- Date filtering

### 📎 Attachments
- Attach any file type to entries
- Encrypted file storage
- Easy file management
- Double-click to save attachments

### 💾 Data Management
- Auto-save functionality
- Manual save/discard options
- Export entries to HTML
- Database backup feature
- Entry deletion with confirmation

## Requirements

- **Windows 10/11** (64-bit)
- **.NET 8 Runtime** or SDK
- **Authenticator app** (Google Authenticator, Microsoft Authenticator, Authy, etc.)

## Building from Source

### Prerequisites
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- Visual Studio 2022 (optional, recommended for best experience)

### Build Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/QuantumPixelator/MyJournal.git
   cd MyJournal
   git checkout wpf
   ```

2. **Restore dependencies:**
   ```bash
   dotnet restore MyJournalWPF.sln
   ```

3. **Build the application:**
   ```bash
   dotnet build MyJournalWPF.sln --configuration Release
   ```

4. **Run the application:**
   ```bash
   dotnet run --project MyJournalWPF/MyJournalWPF.csproj
   ```

   Or open `MyJournalWPF.sln` in Visual Studio and press F5.

## First-Time Setup

1. **Launch the application**
   - On first run, you'll see the setup wizard

2. **Create master password**
   - Choose a strong, memorable password
   - Confirm your password

3. **Scan QR code**
   - Open your authenticator app
   - Scan the displayed QR code
   - Save the entry in your authenticator

4. **Complete setup**
   - Click "Complete Setup"
   - The setup is now complete!

## Usage

### Logging In
1. Enter your master password
2. Enter the 6-digit code from your authenticator app
3. Click "Login"

### Creating Entries
- Click "New Entry" or use **Ctrl+N**
- Add a title (required)
- Write your content in the rich text editor
- Add tags (comma-separated)
- Attach files if needed
- Click "Save Entry" or use **Ctrl+S**

### Formatting Text
- **Bold**: Ctrl+B or toolbar button
- **Italic**: Ctrl+I or toolbar button
- **Underline**: Ctrl+U or toolbar button
- Change font family and size from toolbar
- Select text color using the color picker
- Insert images using the "Insert Image" button

### Organizing Entries
- Use the calendar to view entries by date
- Search using the search box (searches titles, content, and tags)
- Click any entry in the list to view/edit it

### Managing Attachments
- Click "Attach File" to add files to an entry
- Attachments are encrypted and stored with the entry
- Double-click an attachment to save it to disk

## Architecture & Technology Stack

### WPF Framework
- **XAML**: Declarative UI markup
- **Data Binding**: MVVM-ready architecture
- **Styling**: Custom control templates and styles
- **Rich Controls**: Calendar, RichTextBox, ListBox, etc.

### Security
- **AES Encryption**: Industry-standard symmetric encryption
- **PBKDF2**: Password-based key derivation
- **TOTP**: RFC 6238 compliant two-factor authentication
- **Entity Framework Core**: Secure database access

### Libraries Used
- **Microsoft.EntityFrameworkCore.Sqlite**: Database ORM
- **Otp.NET**: TOTP implementation
- **QRCoder**: QR code generation for TOTP setup
- **System.Drawing.Common**: Image processing

### Project Structure
```
MyJournalWPF/
├── Models/
│   └── Entry.cs              # Data models
├── Services/
│   └── EncryptionService.cs  # Encryption logic
├── App.xaml                   # Application resources and startup
├── App.xaml.cs               # Application logic
├── MainWindow.xaml           # Main UI layout
├── MainWindow.xaml.cs        # Main window logic
├── SetupWindow.xaml          # Initial setup UI
├── SetupWindow.xaml.cs       # Setup logic
├── LoginWindow.xaml          # Login UI
├── LoginWindow.xaml.cs       # Login logic
├── SettingsWindow.xaml       # Settings UI
├── SettingsWindow.xaml.cs    # Settings logic
└── JournalDbContext.cs       # Database context
```

## Comparison: Qt/PySide6 vs WPF

### What Makes WPF Special

1. **Native Windows Integration**
   - Deep OS integration
   - Hardware acceleration via DirectX
   - Native Windows controls and feel

2. **XAML Power**
   - Separation of UI and logic
   - Designer-friendly
   - Powerful data binding
   - Resource dictionaries for theming

3. **Styling & Templating**
   - Complete control over visual appearance
   - Reusable styles and templates
   - Triggers and animations built-in
   - No code required for many customizations

4. **Performance**
   - GPU-accelerated rendering
   - Efficient layout system
   - Smooth animations

5. **Rich Control Library**
   - Calendar, DatePicker
   - RichTextBox with full formatting
   - Built-in data grids
   - Document viewers

## Security Notes

⚠️ **Important**: 
- Keep your master password secure
- Back up your authenticator app TOTP secret
- Regularly backup your database using the built-in backup feature
- Losing your password or TOTP secret means **permanent data loss**

## License

See the main repository for license information.

## Contributing

Contributions are welcome! This WPF branch demonstrates modern Windows desktop development.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Built with ❤️ using WPF and .NET 8**
