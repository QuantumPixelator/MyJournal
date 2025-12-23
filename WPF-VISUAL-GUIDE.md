# MyJournal WPF - Visual Guide

This guide provides a visual walkthrough of the MyJournal WPF application's modern and elegant interface.

## Application Flow

### 1. Initial Setup Window
**First-time users see this setup wizard**

```
┌─────────────────────────────────────────────┐
│  Welcome to MyJournal                       │
│                                             │
│  Create Your Master Password                │
│  ┌─────────────────────────────────────┐   │
│  │ Password: •••••••••                 │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Confirm Password: •••••••••         │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Scan QR Code with Authenticator App        │
│  ┌─────────────────┐                        │
│  │   ▓▓  ▓▓  ▓▓   │  [QR CODE]            │
│  │   ▓▓▓▓▓▓▓▓▓▓   │                        │
│  │   ▓▓  ▓▓  ▓▓   │                        │
│  └─────────────────┘                        │
│                                             │
│  Use Google Authenticator, Authy, etc.     │
│                                             │
│  [ Complete Setup ]  [ Cancel ]             │
└─────────────────────────────────────────────┘
```

**Features:**
- Clean, centered layout with card-style design
- Drop shadow effect for depth
- Large, readable QR code
- Clear instructions
- Modern button styling with rounded corners

---

### 2. Login Window
**Secure authentication screen**

```
┌─────────────────────────────────────────────┐
│                                             │
│           MyJournal                         │
│      Secure Personal Journal                │
│                                             │
│  Master Password                            │
│  ┌─────────────────────────────────────┐   │
│  │ •••••••••••••                       │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Authenticator Code                         │
│  ┌─────────────────────────────────────┐   │
│  │ 123456                              │   │
│  └─────────────────────────────────────┘   │
│                                             │
│           [ Login ]                         │
│           [ Cancel ]                        │
│                                             │
│  ⚠ Invalid code. Attempts remaining: 4     │
└─────────────────────────────────────────────┘
```

**Features:**
- Minimalist, focused design
- Password masking
- 6-digit TOTP code field
- Attempt counter for security
- Error messages in red
- Large, accessible buttons

---

### 3. Main Application Window
**The main journaling interface**

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ ☰ File   Settings                                                               │
├──────────────────────────────────────────────────────────────────────────────────┤
│ [New Entry] │ Font: [Segoe UI ▼] Size: [12 ▼] │ [B][I][U] [Color] [Insert Image]│
├─────────────────────────┬────────────────────────────────────────────────────────┤
│  Calendar               │  Entry Title...                                        │
│  ┌───────────────────┐  │  ─────────────────────────────────────────────────     │
│  │  S  M  T  W  T  F  S │  │                                                     │
│  │     1  2  3  4  5  6 │  │  ┌──────────────────────────────────────────────┐  │
│  │  7  8  9 10 11 12 13 │  │  │ Start writing your journal entry here...    │  │
│  │ 14 15 [16]17 18 19 20│  │  │                                             │  │
│  │ 21 22 23 24 25 26 27 │  │  │ This is a rich text editor with full       │  │
│  │ 28 29 30 31          │  │  │ formatting support including bold,         │  │
│  └───────────────────┘  │  │  │ italic, colors, and images.                │  │
│                         │  │  │                                             │  │
│  Entries                │  │  │                                             │  │
│  ┌───────────────────┐  │  │  └──────────────────────────────────────────────┘  │
│  │ ► My First Entry  │  │  │                                                     │
│  │   Dec 23, 2025    │  │  │  Tags: ┌────────────────────┐  [Attach File]       │
│  ├───────────────────┤  │  │        │ personal, journal  │                       │
│  │ ► Weekend Plans   │  │  │        └────────────────────┘                       │
│  │   Dec 22, 2025    │  │  │                                                     │
│  ├───────────────────┤  │  │  Attachments:                                       │
│  │ ► Work Notes      │  │  │  ┌──────────────────────────┐                       │
│  │   Dec 21, 2025    │  │  │  │ 📄 document.pdf          │                       │
│  └───────────────────┘  │  │  └──────────────────────────┘                       │
│                         │  │                                                     │
│  ┌───────────────────┐  │  │                      [Save Entry] [Discard Changes] │
│  │ Search entries... │  │  │                                                     │
│  └───────────────────┘  │  │                                                     │
└─────────────────────────┴────────────────────────────────────────────────────────┘
```

**Features:**
- **Left Panel (300px)**:
  - Interactive calendar with date highlighting
  - List of entries with date/time
  - Search box for filtering
  
- **Right Panel (Main Area)**:
  - Large title field
  - Rich text editor with toolbar
  - Tag input
  - Attachment management
  - Save/Discard buttons

- **Toolbar**:
  - New Entry button
  - Font family and size selectors
  - Formatting buttons (Bold, Italic, Underline)
  - Color picker
  - Image insertion

---

### 4. Rich Text Formatting

The editor supports:

```
Normal Text
𝗕𝗼𝗹𝗱 𝗧𝗲𝘅𝘁
𝘐𝘵𝘢𝘭𝘪𝘤 𝘛𝘦𝘹𝘵
U̲n̲d̲e̲r̲l̲i̲n̲e̲d̲ ̲T̲e̲x̲t̲
Different Sizes: small / medium / Large / HUGE
Colors: Red, Blue, Green, etc.

