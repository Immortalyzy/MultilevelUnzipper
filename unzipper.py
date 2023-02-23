""" MultiLevelUnzipper - unzip multiple levels of zip files at once """
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
import argparse
from pathlib import Path

# for simplicity, use global variables to store write to file settings
settings = {
    "write_to_file": False,
    "log_file_name": "unzipper_log.txt",
    "zip_excutible_path": "C:\\Program Files\\7-Zip\\7z.exe",
    "autodelete": False,
    "autodeleteexisting": False,
    "automoveup": False,
}

# the settings .json file will be stored in the users home directory
setting_file_name = ".MultiLevelUnzipperSettings.json"


# log function, its settings are controlled by global variables
def log_msg(message):
    """ log the message to the console and optionally to a file, automatically add time stamp """
    time_message = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "-" + message
    if settings["write_to_file"]:
        with open(settings["log_file_name"], "a") as f:
            f.write(time_message + "\n")
    else:
        print(time_message)


# find the 7z.exe
def find7z():
    """ find the 7z.exe, return the path if found, otherwise return None """
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
            log_msg("7z.exe not found, please specify the path to 7z.exe")
            return None
    return path


def read_settings():
    """Reads the settings file and returns a list of the lines"""
    global settings  # global is required only if you want to modify the global variable, super confusing (the word confusing is completed by Copilot)

    # generate the setting file path
    home = os.path.expanduser("~")
    settings_file = os.path.join(home, setting_file_name)
    is_valid_setting = True

    # if the file doesn't exist, create it and write the default settings
    if not os.path.exists(settings_file):
        # try to find the 7z.exe here
        zip_path = find7z()
        if zip_path is not None:
            settings["zip_excutible_path"] = zip_path
        else:
            log_msg(
                "7z.exe not found, please manually specify the path to 7z.exe in "
                + settings_file
                + ", remember to use double backslashes (\\\\) to escape the backslashes"
            )
            is_valid_setting = False

        with open(settings_file, "w") as f:
            json.dump(settings, f)

    # if the file exists, read the settings
    with open(settings_file, "r") as f:
        settings = json.load(f)

        # check if the 7z.exe path is valid
        if not os.path.exists(settings["zip_excutible_path"]):
            log_msg(
                "7z.exe not found, please check the path to 7z.exe in "
                + settings_file
                + ", remember to use DOUBLE backslashes (\\\\) to escape the backslashes"
            )
            is_valid_setting = False

    # if the settings are not valid, return false, the program should not continue
    return is_valid_setting


# get password list
def getPasswordList(dir):
    """ get the password list from the passwords.txt file (under current directory and under users home directory), return a list of passwords """
    passwordList = [""]
    # check if the password file exists
    if not os.path.exists(os.path.join(dir, "passwords.txt")):
        log_msg("passwords.txt not found")
        return passwordList
    with open(os.path.join(dir, "passwords.txt"), "r") as f:
        for line in f:
            passwordList.append(line.strip())

    # TODO: add global password, if the global password is not empty, add it to the list
    # global password is stored in ~/.passwords.txt
    return passwordList


