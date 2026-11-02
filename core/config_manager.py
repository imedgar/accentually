"""
Configuration manager for QuickAccent.
Handles loading, saving, and querying character profiles and settings.
"""
import json
import os
import copy
from typing import Dict, List, Optional, Callable

from core.paths import default_config_path

DEFAULT_CONFIG_PATH = default_config_path()

class ConfigManager:
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self._listeners: List[Callable[[], None]] = []
        self.config = self._load()

    def _get_default_config(self) -> dict:
        return {
            "active_profile": "latvian_first",
            "hold_delay_ms": 350,
            "theme": "dark",
            "position_mode": "caret_or_center",
            "play_sound": False,
            "auto_capitalize": True,
            "pause_in_fullscreen": False,
            "check_updates": True,
            "last_update_check": 0,
            "profiles": {
                "latvian_first": {
                    "name": "Latvian + International",
                    "description": "Latvian accents as #1, followed by common European accents",
                    "mappings": {
                        "a": ["ā", "á", "ä", "à", "â", "å", "ą", "ã", "æ"],
                        "c": ["č", "ç", "ć"],
                        "e": ["ē", "é", "è", "ê", "ë", "ė", "ę"],
                        "g": ["ģ", "ğ"],
                        "i": ["ī", "í", "ì", "î", "ï", "į"],
                        "k": ["ķ"],
                        "l": ["ļ", "ł"],
                        "n": ["ņ", "ñ", "ń"],
                        "o": ["ō", "ó", "ö", "ò", "ô", "õ", "ø", "œ"],
                        "r": ["ŗ", "ř"],
                        "s": ["š", "ś", "ş", "ß"],
                        "u": ["ū", "ú", "ü", "ù", "û", "ų", "ů"],
                        "z": ["ž", "ź", "ż"],
                        "d": ["ď", "đ", "ð"],
                        "t": ["ť", "ţ", "þ"],
                        "y": ["ý", "ÿ"],
                        "w": ["ŵ"],
                        "$": ["€", "£", "¥", "¢", "₹", "₽", "₩", "§"],
                        "0": ["°", "º", "⁰", "₀"],
                        "?": ["¿", "⽽"],
                        "!": ["¡"],
                        "-": ["–", "—", "−"],
                        "=": ["≠", "≈", "±", "≤", "≥"],
                        "/": ["÷", "\\"]
                    }
                },
                "latvian_only": {
                    "name": "Latvian Exclusive",
                    "description": "Pure Latvian diacritics only (ā, č, ē, ģ, ī, ķ, ļ, ņ, ō, ŗ, š, ū, ž)",
                    "mappings": {
                        "a": ["ā"],
                        "c": ["č"],
                        "e": ["ē"],
                        "g": ["ģ"],
                        "i": ["ī"],
                        "k": ["ķ"],
                        "l": ["ļ"],
                        "n": ["ņ"],
                        "o": ["ō"],
                        "r": ["ŗ"],
                        "s": ["š"],
                        "u": ["ū"],
                        "z": ["ž"]
                    }
                },
                "international": {
                    "name": "Western European",
                    "description": "French, German, Spanish, and standard European accents",
                    "mappings": {
                        "a": ["á", "à", "ä", "â", "å", "ā", "ą", "ã", "æ"],
                        "c": ["ç", "č", "ć"],
                        "e": ["é", "è", "ê", "ë", "ē", "ė", "ę"],
                        "i": ["í", "ì", "î", "ï", "ī", "į"],
                        "n": ["ñ", "ń", "ņ"],
                        "o": ["ó", "ò", "ö", "ô", "õ", "ō", "ø", "œ"],
                        "s": ["ß", "š", "ś", "ş"],
                        "u": ["ú", "ù", "ü", "û", "ū", "ų", "ů"],
                        "y": ["ý", "ÿ"],
                        "z": ["ž", "ź", "ż"],
                        "$": ["€", "£", "¥", "¢"]
                    }
                },
                "custom": {
                    "name": "Custom Profile",
                    "description": "User-defined character sets and symbols",
                    "mappings": {
                        "a": ["ā", "ä"],
                        "c": ["č"],
                        "e": ["ē"],
                        "g": ["ģ"],
                        "i": ["ī"],
                        "k": ["ķ"],
                        "l": ["ļ"],
                        "n": ["ņ"],
                        "o": ["ō", "ö"],
                        "s": ["š"],
                        "u": ["ū", "ü"],
                        "z": ["ž"]
                    }
                }
            }
        }

    def _load(self) -> dict:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    defaults = self._get_default_config()
                    # Ensure base keys exist
                    for k, v in defaults.items():
                        if k not in data:
                            data[k] = v
                    return data
            except Exception as e:
                print(f"[ConfigManager] Error reading config: {e}. Falling back to default.")
        cfg = self._get_default_config()
        self.save(cfg)
        return cfg

    def save(self, new_config: Optional[dict] = None) -> bool:
        if new_config is not None:
            self.config = new_config
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self._notify_listeners()
            return True
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")
            return False

    def add_listener(self, callback: Callable[[], None]):
        self._listeners.append(callback)

    def _notify_listeners(self):
        for cb in self._listeners:
            try:
                cb()
            except Exception as e:
                print(f"[ConfigManager] Listener error: {e}")

    @property
    def check_updates(self) -> bool:
        return self.config.get("check_updates", True)

    @check_updates.setter
    def check_updates(self, enabled: bool):
        self.config["check_updates"] = bool(enabled)
        self.save()

    @property
    def last_update_check(self) -> float:
        return float(self.config.get("last_update_check", 0) or 0)

    @last_update_check.setter
    def last_update_check(self, timestamp: float):
        self.config["last_update_check"] = timestamp
        self.save()

    @property
    def pause_in_fullscreen(self) -> bool:
        return self.config.get("pause_in_fullscreen", False)

    @pause_in_fullscreen.setter
    def pause_in_fullscreen(self, enabled: bool):
        self.config["pause_in_fullscreen"] = bool(enabled)
        self.save()

    @property
    def hold_delay_ms(self) -> int:
        return self.config.get("hold_delay_ms", 350)

    @hold_delay_ms.setter
    def hold_delay_ms(self, val: int):
        self.config["hold_delay_ms"] = max(150, min(1000, int(val)))
        self.save()

    @property
    def active_profile_name(self) -> str:
        return self.config.get("active_profile", "latvian_first")

    @active_profile_name.setter
    def active_profile_name(self, profile_key: str):
        if profile_key in self.config.get("profiles", {}):
            self.config["active_profile"] = profile_key
            self.save()

    def get_profiles(self) -> dict:
        return self.config.get("profiles", {})

    def get_mappings_for_key(self, base_key: str, is_upper: bool = False) -> List[str]:
        """
        Returns the list of accented characters for the given base character.
        If is_upper is True, converts lowercase characters to uppercase.
        """
        prof_key = self.active_profile_name
        profiles = self.get_profiles()
        profile = profiles.get(prof_key, profiles.get("latvian_first", {}))
        mappings = profile.get("mappings", {})
        
        lookup_key = base_key.lower()
        chars = mappings.get(lookup_key, [])
        if not chars:
            return []
            
        if is_upper and self.config.get("auto_capitalize", True):
            return [ch.upper() for ch in chars]
        return list(chars)

    def get_all_active_base_keys(self) -> List[str]:
        prof_key = self.active_profile_name
        profiles = self.get_profiles()
        profile = profiles.get(prof_key, {})
        mappings = profile.get("mappings", {})
        return list(mappings.keys())
