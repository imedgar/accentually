# AGENTS.md

## What this is

Accentually is a Windows tray app for typing accented characters. Holding a letter opens a popup near the caret with numbered choices and Latvian-first defaults. It uses Python, Tkinter, Win32 and UI Automation.

## Commands

Run from the repository root on Windows. CI uses Python 3.13.

- Install: `python -m pip install -r requirements.txt`
- Run: `python quick_accent.py`
- Test: `python -m unittest discover -s tests`
- Lint: none yet

## Layout

- `.github/`: Windows CI, release workflow and contribution templates
- `assets/`: app icon and icon generator
- `core/`: keyboard hook, character insertion, caret detection, popup, tray, config and updates
- `installer/`: Inno Setup installer definition. Root `build.ps1` builds the Windows package using PyInstaller and Inno Setup.
- `tests/`: unittest suite
- `ui/`: Tkinter settings dialog

## Project rules

- Set `argtypes` and `restype` on Win32 calls to preserve 64-bit handles. Move slow work off the keyboard hook and Tk threads.
- Keep the popup from taking focus. Never store, log or transmit typed text.
- Use `core/paths.py` for bundled resources and user data so source and packaged builds both work.
- Add regression tests for bug fixes. Keep tests independent of the display and foreground app. Discuss new dependencies before adding them.

## Principles

This repo follows [groundwork](https://github.com/imedgar/groundwork/blob/main/PRINCIPLES.md). Cloud agents, CI and collaborators may not have it loaded, so these are the rules that matter most here:
- Work on a branch and open a PR; never push to main. Never commit secrets.
- Do what was asked, and only that, with the smallest change that solves it.
- Done means checked: run the test and lint commands above and report what actually happened, including failures.
- Get facts from tools and the scripts in this repo, not from memory. Pin versions, refs and time windows.
