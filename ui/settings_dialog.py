"""
Modern Settings Dialog for Accentually.
Allows user to change profiles, customize hold delay, view/edit character sets,
test accents in an interactive test field, and toggle startup with Windows.
"""
import tkinter as tk
import os
from typing import Callable, Optional
from PIL import Image, ImageDraw, ImageTk
from core.config_manager import ConfigManager
from core.paths import resource_path
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
        self.window.title("Accentually - Settings")
        self.window.iconbitmap(resource_path("assets", "app_icon.ico"))
        self.window.geometry("720x790")
        self.window.minsize(640, 700)
        self.bg_color = "#313338"
        self.card_bg = "#2b2d31"
        self.text_color = "#f2f3f5"
        self.subtext_color = "#b5bac1"
        self.accent_color = "#5865f2"
        self.border_color = "#1e1f22"
        self.window.configure(bg=self.bg_color)

        self._build_ui()
        self.window.focus_force()

    def _label(self, parent, text, size=10, color=None, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"),
                        fg=color or self.text_color,
                        font=("Segoe UI", size, "bold" if bold else "normal"),
                        anchor="w", **kwargs)

    def _section(self, parent, title, subtitle=None):
        header = tk.Frame(parent, bg=self.bg_color)
        header.pack(fill="x", pady=(10, 5))
        self._label(header, title.upper(), 9, self.subtext_color, True).pack(side="left")
        if subtitle:
            self._label(header, subtitle, 9, self.subtext_color).pack(side="right")
        return header

    def _button(self, parent, text, command, primary=False):
        bg = self.accent_color if primary else "#404249"
        hover = "#4752c4" if primary else "#4e5058"
        button = tk.Button(parent, text=text, command=command, bg=bg, fg="white",
                           activebackground=hover, activeforeground="white", relief="flat",
                           bd=0, padx=18, pady=8, cursor="hand2", font=("Segoe UI", 9, "bold"))
        button.bind("<Enter>", lambda event: button.configure(bg=hover))
        button.bind("<Leave>", lambda event: button.configure(bg=bg))
        return button

    def _build_ui(self):
        # Pack the footer first so it remains visible on smaller windows.
        footer = tk.Frame(self.window, bg="#2b2d31", padx=28, pady=12)
        footer.pack(side="bottom", fill="x")
        self._button(footer, "Edit config.json", self._open_config_file).pack(side="left")
        self._button(footer, "Done", self.window.destroy, primary=True).pack(side="right")

        content = tk.Frame(self.window, bg=self.bg_color, padx=28, pady=18)
        content.pack(fill="both", expand=True)
        heading = tk.Frame(content, bg=self.bg_color)
        heading.pack(fill="x")
        self._label(heading, "Accentually", 21, bold=True).pack(anchor="w")
        self._label(heading, "Your accents, your way.", 10, self.subtext_color).pack(anchor="w", pady=(1, 0))

        self._section(content, "Character profile", "Choose your accent collection")
        profiles_frame = tk.Frame(content, bg=self.bg_color)
        profiles_frame.pack(fill="x")
        profiles_frame.grid_columnconfigure((0, 1), weight=1, uniform="profiles")
        self.profile_var = tk.StringVar(value=self.config_manager.active_profile_name)
        self.profile_cards = {}
        profiles = [
            ("latvian_first", "Latvian + International", "Latvian first, plus European accents"),
            ("latvian_only", "Latvian Exclusive", "Only Latvian characters"),
            ("international", "Western European", "French, German, Spanish & more"),
            ("custom", "Custom", "Your own character collection"),
        ]
        for index, (key, name, description) in enumerate(profiles):
            card = tk.Frame(profiles_frame, bg=self.card_bg, padx=14, pady=8,
                            highlightthickness=1, highlightbackground=self.card_bg,
                            highlightcolor=self.accent_color, cursor="hand2", takefocus=True)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0, 6) if index % 2 == 0 else (6, 0), pady=4)
            indicator = tk.Canvas(card, width=16, height=16, bg=self.card_bg, highlightthickness=0)
            indicator.pack(side="right", anchor="n", padx=(6, 0), pady=2)
            title = self._label(card, name, 10, bold=True)
            title.pack(anchor="w")
            desc = self._label(card, description, 9, self.subtext_color)
            desc.pack(anchor="w", pady=(3, 0))
            for widget in (card, title, desc, indicator):
                widget.bind("<Button-1>", lambda event, value=key: self._choose_profile(value))
            card.bind("<space>", lambda event, value=key: self._choose_profile(value))
            card.bind("<Return>", lambda event, value=key: self._choose_profile(value))
            self.profile_cards[key] = (card, indicator)
        self._update_profile_cards()

        self._section(content, "Hold delay")
        delay = tk.Frame(content, bg=self.card_bg, padx=14, pady=9)
        delay.pack(fill="x")
        delay_top = tk.Frame(delay, bg=self.card_bg)
        delay_top.pack(fill="x")
        self._label(delay_top, "Time before the menu appears", 10).pack(side="left")
        self.delay_lbl = self._label(delay_top, f"{self.config_manager.hold_delay_ms} ms", 10, "#a5adff", True)
        self.delay_lbl.pack(side="right")
        self.delay_slider = tk.Canvas(delay, height=24, bg=self.card_bg, highlightthickness=1,
                                      highlightbackground=self.card_bg, highlightcolor=self.accent_color,
                                      cursor="hand2", takefocus=True)
        self.delay_slider.pack(fill="x", pady=(8, 3))
        self.delay_slider.bind("<Configure>", lambda event: self._draw_delay_slider())
        self.delay_slider.bind("<Button-1>", self._drag_delay_slider)
        self.delay_slider.bind("<B1-Motion>", self._drag_delay_slider)
        self.delay_slider.bind("<Left>", lambda event: self._step_delay(-10))
        self.delay_slider.bind("<Right>", lambda event: self._step_delay(10))
        markers = tk.Frame(delay, bg=self.card_bg)
        markers.pack(fill="x")
        self._label(markers, "Faster", 9, self.subtext_color).pack(side="left")
        self._label(markers, "More relaxed", 9, self.subtext_color).pack(side="right")

        self._section(content, "Preferences")
        options = tk.Frame(content, bg=self.card_bg, padx=12, pady=7)
        options.pack(fill="x")
        self.fullscreen_var = tk.BooleanVar(value=self.config_manager.pause_in_fullscreen)
        self.startup_var = tk.BooleanVar(value=is_startup_enabled())
        for text, variable, command in [
            ("Pause in full-screen apps (for gaming)", self.fullscreen_var, self._on_fullscreen_toggle),
            ("Start Accentually with Windows", self.startup_var, self._on_startup_toggle),
        ]:
            self._add_toggle(options, text, variable, command)

        self._section(content, "Try it out", "Hold a letter, then choose a number")
        self.test_entry = tk.Entry(content, font=("Segoe UI", 11), bg=self.border_color,
                                   fg=self.text_color, insertbackground=self.text_color, relief="flat",
                                   highlightthickness=1, highlightbackground=self.border_color,
                                   highlightcolor=self.accent_color)
        self.test_entry.insert(0, "Hold 'a' here to try an accent...")
        self.test_entry.pack(fill="x", ipady=8)
        self.test_entry.bind("<FocusIn>", self._clear_test_entry_placeholder)

        self._section(content, "Character mappings", "For the selected profile")
        table = tk.Frame(content, bg=self.card_bg, padx=12, pady=6)
        table.pack(fill="both", expand=True)
        table_header = tk.Frame(table, bg=self.card_bg)
        table_header.pack(fill="x", pady=(0, 4))
        self._label(table_header, "KEY", 8, self.subtext_color, True, width=8).pack(side="left")
        self._label(table_header, "AVAILABLE ACCENTS", 8, self.subtext_color, True).pack(side="left")
        table_body = tk.Frame(table, bg=self.card_bg)
        table_body.pack(fill="both", expand=True)
        self.mapping_canvas = tk.Canvas(table_body, bg=self.card_bg, highlightthickness=0, bd=0)
        self.mapping_scrollbar = tk.Canvas(table_body, width=8, bg=self.card_bg,
                                           highlightthickness=0, bd=0, cursor="hand2")
        self.mapping_scrollbar.pack(side="right", fill="y", padx=(4, 0))
        self.mapping_canvas.pack(side="left", fill="both", expand=True)
        self.mapping_rows = tk.Frame(self.mapping_canvas, bg=self.card_bg)
        self.mapping_window = self.mapping_canvas.create_window(0, 0, anchor="nw", window=self.mapping_rows)
        self.mapping_rows.bind("<Configure>", self._update_mapping_scroll)
        self.mapping_canvas.bind("<Configure>", self._resize_mapping_rows)
        self.mapping_canvas.configure(yscrollcommand=self._draw_mapping_scrollbar)
        self.mapping_scrollbar.bind("<Button-1>", self._scroll_mapping_to)
        self.mapping_scrollbar.bind("<B1-Motion>", self._scroll_mapping_to)
        for widget in (self.mapping_canvas, self.mapping_rows):
            widget.bind("<MouseWheel>", self._scroll_mappings)
        self._populate_character_table()

    def _choose_profile(self, key):
        self.profile_var.set(key)
        self._on_profile_changed()

    def _update_profile_cards(self):
        for key, (card, indicator) in self.profile_cards.items():
            selected = key == self.profile_var.get()
            card.configure(highlightbackground=self.accent_color if selected else self.card_bg)
            indicator.delete("all")
            image = Image.new("RGBA", (64, 64), self.card_bg)
            draw = ImageDraw.Draw(image)
            draw.ellipse((5, 5, 59, 59), outline=self.accent_color if selected else "#80848e", width=7)
            if selected:
                draw.ellipse((20, 20, 44, 44), fill=self.accent_color)
            indicator.image = ImageTk.PhotoImage(image.resize((16, 16), Image.Resampling.LANCZOS))
            indicator.create_image(0, 0, image=indicator.image, anchor="nw")

    def _add_toggle(self, parent, text, variable, command):
        row = tk.Frame(parent, bg=self.card_bg, cursor="hand2")
        row.pack(fill="x", pady=3)
        label = self._label(row, text, 10)
        label.pack(side="left")
        switch = tk.Canvas(row, width=38, height=22, bg=self.card_bg, highlightthickness=1,
                           highlightbackground=self.card_bg, highlightcolor=self.accent_color,
                           cursor="hand2", takefocus=True)
        switch.pack(side="right")

        def draw(*_):
            switch.delete("all")
            enabled = variable.get()
            color = self.accent_color if enabled else "#6d6f78"
            image = Image.new("RGBA", (152, 88), self.card_bg)
            painter = ImageDraw.Draw(image)
            painter.rounded_rectangle((4, 4, 148, 84), radius=40, fill=color)
            x = 108 if enabled else 44
            painter.ellipse((x - 27, 17, x + 27, 71), fill="white")
            switch.image = ImageTk.PhotoImage(image.resize((38, 22), Image.Resampling.LANCZOS))
            switch.create_image(0, 0, image=switch.image, anchor="nw")

        def toggle(event=None):
            variable.set(not variable.get())
            command()

        variable.trace_add("write", draw)
        for widget in (row, label, switch):
            widget.bind("<Button-1>", toggle)
        switch.bind("<space>", toggle)
        switch.bind("<Return>", toggle)
        draw()

    def _draw_delay_slider(self):
        canvas = self.delay_slider
        width = max(canvas.winfo_width(), 24)
        left, right = 10, width - 10
        x = left + (right - left) * (self.config_manager.hold_delay_ms - 180) / 420
        x = max(left, min(right, x))
        canvas.delete("all")
        image = Image.new("RGBA", (width * 4, 96), self.card_bg)
        painter = ImageDraw.Draw(image)
        painter.rounded_rectangle((left * 4, 38, right * 4, 58), radius=10, fill="#1e1f22")
        if x > left:
            painter.rounded_rectangle((left * 4, 38, int(x * 4), 58), radius=10, fill=self.accent_color)
        painter.ellipse((int((x - 7) * 4), 20, int((x + 7) * 4), 76), fill="#f2f3f5")
        canvas.image = ImageTk.PhotoImage(image.resize((width, 24), Image.Resampling.LANCZOS))
        canvas.create_image(0, 0, image=canvas.image, anchor="nw")

    def _drag_delay_slider(self, event):
        width = max(self.delay_slider.winfo_width() - 20, 1)
        value = 180 + 420 * max(0, min(width, event.x - 10)) / width
        self._on_delay_slider_change(value)

    def _step_delay(self, step):
        self._on_delay_slider_change(max(180, min(600, self.config_manager.hold_delay_ms + step)))

    def _clear_test_entry_placeholder(self, event):
        if "Hold 'a'" in self.test_entry.get():
            self.test_entry.delete(0, 'end')

    def _on_profile_changed(self):
        new_prof = self.profile_var.get()
        self.config_manager.active_profile_name = new_prof
        self._populate_character_table()
        self._update_profile_cards()
        if self.on_change:
            self.on_change()

    def _on_delay_slider_change(self, val):
        ms = round(float(val) / 10) * 10
        self.delay_lbl.configure(text=f"{ms} ms")
        self.config_manager.hold_delay_ms = ms
        self._draw_delay_slider()
        if self.on_change:
            self.on_change()

    def _on_startup_toggle(self):
        enabled = self.startup_var.get()
        set_startup_enabled(enabled)

    def _on_fullscreen_toggle(self):
        self.config_manager.pause_in_fullscreen = self.fullscreen_var.get()

    def _resize_mapping_rows(self, event):
        self.mapping_canvas.itemconfigure(self.mapping_window, width=event.width)
        self._update_mapping_scroll()

    def _update_mapping_scroll(self, event=None):
        self.mapping_canvas.configure(scrollregion=self.mapping_canvas.bbox("all"))

    def _draw_mapping_scrollbar(self, first, last):
        bar = self.mapping_scrollbar
        bar.delete("all")
        height = bar.winfo_height()
        first, last = float(first), float(last)
        if height > 1 and last - first < 1:
            top = int(first * height)
            bottom = max(top + 12, int(last * height))
            bar.create_line(4, top + 4, 4, min(height - 4, bottom - 4),
                            fill="#6d6f78", width=5, capstyle="round")

    def _scroll_mapping_to(self, event):
        self.mapping_canvas.yview_moveto(event.y / max(self.mapping_scrollbar.winfo_height(), 1))

    def _scroll_mappings(self, event):
        self.mapping_canvas.yview_scroll(-int(event.delta / 120), "units")
        return "break"

    def _populate_character_table(self):
        for child in self.mapping_rows.winfo_children():
            child.destroy()
            
        prof_key = self.config_manager.active_profile_name
        profiles = self.config_manager.get_profiles()
        profile = profiles.get(prof_key, {})
        mappings = profile.get("mappings", {})

        for base_key, accents in sorted(mappings.items()):
            numbered_accents = "  ".join([f"{i+1}:{ch}" for i, ch in enumerate(accents[:9])])
            if len(accents) > 9:
                numbered_accents += "  (" + ", ".join(accents[9:]) + ")"
            row = tk.Frame(self.mapping_rows, bg=self.card_bg, pady=4)
            row.pack(fill="x")
            key_label = self._label(row, base_key.upper(), 10, self.text_color, True, width=8)
            key_label.pack(side="left")
            accents_label = self._label(row, numbered_accents, 10, self.subtext_color)
            accents_label.pack(side="left", fill="x", expand=True)
            for widget in (row, key_label, accents_label):
                widget.bind("<MouseWheel>", self._scroll_mappings)
        self.mapping_canvas.yview_moveto(0)
        self._update_mapping_scroll()

    def _open_config_file(self):
        cfg_path = self.config_manager.config_path
        if os.path.exists(cfg_path):
            os.startfile(cfg_path)