• Bulleted lists
• With multiple items

1. Numbered lists
2. Sequential items

[Inline Images]
```

---

### 5. Settings Window

```
┌─────────────────────────────────────────────┐
│  Application Settings                       │
│                                             │
│  ┌─ Theme ──────────────────────────────┐  │
│  │ ○ Light Theme                        │  │
│  │ ● Dark Theme                         │  │
│  │ ○ Auto (System)                      │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌─ Default Font ───────────────────────┐  │
│  │ Font: [Segoe UI ▼]  Size: [12 ▼]    │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌─ Auto-save ──────────────────────────┐  │
│  │ ☑ Enable auto-save                   │  │
│  │ Interval: [30 seconds ▼]             │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌─ Security ───────────────────────────┐  │
│  │ ☑ Lock after 15 min inactivity       │  │
│  │ ☑ Clear clipboard after copy         │  │
│  └──────────────────────────────────────┘  │
│                                             │
│              [ Save ]  [ Cancel ]           │
└─────────────────────────────────────────────┘
```

---

## Design Highlights

### Color Palette
- **Primary**: #2C3E50 (Dark Blue-Gray)
- **Secondary**: #34495E (Darker Gray)
- **Accent**: #3498DB (Bright Blue)
- **Background**: #ECF0F1 (Light Gray)
- **Surface**: #FFFFFF (White)
- **Text**: #2C3E50 (Dark)
- **Secondary Text**: #7F8C8D (Gray)
- **Error**: #E74C3C (Red)

### Typography
- **Primary Font**: Segoe UI (Modern Windows font)
- **Sizes**: 
  - Headlines: 24-32px
  - Body: 14px
  - Small: 11-12px

### Visual Effects
- **Rounded Corners**: 4-8px border radius
- **Drop Shadows**: Subtle shadows for depth
- **Hover Effects**: Color changes on interactive elements
- **Smooth Transitions**: Animated state changes

### Layout Principles
- **Spacing**: Generous padding and margins
- **Hierarchy**: Clear visual hierarchy
- **Consistency**: Uniform styling across components
- **Responsiveness**: Resizable panels with GridSplitter
- **Accessibility**: Large click targets, readable fonts

---

## Modern WPF Features Showcased

1. **XAML Declarative UI**: Clean separation of design and logic
2. **Data Binding**: Automatic UI updates
3. **Styles and Templates**: Reusable design components
4. **Resource Dictionaries**: Centralized theming
5. **Drop Shadows**: Built-in visual effects
6. **Rich Controls**: Calendar, RichTextBox, etc.
7. **Hardware Acceleration**: Smooth rendering via DirectX
8. **Type Safety**: Compile-time checking

---

## Comparison with Qt Version

| Feature | Qt/PySide6 | WPF |
|---------|-----------|-----|
| Window Style | Functional | Modern with rounded corners |
| Colors | Dark theme | Light with accent colors |
| Shadows | None | Drop shadows everywhere |
| Font | Monospace feel | Segoe UI (modern) |
| Spacing | Compact | Generous padding |
| Icons | Custom drawn | Vector-based |
| Animations | Limited | Built-in support |
| Overall Feel | Desktop utility | Modern app |

---

This WPF implementation demonstrates the evolution from a functional Qt application to a polished, modern Windows application that feels native and professional.
