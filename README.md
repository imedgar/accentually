# QuickAccent for Windows

> **macOS-style character popup with 1–9 quick selection and first-class Latvian language support.**

QuickAccent brings the beloved macOS press-and-hold accent menu to Windows. When you hold down a key (such as `a`, `c`, `e`, `g`, `s`, `z`), an elegant floating popup appears near your text cursor. Pressing **1–9** immediately inserts the corresponding accented character and replaces the base letter.

Built specifically to solve the frustration with PowerToys Quick Accent lacking proper Latvian language support and clumsy arrow/space cycling.

---

## 🇱🇻 First-Class Latvian Support

Every Latvian diacritic is mapped directly to **Option #1**, allowing instant, effortless muscle-memory typing:

| Key | Option 1 (Latvian) | Capital Variant | Name / Diacritic |
|:---:|:------------------:|:---------------:|:-----------------|
| `A` | **ā** (1) | **Ā** | A ar garumzīmi (Macron) |
| `C` | **č** (1) | **Č** | Č ar mīkstinājuma zīmi (Caron / Hacek) |
| `E` | **ē** (1) | **Ē** | E ar garumzīmi (Macron) |
| `G` | **ģ** (1) | **Ģ** | Ģ ar mīkstinājuma zīmi (Cedilla / Turned Comma) |
| `I` | **ī** (1) | **Ī** | I ar garumzīmi (Macron) |
| `K` | **ķ** (1) | **Ķ** | Ķ ar mīkstinājuma zīmi (Cedilla / Comma) |
| `L` | **ļ** (1) | **Ļ** | Ļ ar mīkstinājuma zīmi (Cedilla / Comma) |
| `N` | **ņ** (1) | **Ņ** | Ņ ar mīkstinājuma zīmi (Cedilla / Comma) |
| `O` | **ō** (1) | **Ō** | O ar garumzīmi (Latgalian / Archaic) |
| `R` | **ŗ** (1) | **Ŗ** | Ŗ ar mīkstinājuma zīmi (Historical Latvian) |
| `S` | **š** (1) | **Š** | Š ar mīkstinājuma zīmi (Caron / Hacek) |
| `U` | **ū** (1) | **Ū** | U ar garumzīmi (Macron) |
| `Z` | **ž** (1) | **Ž** | Ž ar mīkstinājuma zīmi (Caron / Hacek) |

---

## ⚡ How It Works (macOS Behavior)

1. **Press and Hold** any supported letter key (e.g., hold `e`).
2. After **350 ms** (customizable), the popup appears right above your text cursor:
   ```
   ┌───────────────────────────────────────────────┐
   │ [ ē ]   [ é ]   [ è ]   [ ê ]   [ ë ]   [ ė ] │
   │   1       2       3       4       5       6   │
   └───────────────────────────────────────────────┘
   ```
3. Choose your character using any method:
   - **Press 1–9**: Immediately replaces the letter with that accented variant (e.g., press `1` -> `ē`).
   - **Arrow keys (`←` / `→`) + `Enter` or `Space`**: Navigate and confirm.
   - **Mouse click**: Click any card in the popup.
   - **`Esc`**: Dismiss popup and keep the base letter.
   - **Continue typing**: Pressing another letter auto-dismisses the popup without interrupting typing.
4. **Shift & Caps Lock**: Holding `Shift + A` automatically displays capital variants (`Ā`, `Á`, `Ä`...).
5. **Zero Latency**: Normal fast typing is completely unaffected. The base character appears instantly at `t = 0`; key repeat suppression only kicks in if you hold past the threshold.

---

## 🚀 How to Run

### Option 1: Silent Background Mode (Recommended)
Double-click `run_background.vbs`.  
QuickAccent will start silently in the background with an icon in your Windows system tray.

### Option 2: Console / Debug Mode
Double-click `run.bat` or run:
```cmd
python quick_accent.py
```

### Option 3: Open Settings Directly
```cmd
python quick_accent.py --settings
```

---

## ⚙️ Configuration & Profiles

QuickAccent includes a visual Settings Dialog accessible from the system tray icon or by running with `--settings`.

### Built-in Profiles
1. **Latvian + International (Default)**:  
   Latvian diacritics are always at `#1`, followed by common European accents (`ä`, `é`, `ü`, `ñ`, etc.).
2. **Latvian Exclusive**:  
   Only Latvian characters (`ā, č, ē, ģ, ī, ķ, ļ, ņ, ō, ŗ, š, ū, ž`).
3. **Western European**:  
   Standard French, German, Spanish, and Nordic accents.
4. **Custom**:  
   Define your own characters or symbols in `config.json`.

### Editing `config.json`
You can customize or add any key in `config.json`:
```json
{
  "active_profile": "latvian_first",
  "hold_delay_ms": 350,
  "profiles": {
    "latvian_first": {
      "mappings": {
        "a": ["ā", "á", "ä", "à", "â", "å", "ą", "ã"],
        "c": ["č", "ç", "ć"],
        "e": ["ē", "é", "è", "ê", "ë", "ė", "ę"],
        "s": ["š", "ś", "ş", "ß"]
      }
    }
  }
}
```

---

## 💻 Start with Windows

- **From Tray / Settings**: Right-click the QuickAccent tray icon and check **Start with Windows**, or toggle the checkbox in Settings.
- **Via Scripts**:
  - Run `install_startup.bat` to enable automatic startup.
  - Run `uninstall_startup.bat` to disable it.

---

## 🛠️ Architecture

- **`core/keyboard_hook.py`**: Win32 low-level keyboard hook (`WH_KEYBOARD_LL`) with hold state machine.
- **`core/key_injector.py`**: Atomic `SendInput` Unicode & Backspace injector.
- **`core/overlay_window.py`**: macOS-styled dark floating window with `WS_EX_NOACTIVATE`, DWM rounded corners, and anti-aliased font rendering.
- **`core/caret_detector.py`**: Smart caret, mouse, and active window coordinate detector with work area boundary clamping.
- **`core/tray_icon.py`**: Windows notification tray icon with instant profile and delay switching.
- **`ui/settings_dialog.py`**: Settings interface with an interactive test field.
