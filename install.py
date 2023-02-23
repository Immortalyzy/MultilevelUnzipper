"""
this script will be exported to the "install.exe" file,
it will automatically install the program and add right-click menus
"""

import os
import winreg


def add_right_click_menu_option(menu_name, command, key_name):
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_CLASSES_ROOT)
        shell_key = winreg.CreateKey(reg, "*\\shell\\" + menu_name)
        winreg.SetValue(shell_key, "", winreg.REG_SZ, menu_name)
        command_key = winreg.CreateKey(shell_key, "command")
        winreg.SetValue(command_key, "", winreg.REG_SZ, command)
        winreg.CloseKey(command_key)
        winreg.CloseKey(shell_key)
        winreg.CloseKey(reg)
        print(f"Successfully added {menu_name} option to right-click menu for {key_name}.")
    except WindowsError as e:
        print(f"Failed to add {menu_name} option to right-click menu for {key_name}: {e}")


# add "Run on this file" option to right-click menu for files
add_right_click_menu_option(
    "Run on this file", '"C:\path\to\your_python_program.exe" "%1"', "files"
)

# add "Run on current directory" option to right-click menu for directories
add_right_click_menu_option(
    "Run on current directory", '"C:\path\to\your_python_program.exe" "%V"', "directories"
)


def main():
    """ main function """
    # get user's home directory
    home_dir = os.path.expanduser("~")

    # create the program directory under ~/AppData/Local/Programs
    program_dir = os.path.join(home_dir, "AppData", "Local", "Programs", "MultiLevelUnzipper")
    os.makedirs(program_dir)

    # check if the program exists in the current directory
    if not os.path.exists("MultiLevelUnzipper.exe"):
        print("MultiLevelUnzipper.exe not found!")
        input("Press enter to exit...")
        return

    # copy the program to the program directory
    os.system(f"copy MultiLevelUnzipper.exe {program_dir}")

    # generate new program path
    program_path = os.path.join(program_dir, "MultiLevelUnzipper.exe")

    # add registry keys
    # add "Multi-level unzip this file"

    # add "Multi-level unzip all files under this folder"

    # add "Multi-level unzip all files under current folder"

    # add "Multi-level unzip selected files"

    # wait for user to press enter
    input("Press enter to exit...")


if __name__ == "__main__":
    main()
