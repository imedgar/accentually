"""
Modern Settings Dialog for QuickAccent.
Allows user to change profiles, customize hold delay, view/edit character sets,
test accents in an interactive test field, and toggle startup with Windows.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
from typing import Callable, Optional
from core.config_manager import ConfigManager
from core.startup_manager import is_startup_enabled, set_startup_enabled

class SettingsDialog:
    def __init__(self, root: tk.Tk, config_manager: ConfigManager, on_change: Optional[Callable[[], None]] = None):
        self.root = root
        self.config_manager = config_manager
        self.on_change = on_change
        self.window: Optional[tk.Toplevel] = None

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.root)
        self.window.title("QuickAccent - Settings")
        self.window.geometry("640x700")
        self.window.minsize(580, 620)
        
        # Modern Dark Palette
        self.bg_color = "#1E1E20"
        self.card_bg = "#28282B"
        self.text_color = "#FFFFFF"
        self.subtext_color = "#A0A0A5"
        self.accent_color = "#0A84FF"
        self.border_color = "#3A3A3C"
        
        self.window.configure(bg=self.bg_color)
        
        # Style ttk widgets
        style = ttk.Style(self.window)
        style.theme_use('clam')
        style.configure('Treeview',
                        background=self.card_bg,
                        foreground=self.text_color,
                        fieldbackground=self.card_bg,
                        rowheight=28,
                        font=('Segoe UI', 10))
        style.configure('Treeview.Heading',
                        background='#333336',
                        foreground=self.text_color,
                        font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', self.accent_color)])

        self._build_ui()
        self.window.focus_force()

    def _build_ui(self):
        # 1. Header Frame
        header = tk.Frame(self.window, bg=self.bg_color, padx=20, pady=15)
        header.pack(fill='x')
        
        title_lbl = tk.Label(
            header,
            text="QuickAccent",
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_color,
            fg=self.text_color
        )
        title_lbl.pack(anchor='w')
        
        subtitle_lbl = tk.Label(
            header,
            text="macOS-style character popup with first-class Latvian language support",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg=self.subtext_color
        )
        subtitle_lbl.pack(anchor='w')

        # 2. Main Scrollable or Notebook Content
        content = tk.Frame(self.window, bg=self.bg_color, padx=20, pady=0)
        content.pack(fill='both', expand=True)

        # Profile Selection Section
        prof_frame = tk.LabelFrame(
            content,
            text=" Character Profile ",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_color,
            fg=self.text_color,
            padx=12,
            pady=10
        )
        prof_frame.pack(fill='x', pady=6)

        self.profile_var = tk.StringVar(value=self.config_manager.active_profile_name)
        profiles = [
            ("latvian_first", "Latvian + International (Recommended)", "Latvian characters at #1, followed by European accents"),
            ("latvian_only", "Latvian Exclusive", "Strictly Latvian diacritics only (ā, č, ē, ģ, ī, ķ, ļ, ņ, ō, ŗ, š, ū, ž)"),
            ("international", "Western European", "Standard French, German, Spanish diacritics"),
            ("custom", "Custom Profile", "Editable user-defined characters")
        ]

        for key, name, desc in profiles:
            rb_frame = tk.Frame(prof_frame, bg=self.bg_color)
            rb_frame.pack(fill='x', pady=2)
            rb = tk.Radiobutton(
                rb_frame,
                text=name,
                variable=self.profile_var,
                value=key,
                font=("Segoe UI", 10, "bold"),
                bg=self.bg_color,
                fg=self.text_color,
                selectcolor="#333336",
                activebackground=self.bg_color,
                activeforeground=self.text_color,
                command=self._on_profile_changed
            )
            rb.pack(anchor='w')
            desc_lbl = tk.Label(
                rb_frame,
                text=f"  {desc}",
                font=("Segoe UI", 8),
                bg=self.bg_color,
                fg=self.subtext_color
            )
            desc_lbl.pack(anchor='w')

        # Hold Delay Section
        delay_frame = tk.LabelFrame(
            content,
            text=" Key Hold Delay ",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_color,
            fg=self.text_color,
            padx=12,
            pady=8
        )
        delay_frame.pack(fill='x', pady=6)

        delay_top = tk.Frame(delay_frame, bg=self.bg_color)
        delay_top.pack(fill='x')

        self.delay_lbl = tk.Label(
            delay_top,
            text=f"Hold duration: {self.config_manager.hold_delay_ms} ms",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg=self.text_color
        )
        self.delay_lbl.pack(side='left')

        self.delay_slider = tk.Scale(
            delay_frame,
            from_=180,
            to_=600,
            orient='horizontal',
            resolution=10,
            showvalue=False,
            bg=self.bg_color,
            fg=self.text_color,
            troughcolor=self.card_bg,
            highlightthickness=0,
            activebackground=self.accent_color,
            command=self._on_delay_slider_change
        )
        self.delay_slider.set(self.config_manager.hold_delay_ms)
        self.delay_slider.pack(fill='x', pady=(4, 2))

        markers_frame = tk.Frame(delay_frame, bg=self.bg_color)
        markers_frame.pack(fill='x')
        tk.Label(markers_frame, text="Fast (200ms)", font=("Segoe UI", 8), bg=self.bg_color, fg=self.subtext_color).pack(side='left')
        tk.Label(markers_frame, text="Normal (350ms)", font=("Segoe UI", 8), bg=self.bg_color, fg=self.subtext_color).pack(side='left', expand=True)
        tk.Label(markers_frame, text="Relaxed (500ms)", font=("Segoe UI", 8), bg=self.bg_color, fg=self.subtext_color).pack(side='right')

        # Interactive Test Box
        test_frame = tk.LabelFrame(
            content,
            text=" Interactive Test Field ",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_color,
            fg=self.text_color,
            padx=12,
            pady=8
        )
        test_frame.pack(fill='x', pady=6)

        self.test_entry = tk.Entry(
            test_frame,
            font=("Segoe UI", 13),
            bg=self.card_bg,
            fg=self.text_color,
            insertbackground=self.text_color,
            relief='flat',
            highlightthickness=1,
            highlightbackground=self.border_color
        )
        self.test_entry.insert(0, "Hold 'a', 'c', 'e', 'g', 'i', 'k', 'l', 'n', 's', 'u', 'z' here...")
        self.test_entry.pack(fill='x', ipady=4)
        self.test_entry.bind("<FocusIn>", self._clear_test_entry_placeholder)

        # Character Map Table Section
        map_frame = tk.LabelFrame(
            content,
            text=" Active Character Mappings ",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_color,
            fg=self.text_color,
            padx=12,
            pady=8
        )
        map_frame.pack(fill='both', expand=True, pady=6)

        table_container = tk.Frame(map_frame, bg=self.bg_color)
        table_container.pack(fill='both', expand=True)

        columns = ("key", "accents")
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', height=5)
        self.tree.heading("key", text="Base Key")
        self.tree.heading("accents", text="Available Accents (1-9)")
        self.tree.column("key", width=80, anchor='center')
        self.tree.column("accents", width=460, anchor='w')

        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self._populate_character_table()

        # Options Section
        opts_frame = tk.Frame(content, bg=self.bg_color)
        opts_frame.pack(fill='x', pady=4)

        self.startup_var = tk.BooleanVar(value=is_startup_enabled())
        startup_cb = tk.Checkbutton(
            opts_frame,
            text="Start QuickAccent automatically with Windows",
            variable=self.startup_var,
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.text_color,
            selectcolor="#333336",
            activebackground=self.bg_color,
            activeforeground=self.text_color,
            command=self._on_startup_toggle
        )
        startup_cb.pack(anchor='w')

        # 3. Bottom Action Buttons
        btn_bar = tk.Frame(self.window, bg=self.bg_color, padx=20, pady=12)
        btn_bar.pack(fill='x', side='bottom')

        btn_open_json = tk.Button(
            btn_bar,
            text="Edit config.json",
            font=("Segoe UI", 9),
            bg=self.card_bg,
            fg=self.text_color,
            relief='flat',
            padx=10,
            pady=4,
            command=self._open_config_file
        )
        btn_open_json.pack(side='left')

        btn_close = tk.Button(
            btn_bar,
            text="Done",
            font=("Segoe UI", 10, "bold"),
            bg=self.accent_color,
            fg="#FFFFFF",
            relief='flat',
            padx=20,
            pady=4,
            command=self.window.destroy
        )
        btn_close.pack(side='right')

    def _clear_test_entry_placeholder(self, event):
        if "Hold 'a'" in self.test_entry.get():
            self.test_entry.delete(0, 'end')

    def _on_profile_changed(self):
        new_prof = self.profile_var.get()
        self.config_manager.active_profile_name = new_prof
        self._populate_character_table()
        if self.on_change:
            self.on_change()

    def _on_delay_slider_change(self, val):
        ms = int(float(val))
        self.delay_lbl.configure(text=f"Hold duration: {ms} ms")
        self.config_manager.hold_delay_ms = ms
        if self.on_change:
            self.on_change()

    def _on_startup_toggle(self):
        enabled = self.startup_var.get()
        set_startup_enabled(enabled)

    def _populate_character_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        prof_key = self.config_manager.active_profile_name
        profiles = self.config_manager.get_profiles()
        profile = profiles.get(prof_key, {})
        mappings = profile.get("mappings", {})

        for base_key, accents in sorted(mappings.items()):
            numbered_accents = "  ".join([f"{i+1}:{ch}" for i, ch in enumerate(accents[:9])])
            if len(accents) > 9:
                numbered_accents += "  (" + ", ".join(accents[9:]) + ")"
            self.tree.insert("", "end", values=(base_key.upper() + " / " + base_key, numbered_accents))

    def _open_config_file(self):
        cfg_path = self.config_manager.config_path
        if os.path.exists(cfg_path):
            os.startfile(cfg_path)
