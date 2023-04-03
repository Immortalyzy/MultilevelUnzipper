"""
this script will be exported to the "install.exe" file,
it will automatically install the program and add right-click menus
"""

import os
import shutil
import json
import tkinter as tk
from tkinter import ttk
import winreg
from setting import settings as example_settings
from setting import setting_file_name


# this version I needs click "show more options" to see the option
# def add_context_menu_option(option_name, exe_path, reg_class):
#     """
#     Add a context menu option for the given executable.
#
#     Args:
#     option_name (str): The name of the context menu option.
#     exe_path (str): The path to the executable file.
#     reg_class (str): The registry class for the context menu option.
#     """
#     try:
#         registry_path = fr"Software\\Classes\\{reg_class}\\ShellEx\\{option_name}"
#         command = f'"{exe_path}" "%V"'
#         with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
#             winreg.SetValue(key, "", winreg.REG_SZ, option_name)
#
#         registry_path_command = fr"{registry_path}\\command"
#         with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path_command) as key:
#             winreg.SetValue(key, "", winreg.REG_SZ, command)
#     except Exception as e:
#         print(f"Failed to add context menu option '{option_name}': {e}")


def add_context_menu_option(option_name, exe_path, reg_class):
    """
    Add a context menu option for the given executable.

    Args:
    option_name (str): The name of the context menu option.
    exe_path (str): The path to the executable file.
    reg_class (str): The registry class for the context menu option.
    """
    try:
        registry_path = fr"Software\\Classes\\{reg_class}\\shell\\{option_name}"
        command = f'"{exe_path}" "%V"'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, option_name)
            winreg.SetValue(key, "Extended", winreg.REG_SZ, "")

        registry_path_command = fr"{registry_path}\command"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path_command) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, command)
    except Exception as e:
        print(f"Failed to add context menu option '{option_name}': {e}")


def save_settings(settings):
    """
    Save settings as a JSON file in the user's home directory.

    Args:
    settings (dict): The settings to save.
    """
    user_home = os.path.expanduser("~")
    settings_file = os.path.join(user_home, setting_file_name)
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=4)


def on_install_click(collected_settings_vars):
    """
    Install the script and save the settings.

    Args:
    collected_settings_vars (dict): A dictionary containing the Tkinter variable objects for each setting.
    """
    settings = {k: v.get() for k, v in collected_settings_vars.items()}
    save_settings(settings)

    appdata_path = os.getenv("APPDATA")
    destination_folder = os.path.join(appdata_path, "MultilevelUnzipper")
    os.makedirs(destination_folder, exist_ok=True)
    shutil.copy("./MultilevelUnzipper.exe", destination_folder)

    try:
        # ... Rest of the on_install_click function ...

        # Add context menu options
        exe_path = os.path.join(destination_folder, "MultilevelUnzipper.exe")
        add_context_menu_option(
            "Unzip all files under this directory", exe_path, "Directory\\Background"
        )
        add_context_menu_option("Unzip this file", exe_path, "AllFileSystemObjects")

        # ... Rest of the on_install_click function ...
    except Exception as e:
        print(f"Installation failed: {e}")


def create_setting_component(parent, row, setting_key, setting_value):
    """
    Create a setting component based on the setting data type.

    Args:
    parent (Tkinter object): The parent Tkinter object for the component.
    row (int): The row number in the grid where the component will be placed.
    setting_key (str): The name of the setting.
    setting_value (str, int, bool): The default value of the setting.

    Returns:
    Tkinter variable object: The variable object associated with the created component.
    """
    ttk.Label(parent, text=f"{setting_key}:").grid(column=1, row=row, sticky=tk.E)
    setting_var = None

    if isinstance(setting_value, str):
        setting_var = tk.StringVar(value=setting_value)
        ttk.Entry(parent, width=40, textvariable=setting_var).grid(column=2, row=row, sticky=tk.W)
    elif isinstance(setting_value, bool):
        setting_var = tk.BooleanVar(value=setting_value)
        ttk.Checkbutton(parent, variable=setting_var).grid(column=2, row=row, sticky=tk.W)
    elif isinstance(setting_value, int):
        setting_var = tk.IntVar(value=setting_value)
        ttk.Entry(parent, width=15, textvariable=setting_var).grid(column=2, row=row, sticky=tk.W)

    return setting_var


def main():
    """
    The main function that creates and displays the installer GUI.
    """
    root = tk.Tk()
    root.title("My Script Installer")
    root.geometry("400x300")
    root.resizable(False, False)

    mainframe = ttk.Frame(root, padding="20 20 20 20")
    mainframe.grid(column=0, row=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    collected_settings_vars = {}
    for index, (setting_key, setting_value) in enumerate(example_settings.items()):
        collected_settings_vars[setting_key] = create_setting_component(
            mainframe, index + 1, setting_key, setting_value
        )

    # Customize the install button
    install_button_style = ttk.Style()
    install_button_style.configure("TButton", font=("Helvetica", 12, "bold"))
    install_button = ttk.Button(
        mainframe,
        text="Install",
        style="TButton",
        width=20,
        command=lambda: on_install_click(collected_settings_vars),
    )
    install_button.grid(
        column=1, row=len(example_settings) + 1, columnspan=2, pady=(20, 0), sticky=tk.EW
    )

    # Add padding between components for a cleaner look
    install_button = ttk.Button(
        mainframe, text="Install", command=lambda: on_install_click(collected_settings_vars)
    )

    root.mainloop()


if __name__ == "__main__":
    main()
