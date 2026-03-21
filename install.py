"""
This script will be exported to install.exe.
It will automatically install the program and add right-click menus.
"""

import ctypes
import json
import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import winreg

from setting import DEFAULT_SETTINGS, select_zip_executable_path, setting_file_name

PAYLOAD_FOLDER_NAME = "MultilevelUnzipper"
CONTEXT_MENU_ENTRIES = (
    ("Unzip all files under this directory", "Directory\\Background"),
    ("Unzip this file", "AllFileSystemObjects"),
)

INTEGER_FIELDS = {
    "log_level": "Log level",
    "maximum_lv": "Maximum unzip depth",
}

PATH_FIELDS = {
    "zip_executable_path_7z": "7-Zip executable",
    "zip_executable_path_bandizip": "Bandizip executable",
}

BOOLEAN_FIELDS = {
    "use_bandizip",
    "autodelete",
    "autodeleteexisting",
    "automoveup",
    "unzipsubfolder",
    "log_to_file",
}


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def add_context_menu_option(option_name, exe_path, reg_class):
    """
    Add a context menu option for the given executable.

    Args:
    option_name (str): The name of the context menu option.
    exe_path (str): The path to the executable file.
    reg_class (str): The registry class for the context menu option.
    """
    try:
        registry_path = rf"Software\\Classes\\{reg_class}\\shell\\{option_name}"
        command = f'"{exe_path}" "%V"'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, option_name)
            winreg.SetValue(key, "Extended", winreg.REG_SZ, "")

        registry_path_command = rf"{registry_path}\command"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path_command) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, command)
    except Exception as e:
        print(f"Failed to add context menu option '{option_name}': {e}")


def get_settings_output_path():
    default_path = os.path.join(os.path.expanduser("~"), setting_file_name)
    return os.environ.get("MULTILEVEL_UNZIPPER_SETTINGS_FILE", default_path)


def save_settings(settings):
    """
    Save settings as a JSON file in the user's home directory.

    Args:
    settings (dict): The settings to save.
    """
    settings_file = get_settings_output_path()
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)
    return settings_file


def normalize_install_settings(raw_settings):
    """Coerce collected UI values into the persisted settings schema."""
    normalized = dict(DEFAULT_SETTINGS)
    normalized.update(raw_settings)

    for key, value in list(normalized.items()):
        if key in BOOLEAN_FIELDS:
            if isinstance(value, str):
                normalized[key] = value.strip().lower() in {"1", "true", "yes", "on"}
            else:
                normalized[key] = bool(value)
            continue

        if key in INTEGER_FIELDS:
            try:
                normalized[key] = int(str(value).strip())
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{INTEGER_FIELDS[key]} must be a whole number.") from exc
            continue

        if isinstance(value, str):
            normalized[key] = value.strip()

    return normalized


def validate_install_settings(raw_settings):
    """Validate backend paths and core numeric settings before installation."""
    settings = normalize_install_settings(raw_settings)

    if settings["maximum_lv"] < 0:
        raise ValueError("Maximum unzip depth must be 0 or greater.")
    if settings["log_level"] < 0:
        raise ValueError("Log level must be 0 or greater.")

    preferred_key = (
        "zip_executable_path_bandizip"
        if settings["use_bandizip"]
        else "zip_executable_path_7z"
    )
    alternate_key = (
        "zip_executable_path_7z"
        if settings["use_bandizip"]
        else "zip_executable_path_bandizip"
    )
    preferred_label = "Bandizip" if settings["use_bandizip"] else "7-Zip"
    alternate_label = "7-Zip" if settings["use_bandizip"] else "Bandizip"

    errors = []
    warnings = []

    preferred_path = settings.get(preferred_key, "")
    if not preferred_path:
        errors.append(
            f"{preferred_label} is selected as the preferred backend, so its executable path is required."
        )
    elif not os.path.isfile(preferred_path):
        errors.append(
            f"{preferred_label} executable was not found:\n{preferred_path}\n\n"
            f"Choose a valid {preferred_label} executable or switch the preferred backend."
        )

    alternate_path = settings.get(alternate_key, "")
    if alternate_path:
        if not os.path.isfile(alternate_path):
            errors.append(
                f"{alternate_label} executable was not found:\n{alternate_path}\n\n"
                f"Choose a valid {alternate_label} executable or clear the field to install without fallback."
            )
    else:
        warnings.append(
            f"{alternate_label} is not configured. Extraction fallback will stay disabled until you add its executable path."
        )

    if errors:
        raise ValueError("\n\n".join(errors))

    return settings, warnings


