# Contributing to Accentually

Thanks for helping out! Accentually is a small Windows tray app (Python, Tkinter, Win32/UI Automation), so changes are easy to review when they stay focused.

## Workflow

1. Open an issue first for anything larger than a small fix, so we can agree on the approach.
2. Fork the repo (or branch, if you have write access) and create a topic branch from `master`, e.g. `fix/popup-position` or `feat/new-profile`.
3. Make your change, add or update tests, and run them:
   ```
   pip install -r requirements.txt
   python -m unittest discover -s tests
   ```
4. Open a pull request against `master`. Fill in the template and keep the PR to one logical change.

`master` is protected: changes land through pull requests that pass CI and get a review. The maintainer may push directly.

## Guidelines

- **Windows only.** Code may use `ctypes`/`winreg`; keep Win32 calls typed (`argtypes`/`restype`) so 64-bit handles don't truncate.
- **Never block the keyboard hook or the Tk thread.** Slow work (UI Automation, network) runs off-thread or in a child process.
- **Don't steal focus or log keystrokes.** The app sees every key press: never store, print or transmit typed text.
- **Paths:** use `core/paths.py` (`resource_path`, `user_data_dir`) rather than `__file__`, so source and installed builds both work.
- **Style:** match the surrounding code; type hints and short docstrings where they help. No new dependencies without discussion, since each one grows the installer.
- **Tests:** add a regression test for bug fixes. Tests must not need a display or a specific foreground app.
- **Commits:** short imperative subject (`Fix popup position on second monitor`), details in the body.

## Testing manually

Run `python quick_accent.py`, then hold a letter in Notepad, a browser text box, and an Electron/WebView2 app (VS Code, WhatsApp) and check the popup lands above the caret. Mention which apps you tried in the PR.

## Releases (maintainer)

Bump `__version__` in `core/version.py`, merge, then push a tag `vX.Y.Z`. The Release workflow builds the installer and publishes it; installed clients update from it. See the README.

## Reporting security issues

Please don't open a public issue; see [SECURITY.md](SECURITY.md).

## License

By contributing you agree your work is licensed under the [MIT License](LICENSE).
