"""Settings and global variables for MultilevelUnzipper."""

import json
import os
import shutil

# The settings .json file will be stored in the users home directory unless overridden.
setting_file_name = ".MultiLevelUnzipperSettings.json"

DEFAULT_SETTINGS = {
    "log_to_file": False,
    "log_file_name": "unzipper_log.txt",
    "zip_executable_path": "C:\\Program Files\\Bandizip\\bz.exe",
    "zip_executable_path_7z": "C:\\Program Files\\7-Zip\\7z.exe",
    "zip_executable_path_bandizip": "C:\\Program Files\\Bandizip\\bz.exe",
    "use_bandizip": True,
    "autodelete": True,
    "autodeleteexisting": False,
    "automoveup": True,
    "unzipsubfolder": True,
    "log_level": 3,
    "pass_in_file_separator": "_",
    "maximum_lv": 7,
}


LEGACY_KEY_MAP = {
    "zip_excutible_path": "zip_executable_path",
    "zip_excutible_path_7z": "zip_executable_path_7z",
    "zip_excutible_path_bandizip": "zip_executable_path_bandizip",
    "pass_in_file_seperator": "pass_in_file_separator",
}


def _migrate_legacy_keys(settings_local):
    """Migrate legacy keys to standardized names and drop the old keys."""
    migrated = dict(settings_local)
    for old_key, new_key in LEGACY_KEY_MAP.items():
        if old_key in migrated and new_key not in migrated:
            migrated[new_key] = migrated[old_key]
        if old_key in migrated:
            migrated.pop(old_key)
    return migrated


def _ensure_executable_paths(settings):
    """Fill in missing or invalid executable paths when possible."""
    if not os.path.exists(settings.get("zip_executable_path_7z", "")):
        found_7z = find7z()
        if found_7z:
            settings["zip_executable_path_7z"] = found_7z
    if not os.path.exists(settings.get("zip_executable_path_bandizip", "")):
        found_bz = find_bandizip()
        if found_bz:
            settings["zip_executable_path_bandizip"] = found_bz
    return settings


def select_zip_executable_path(settings):
    """Select the active executable path based on config and availability."""
    use_bandizip = settings.get("use_bandizip", False)
    bandizip_path = settings.get("zip_executable_path_bandizip", "")
    seven_zip_path = settings.get("zip_executable_path_7z", "")

    if use_bandizip and os.path.exists(bandizip_path):
        settings["zip_executable_path"] = bandizip_path
        return settings

    if os.path.exists(seven_zip_path):
        settings["zip_executable_path"] = seven_zip_path
        settings["use_bandizip"] = False
        return settings

    if os.path.exists(bandizip_path):
        settings["zip_executable_path"] = bandizip_path
        settings["use_bandizip"] = True
        return settings

    # Leave as-is if nothing is found; caller can handle the error.
    settings.setdefault("zip_executable_path", "")
    return settings


class Config:
    """Config Singleton class."""

    _instance = None

    @staticmethod
    def get_instance():
        """Get the instance of the singleton class"""
        if Config._instance is None:
            Config()
        return Config._instance

    def __init__(self):
        if Config._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            Config._instance = self
            self.settings = self.load_config()

    def load_config(self, settings_file=setting_file_name):
        """Load config from local file; if missing, create one."""
        # Generate the setting file path (with optional override).
        home = os.path.expanduser("~")
        settings_file = os.path.join(home, setting_file_name)
        settings_file = os.environ.get("MULTILEVEL_UNZIPPER_SETTINGS_FILE", settings_file)
        read_only = os.environ.get("MULTILEVEL_UNZIPPER_READONLY_SETTINGS") == "1"

        # If the file doesn't exist, create it and write default settings.
        if not os.path.exists(settings_file):
            temp_settings = dict(DEFAULT_SETTINGS)
            _ensure_executable_paths(temp_settings)
            select_zip_executable_path(temp_settings)
            if not read_only:
                with open(settings_file, "w", encoding="utf-8") as f:
                    json.dump(temp_settings, f, indent=4)
            return temp_settings

        # If the file exists, read and merge settings.
        with open(settings_file, "r", encoding="utf-8") as f:
            settings_local = json.load(f)

        settings_local = _migrate_legacy_keys(settings_local)
        temp_settings = {**DEFAULT_SETTINGS, **settings_local}

        _ensure_executable_paths(temp_settings)
        select_zip_executable_path(temp_settings)

        # Write back if there were changes or new defaults added.
        if not read_only and temp_settings != settings_local:
            added = set(temp_settings.keys()) - set(settings_local.keys())
            if added:
                print("new settings added: " + str(sorted(added)))
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(temp_settings, f, indent=4)

        return temp_settings


def find7z():
    """Find 7z.exe, return the path if found, otherwise return None."""
    path = shutil.which("7z.exe")
    if path is None:
        # check if 7z.exe is in the default installation directory
        if os.path.exists("C:\\Program Files\\7-Zip\\7z.exe"):
            path = "C:\\Program Files\\7-Zip\\7z.exe"
            return path
        elif os.path.exists("C:\\Program Files (x86)\\7-Zip\\7z.exe"):
            path = "C:\\Program Files (x86)\\7-Zip\\7z.exe"
            return path
        else:
            print("7z.exe not found, please specify the path to 7z.exe")
            return None
    return path


def find_bandizip():
    """Find the Bandizip executable, return the path if found, otherwise return None."""
    bandizip_names = ["bz.exe"]
    # Try to find in PATH
    for exe_name in bandizip_names:
        path = shutil.which(exe_name)
        if path:
            return path
    # Check default installation directories
    default_dirs = [
        "C:\\Program Files\\Bandizip\\bz.exe",
        "C:\\Program Files (x86)\\Bandizip\\bz.exe",
    ]
    for path in default_dirs:
        if os.path.exists(path):
            return path
    print("Bandizip executable not found, please specify the path to Bandizip.")
    return None


def dict_compare(d1, d2):
    """Compare two dictionaries; kept for backward compatibility."""
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    shared_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in shared_keys if d1[o] != d2[o]}
    same = set(o for o in shared_keys if d1[o] == d2[o])
    return added, removed, modified, same