def get_runtime_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_payload_source_folder():
    """
    Resolve payload folder location.

    Priority:
    1. Side-by-side folder next to install.exe/script (new release layout)
    2. Frozen bundle payload under _MEIPASS (legacy fallback)
    """
    checked_locations = []

    side_by_side = os.path.join(get_runtime_root(), PAYLOAD_FOLDER_NAME)
    checked_locations.append(side_by_side)
    if os.path.isdir(side_by_side):
        return side_by_side, checked_locations

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled_payload = os.path.join(sys._MEIPASS, PAYLOAD_FOLDER_NAME)
        checked_locations.append(bundled_payload)
        if os.path.isdir(bundled_payload):
            return bundled_payload, checked_locations

    return None, checked_locations


def copy_payload(source_folder, destination_folder):
    os.makedirs(destination_folder, exist_ok=True)
    for item in os.listdir(source_folder):
        src_item_path = os.path.join(source_folder, item)
        dst_item_path = os.path.join(destination_folder, item)

        if os.path.isfile(src_item_path):
            shutil.copy(src_item_path, dst_item_path)
        elif os.path.isdir(src_item_path):
            if os.path.exists(dst_item_path):
                shutil.rmtree(dst_item_path)
            shutil.copytree(src_item_path, dst_item_path)


def register_context_menu_entries(exe_path):
    for option_name, reg_class in CONTEXT_MENU_ENTRIES:
        add_context_menu_option(option_name, exe_path, reg_class)


def install_application(raw_settings):
    settings, warnings = validate_install_settings(raw_settings)
    select_zip_executable_path(settings)
    settings_path = save_settings(settings)

    appdata_path = os.getenv("APPDATA")
    if not appdata_path:
        raise RuntimeError("Environment variable APPDATA is not set.")

    destination_folder = os.path.join(appdata_path, PAYLOAD_FOLDER_NAME)
    src_folder, checked_locations = get_payload_source_folder()
    if not src_folder:
        checked_locations_text = "\n".join(checked_locations)
        raise FileNotFoundError(
            "Could not find the installer payload folder 'MultilevelUnzipper'.\n\n"
            "Please unzip the full release package and run install.exe from that folder.\n\n"
            f"Checked locations:\n{checked_locations_text}"
        )

    copy_payload(src_folder, destination_folder)

    exe_path = os.path.join(destination_folder, "MultilevelUnzipper.exe")
    register_context_menu_entries(exe_path)
    return {
        "destination_folder": destination_folder,
        "exe_path": exe_path,
        "settings_path": settings_path,
        "warnings": warnings,
        "settings": settings,
    }