# unzip a file
def unzipFileWith7z(
    file, z7path, passwords, autodelete=False, autodeleteexisting=False, lv=0, maximum_lv=2
):
    """ principle function, unzip a file with 7z.exe, return True if success, otherwise return False """
    has_archive = False
    password_protected = False

    # check if the file exists
    if not os.path.exists(file):
        log_msg(f"File {file} does not exist")
        return

    # check if is a .lib, .dll or .exe file, if yes skip
    # TODO: maybe a temporary solution, need to find a way to unzip .lib files
    if file.endswith(".lib") or file.endswith(".dll") or file.endswith(".exe"):
        log_msg(f"File {file} is a .lib, .dll or .exe file, skipping...")
        return

    # check if the output directory already exists
    if os.path.exists(f"{file}lv{lv:d}"):
        if autodeleteexisting:
            log_msg(f"Output directory {file}lv{lv:d} already exists, deleting...")
            shutil.rmtree(f"{file}lv{lv:d}")
        else:
            log_msg(f"Output directory {file}lv{lv:d} already exists, skipping...")
            return

    # unzip without password
    # verify file is a a os.PathLike
    right_pass_found = False
    if not isinstance(file, os.PathLike) and not isinstance(file, str):
        raise TypeError(f"{file} must be a os.PathLike")

    log_msg(f"Unzipping {file} without password...")

    result = subprocess.run(
        [z7path, "x", "-p", file, f"-o{file}lv{lv:d}"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if (
        result.returncode == 2
        and result.stderr.decode("utf-8", errors="replace").find("Wrong password") != -1
    ):
        log_msg(f"Archive {file} is password protected, start to unzip with passwords...")
        shutil.rmtree(f"{file}lv{lv:d}", ignore_errors=True)
        has_archive = True
        password_protected = True
    if (
        result.returncode == 2
        and result.stderr.decode("utf-8", errors="replace").find("Cannot open the file as archive")
        != -1
    ):
        if lv == 0:
            log_msg(f'File "{file}" is not an archive')
        # remove the empty directory due to file is not an archive
        shutil.rmtree(f"{file}lv{lv:d}", ignore_errors=True)
        return False
    if result.returncode == 0:
        log_msg(f"Archive {file} is not password protected, unzipped to {file}lv{lv:d}")
        right_pass_found = True
        has_archive = True
    elif password_protected is False:
        log_msg(f"Unknown error when unzipping {file}")
        log_msg(result.stderr.decode("utf-8", errors="replace"))
        return False

    # unzip with password
    if password_protected:
        for password in passwords:
            result = subprocess.run(
                [z7path, "x", f"-p{password}", file, f"-o{file}lv{lv:d}"],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                check=False,
            )
            if (
                result.returncode == 2
                and result.stderr.decode("utf-8", errors="replace").find("Wrong password") != -1
            ):
                # remove empty files created due to wrong password
                shutil.rmtree(f"{file}lv{lv:d}", ignore_errors=True)
            else:
                log_msg(f"Correct password for {file} is {password}, unzipped to {file}lv{lv:d}")
                has_archive = True
                right_pass_found = True
                break

    # no password found for the file
    if not right_pass_found:
        log_msg(f"Cannot find the correct password for {file}")
        return False

    if has_archive:
        files = os.listdir(f"{file}lv{lv:d}")

        # check if the file just unzipped is a normal file
        is_normal_dll = 0
        if ".rdata" in files:
            is_normal_dll += 1
        if ".text" in files:
            is_normal_dll += 1
        if ".data" in files:
            is_normal_dll += 1
        if ".idata" in files:
            is_normal_dll += 1
        if is_normal_dll >= 2:
            log_msg(f"File {file} is a normal file, skipping...")
            shutil.rmtree(path=f"{file}lv{lv:d}", ignore_errors=True)
            return False, lv
        else:
            log_msg(
                f"File {file} is an archive, if auto delete is enabled, will delete the file after unzipping"
            )
            if autodelete:
                os.remove(file)

        # check if last level is reached
        # criteria 1 : files just extracted contains at the same time .dll and .exe files (it is a program)
        contains_dll = False
        contains_exe = False
        for root, dirs, files in os.walk(f"{file}lv{lv:d}"):
            for file_ in files:
                if file_.endswith(".dll"):
                    contains_dll = True
                if file_.endswith(".exe"):
                    contains_exe = True
        if contains_dll and contains_exe:
            log_msg(f"File {file} is a program, will not go to next level")
            return False, lv

        # criteria 2 : files just extracted contains at the same time .exe files and folders (it is a program without .dll files)
        contains_folder = False
        if any(
            os.path.isdir(os.path.join(f"{file}lv{lv:d}", item))
            for item in os.listdir(f"{file}lv{lv:d}")
        ):
            contains_folder = True

        if contains_exe and contains_folder:
            log_msg(f"File {file} is a program, will not go to next level")
            return False, lv

        # other files without .dll or .exe files will automatically stop at the next level

        log_msg(f"Archive {file} has been unzipped to {file}lv{lv:d}, going to next level")
        lv += 1
        # recursively unzip the files in the directory just created
        for root, dirs, files in os.walk(f"{file}lv{lv-1:d}"):
            for file in files:
                unzipFileWith7z(
                    os.path.join(root, file), z7path, passwords, autodelete, autodeleteexisting, lv
                )
        return True, lv
    return False, lv


def move_files_up(dir_path):
    """ remove all redundant directories and move all files up to the first level """
    contents = os.listdir(dir_path)

    if len(contents) == 1 and os.path.isdir(os.path.join(dir_path, contents[0])):
        subdir_path = os.path.join(dir_path, contents[0])
        if os.path.isdir(subdir_path):
            subdir_contents = os.listdir(subdir_path)
            for item in subdir_contents:
                shutil.move(os.path.join(subdir_path, item), dir_path)
            os.rmdir(subdir_path)
            move_files_up(dir_path)


################### MAIN FUNCTION ################################################################
def main(target):
    """ main function, can take both a file or a directory as argument """

    # get the password list
    passwords = getPasswordList(target)

    # load settings
    valid_ = read_settings()
    if not valid_:
        print("Settings file is not valid, please check the settings file")
        input("Press any key to exit...")
        return
    else:
        print("Settings file is valid")
        # print the settings
        print("Settings:")
        for key, value in settings.items():
            print(f"\t{key} : {value}")

    # if target is a directory
    if os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            for file in files:
                unzipFileWith7z(
                    os.path.join(root, file),
                    settings["zip_excutible_path"],
                    passwords=passwords,
                    autodelete=settings["autodelete"],
                    autodeleteexisting=settings["autodeleteexisting"],
                )
        if settings["automoveup"]:
            dirs = os.listdir(target)
            for dir_ in dirs:
                # if dir is a directory, it could just unzipped from a file
                #! it can also be a directory existing before the program runs
                if os.path.isdir(os.path.join(target, dir_)):
                    move_files_up(os.path.join(target, dir_))

    # if target is a file
    if os.path.isfile(target):
        unzipFileWith7z(
            target,
            settings["zip_excutible_path"],
            passwords=passwords,
            autodelete=settings["autodelete"],
            autodeleteexisting=settings["autodeleteexisting"],
        )
        if settings["automoveup"]:
            move_files_up(target)


################### MAIN FUNCTION ################################################################

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # run the main function
        if os.path.exists(sys.argv[1]):
            main(sys.argv[1],)
