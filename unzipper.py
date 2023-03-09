""" MultiLevelUnzipper - unzip multiple levels of zip files at once """
import os
import shutil
import subprocess

from last_level import check_if_is_last_level
from setting import log_msg


# get password list
def getPasswordList(dir_):
    """ get the password list from the passwords.txt file (under current directory and under users home directory), return a list of passwords """
    passwordList = [""]
    # check if the password file exists
    if not os.path.exists(os.path.join(dir_, "passwords.txt")):
        log_msg("passwords.txt not found", log_level=5)
    else:
        with open(os.path.join(dir_, "passwords.txt"), "r") as f:
            for line in f:
                passwordList.append(line.strip())
    # print info message
    log_msg(f"Found {len(passwordList):d} passwords in local passwords.txt", log_level=3)

    # global password is stored in ~/.passwords.txt
    if os.path.exists(os.path.join(os.path.expanduser("~"), ".passwords.txt")):
        with open(os.path.join(os.path.expanduser("~"), ".passwords.txt"), "r") as f:
            for line in f:
                passwordList.append(line.strip())

    log_msg(f"Found {len(passwordList):d} passwords in total", log_level=4)
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
        log_msg(f"File {file} does not exist", log_level=5)
        return False, lv

    # check if is a .lib, .dll or .exe file, if yes skip
    # TODO: maybe a temporary solution, need to find a way to unzip .lib files
    if file.endswith(".lib") or file.endswith(".dll") or file.endswith(".exe"):
        log_msg(f"File {file} is a .lib, .dll or .exe file, skipping...", log_level=5)
        return False, lv

    # check if the output directory already exists
    if os.path.exists(f"{file}lv{lv:d}"):
        if autodeleteexisting:
            log_msg(f"Output directory {file}lv{lv:d} already exists, deleting...", log_level=4)
            shutil.rmtree(f"{file}lv{lv:d}")
        else:
            log_msg(f"Output directory {file}lv{lv:d} already exists, skipping...", log_level=4)
            return False, lv

    # unzip without password
    # verify file is a a os.PathLike
    right_pass_found = False
    if not isinstance(file, os.PathLike) and not isinstance(file, str):
        raise TypeError(f"{file} must be a os.PathLike")

    log_msg(f"Unzipping {file} without password...", log_level=2)

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
        log_msg(
            f"Archive {file} is password protected, start to unzip with passwords...", log_level=2
        )
        shutil.rmtree(f"{file}lv{lv:d}", ignore_errors=True)
        has_archive = True
        password_protected = True
    if (
        result.returncode == 2
        and result.stderr.decode("utf-8", errors="replace").find("Cannot open the file as archive")
        != -1
    ):
        if lv == 0:
            log_msg(f'File "{file}" is not an archive', log_level=4)
        # remove the empty directory due to file is not an archive
        shutil.rmtree(f"{file}lv{lv:d}", ignore_errors=True)
        return False, lv
    if result.returncode == 0:
        log_msg(
            f"Archive {file} is not password protected, unzipped to {file}lv{lv:d}", log_level=3
        )
        right_pass_found = True
        has_archive = True
    elif password_protected is False:
        log_msg(f"Unknown error when unzipping {file}", log_level=5)
        log_msg(result.stderr.decode("utf-8", errors="replace"), log_level=5)
        return False, lv

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
                log_msg(
                    f"Correct password for {file} is {password}, unzipped to {file}lv{lv:d}",
                    log_level=3,
                )
                has_archive = True
                right_pass_found = True
                break

    # no password found for the file
    if not right_pass_found:
        log_msg(f"Cannot find the correct password for {file}", log_level=5)
        return False, lv

    if has_archive:
        # check if is the last level
        if check_if_is_last_level(f"{file}lv{lv:d}"):
            # the file just unzipped is a program, stop at this level
            return False, lv

        log_msg(
            f"Archive {file} has been unzipped to {file}lv{lv:d}, going to next level", log_level=3
        )
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
    log_msg(f"Moving files up in {dir_path}", log_level=3)

    if len(contents) == 1 and os.path.isdir(os.path.join(dir_path, contents[0])):
        subdir_path = os.path.join(dir_path, contents[0])
        if os.path.isdir(subdir_path):
            subdir_contents = os.listdir(subdir_path)
            for item in subdir_contents:
                shutil.move(os.path.join(subdir_path, item), dir_path)
            os.rmdir(subdir_path)
            move_files_up(dir_path)