class InstallerApp:
    """Grouped Tkinter installer interface for the packaged release."""

    def __init__(self, root):
        self.root = root
        self.root.title("MultilevelUnzipper Installer")
        self.root.geometry("820x620")
        self.root.minsize(760, 560)

        self.status_var = tk.StringVar(
            value=(
                "Configure your preferred extractor and installation settings. "
                "If only one backend path is valid, installation still works but fallback stays disabled."
            )
        )
        self.setting_vars = self._build_setting_vars()
        self._build_layout()

    def _build_setting_vars(self):
        vars_by_key = {}
        for key, value in DEFAULT_SETTINGS.items():
            if key == "zip_executable_path":
                continue
            if key in BOOLEAN_FIELDS:
                vars_by_key[key] = tk.BooleanVar(value=bool(value))
            else:
                vars_by_key[key] = tk.StringVar(value=str(value))
        return vars_by_key

    def _build_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container = ttk.Frame(self.root, padding="18 18 18 18")
        container.grid(column=0, row=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        ttk.Label(
            container,
            text="MultilevelUnzipper Setup",
            font=("Segoe UI", 16, "bold"),
        ).grid(column=0, row=0, sticky="w")
        ttk.Label(
            container,
            text=(
                "Install the release payload, save compatible settings, and register the "
                "Windows context-menu entries in one step."
            ),
            wraplength=760,
        ).grid(column=0, row=1, sticky="w", pady=(6, 14))

        content = ttk.Frame(container)
        content.grid(column=0, row=2, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        self._build_backend_section(content).grid(
            column=0, row=0, sticky="nsew", padx=(0, 10), pady=(0, 10)
        )
        self._build_paths_section(content).grid(
            column=1, row=0, sticky="nsew", pady=(0, 10)
        )
        self._build_core_settings_section(content).grid(
            column=0, row=1, columnspan=2, sticky="nsew", pady=(0, 10)
        )
        self._build_actions_section(container).grid(column=0, row=3, sticky="ew")

    def _build_backend_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Backend Preference", padding=12)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=(
                "Choose the backend to try first. When both executables are configured, "
                "the app automatically retries the alternate backend before giving up."
            ),
            wraplength=320,
        ).grid(column=0, row=0, sticky="w")

        ttk.Radiobutton(
            frame,
            text="Prefer Bandizip first",
            variable=self.setting_vars["use_bandizip"],
            value=True,
        ).grid(column=0, row=1, sticky="w", pady=(10, 4))
        ttk.Radiobutton(
            frame,
            text="Prefer 7-Zip first",
            variable=self.setting_vars["use_bandizip"],
            value=False,
        ).grid(column=0, row=2, sticky="w")

        return frame

    def _build_paths_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Executable Paths", padding=12)
        frame.columnconfigure(1, weight=1)

        path_rows = (
            ("zip_executable_path_7z", "7-Zip executable"),
            ("zip_executable_path_bandizip", "Bandizip executable"),
        )
        for row, (key, label) in enumerate(path_rows):
            ttk.Label(frame, text=label).grid(column=0, row=row, sticky="w", pady=4)
            ttk.Entry(
                frame,
                textvariable=self.setting_vars[key],
                width=48,
            ).grid(column=1, row=row, sticky="ew", padx=8, pady=4)
            ttk.Button(
                frame,
                text="Browse",
                command=lambda setting_key=key: self._browse_for_executable(setting_key),
            ).grid(column=2, row=row, sticky="e", pady=4)

        ttk.Label(
            frame,
            text=(
                "Leave the alternate backend empty if you only want one extractor. "
                "Invalid non-empty paths block installation."
            ),
            wraplength=320,
        ).grid(column=0, row=2, columnspan=3, sticky="w", pady=(10, 0))

        return frame

    def _build_core_settings_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Core Settings", padding=12)
        for column in range(4):
            frame.columnconfigure(column, weight=1 if column in {1, 3} else 0)

        checkboxes = (
            ("autodelete", "Delete source archives after successful extraction"),
            ("autodeleteexisting", "Replace existing extraction folders"),
            ("automoveup", "Move single nested folders upward automatically"),
            ("unzipsubfolder", "Scan subfolders recursively"),
            ("log_to_file", "Write logs to a file"),
        )
        for row, (key, label) in enumerate(checkboxes):
            ttk.Checkbutton(
                frame,
                text=label,
                variable=self.setting_vars[key],
            ).grid(column=0, row=row, columnspan=2, sticky="w", pady=2)

        entry_fields = (
            ("maximum_lv", "Maximum unzip depth"),
            ("pass_in_file_separator", "Password separator"),
            ("log_level", "Log level"),
            ("log_file_name", "Log file name"),
        )
        for row, (key, label) in enumerate(entry_fields):
            column = 2 if row < 2 else 0
            target_row = row if row < 2 else row - 2 + len(checkboxes)
            entry_column = column + 1
            ttk.Label(frame, text=label).grid(column=column, row=target_row, sticky="w", padx=(20 if column else 0, 8), pady=4)
            ttk.Entry(
                frame,
                textvariable=self.setting_vars[key],
                width=18 if key != "log_file_name" else 28,
            ).grid(column=entry_column, row=target_row, sticky="ew", pady=4)

        return frame

    def _build_actions_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Installation Actions", padding=12)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            textvariable=self.status_var,
            wraplength=720,
        ).grid(column=0, row=0, sticky="w")

        button_bar = ttk.Frame(frame)
        button_bar.grid(column=0, row=1, sticky="e", pady=(12, 0))

        ttk.Button(
            button_bar,
            text="Validate",
            command=self.on_validate_click,
        ).grid(column=0, row=0, padx=(0, 8))
        ttk.Button(
            button_bar,
            text="Install",
            command=self.on_install_click,
        ).grid(column=1, row=0)
        return frame

    def _browse_for_executable(self, setting_key):
        selected = filedialog.askopenfilename(
            title=f"Select {PATH_FIELDS.get(setting_key, 'executable')}",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")],
        )
        if selected:
            self.setting_vars[setting_key].set(selected)

    def collect_settings(self):
        return {key: variable.get() for key, variable in self.setting_vars.items()}

    def on_validate_click(self):
        try:
            settings, warnings = validate_install_settings(self.collect_settings())
        except ValueError as exc:
            self.status_var.set(str(exc))
            messagebox.showerror("Invalid Configuration", str(exc))
            return

        message_lines = [
            "Configuration is valid.",
            "",
            f"Preferred backend: {'Bandizip' if settings['use_bandizip'] else '7-Zip'}",
        ]
        if warnings:
            message_lines.append("")
            message_lines.append("Notes:")
            for warning in warnings:
                message_lines.append(f"- {warning}")
            self.status_var.set(warnings[0])
        else:
            self.status_var.set(
                "Configuration looks good. Installation will copy the payload, save settings, and register the context-menu entries."
            )

        messagebox.showinfo("Configuration Ready", "\n".join(message_lines))

    def on_install_click(self):
        try:
            result = install_application(self.collect_settings())
        except ValueError as exc:
            self.status_var.set(str(exc))
            messagebox.showerror("Invalid Configuration", str(exc))
            return
        except FileNotFoundError as exc:
            self.status_var.set(str(exc))
            messagebox.showerror("Installation Failed", str(exc))
            return
        except Exception as exc:
            self.status_var.set(str(exc))
            messagebox.showerror(
                "Installation Failed",
                f"An unexpected error occurred:\n{exc}",
            )
            return

        success_lines = [
            "MultilevelUnzipper has been installed successfully.",
            "",
            f"Payload copied to: {result['destination_folder']}",
            f"Settings saved to: {result['settings_path']}",
            f"Context-menu target: {result['exe_path']}",
            "",
            "Registered entries:",
        ]
        for option_name, reg_class in CONTEXT_MENU_ENTRIES:
            success_lines.append(f"- {option_name}")

        if result["warnings"]:
            success_lines.append("")
            success_lines.append("Notes:")
            for warning in result["warnings"]:
                success_lines.append(f"- {warning}")
            self.status_var.set(result["warnings"][0])
        else:
            self.status_var.set(
                "Installation complete. Payload copied, settings saved, and context-menu entries registered."
            )

        messagebox.showinfo("Installation Complete", "\n".join(success_lines))


def main():
    """
    The main function that creates and displays the installer GUI.
    """
    root = tk.Tk()
    ttk.Style(root).theme_use("vista")
    InstallerApp(root)
    root.mainloop()


if __name__ == "__main__":
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, sys.argv[0], None, 1
        )
        sys.exit(0)
    else:
        print("Running with administrator privileges")

    main()
